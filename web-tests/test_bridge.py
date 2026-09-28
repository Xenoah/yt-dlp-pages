import http.client
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('local_bridge', ROOT / 'docs/bridge/bridge.py')
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class ValidationTests(unittest.TestCase):
    def test_url_restrictions(self):
        for url in (None, 12, '--exec', 'file:///etc/passwd', 'https://user:pass@example.org', 'https://example.org/\nnext'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                bridge.valid_url(url)
        self.assertEqual(bridge.valid_url('https://example.org/?x=1&y=2'), 'https://example.org/?x=1&y=2')

    def test_options_restrict_injection_and_playlist_size(self):
        for data in ({'quality': '1080];--exec=cmd'}, {'playlistLimit': 101}, {'playlistLimit': True},
                     {'metadata': 'true'}, {'container': 'exe'}, {'mode': []}, []):
            with self.subTest(data=data), self.assertRaises(ValueError):
                bridge.normalize_options(data)
        opts = bridge.normalize_options({'exec': 'evil', 'output': '../../outside'})
        args = bridge.download_args(opts, '/tmp/fixed-output')
        self.assertNotIn('evil', args)
        self.assertNotIn('../../outside', args)
        self.assertIn('--no-playlist', args)
        self.assertIn('--no-plugin-dirs', bridge.engine_command())
        self.assertIn('--ignore-config', bridge.engine_command())

    def test_audio_and_subtitle_mapping(self):
        opts = bridge.normalize_options({'mode': 'audio', 'audioFormat': 'flac', 'subtitles': 'auto', 'playlist': True, 'playlistLimit': 3})
        args = bridge.download_args(opts, '/tmp/output')
        self.assertEqual(args[args.index('--audio-format') + 1], 'flac')
        self.assertEqual(args[args.index('--playlist-end') + 1], '3')
        self.assertIn('--write-auto-subs', args)


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.ffmpeg_patch = patch.object(bridge.shutil, 'which', return_value='/test/bin/ffmpeg')
        cls.command_patch = patch.object(bridge, 'engine_command', return_value=[sys.executable, str(ROOT / 'web-tests/fake_engine.py')])
        cls.ffmpeg_patch.start()
        cls.command_patch.start()
        cls.engine = bridge.Engine(cls.temp.name)
        cls.server = bridge.Server(0, cls.engine)
        cls.origin = f'http://127.0.0.1:{cls.server.server_port}'
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.engine.close()
        cls.server.shutdown()
        cls.server.server_close()
        cls.engine.worker.join(timeout=5)
        cls.command_patch.stop()
        cls.ffmpeg_patch.stop()
        cls.temp.cleanup()

    def request(self, method, path, data=None, auth=True, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        request_headers = {'Origin': self.origin}
        if auth:
            request_headers['Authorization'] = 'Bearer ' + self.server.token
        if data is not None:
            request_headers['Content-Type'] = 'application/json'
        request_headers.update(headers or {})
        connection.request(method, path, body=json.dumps(data) if data is not None else None, headers=request_headers)
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def wait_job(self, job_id, terminal=True):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            job = next(j for j in self.engine.snapshot() if j['id'] == job_id)
            if (terminal and job['status'] in ('completed', 'failed', 'cancelled')) or (not terminal and job['percent'] > 0):
                return job
            time.sleep(0.02)
        self.fail('Job did not reach expected state')

    def enqueue(self, suffix='video'):
        status, _, body = self.request('POST', '/api/jobs', {'urls': ['https://example.org/' + suffix], 'options': {}})
        self.assertEqual(status, 202, body)
        return json.loads(body)['ids'][0]

    def test_auth_origin_host_and_preflight(self):
        self.assertEqual(self.request('GET', '/api/jobs', auth=False)[0], 401)
        self.assertEqual(self.request('GET', '/api/jobs', headers={'Authorization': 'Bearer wrong'})[0], 401)
        self.assertEqual(self.request('GET', '/api/jobs', headers={'Origin': 'https://evil.example'})[0], 403)
        self.assertEqual(self.request('GET', '/api/jobs', headers={'Origin': 'https://xenoah.github.io'})[0], 403)
        self.assertEqual(self.request('GET', '/api/jobs', headers={'Origin': 'http://127.0.0.1:1'})[0], 403)
        self.assertEqual(self.request('GET', '/api/jobs', headers={'Origin': 'null'})[0], 403)
        self.assertEqual(self.request('GET', '/api/jobs', headers={'Host': 'evil.example'})[0], 403)
        status, headers, _ = self.request('OPTIONS', '/api/jobs', auth=False)
        self.assertEqual(status, 204)
        self.assertEqual(headers['Access-Control-Allow-Origin'], self.origin)
        self.assertNotIn('Access-Control-Allow-Private-Network', headers)
        local = f'http://localhost:{self.server.server_port}'
        self.assertEqual(self.request('GET', '/api/jobs', headers={'Origin': local})[0], 200)

    def test_local_ui_assets_and_module_mime_types(self):
        for path, mime in (('/', 'text/html'), ('/app.js', 'text/javascript'), ('/core.mjs', 'text/javascript'),
                           ('/styles.css', 'text/css'), ('/favicon.svg', 'image/svg+xml')):
            with self.subTest(path=path):
                status, headers, body = self.request('GET', path, auth=False)
                self.assertEqual(status, 200)
                self.assertEqual(headers['Content-Type'].split(';')[0], mime)
                self.assertTrue(body)
        self.assertEqual(self.request('GET', '/bridge/bridge.py', auth=False)[0], 404)

    def test_completed_files_and_one_use_download(self):
        job_id = self.enqueue()
        job = self.wait_job(job_id)
        self.assertEqual(job['status'], 'completed')
        self.assertEqual(job['title'], 'Offline fixture')
        self.assertEqual({f['name'] for f in job['files']}, {'fixture.mp4', 'caption.ja.vtt'})
        self.assertFalse(any(k.startswith('_') for k in job))
        self.assertEqual(self.request('POST', '/api/ticket', {'id': job_id, 'name': '../outside'})[0], 400)
        self.assertEqual(self.request('GET', '/bridge/bridge.py', auth=False)[0], 404)
        self.assertEqual(self.request('GET', '/../../LICENSE', auth=False)[0], 404)
        status, _, body = self.request('POST', '/api/ticket', {'id': job_id, 'name': 'fixture.mp4'})
        self.assertEqual(status, 200)
        path = json.loads(body)['path']
        status, headers, data = self.request('GET', path, auth=False)
        self.assertEqual(status, 200)
        self.assertEqual(data, b'fixture-media')
        self.assertIn('attachment', headers['Content-Disposition'])
        self.assertEqual(self.request('GET', path, auth=False)[0], 404)

    def test_cancel_running_and_next_job_completes(self):
        slow = self.enqueue('slow')
        self.wait_job(slow, terminal=False)
        next_job = self.enqueue('next')
        self.assertEqual(self.request('POST', '/api/cancel', {'id': slow})[0], 200)
        self.assertEqual(self.wait_job(slow)['status'], 'cancelled')
        self.assertEqual(self.wait_job(next_job)['status'], 'completed')

    def test_process_failure_is_not_reported_as_success(self):
        job = self.wait_job(self.enqueue('failure'))
        self.assertEqual(job['status'], 'failed')
        self.assertIn('fixture failure', job['error'])
        self.assertEqual(job['files'], [])

    def test_probe_sanitizes_thumbnail(self):
        status, _, body = self.request('POST', '/api/probe', {'url': 'https://example.org/video'})
        self.assertEqual(status, 200)
        info = json.loads(body)
        self.assertEqual(info['thumbnail'], '')
        self.assertEqual(info['formats'], 2)

    def test_payload_validation(self):
        cases = ({'urls': ['file:///etc/passwd']}, {'urls': []}, {'urls': ['https://example.org'], 'options': {'playlistLimit': 0}}, [])
        for payload in cases:
            self.assertEqual(self.request('POST', '/api/jobs', payload)[0], 400)
        with patch.object(bridge.shutil, 'which', return_value=None):
            status, _, body = self.request('POST', '/api/jobs', {'urls': ['https://example.org']})
            self.assertEqual(status, 400)
            self.assertIn('FFmpeg', json.loads(body)['error'])


if __name__ == '__main__':
    unittest.main()
