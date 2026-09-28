#!/bin/sh
set -eu
cd "$(dirname "$0")"
if ! python3 -c 'import sys; assert sys.version_info >= (3, 10)' 2>/dev/null; then
    echo 'Python 3.10 or newer is required. Install it from python.org or Homebrew.'
    exit 1
fi
if [ ! -x .venv/bin/python ]; then
    python3 -m venv .venv
fi
if ! .venv/bin/python -c 'import yt_dlp' 2>/dev/null; then
    .venv/bin/python -m pip install --upgrade 'yt-dlp[default]'
fi
exec .venv/bin/python bridge.py
