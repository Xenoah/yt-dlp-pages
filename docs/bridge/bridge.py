#!/usr/bin/env python3
"""Loopback-only yt-dlp companion for the GitHub Pages UI (Python 3.10+)."""

import argparse
import collections
import contextlib
import hmac
import json
import mimetypes
import os
from pathlib import Path
import secrets
import shutil
import signal
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, unquote, urlsplit
import webbrowser

VERSION = '1.0.0'
PAGES = 'https://xenoah.github.io/yt-dlp-pages/'
HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
ENGINE_CWD = REPO if (REPO / 'yt_dlp').is_dir() else HERE
UI_ROOT = HERE / 'ui' if (HERE / 'ui').is_dir() else HERE.parent
PROGRESS = ('download:@@progress:{"downloaded":%(progress.downloaded_bytes)j,'
            '"total":%(progress.total_bytes,progress.total_bytes_estimate)j,'
            '"speed":%(progress.speed)j,"eta":%(progress.eta)j}')
SAFE_FILES = {'.mp4', '.mkv', '.webm', '.mov', '.m4a', '.mp3', '.flac', '.wav',
              '.opus', '.ogg', '.aac', '.m4v', '.ts', '.vtt', '.srt', '.ass',
              '.lrc', '.ttml', '.srv1', '.srv2', '.srv3', '.json3', '.jpg', '.jpeg', '.png', '.webp'}


def valid_url(value):
    if not isinstance(value, str) or not value or len(value) > 8192 or any(ord(c) < 32 for c in value):
        raise ValueError('URLを確認してください。')
    parsed = urlsplit(value)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('http / https の動画URLを入力してください。')
    return value


def choice(options, key, allowed, default):
    value = options.get(key, default)
    if value not in allowed:
        raise ValueError(f'{key} の設定が正しくありません。')
    return value


def normalize_options(data):
    if not isinstance(data, dict):
        raise ValueError('設定はJSONオブジェクトで指定してください。')
    opts = {
        'mode': choice(data, 'mode', ('video', 'audio'), 'video'),
        'quality': choice(data, 'quality', ('best', '2160', '1440', '1080', '720', '480'), '1080'),
        'container': choice(data, 'container', ('mp4', 'mkv', 'webm'), 'mp4'),
        'audioFormat': choice(data, 'audioFormat', ('mp3', 'm4a', 'flac', 'wav', 'opus', 'original'), 'mp3'),
        'subtitles': choice(data, 'subtitles', ('none', 'manual', 'auto'), 'none'),
        'subLang': choice(data, 'subLang', ('ja,en', 'ja', 'en', 'all,-live_chat'), 'ja,en'),
    }
    for key in ('metadata', 'thumbnail', 'playlist'):
        value = data.get(key, key == 'metadata')
        if not isinstance(value, bool):
            raise ValueError(f'{key} はtrue / falseで指定してください。')
        opts[key] = value
    limit = data.get('playlistLimit', 20)
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        raise ValueError('プレイリストの上限は1〜100件です。')
    opts['playlistLimit'] = limit
    return opts


def engine_command():
    return [sys.executable, '-m', 'yt_dlp', '--ignore-config', '--no-plugin-dirs',
            '--no-colors', '--socket-timeout', '20', '--retries', '3',
            '--js-runtimes', 'node']


