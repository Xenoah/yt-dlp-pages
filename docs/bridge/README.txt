yt-dlp Pages — ローカルブリッジ v1.0.0
========================================

操作画面: https://xenoah.github.io/yt-dlp-pages/
詳しい説明: https://github.com/Xenoah/yt-dlp-pages/blob/master/WEB_UI.md

Windows
1. Python 3.10以降を https://www.python.org/downloads/ から導入します。
2. ZIPを展開して start-windows.cmd を実行します。
   初回はこのフォルダーの .venv にyt-dlpと依存パッケージを導入します。
3. ブラウザに画面が開いたら「接続する」を押します。
   ブラウザに尋ねられた場合はローカルネットワークへのアクセスを許可します。
4. 起動ウィンドウを開いたまま使用します。Ctrl+Cで終了します。

動画・音声変換にはFFmpegが必要です。Windows PowerShellで:
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

Pagesとの接続がブラウザによって制限される場合:
  Windows: .venv\Scripts\python.exe bridge.py --local
  macOS/Linux: .venv/bin/python bridge.py --local
同梱の操作画面を同じPC上で開けます。

標準の保存先: ユーザーの Downloads/yt-dlp-pages
変更例:
  .venv\Scripts\python.exe bridge.py --output "D:/Videos"
ポート番号変更:
  .venv\Scripts\python.exe bridge.py --port 9732

yt-dlpの更新:
  Windows: .venv\Scripts\python.exe -m pip install -U "yt-dlp[default]"
  macOS/Linux: .venv/bin/python -m pip install -U 'yt-dlp[default]'

接続キーは起動ごとに変わります。自分以外に共有しないでください。
ダウンロード済みのファイルはブリッジを終了しても残ります。
ジョブ履歴はメモリ上のみで、再起動すると消えます。
GitHub Pagesは操作画面の配信のみを行い、動画データを保存しません。
Chrome / EdgeでのPC利用を想定しています。

自分のコンテンツ、または保存を許可されたメディアに使用してください。
