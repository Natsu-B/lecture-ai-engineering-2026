"""第1回: 素のLLMに質問するスクリプト。

使い方:
    uv run python -m app.ask "LoRAとは何ですか？"
    uv run python -m app.ask            # 質問を省略すると、講座に固有の質問をする
    uv run python -m app.ask --chat     # /exit、/quit、EOF、Ctrl-C で終了

単発モードはツールも会話履歴も持たない「素の」呼び出し。
対話モードは同じセッションの user / model の履歴をSDKで保持する。
講座に固有のことを聞くと、「分からない」と答えるか、一般論でもっともらしく答える
（講座の実際とは違う）ことを確かめよう。
（第3回で、用語集を検索できるエージェントにして改善する）
"""

import argparse

from google import genai
from google.genai import errors
from google.genai import types

from app.config import MODEL, api_error_message, get_api_key

# 講座に固有の質問。正しい答えは data/glossary.json の homework-levels にある
DEFAULT_QUESTION = "AIE2026の講座の宿題にある「3レベル」とは何ですか？"


def print_usage(response: types.GenerateContentResponse) -> None:
    """今回のリクエストの使用量。欠損と実測の0を区別する。"""
    usage = response.usage_metadata
    prompt = usage.prompt_token_count if usage else None
    output = usage.candidates_token_count if usage else None
    print(f"[tokens] 入力: {prompt if prompt is not None else '取得不可'} / "
          f"出力: {output if output is not None else '取得不可'}")


def response_text(response: types.GenerateContentResponse) -> str:
    print_usage(response)
    return response.text or "回答テキストを取得できませんでした。"


def ask(question: str) -> str:
    with genai.Client(api_key=get_api_key()) as client:
        response = client.models.generate_content(model=MODEL, contents=question)
        return response_text(response)


def chat() -> None:
    """履歴はこの呼び出しの間だけ保持し、APIエラーの後も入力を受け付ける。"""
    with genai.Client(api_key=get_api_key()) as client:
        session = client.chats.create(model=MODEL)
        print("対話モード（/exit または /quit で終了）")
        while True:
            try:
                question = input("あなた> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n対話を終了します。")
                return
            if question in {"/exit", "/quit"}:
                print("対話を終了します。")
                return
            if not question:
                continue
            try:
                print(response_text(session.send_message(question)))
            except errors.APIError as e:
                # レスポンスの詳細には認証情報が含まれ得るため表示しない。
                print(api_error_message(e.code))


def main() -> None:
    parser = argparse.ArgumentParser(description="素のLLMに質問する")
    parser.add_argument("question", nargs="?")
    parser.add_argument("--chat", action="store_true", help="会話履歴を保持して連続質問する")
    args = parser.parse_args()
    if args.chat and args.question is not None:
        parser.error("--chat と単発の質問は同時に指定できません")

    print(f"[model] {MODEL}")
    try:
        if args.chat:
            chat()
        else:
            question = args.question if args.question is not None else DEFAULT_QUESTION
            print(f"[質問] {question}\n")
            print(ask(question))
    except errors.APIError as e:
        print(api_error_message(e.code))
        raise SystemExit(1)
    except KeyboardInterrupt:
        print("\n対話を終了します。")


if __name__ == "__main__":
    main()
