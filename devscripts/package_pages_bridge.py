#!/usr/bin/env python3
"""Build the dependency-free Pages site and portable companion source ZIP."""

from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / 'docs'
UI = ('index.html', 'styles.css', 'app.js', 'core.mjs', 'favicon.svg')
BRIDGE = ('bridge.py', 'start-windows.cmd', 'start-macos.command', 'README.txt')


def build(destination=None):
    destination = Path(destination or DOCS / 'yt-dlp-pages-bridge.zip')
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in BRIDGE:
            archive.write(DOCS / 'bridge' / name, f'yt-dlp-pages-bridge/{name}')
        for name in UI:
            archive.write(DOCS / name, f'yt-dlp-pages-bridge/ui/{name}')
    return destination


if __name__ == '__main__':
    print(build())
