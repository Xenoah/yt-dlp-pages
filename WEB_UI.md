# yt-dlp Pages

yt-dlpを日本語のWeb画面から操作する、GitHub Pages向けのUIです。

**操作画面:** https://xenoah.github.io/yt-dlp-pages/

GitHub Pagesは静的ホスティングのため、Python製のyt-dlpを実行できません。
このUIは **Pagesの画面 → 同じPCのローカルブリッジ → yt-dlp / FFmpeg** の構成で動作します。
ブラウザだけで完結するダウンローダーではありません。動画の処理・保存は利用者のPCで行います。

## 機能

- 日本語UI、デスクトップ・狭い画面への対応
- 動画（MP4 / MKV / WebM）、音声（MP3 / M4A / FLAC / WAV / Opus / 元形式）
- 最高画質 / 4K / 1440p / 1080p / 720p / 480pの解像度上限
- URLの一括投入（20件まで）、逐次キュー、進捗・速度・残り時間
- 中止、再試行、実行ログ、完了ファイルの保存
- 動画情報・サムネイルの取得（先頭URL）
- 字幕・自動字幕の別ファイル保存、メタデータ、サムネイル保存
- プレイリスト（最大100件、初期値20件、標準はOFF）
- 接続不要のPowerShell / Bashコマンド生成
- ブリッジは127.0.0.1に限定、接続キー認証、許可Originの照合
- フロントエンドに外部CDN、広告、アクセス解析、GitHubトークンは不要

## Windowsで使う

1. Python 3.10以降を [python.org](https://www.python.org/downloads/) から導入します。
2. 操作画面の「起動セットをダウンロード」を押してZIPを展開します。
3. `start-windows.cmd` を実行。初回は専用の `.venv` に `yt-dlp[default]` を導入します。
4. 自動で開いたページの「接続する」を押します。必要に応じてブラウザのローカルネットワークへのアクセスを許可します。
5. URLを貼り付けて形式を選び、「ダウンロード開始」を押します。

**FFmpegは別途必要です。** Windows PowerShellで導入できます。

```powershell
winget install --id Gyan.FFmpeg -e
winget install --id DenoLand.Deno -e
```

DenoまたはNode.jsはYouTubeのJavaScript処理に利用します。導入後は起動ウィンドウを閉じ、再度起動してください。
起動ウィンドウは利用中開いたままにします。Ctrl+Cで停止します。

## macOS / Linux

Python 3.10以降、FFmpeg、DenoまたはNode.jsを用意し、展開したフォルダーで次を実行します。

```sh
sh start-macos.command
```

macOSでHomebrewを利用している場合：`brew install python ffmpeg deno`。
Linuxではディストリビューションのパッケージ等で用意してください。

## 保存・接続について

- 標準保存先：`~/Downloads/yt-dlp-pages/<job-id>/`。
- ファイルはダウンロード完了時点でPCに保存されています。キューの保存ボタンはブラウザで別途保存する場合に使用します。
- 字幕・サムネイルもキューから保存できます。取得できる形式・解像度は元サイト次第です。
- FFmpegがない場合は、音声の「変換しない」かつメタデータOFFのみ実行できます。
- このPC用の接続キーは毎回生成され、画面はメモリにのみ保持します。URLフラグメントから受け取ったキーは直ちにアドレスバーから除去します。
- 設定のみlocalStorageに保存します。URL・接続キー・履歴はブラウザの永続ストレージに保存しません。
- 接続先は同じPCの `http://127.0.0.1:<port>` または `http://localhost:<port>` に限定します。
- ブラウザで接続をブロックされた場合、同梱画面を `--local` で開けます。
- スマートフォンから別PCへの接続は対応していません。レスポンシブ表示はコマンド生成にも利用できます。
- 履歴はブリッジのメモリ内に最大約200件保持。終了時に消えます。ファイルは残ります。
- タブを閉じてもブリッジの処理は継続します。ブリッジ自体を停止すると進行中の処理も停止します。
- Cookie送信、ログイン代行、任意の追加コマンド、外部へのサーバー公開には対応していません。

起動オプションの例（Windows）：

```powershell
.venv\Scripts\python.exe bridge.py --local
.venv\Scripts\python.exe bridge.py --output "D:/Videos" --port 9732
.venv\Scripts\python.exe -m pip install -U "yt-dlp[default]"
```

macOS/Linuxでは `.venv/bin/python` に読み替えてください。

## リポジトリのyt-dlp本体を使う

このリポジトリをcloneした場合、ブリッジはリポジトリ内の `yt_dlp` を優先して実行します。
元のyt-dlpコードには変更を加えていません。起動セット単体ではpipで導入したyt-dlpを使用します。

```sh
python -m pip install -e '.[default]'
python docs/bridge/bridge.py --local
```

## GitHub Pagesへの配置

1. GitHubリポジトリの **Settings → Pages → Build and deployment → Source** を **GitHub Actions** にします。
2. **Actions → Publish yt-dlp Pages UI → Run workflow** を実行するか、`docs/` の変更をmasterへpushします。
3. ビルドでテストと起動ZIPの生成を行い、`docs/` だけをPagesへ公開します。

forkして利用する場合は `docs/bridge/bridge.py` の `PAGES` と既定の `--origin` を自分のPagesに変更してください。
Originは `https://yourname.github.io` のようにパスを含めません。コマンドラインの `--origin` でも追加できます。

```sh
python devscripts/package_pages_bridge.py
python -m http.server 8080 --directory docs
```

上記は表示確認用です。別ポートの画面からブリッジに接続する場合は
`python docs/bridge/bridge.py --origin http://localhost:8080` のように許可Originを指定します。

## 検証

```sh
python -m unittest discover -s web-tests -p 'test_*.py' -v
node --test web-tests/core.test.mjs
```

ブリッジの認証・Origin / Host制限、オプション検証、キュー処理、中止、ファイル制限、
コマンドの引用処理を検証します。外部サイトにアクセスしないテストでCIを実行します。
ネットワークを使う実機確認は、保存を許可されたURLで別途行ってください。

## 制約

サイトの仕様変更、ログイン、地域制限、DRM、配信元の制限などで取得できない動画があります。
変換で元の映像や音声の品質が向上することはありません。自分のコンテンツや保存を許可されたメディアに使用してください。

## 仕様の参考

- [GitHub Pagesの概要](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)
- [ChromeのLocal Network Access](https://developer.chrome.com/blog/local-network-access)
- [yt-dlp README](README.md)

このWeb UIとブリッジは本リポジトリのLICENSEに従います。
