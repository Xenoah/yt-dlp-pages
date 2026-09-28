import http.client
import importlib.util
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.parse import parse_qs, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parent.parent


class StartupTests(unittest.TestCase):
    def check_startup(self, script, directory):
        process = subprocess.Popen(
            [sys.executable, str(script), '--no-open', '--port', '0', '--output', str(directory / 'downloads')],
            cwd=directory, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
        )
        lines = queue.Queue()

        def read_output():
            for line in process.stdout:
                lines.put(line)
            lines.put(None)

        reader = threading.Thread(target=read_output, daemon=True)
        reader.start()
        try:
            while True:
                line = lines.get(timeout=15)
                self.assertIsNotNone(line, 'Local server exited before printing its URL')
                if line.startswith('Open: '):
                    url = urlsplit(line.removeprefix('Open: ').strip())
                    break
            self.assertEqual(url.scheme, 'http')
            self.assertEqual(url.hostname, '127.0.0.1')
            self.assertGreater(url.port, 0)
            self.assertEqual(url.path, '/')
            token = parse_qs(url.fragment)['token'][0]
            self.assertGreaterEqual(len(token), 32)
            connection = http.client.HTTPConnection(url.hostname, url.port, timeout=5)
            try:
                connection.request('GET', '/')
                response = connection.getresponse()
                self.assertEqual(response.status, 200)
                self.assertIn(b'yt-dlp Local', response.read())
                connection.request('GET', '/api/jobs', headers={'Authorization': 'Bearer ' + token})
                response = connection.getresponse()
                self.assertEqual(response.status, 200)
                self.assertEqual(json.loads(response.read()), {'jobs': []})
            finally:
                connection.close()
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            reader.join(timeout=5)
            process.stdout.close()

    def test_repository_startup_from_another_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            self.check_startup(ROOT / 'docs/bridge/bridge.py', Path(directory))

    def test_standalone_zip_startup_without_a_build(self):
        spec = importlib.util.spec_from_file_location('package_local_ui', ROOT / 'devscripts/package_local_ui.py')
        package = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(package)
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            archive = package.build(destination / 'yt-dlp-local.zip')
            with zipfile.ZipFile(archive) as source:
                source.extractall(destination)
            self.check_startup(destination / 'yt-dlp-local/bridge.py', destination)


if __name__ == '__main__':
    unittest.main()
