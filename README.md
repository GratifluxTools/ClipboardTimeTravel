# Clipboard Time Travel

![Release](https://img.shields.io/github/v/release/GratifluxTools/ClipboardTimeTravel)
![License](https://img.shields.io/github/license/GratifluxTools/ClipboardTimeTravel)

[English](#english) | [日本語](#日本語)

---

## English

Clipboard Time Travel keeps a private, encrypted history of what you copy. You can find old text by keyword, optionally by meaning, and ask questions about your history with a local AI model through [Ollama](https://ollama.com). Nothing is sent to the cloud.

Supported platforms: **Windows** (full features) and **Linux** (clipboard history and search; no system tray).

### Contents
- [Features](#features-en)
- [Installation](#installation-en)
- [Quick start](#quick-start-en)
- [Using the app](#using-the-app-en)
- [Settings](#settings-en)
- [Privacy and security](#privacy-en)
- [Troubleshooting](#troubleshooting-en)
- [Build from source](#build-en)
- [License](#license-en)

<a id="features-en"></a>
### Features
- **Timeline** of everything you copy, with the time and the app it came from
- **Compact cards**: long entries are shortened; press *Expand* to read the full text
- **Keyword search** that works out of the box, plus optional **semantic search** (finds text by meaning)
- **Chat with your history** through a local Ollama model
- **Encrypted storage**: history is encrypted on disk
- **Retention**: automatically delete history after 1 day, 7 days, 30 days, 90 days, 1 year, or keep it forever
- **Exclusions**: copies from password managers and other apps you choose are never saved
- **Shortcut key** to bring the window up instantly (Windows)
- **System tray** with pause/resume of saving (Windows)
- **English and Japanese** interface
- **Update check** against the latest GitHub Release

<a id="installation-en"></a>
### Installation

**Windows**
1. Open the [Releases](https://github.com/GratifluxTools/ClipboardTimeTravel/releases) page and download the Windows zip.
2. Extract the zip to a folder you keep, for example `C:\Apps\ClipboardTimeTravel`.
3. Run `ClipboardTimeTravel.exe`.

Because the app is not code-signed yet, Windows SmartScreen may show a warning. Choose *More info* → *Run anyway* if you trust the download.

**Linux**
1. Download the Linux zip from the Releases page and extract it.
2. Install a clipboard tool: `xclip` (X11) or `wl-clipboard` (Wayland).
3. Run the `ClipboardTimeTravel` executable inside the extracted folder.

To get the source application name on Linux, install `xdotool` (X11 only).

<a id="quick-start-en"></a>
### Quick start
1. Launch the app and copy some text anywhere. It appears in the **Timeline** tab within a moment.
2. Go to **Search & Chat**, type a few words you remember, and press Enter.
3. Open **Settings** and choose how long to keep history and which apps to exclude.

<a id="using-the-app-en"></a>
### Using the app

**Timeline**
- Each card shows the time, the source app, and the beginning of the copied text.
- Press the arrow button to *expand* a card and see the full text and window title. Press it again to collapse.
- *Copy* puts the text back on the clipboard. The app will not save it a second time.
- *Delete* removes one entry permanently.

**Search & Chat**
- *Keyword search*: type words or phrases. Results are ranked by how many of your terms match. Japanese text is matched by character pairs, so you can search without spaces.
  - Examples: `last week's address`, `meeting notes`, `flight number`
- *Semantic search*: if a model is installed (see Settings), results are ranked by meaning, so `where I live` can find an address you saved.
- *Chat*: ask a question in plain language, for example "Did I save a note about the hotel booking?" The AI answers using your most relevant entries. Requires Ollama (see below).

**Choosing an Ollama model**
1. Install [Ollama](https://ollama.com) and start it.
2. Download a model, for example: `ollama pull llama3.2`
3. In **Settings**, press *Reload models* and choose the model from the dropdown.
4. Set *History items sent to Ollama* (default 15). Higher values give the AI more context but make answers slower.

If Ollama is not running, chat shows a message and the most relevant history entries instead.

<a id="settings-en"></a>
### Settings
| Setting | What it does |
|---|---|
| Save clipboard history | Turn saving on or off. The tray menu has the same switch. |
| Keep history for | Entries older than this are deleted automatically. *Forever* keeps everything. |
| Language | English or Japanese. Restart the app to apply. |
| Start with Windows | Launch the app when you sign in to Windows. |
| Closing the window hides it to the tray | When on, the close button keeps the app running in the tray. |
| Shortcut key | Press *Set by key press*, then your combination, to bring the window forward. |
| Excluded apps | Comma-separated names. Copies from apps whose program name contains one of these are not saved. Defaults include common password managers. |
| Use semantic search | Requires a model folder with `tokenizer.json` and `model.onnx`. Restart after changing. |
| Ollama URL / model / items sent | Where Ollama runs, which model to use, and how many entries to send. |
| Check for updates | Compares your version with the latest release and opens the download page if there is a newer one. |

**Tray menu (Windows)**: *Open*, *Save history* (on/off), and *Quit*.

**Notes**
- Copies of 20,000 characters or more are stored truncated.
- Copying the same text as the most recent entry does not create a duplicate.
- *Delete all history* in Settings removes every entry at once.

<a id="privacy-en"></a>
### Privacy and security
- History is encrypted before it is written to disk. On Windows the encryption key is protected by your Windows user account (DPAPI). On other systems the key file is readable only by your user account.
- Your clipboard content is never uploaded. The only network requests are the update check (to GitHub) and, if you use it, the connection to Ollama on your own computer.
- Data is stored in:
  - Windows: `%APPDATA%\ClipboardTimeTravel`
  - Linux: `~/.clipboard_time_travel`
- Deleting the data folder removes all history and the encryption key.

<a id="troubleshooting-en"></a>
### Troubleshooting
- **Nothing is being saved**: check that *Save clipboard history* is on, and that the source app is not in *Excluded apps*.
- **Clipboard not captured on Linux**: make sure `xclip` or `wl-clipboard` is installed and that you are in a graphical session.
- **Chat says it cannot get an answer**: confirm that Ollama is running and that the model is downloaded. Use *Reload models* to check.
- **Language did not change**: restart the app after changing the language.
- **Shortcut key does nothing**: it works on Windows only, and the combination must not be used by another app.
- **Update check fails**: confirm you have internet access. The check contacts `api.github.com`.

<a id="build-en"></a>
### Build from source
```bash
pip install -r requirements.txt
python main.py
```
Releases are built with GitHub Actions (`.github/workflows/build.yml`). Run the `Build` workflow manually to produce test artifacts. Publishing a Release with a tag such as `v0.2.0` builds the app with that version and attaches the zip files to the Release.

<a id="license-en"></a>
### License
This project is released under the [MIT License](LICENSE).

---

## 日本語

Clipboard Time Travel は、コピーした内容を暗号化して手元に保存するクリップボード履歴アプリです。キーワードで過去のテキストを探せるほか、必要に応じて意味で探すこともできます。[Ollama](https://ollama.com) を使えば、ローカルのAIモデルに履歴について質問できます。データをクラウドへ送信することはありません。

対応環境：**Windows**（すべての機能）、**Linux**（履歴の保存と検索。システムトレイはなし）

### 目次
- [機能](#features-ja)
- [インストール](#installation-ja)
- [はじめに](#quick-start-ja)
- [使い方](#using-the-app-ja)
- [設定](#settings-ja)
- [プライバシーとセキュリティ](#privacy-ja)
- [トラブルシューティング](#troubleshooting-ja)
- [ソースからビルド](#build-ja)
- [ライセンス](#license-ja)

<a id="features-ja"></a>
### 機能
- **タイムライン**：コピーした内容を時刻とコピー元アプリ付きで一覧表示
- **省スペースのカード**：長い内容は短く表示し、「表示を拡大」で全文を読めます
- **キーワード検索**：追加のダウンロードなしで使えます。任意で**意味検索**（意味が近いものを探す）も利用できます
- **履歴へのチャット**：ローカルの Ollama モデルで質問に答えます
- **暗号化保存**：履歴はディスク上で暗号化されます
- **保存期間**：1日・7日・30日・90日・1年・無期限から選び、古い履歴を自動で削除
- **除外設定**：パスワードマネージャーなど、指定したアプリからのコピーは保存しません
- **ショートカットキー**：ウィンドウを素早く前面に出せます（Windows）
- **システムトレイ**：履歴保存のオン／オフをトレイから切り替えられます（Windows）
- **英語・日本語**の表示に対応
- **更新確認**：GitHub の最新リリースと比較します

<a id="installation-ja"></a>
### インストール

**Windows**
1. [Releases](https://github.com/GratifluxTools/ClipboardTimeTravel/releases) ページから Windows 用の zip をダウンロードします。
2. zip を展開します（例：`C:\Apps\ClipboardTimeTravel`）。
3. `ClipboardTimeTravel.exe` を起動します。

現時点ではコード署名をしていないため、Windows の SmartScreen が警告を出すことがあります。配布元を信頼できる場合は「詳細情報」→「実行」を選んでください。

**Linux**
1. Releases ページから Linux 用の zip をダウンロードし、展開します。
2. クリップボード用のツールを入れます：`xclip`（X11）または `wl-clipboard`（Wayland）。
3. 展開したフォルダ内の `ClipboardTimeTravel` を実行します。

Linux でコピー元アプリ名を取得するには `xdotool` が必要です（X11 のみ）。

<a id="quick-start-ja"></a>
### はじめに
1. アプリを起動し、どこかでテキストをコピーします。すぐに「タイムライン」タブに表示されます。
2. 「検索・チャット」タブで、覚えている言葉を入力して Enter を押します。
3. 「設定」で、履歴の保存期間と除外するアプリを決めます。

<a id="using-the-app-ja"></a>
### 使い方

**タイムライン**
- 各カードには、時刻、コピー元アプリ、コピーした内容の冒頭が表示されます。
- 矢印ボタンで「表示を拡大」すると、全文とウィンドウタイトルが見られます。もう一度押すと縮小します。
- 「コピー」で、その内容をクリップボードに戻せます。同じ内容が二重に保存されることはありません。
- 「削除」で、その履歴を完全に消せます。

**検索・チャット**
- **キーワード検索**：言葉やフレーズを入力します。一致する語の数が多い順に並びます。日本語は2文字単位で照合するため、スペースを入れずに検索できます。
  - 例：`先週の住所`、`会議のメモ`、`便名`
- **意味検索**：モデルを入れている場合（設定を参照）、意味の近さで並びます。たとえば「住んでいるところ」で住所の履歴を探せます。
- **チャット**：「ホテルの予約のメモはあったっけ？」のように、普通の言葉で質問します。関連度の高い履歴をもとにAIが答えます。Ollama が必要です（下記）。

**Ollama のモデルの選び方**
1. [Ollama](https://ollama.com) をインストールして起動します。
2. モデルを取得します。例：`ollama pull llama3.2`
3. 「設定」で「モデル一覧を更新」を押し、プルダウンからモデルを選びます。
4. 「Ollamaへ送る履歴の件数」（既定は15件）を設定します。多いほどAIの参考情報は増えますが、回答は遅くなります。

Ollama が起動していない場合、チャットでは案内メッセージと、関連度の高い履歴を表示します。

<a id="settings-ja"></a>
### 設定
| 項目 | 内容 |
|---|---|
| クリップボード履歴を保存 | 保存のオン／オフ。トレイメニューでも切り替えられます。 |
| 保存期間 | この期間より古い履歴は自動で削除されます。「無期限」なら削除しません。 |
| 言語 | 英語または日本語。反映には再起動が必要です。 |
| Windows起動時に自動実行 | Windows にサインインした時にアプリを起動します。 |
| 閉じるボタンでトレイに格納する | 有効にすると、閉じるボタンでアプリがトレイに残ります。 |
| ショートカットキー | 「キー入力で設定」を押してから組み合わせを押すと、ウィンドウを前面に出せます。 |
| 除外するアプリ | カンマ区切りで指定します。プログラム名にこの文字列を含むアプリからのコピーは保存しません。既定では代表的なパスワードマネージャーが入っています。 |
| 意味検索を使う | `tokenizer.json` と `model.onnx` を入れたフォルダが必要です。変更後は再起動します。 |
| Ollama の URL・モデル・送信件数 | Ollama の場所、使うモデル、送る履歴の件数。 |
| 更新を確認 | 現在のバージョンと最新リリースを比べ、新しいものがあればダウンロードページを開きます。 |

**トレイメニュー（Windows）**：「開く」「履歴を保存」（オン／オフ）「終了」

**補足**
- 20,000文字以上のコピーは、先頭部分だけが保存されます。
- 直前の履歴と同じ内容は、二重に保存されません。
- 「設定」の「全履歴を削除」を押すと、すべての履歴を一度に消去します。

<a id="privacy-ja"></a>
### プライバシーとセキュリティ
- 履歴はディスクに書き込む前に暗号化されます。Windows では、暗号化キーを Windows のユーザーアカウントで保護します（DPAPI）。ほかの OS では、鍵ファイルはユーザー本人だけが読める権限で保存されます。
- クリップボードの内容がアップロードされることはありません。ネットワーク通信は、更新確認（GitHub への問い合わせ）と、使う場合の自分のPC上の Ollama への接続だけです。
- データの保存先：
  - Windows：`%APPDATA%\ClipboardTimeTravel`
  - Linux：`~/.clipboard_time_travel`
- データフォルダを削除すると、すべての履歴と暗号化キーが消えます。

<a id="troubleshooting-ja"></a>
### トラブルシューティング
- **保存されない**：「クリップボード履歴を保存」がオンか確認し、コピー元アプリが「除外するアプリ」に入っていないか確認してください。
- **Linux でコピーを取得できない**：`xclip` または `wl-clipboard` が入っているか、グラフィカルなセッションで起動しているか確認してください。
- **チャットで回答を取得できない**：Ollama が起動していて、モデルを取得済みか確認してください。「モデル一覧を更新」で確認できます。
- **言語が変わらない**：言語を変えたあと、アプリを再起動してください。
- **ショートカットキーが効かない**：Windows でのみ動作します。ほかのアプリが同じ組み合わせを使っていないか確認してください。
- **更新確認に失敗する**：インターネットに接続できているか確認してください。`api.github.com` に問い合わせます。

<a id="build-ja"></a>
### ソースからビルド
```bash
pip install -r requirements.txt
python main.py
```
リリースは GitHub Actions（`.github/workflows/build.yml`）でビルドされます。`Build` ワークフローを手動実行すると、テスト用の成果物が作られます。`v0.2.0` のようなタグで Release を公開すると、そのバージョンでビルドされ、zip が Release に添付されます。

<a id="license-ja"></a>
### ライセンス
本プロジェクトは [MIT License](LICENSE) のもとで公開されています。
