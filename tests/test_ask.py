"""第1回CLI: 実SDKの会話管理を通し、通信部分だけをモックする。"""

import sys
from unittest.mock import Mock

import pytest
from google import genai
from google.genai import errors, types

from app import ask


def reply(text="回答", usage=None):
    return types.GenerateContentResponse(
        candidates=[types.Candidate(
            content=types.Content(role="model", parts=[types.Part(text=text)]),
            finish_reason="STOP",
        )],
        usage_metadata=usage,
    )


@pytest.fixture
def client(monkeypatch):
    # キーはテスト用のダミー。ネットワークは generate_content を置換して遮断する。
    real_client = genai.Client(api_key="test-key")
    generate = Mock(return_value=reply())
    monkeypatch.setattr(real_client.models, "generate_content", generate)
    monkeypatch.setattr(ask, "get_api_key", lambda: "test-key")
    monkeypatch.setattr(ask.genai, "Client", Mock(return_value=real_client))
    return real_client, generate


def inputs(monkeypatch, values):
    values = iter(values)
    def read(_):
        value = next(values)
        if isinstance(value, BaseException):
            raise value
        return value
    monkeypatch.setattr("builtins.input", read)


@pytest.mark.parametrize("usage, expected", [
    (None, "入力: 取得不可 / 出力: 取得不可"),
    (types.GenerateContentResponseUsageMetadata(), "入力: 取得不可 / 出力: 取得不可"),
    (types.GenerateContentResponseUsageMetadata(prompt_token_count=12, candidates_token_count=4),
     "入力: 12 / 出力: 4"),
    (types.GenerateContentResponseUsageMetadata(prompt_token_count=0, candidates_token_count=0),
     "入力: 0 / 出力: 0"),
    (types.GenerateContentResponseUsageMetadata(prompt_token_count=8),
     "入力: 8 / 出力: 取得不可"),
])
def test_usage(usage, expected, capsys):
    ask.print_usage(reply(usage=usage))
    assert expected in capsys.readouterr().out


def test_single_question(client, capsys):
    real_client, generate = client
    assert ask.ask("LoRAとは？") == "回答"
    generate.assert_called_once_with(model=ask.MODEL, contents="LoRAとは？")
    assert "[tokens]" in capsys.readouterr().out


def test_chat_reuses_user_and_model_history(client, monkeypatch, capsys):
    _, generate = client
    generate.side_effect = [reply("Rustですね。"), reply("Rustです。")]
    inputs(monkeypatch, ["好きな言語はRustです", "好きな言語は？", "/exit"])
    ask.chat()
    calls = generate.call_args_list
    assert len(calls) == 2
    # 実SDKが次のリクエストへ以前のuserとmodelを送っていることを確認。
    history = calls[1].kwargs["contents"]
    assert [c.role for c in history] == ["user", "model", "user"]
    assert [c.parts[0].text for c in history] == [
        "好きな言語はRustです", "Rustですね。", "好きな言語は？",
    ]
    assert capsys.readouterr().out.count("[tokens]") == 2


def test_single_questions_do_not_share_history(client):
    _, generate = client
    ask.ask("好きな言語はRustです")
    ask.ask("好きな言語は？")
    assert generate.call_args_list[1].kwargs["contents"] == "好きな言語は？"


@pytest.mark.parametrize("ending", ["/exit", "/quit", EOFError(), KeyboardInterrupt()])
def test_chat_exit_and_blank_input(client, monkeypatch, ending):
    _, generate = client
    inputs(monkeypatch, ["  ", ending])
    ask.chat()
    generate.assert_not_called()


def test_chat_api_error_keeps_successful_history(client, monkeypatch, capsys):
    _, generate = client
    generate.side_effect = [
        reply("Rustですね。"), errors.APIError(429, {"message": "private-detail"}),
        reply("Rustです。"),
    ]
    inputs(monkeypatch, ["Rustを覚えて", "失敗する質問", "好きな言語は？", "/quit"])
    ask.chat()
    history = generate.call_args_list[2].kwargs["contents"]
    assert [c.parts[0].text for c in history] == [
        "Rustを覚えて", "Rustですね。", "好きな言語は？",
    ]
    out = capsys.readouterr().out
    assert "レート制限" in out
    assert "private-detail" not in out


def test_empty_response(capsys):
    assert "回答テキストを取得できません" in ask.response_text(
        types.GenerateContentResponse()
    )
    assert "取得不可" in capsys.readouterr().out


@pytest.mark.parametrize("argv, question", [
    (["ask"], ask.DEFAULT_QUESTION),
    (["ask", "LoRAとは？"], "LoRAとは？"),
])
def test_single_cli(monkeypatch, argv, question):
    monkeypatch.setattr(sys, "argv", argv)
    single = Mock(return_value="回答")
    monkeypatch.setattr(ask, "ask", single)
    ask.main()
    single.assert_called_once_with(question)


def test_chat_cli(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["ask", "--chat"])
    chat = Mock()
    monkeypatch.setattr(ask, "chat", chat)
    ask.main()
    chat.assert_called_once_with()


def test_conflicting_cli_arguments(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["ask", "--chat", "質問"])
    with pytest.raises(SystemExit) as exc:
        ask.main()
    assert exc.value.code == 2


@pytest.mark.parametrize("code", [400, 401, 403, 404, 429, 500, 503])
def test_single_api_error(client, monkeypatch, capsys, code):
    _, generate = client
    generate.side_effect = errors.APIError(code, {"message": "private-detail"})
    monkeypatch.setattr(sys, "argv", ["ask", "質問"])
    with pytest.raises(SystemExit) as exc:
        ask.main()
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert ask.api_error_message(code) in out
    assert "private-detail" not in out


def test_missing_key(monkeypatch):
    from app.config import get_api_key
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(SystemExit, match="GEMINI_API_KEY"):
        get_api_key()
