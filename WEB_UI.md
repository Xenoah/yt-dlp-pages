# yt-dlp Local

yt-dlpを日本語のWeb画面から操作する、PC用のローカルツールです。
画面の配信、yt-dlp / FFmpegの実行、ファイルの保存をすべて同じPCで行います。
**GitHub Pages・外部ホスティング・フロントエンドのビルドは不要です。**

## Windowsですぐ使う

1. Python 3.10以降を [python.org](https://www.python.org/downloads/) から導入します。
2. [リポジトリのZIP](https://github.com/Xenoah/yt-dlp-pages/archive/refs/heads/master.zip) をダウンロードし、**フォルダー全体を展開**します。clone済みなら `git pull` で更新します。
3. 展開したフォルダーの先頭にある **`start-windows.cmd`** を実行します。
4. 初回は専用のPython環境と依存パッケージを準備します。その後、ブラウザで `http://127.0.0.1:9731/` が開いて自動接続します。
5. URLを貼り付け、形式・画質を選んで「ダウンロード開始」を押します。

利用中は起動ウィンドウを開いたままにしてください。**Ctrl+Cで終了**します。
`docs/index.html` を直接開く必要はありません。ブラウザが開かない場合は、起動ウィンドウの `Open:` のURLをコピーして開いてください。

**動画の結合・音声変換・メタデータ埋め込みにはFFmpegが必要です。**
Windows PowerShellから導入できます。YouTube用のJavaScript処理にはDenoを推奨します。

```powershell
winget install --id Gyan.FFmpeg -e
winget install --id DenoLand.Deno -e
```

導入後は起動ウィンドウを閉じ、再度起動してください。
初回のパッケージ導入と、外部サイトからのダウンロードにはインターネット接続が必要です。

## macOS / Linux

Python 3.10以降、FFmpeg、DenoまたはNode.jsを用意します。
macOSでHomebrewを利用している場合は `brew install python ffmpeg deno` で導入できます。
Linuxではディストリビューションのパッケージ等を利用してください。

展開したフォルダーで実行します。

```sh
sh start-macos.command
```

macOSは `start-macos.command` のダブルクリックでも起動できます。
初回は `docs/bridge/.venv` に専用環境を作ります。Linuxでvenvが見つからない場合は、OSのPython venvパッケージを導入してください。

## 起動オプション

フォルダーの先頭で実行します。Windows PowerShellの場合：

```powershell
.\start-windows.cmd --output "D:/Videos"
.\start-windows.cmd --port 9732
.\start-windows.cmd --no-open
```

macOS / Linuxの場合：

```sh
sh start-macos.command --output "$HOME/Videos"
sh start-macos.command --port 9732
sh start-macos.command --no-open
```

- `--output`：保存先を変更します。
- `--port`：使用中のポートを避けて起動します。開く画面と接続先も同じポートに変わります。
- `--no-open`：ブラウザを自動起動せず、接続用URLだけを表示します。
- 旧版の `--local` は互換性のため受け付けますが、現在は常にローカル起動です。

Python環境を自分で用意する場合：

```sh
python -m pip install -e '.[default]'
python docs/bridge/bridge.py
```

## 機能

- 日本語UI、動画（MP4 / MKV / WebM）、音声（MP3 / M4A / FLAC / WAV / Opus / 元形式）
- 最高画質 / 4K / 1440p / 1080p / 720p / 480pの解像度上限
- URLの一括投入（20件まで）、逐次キュー、進捗・速度・残り時間
- 中止、再試行、実行ログ、完了ファイルの保存
- 先頭URLの動画情報・サムネイル取得
- 字幕・自動字幕、サムネイルの別ファイル保存、メタデータ埋め込み
- プレイリスト（最大100件、初期値20件、標準はOFF）
- PowerShell / Bashコマンドの生成とコピー

フロントエンドに外部CDN、広告、アクセス解析、GitHubトークンは使いません。
Node.jsは画面のビルドには不要です。Deno / Node.jsはyt-dlpが動画サイトのJavaScriptを処理するために利用します。

## 保存・再接続

- 標準保存先：`~/Downloads/yt-dlp-pages/<job-id>/`。以前の保存先を引き継ぎます。
- ファイルはダウンロード完了時点でPCに保存されています。キューの保存ボタンはブラウザ経由で別途保存したい場合に使えます。
- 接続キーは起動ごとに生成します。起動用URLから読み込んだキーはアドレスバーから直ちに取り除き、タブのメモリにのみ保持します。
- 再読み込み時は、起動ウィンドウの `Open:` のURLを開き直すか、接続設定に `Connection key:` を入力してください。
- 設定のみlocalStorageに保存します。URL・接続キー・履歴はブラウザの永続ストレージに保存しません。
- 履歴は実行中のメモリ内に最大約200件保持します。終了すると履歴は消えますが、ファイルは残ります。
- ブラウザのタブを閉じても処理は継続します。起動ウィンドウを終了すると進行中の処理も停止します。

## 接続できないとき

- **起動できない**：Python 3.10以降が入っているか、ZIP全体を展開したか確認してください。初回のパッケージ導入にはネット接続が必要です。
- **ポートが使用中**：古い起動ウィンドウを閉じるか、`--port 9732` で起動します。
- **再読み込み後に未接続**：起動ウィンドウの `Open:` のURLを開き直します。
- **FFmpegが未導入**：上記の手順で導入して再起動します。未導入時は音声の「変換しない」かつメタデータOFFのみ実行できます。
- **画面が見つからない**：起動ファイルや `bridge.py` だけを移動せず、フォルダー全体を同じ構成のまま配置します。

サーバーは `127.0.0.1` だけで待ち受けます。操作APIは接続キーとHost / Originを確認し、同じローカルサーバー以外のWebサイトからの操作を拒否します。
スマートフォンや別PCからの利用、外部への公開、Cookie送信、ログイン代行、任意の追加コマンドには対応していません。

## 更新と配布

このリポジトリをclone・ZIP展開した場合、同梱の `yt_dlp` を優先して実行します。
更新は `git pull` または新しいZIPへの置き換えで行います。
yt-dlp本体のコードはこのUIのために変更していません。

小さな起動セットだけを配布する場合、次のコマンドで `dist/yt-dlp-local.zip` を作れます。
これは**配布用の任意操作**で、通常の起動にビルド・パッケージ生成は不要です。

```sh
python devscripts/package_local_ui.py
```

このZIPには画面・起動スクリプトを同梱し、yt-dlp本体は初回起動時にpipで導入します。
単体ZIPのyt-dlpを更新する場合は、展開先で次を実行します。

```powershell
.venv\Scripts\python.exe -m pip install -U "yt-dlp[default]"
```

macOS / Linuxでは `.venv/bin/python` に読み替えてください。
Pagesへの公開ワークフローは削除しました。GitHub ActionsはWindows / LinuxでローカルUIのテストだけを行います。

## 開発時の検証

```sh
python -m unittest discover -s web-tests -p 'test_*.py' -v
node --test web-tests/core.test.mjs
node --check docs/app.js
```

起動URL、ローカルHTTP配信、認証・Origin / Host制限、キュー、中止、ファイル制限、コマンド生成を検証します。
ブラウザのレンダリングや外部ホスティングは必要ありません。

取得できる形式・画質は配信元に依存します。サイトの変更、ログイン、地域制限、DRMなどによって取得できない場合があります。
自分のコンテンツや保存を許可されたメディアに使用してください。
このUIは本リポジトリのLICENSEに従います。yt-dlp本体の仕様は [README](README.md) を参照してください。