def download_args(opts, directory):
    args = ['--newline', '--no-simulate', '--progress', '--progress-delta', '0.4',
            '--progress-template', PROGRESS, '--print', 'before_dl:@@title:%(title)j',
            '--print', 'after_move:@@file:%(filepath)j', '--no-overwrites',
            '--windows-filenames', '--trim-filenames', '180', '-P', str(directory),
            '-o', '%(title).150B [%(id)s].%(ext)s']
    args += ['--yes-playlist', '--playlist-end', str(opts['playlistLimit'])] if opts['playlist'] else ['--no-playlist']
    if opts['mode'] == 'audio':
        args += ['-f', 'ba/b']
        if opts['audioFormat'] != 'original':
            args += ['-x', '--audio-format', opts['audioFormat'], '--audio-quality', '0']
    else:
        height = '' if opts['quality'] == 'best' else f"[height<=?{opts['quality']}]"
        container = opts['container']
        video_ext = f'[ext={container}]' if container in ('mp4', 'webm') else ''
        audio_ext = {'mp4': '[ext=m4a]', 'webm': '[ext=webm]', 'mkv': ''}[container]
        args += ['-f', f'bv*{height}{video_ext}+ba{audio_ext}/b{height}{video_ext}',
                 '--merge-output-format', container, '--remux-video', container]
    if opts['metadata']:
        args += ['--embed-metadata']
    if opts['thumbnail']:
        args += ['--write-thumbnail']
    if opts['subtitles'] != 'none':
        args += ['--write-subs', '--sub-langs', opts['subLang']]
        if opts['subtitles'] == 'auto':
            args += ['--write-auto-subs']
    return args


def stop_process(proc):
    if proc.poll() is not None:
        return
    try:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        else:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
    except (OSError, ProcessLookupError):
        pass


def popen(command):
    return subprocess.Popen(command, cwd=ENGINE_CWD, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace',
                            start_new_session=os.name != 'nt',
                            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0)


