#!/usr/bin/env python3
"""Package an optional standalone local UI ZIP; normal startup needs no build."""

from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / 'docs'
UI = ('index.html', 'styles.css', 'app.js', 'core.mjs', 'favicon.svg')
BRIDGE = ('bridge.py', 'start-windows.cmd', 'start-macos.command', 'README.txt')


def build(destination=None):
    destination = Path(destination or ROOT / 'dist' / 'yt-dlp-local.zip')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in BRIDGE:
            archive.write(DOCS / 'bridge' / name, f'yt-dlp-local/{name}')
        for name in UI:
            archive.write(DOCS / name, f'yt-dlp-local/ui/{name}')
        archive.write(ROOT / 'LICENSE', 'yt-dlp-local/LICENSE')
    return destination


if __name__ == '__main__':
    print(build())
