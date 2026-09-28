yt-dlp Local v1.1.0
========================================

このPCだけで動く、日本語のyt-dlp操作画面です。
外部ホスティングや画面のビルドは不要です。
詳しい説明: https://github.com/Xenoah/yt-dlp-pages/blob/master/WEB_UI.md

Windows
1. Python 3.10以降を https://www.python.org/downloads/ から導入します。
2. ZIP全体を展開して start-windows.cmd を実行します。
   初回は専用の .venv にyt-dlpと依存パッケージを導入します。
3. http://127.0.0.1:9731/ に操作画面が開き、自動で接続します。
4. 起動ウィンドウを開いたまま使用します。Ctrl+Cで終了します。

動画の結合・音声変換・メタデータ埋め込みにはFFmpegが必要です。
Windows PowerShellで:
  winget install --id Gyan.FFmpeg -e
YouTube向けのJavaScriptランタイム:
  winget install --id DenoLand.Deno -e
導入後は起動ウィンドウを閉じ、もう一度起動してください。

macOS / Linux
  Python 3.10以降、FFmpeg、DenoまたはNode.jsを用意します。
  ターミナルでこのフォルダーに移動して:
    sh start-macos.command
  macOSのHomebrewの場合:
    brew install python ffmpeg deno

ブラウザが開かない・再読み込み後に未接続の場合:
  起動ウィンドウの Open: のURLを開き直してください。
  接続設定に Connection key: を入力しても再接続できます。
  HTMLを直接開かず、起動ファイルから使用します。

標準の保存先: ユーザーの Downloads/yt-dlp-pages
変更例 (Windows):
  start-windows.cmd --output "D:/Videos"
  start-windows.cmd --port 9732
  start-windows.cmd --no-open
macOS / Linux:
  sh start-macos.command --port 9732

単体の起動セットのyt-dlpを更新:
  Windows: .venv\Scripts\python.exe -m pip install -U "yt-dlp[default]"
  macOS/Linux: .venv/bin/python -m pip install -U 'yt-dlp[default]'
リポジトリ全体を展開した場合は、同梱のyt-dlp本体を優先します。
更新はgit pull、または新しいリポジトリZIPへの置き換えで行います。

接続キーは起動ごとに変わります。自分以外に共有しないでください。
保存したファイルは終了後も残ります。ジョブ履歴は再起動すると消えます。
画面は同じPC専用です。別PCや外部Webサイトからの操作には対応しません。
初回のパッケージ導入とメディアのダウンロードにはネット接続が必要です。

自分のコンテンツ、または保存を許可されたメディアに使用してください。