class Engine:
    def __init__(self, output):
        self.output = Path(output).expanduser().resolve()
        self.output.mkdir(parents=True, exist_ok=True)
        self.jobs = collections.OrderedDict()
        self.lock = threading.RLock()
        self.wake = threading.Condition(self.lock)
        self.stopping = False
        self.probe_lock = threading.Lock()
        self.worker = threading.Thread(target=self.run, daemon=True)
        self.worker.start()

    def capabilities(self):
        result = subprocess.run([sys.executable, '-m', 'yt_dlp', '--version'], cwd=ENGINE_CWD,
                                capture_output=True, text=True, timeout=15, check=False)
        return {'version': VERSION, 'engine': result.stdout.strip() if result.returncode == 0 else None,
                'ffmpeg': bool(shutil.which('ffmpeg')), 'ffprobe': bool(shutil.which('ffprobe')),
                'runtime': 'deno' if shutil.which('deno') else 'node' if shutil.which('node') else None,
                'output': str(self.output)}

    def snapshot(self):
        with self.lock:
            return [{k: v for k, v in j.items() if not k.startswith('_')} for j in self.jobs.values()]

    def enqueue(self, urls, options):
        if not isinstance(urls, list) or not 1 <= len(urls) <= 20:
            raise ValueError('URLは1〜20件まで指定できます。')
        urls = list(dict.fromkeys(valid_url(url) for url in urls))
        opts = normalize_options(options)
        needs_ffmpeg = opts['mode'] == 'video' or opts['audioFormat'] != 'original' or opts['metadata']
        if needs_ffmpeg and not shutil.which('ffmpeg'):
            raise ValueError('FFmpegが見つかりません。接続設定の導入手順を確認してください。音声「変換しない」＋メタデータOFFなら単体で使用できます。')
        with self.wake:
            active = sum(j['status'] in ('queued', 'running', 'processing') for j in self.jobs.values())
            if active + len(urls) > 50:
                raise ValueError('待機中のジョブは50件までです。完了後に追加してください。')
            for key in list(self.jobs):
                if len(self.jobs) < 200:
                    break
                if self.jobs[key]['status'] not in ('queued', 'running', 'processing'):
                    del self.jobs[key]
            created = []
            for url in urls:
                job_id = secrets.token_hex(8)
                self.jobs[job_id] = {'id': job_id, 'url': url, 'options': opts, 'title': url,
                                     'status': 'queued', 'percent': 0, 'speed': None, 'eta': None,
                                     'files': [], 'logs': [], 'error': '', 'created': time.time(),
                                     '_cancel': False, '_proc': None}
                created.append(job_id)
            self.wake.notify_all()
        return created

    def cancel(self, job_id):
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                raise ValueError('ジョブが見つかりません。')
            if job['status'] not in ('queued', 'running', 'processing'):
                return
            job['_cancel'] = True
            job['status'] = 'cancelled'
            proc = job['_proc']
        if proc:
            stop_process(proc)

    def clear(self):
        with self.lock:
            self.jobs = collections.OrderedDict((k, v) for k, v in self.jobs.items()
                                                if v['status'] in ('queued', 'running', 'processing'))

    def run(self):
        while True:
            with self.wake:
                self.wake.wait_for(lambda: self.stopping or any(j['status'] == 'queued' for j in self.jobs.values()))
                if self.stopping:
                    return
                job = next(j for j in self.jobs.values() if j['status'] == 'queued')
                job['status'] = 'running'
            self.execute(job)

    def execute(self, job):
        directory = self.output / job['id']
        directory.mkdir(exist_ok=True)
        proc = None
        try:
            command = engine_command() + download_args(job['options'], directory) + ['--', job['url']]
            proc = popen(command)
            with self.lock:
                job['_proc'] = proc
                cancelled = job['_cancel']
            if cancelled:
                stop_process(proc)
            for raw in proc.stdout:
                line = raw.strip()
                with self.lock:
                    if line.startswith('@@progress:'):
                        try:
                            p = json.loads(line.removeprefix('@@progress:'))
                            total, done = p.get('total'), p.get('downloaded')
                            job.update(speed=p.get('speed'), eta=p.get('eta'))
                            if isinstance(total, (int, float)) and total > 0 and isinstance(done, (int, float)):
                                job['percent'] = min(100, round(done / total * 100, 1))
                            if not job['_cancel']:
                                job['status'] = 'running'
                        except (ValueError, TypeError):
                            pass
                    elif line.startswith('@@title:'):
                        with contextlib.suppress(ValueError):
                            job['title'] = str(json.loads(line.removeprefix('@@title:')))
                    elif not line.startswith('@@file:'):
                        if line:
                            job['logs'] = (job['logs'] + [line[:2000]])[-60:]
                        if line.startswith(('[Merger]', '[ExtractAudio]', '[Metadata]', '[VideoRemuxer]')) and not job['_cancel']:
                            job['status'] = 'processing'
            code = proc.wait()
            proc.stdout.close()
            with self.lock:
                if job['_cancel']:
                    job['status'] = 'cancelled'
                elif code != 0:
                    job['status'] = 'failed'
                    errors = [line for line in job['logs'] if 'ERROR:' in line]
                    job['error'] = errors[-1] if errors else f'yt-dlpが終了コード{code}で停止しました。ログを確認してください。'
                else:
                    files = []
                    for path in sorted(directory.iterdir()):
                        if path.is_file() and not path.is_symlink() and path.suffix.lower() in SAFE_FILES:
                            files.append({'name': path.name, 'size': path.stat().st_size})
                    job['files'] = files
                    job['status'] = 'completed' if files else 'failed'
                    job['percent'] = 100 if files else 0
                    if not files:
                        job['error'] = '保存可能なファイルが見つかりません。ログを確認してください。'
                job['_proc'] = None
        except Exception as error:
            with self.lock:
                proc = job.get('_proc')
                job['status'] = 'cancelled' if job['_cancel'] else 'failed'
                job['error'] = str(error)[:1000]
                job['_proc'] = None
            if proc:
                stop_process(proc)
        finally:
            if proc and proc.stdout:
                proc.stdout.close()

    def probe(self, url):
        valid_url(url)
        if not self.probe_lock.acquire(blocking=False):
            raise ValueError('動画情報を取得中です。完了までお待ちください。')
        try:
            command = [*engine_command(), '--dump-single-json', '--skip-download', '--no-playlist',
                       '--playlist-items', '1', '--retries', '1', '--', url]
            proc = popen(command)
            try:
                output, _ = proc.communicate(timeout=60)
            except subprocess.TimeoutExpired:
                stop_process(proc)
                proc.communicate()
                raise ValueError('動画情報の取得がタイムアウトしました。URLやネットワークを確認してください。') from None
            lines = output.splitlines()
            if proc.returncode:
                errors = [line for line in lines if 'ERROR:' in line]
                raise ValueError((errors[-1] if errors else '動画情報を取得できませんでした。')[:1000])
            data = next((json.loads(line) for line in reversed(lines) if line.startswith('{')), None)
            if not data:
                raise ValueError('動画情報が空でした。')
            if data.get('entries'):
                data = next((entry for entry in data['entries'] if entry), data)
            thumbnail = data.get('thumbnail', '')
            if not isinstance(thumbnail, str) or urlsplit(thumbnail).scheme not in ('http', 'https'):
                thumbnail = ''
            return {key: data.get(key) for key in ('title', 'uploader', 'duration', 'extractor_key', 'id')} | {
                'thumbnail': thumbnail, 'formats': len(data.get('formats') or []),
                'subtitles': list((data.get('subtitles') or {}).keys())[:100]}
        finally:
            self.probe_lock.release()

    def file(self, job_id, name):
        with self.lock:
            job = self.jobs.get(job_id)
            if not job or job['status'] != 'completed' or name not in [f['name'] for f in job['files']]:
                raise ValueError('ファイルが見つかりません。')
        base = (self.output / job_id).resolve()
        path = (base / name).resolve()
        if path.parent != base or not path.is_file() or path.is_symlink():
            raise ValueError('ファイルが見つかりません。')
        return path

    def close(self):
        with self.wake:
            self.stopping = True
            ids = list(self.jobs)
            self.wake.notify_all()
        for job_id in ids:
            self.cancel(job_id)


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port, engine, origins):
        super().__init__(('127.0.0.1', port), Handler)
        self.engine = engine
        self.token = secrets.token_urlsafe(32)
        self.origins = set(origins) | {f'http://127.0.0.1:{self.server_port}', f'http://localhost:{self.server_port}'}
        self.tickets = {}
        self.ticket_lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    server_version = 'YTdlpPages/1'

    def log_message(self, fmt, *args):
        # Never log bearer tokens, URL queries, or one-use download tickets.
        pass

    def allowed(self):
        host = self.headers.get('Host', '')
        if host not in {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}:
            self.send_json(403, {'error': 'Host not allowed'})
            return False
        origin = self.headers.get('Origin')
        if origin is not None and origin not in self.server.origins:
            self.send_json(403, {'error': 'Origin not allowed'})
            return False
        return True

    def authorized(self):
        supplied = self.headers.get('Authorization', '')
        if not hmac.compare_digest(supplied.encode('utf-8'), f'Bearer {self.server.token}'.encode()):
            self.send_json(401, {'error': '接続キーが違うか、ブリッジが再起動されました。再接続してください。'})
            return False
        return True

    def common_headers(self):
        origin = self.headers.get('Origin')
        if origin in self.server.origins:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')

    def send_json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.common_headers()
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        with contextlib.suppress(BrokenPipeError, ConnectionResetError):
            self.wfile.write(body)

    def do_OPTIONS(self):
        if not self.allowed():
            return
        self.send_response(204)
        self.common_headers()
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
        self.send_header('Access-Control-Allow-Private-Network', 'true')
        self.send_header('Access-Control-Max-Age', '600')
        self.end_headers()

    def do_GET(self):
        if not self.allowed():
            return
        path = urlsplit(self.path).path
        if path.startswith('/download/'):
            ticket = path.removeprefix('/download/')
            with self.server.ticket_lock:
                item = self.server.tickets.pop(ticket, None)
            if not item or item['expires'] < time.monotonic():
                self.send_json(404, {'error': '保存リンクが失効しました。もう一度「保存」を押してください。'})
                return
            try:
                file = self.server.engine.file(item['job'], item['name'])
                self.send_file(file, attachment=True)
            except ValueError as error:
                self.send_json(404, {'error': str(error)})
            return
        if path.startswith('/api/'):
            if not self.authorized():
                return
            try:
                if path == '/api/health':
                    self.send_json(200, self.server.engine.capabilities())
                elif path == '/api/jobs':
                    self.send_json(200, {'jobs': self.server.engine.snapshot()})
                else:
                    self.send_json(404, {'error': 'Not found'})
            except (OSError, subprocess.SubprocessError) as error:
                self.send_json(500, {'error': str(error)[:500]})
            return
        relative = unquote(path.lstrip('/')) or 'index.html'
        if relative not in {'index.html', 'app.js', 'core.mjs', 'styles.css', 'favicon.svg'}:
            self.send_json(404, {'error': 'Not found'})
            return
        file = UI_ROOT / relative
        if not file.is_file():
            self.send_json(404, {'error': f'操作画面は {PAGES} で開いてください。'})
            return
        self.send_file(file)

    def send_file(self, path, attachment=False):
        try:
            with path.open('rb') as stream:
                self.send_response(200)
                self.common_headers()
                self.send_header('Content-Type', 'application/octet-stream' if attachment else
                                 (mimetypes.guess_type(path.name)[0] or 'application/octet-stream'))
                self.send_header('Content-Length', str(path.stat().st_size))
                if attachment:
                    self.send_header('Content-Disposition', "attachment; filename*=UTF-8''" + quote(path.name))
                self.end_headers()
                shutil.copyfileobj(stream, self.wfile)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self):
        if not self.allowed() or not self.authorized():
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 65536:
                raise ValueError('リクエストのサイズが正しくありません。')
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                raise ValueError('JSONで送信してください。')
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError('JSONオブジェクトが必要です。')
            path = urlsplit(self.path).path
            if path == '/api/jobs':
                ids = self.server.engine.enqueue(body.get('urls'), body.get('options', {}))
                self.send_json(202, {'ids': ids})
            elif path == '/api/probe':
                self.send_json(200, self.server.engine.probe(body.get('url')))
            elif path == '/api/cancel':
                self.server.engine.cancel(str(body.get('id', '')))
                self.send_json(200, {'ok': True})
            elif path == '/api/clear':
                self.server.engine.clear()
                self.send_json(200, {'ok': True})
            elif path == '/api/ticket':
                job_id, name = str(body.get('id', '')), str(body.get('name', ''))
                self.server.engine.file(job_id, name)
                ticket = secrets.token_urlsafe(32)
                with self.server.ticket_lock:
                    now = time.monotonic()
                    self.server.tickets = {k: v for k, v in self.server.tickets.items() if v['expires'] > now}
                    self.server.tickets[ticket] = {'job': job_id, 'name': name, 'expires': now + 60}
                self.send_json(200, {'path': '/download/' + ticket})
            else:
                self.send_json(404, {'error': 'Not found'})
        except (ValueError, TypeError, KeyError) as error:
            self.send_json(400, {'error': str(error)[:1000]})
        except Exception as error:
            self.send_json(500, {'error': str(error)[:500]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=9731)
    parser.add_argument('--output', default=str(Path.home() / 'Downloads' / 'yt-dlp-pages'))
    parser.add_argument('--origin', action='append', default=['https://xenoah.github.io'])
    parser.add_argument('--no-open', action='store_true')
    parser.add_argument('--local', action='store_true', help='Open the bundled UI instead of GitHub Pages')
    args = parser.parse_args()
    for origin in args.origin:
        parsed = urlsplit(origin)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.path or parsed.query or parsed.fragment:
            parser.error('--origin must be an exact origin without a path, e.g. https://example.github.io')
    engine = Engine(args.output)
    try:
        server = Server(args.port, engine, args.origin)
    except OSError as error:
        engine.close()
        parser.exit(1, f'Cannot start bridge: {error}\nTry --port 9732\n')
    local = f'http://127.0.0.1:{server.server_port}'
    base = local + '/' if args.local else PAGES
    link = base + '#token=' + quote(server.token) + '&bridge=' + quote(local, safe='')
    print(f'\nyt-dlp Pages Bridge v{VERSION}\nAddress: {local}\nConnection key: {server.token}\n'
          f'Output: {engine.output}\n\nOpen: {link}\n\nKeep this window open. Ctrl+C to stop.\n', flush=True)
    if not args.no_open:
        webbrowser.open(link)
    try:
        server.serve_forever(poll_interval=0.3)
    except KeyboardInterrupt:
        pass
    finally:
        engine.close()
        server.server_close()


if __name__ == '__main__':
    main()
