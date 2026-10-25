# 第1回 解答

## 演習

- 講座に固有の質問（宿題の3レベル）へのモデルの回答（要約でよい）：
  **未検証**。初回はuv未導入で停止した。現在はNix環境と依存導入・全テストが成功しているが、このセッションには `GEMINI_API_KEY` が未設定である。Gemini APIへのリクエストは送信されていないため、実際の回答はない。
  - 一般知識：「LoRAとは何ですか？」：未検証。
  - 講座固有：「AIE2026の講座の宿題にある「3レベル」とは何ですか？」：未検証。
- 用語集の正しい意味と比べて気づいたこと：
  `data/glossary.json` の `homework-levels` では、基礎は講義内容の確認、実装は自分でコードを書くこと、発展は調査や試行に当たる。どれか1つに取り組めばその回の宿題は完了し、原則として採点はしない。実際のモデル回答がないため、一致・不一致やハルシネーションの有無は判断できない。
- 表示できたトークン数（入力 / 出力）：
  実測は**未検証 / 未検証**。固定版SDKの `GenerateContentResponseUsageMetadata.prompt_token_count` と `candidates_token_count` を使う表示機能を実装した。メタデータ全体または片方の値が欠けた場合は「取得不可」、0の場合は0を表示する。対話モードの入力数には過去の履歴も含まれ、出力数は候補のトークン数である。
- 使用モデル：
  実際に呼び出したモデルはない。設定上の既定値は `gemini-3.5-flash-lite`。実行時は `AIE_MODEL` による上書きを含むモデル名を表示する。

## 宿題

- 取り組んだレベル：**実装**
- やったこと：
  - ローカル環境用に `flake.nix` を追加。`nix develop` でPython 3.12・uv・Git・GitHub CLIを用意し、`UV_PYTHON` でuvが使うPythonを指定する。依存パッケージは引き続き `uv sync --frozen` で導入する。Nixの構文解析・環境起動ともに成功し、生成した `flake.lock` でnixpkgsのリビジョンを固定した。
  - `app/ask.py` に `--chat` を追加。SDKの `client.chats.create(model=MODEL)` と `send_message()` を使い、同じセッションのuser・modelの発言を後続の質問に渡す。履歴はプロセス終了時に失われる。
  - 質問引数を渡す単発CLI、引数省略時の既定質問、`ask(question) -> str` を維持した。
  - 各応答の入力・出力トークン数を表示。本文がない場合は、その旨を表示する。
  - 空行は送信せず、`/exit`・`/quit`・EOF・Ctrl-Cで終了する。
  - APIエラーを日本語で表示する。対話中は入力を継続し、単発実行は終了コード1とする。APIのエラー詳細は認証情報の混入を避けるため表示しない。クライアントは終了時に閉じる。
  - `tests/test_ask.py` を追加。実SDKの通信部分だけをモックして、2回目の送信内容にuser・model双方の履歴が入ること、エラーになった質問が成功済み履歴を壊さないこと、単発質問が履歴を共有しないことを検証する。トークン数、欠損値、0、空の応答、終了操作、CLI互換性、APIエラー、キー未設定も対象とした。既存テストは変更していない。
  - SDKの型・会話APIは固定版のソースで確認した：
    [types.py](https://github.com/googleapis/python-genai/blob/v2.31.0/google/genai/types.py)、
    [chats.py](https://github.com/googleapis/python-genai/blob/v2.31.0/google/genai/chats.py)。

- 実行手順：

  Python 3.12とuvが使える環境で、再発行したAPIキーを環境変数 `GEMINI_API_KEY` に設定してから実行する。キーをコードや実行記録に書かない。

  ```bash
  nix develop
  uv sync --frozen
  uv run pytest -q
  uv run python -m app.ask "LoRAとは何ですか？"
  uv run python -m app.ask "AIE2026の講座の宿題にある「3レベル」とは何ですか？"
  uv run python -m app.ask --chat
  ```

  対話モードで順に入力する：

  ```text
  私の好きなプログラミング言語はRustです。覚えてください。
  私の好きなプログラミング言語は何ですか？
  /exit
  ```

  その後、履歴のない単発実行と比較する：

  ```bash
  uv run python -m app.ask "私の好きなプログラミング言語は何ですか？"
  ```

- 結果：
  - 環境：`nix develop` が成功。Python 3.12.15・uv 0.13.4を使用した。`flake.lock` を生成して固定した。
  - 依存導入：`nix develop --command uv sync --frozen` が成功（終了コード0）。講座の固定依存76パッケージを導入した。
  - 全テスト：`nix develop --command uv run pytest -q` が成功（終了コード0）。**37 passed in 3.80s**。既存11件・追加26件が成功し、会話履歴、単発互換性、トークン表示、メタデータ欠損、終了操作、APIエラー処理を自動検証した。
  - 構文チェック：Pythonコード・Nix式の構文解析と `git diff --check` が成功した。
  - 初回はuv未導入とsandbox内のNix daemon・ネットワーク制限で失敗したが、許可されたsandbox外の実行で依存導入とテストまで完了した。
  - API検証：指定の2質問、Rustを覚える連続質問、単発実行との回答比較はいずれも**未検証**。このセッションには `GEMINI_API_KEY` が設定されていない。モデル回答・実測トークン数は取得していない。
  - Git：開始時は対象リポジトリがなく、GitHub連携で取得したスナップショットから復元した。過去のGitオブジェクトが欠けてNix起動時にエラーになったため、forkから履歴を取得して修復した。`git rev-parse --is-shallow-repository` はfalse、`git fsck --connectivity-only` は成功。originは自分のforkのみで、作業ブランチは `lec01`。

- 気づき・疑問：
  - 会話履歴の検証では、固定の「Rust」という回答をモックするだけでは不十分。実SDKが次の送信に過去のuser・modelの内容を含めるかを確認する必要がある。
  - 会話が長くなると再送する履歴も増えるため、入力トークン数の変化を観察したい。
  - 履歴の実装が正しくても、実際のモデルが過去の発言を参照して答えるかは別途確認が必要である。

- 残る検証：
  依存導入と全テストは完了した。`GEMINI_API_KEY` を環境変数として渡し、上記API検証の回答全文・モデル名・各回の入力/出力トークン数を追記する。Codexを使う場合は利用する環境のSecrets設定に `GEMINI_API_KEY` を登録して環境を再起動する。Codespacesを使う場合はGitHubのSettings → Codespaces → Secretsで同名のSecretを登録し、forkへのアクセスを許可して再起動する。
