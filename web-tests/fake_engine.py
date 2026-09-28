"""Offline subprocess fixture; intentionally only used by the bridge tests."""
import json
from pathlib import Path
import sys
import time

if '--dump-single-json' in sys.argv:
    print(json.dumps({'title': '<fixture>', 'duration': 2, 'thumbnail': 'javascript:alert(1)', 'formats': [{}, {}]}))
    sys.exit(0)
directory = Path(sys.argv[sys.argv.index('-P') + 1])
url = sys.argv[-1]
if 'failure' in url:
    print('ERROR: fixture failure', flush=True)
    sys.exit(1)
print('@@title:"Offline fixture"', flush=True)
print('@@progress:{"downloaded":4,"total":8,"speed":4,"eta":1}', flush=True)
if 'slow' in url:
    time.sleep(20)
(directory / 'fixture.mp4').write_bytes(b'fixture-media')
(directory / 'caption.ja.vtt').write_text('WEBVTT\n', encoding='utf-8')
(directory / 'unfinished.mp4.part').write_bytes(b'partial')
(directory / 'do-not-serve.exe').write_bytes(b'not-media')
print('@@file:' + json.dumps(str(directory / 'fixture.mp4')), flush=True)
