# Clipboard Time Travel

クリップボードの履歴を保存し、キーワードまたは（任意で）意味検索・ローカルAIチャットで振り返れる Flet 製アプリです。
Windows / Linux に対応します。

## 特徴
- 履歴はすべて暗号化して保存（Windowsは DPAPI でユーザー単位に保護、他OSはファイル権限 0600）
- 保存期間を 1日 / 7日 / 30日 / 90日 / 1年 / 無期限 から選択
- 既定は軽量なキーワード検索（追加ダウンロードなし）
- 任意: ONNX 多言語MiniLM による意味検索、ローカル Ollama によるチャット（有料APIは不使用）
- パスワードマネージャーなど除外アプリからのコピーは保存しない
- Windows: グローバルホットキーでウィンドウ呼び出し、スタートアップ登録

## ローカルで実行
```bash
pip install -r requirements.txt
python main.py
```

## ビルド（GitHub Actions）
- リポジトリの Actions から `Build` を手動実行（workflow_dispatch）
- Release を公開すると自動でビルドし、zip を Release に添付
- Windows と Linux の zip を Release に添付します
- 成果物は Actions の Artifacts からも取得可能

## 意味検索を有効にする（任意）
`tokenizer.json` と `model.onnx`（paraphrase-multilingual-MiniLM-L12-v2 の ONNX 版）を同じフォルダに置き、
設定で「意味検索を使う」と「モデルフォルダ」を指定して再起動します。
必要ならば `pyproject.toml` / `requirements.txt` に `numpy`, `onnxruntime`, `tokenizers` を追加してください（アプリサイズが増えます）。

## チャットを有効にする（任意）
ローカルに [Ollama](https://ollama.com) を入れ、`ollama pull llama3.2` でモデルを取得します。
接続できない場合は、関連する履歴を一覧表示する動作になります。

## 制限事項
- Linux では pyperclip の都合で `xclip`（X11）または `wl-clipboard`（Wayland）が必要です
- コピー元アプリ名の取得は Windows と Linux（xdotool）のみ対応です
- ホットキーは Windows のみ対応です
- 意味検索の設定変更はアプリ再起動後に反映されます
