"""Session token, private files, bad requests and backups, on disposable servers and data folders."""
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from library import import_book
from book_fixture import make_epub
from server_fixture import server_token

POSIX = os.name != 'nt'
BANNER = 'Open Engineering Workshop from its shortcut or start command to connect this browser.'


def mode(path):
    return path.stat().st_mode & 0o777


class LocalServer:
    def __init__(self, data):
        self.data = Path(data)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            self.port = sock.getsockname()[1]
        assert self.port != 7318, 'Refusing the production port'
        self.url = f'http://127.0.0.1:{self.port}'
        self.proc = subprocess.Popen([sys.executable, str(ROOT / 'backend/server.py'), '--port', str(self.port)],
                                     env={**os.environ, 'ML_WORKSHOP_DATA_DIR': str(self.data)},
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.token = server_token(self.url, self.data, self.proc)

    def stop(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()

    def request(self, path, token=None, body=None):
        """Return (status, headers, body bytes). Send token='' for no token header."""
        headers = {'Content-Type': 'application/json'} if body is not None else {}
        token = self.token if token is None else token
        if token:
            headers['X-Workshop-Token'] = token
        request = urllib.request.Request(self.url + path, data=None if body is None else json.dumps(body).encode(), headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status, response.headers, response.read()
        except urllib.error.HTTPError as error:
            with error:
                return error.code, error.headers, error.read()

    def raw(self, head):
        """Send raw request bytes and return the status line, or b'' if the server dropped the connection."""
        with socket.create_connection(('127.0.0.1', self.port), timeout=10) as sock:
            sock.sendall(head.replace(b'HOST', f'127.0.0.1:{self.port}'.encode()))
            chunks = []
            while chunk := sock.recv(65536):
                chunks.append(chunk)
        return b''.join(chunks).split(b'\r\n', 1)[0]


class SessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='ml-security-test-')
        cls.data = Path(cls.tmp.name) / 'data'
        # A folder made by an older version with the default umask.
        cls.data.mkdir(mode=0o755)
        os.chmod(cls.data, 0o755)
        cls.book = import_book(make_epub(Path(cls.tmp.name) / 'fixture.epub'), cls.data, 'fixture')
        cls.server = LocalServer(cls.data)

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()
        cls.tmp.cleanup()

    def test_no_endpoint_returns_the_token(self):
        self.assertEqual(self.server.request('/api/bootstrap', token='')[0], 403)
        status, _, body = self.server.request('/api/bootstrap')
        self.assertEqual(status, 404)
        self.assertNotIn(self.server.token.encode(), body)

    def test_learner_data_needs_the_token(self):
        paths = ['/api/state', '/api/library', '/api/library/search?q=warp', '/api/library/fixture/chapter/1',
                 '/api/portfolio', '/api/game', '/api/game/summary', '/api/curriculum', '/api/runtime',
                 '/api/solution/foundations-1', '/api/session', '/api/backups/ml-workshop-20260101-000000-000000.json']
        for path in paths:
            for token in ('', 'wrong', self.server.token[:-1] + 'x'):
                with self.subTest(path=path, token=token):
                    status, _, body = self.server.request(path, token=token)
                    self.assertEqual(status, 403)
                    self.assertEqual(json.loads(body), {'error': BANNER, 'code': 'session-expired'})
            with self.subTest(path=path, token='valid'):
                self.assertIn(self.server.request(path)[0], (200, 404))
        status, _, _ = self.server.request('/api/run', token='', body=dict(lessonId='foundations-1', code='print(1)', mode='run'))
        self.assertEqual(status, 403)
        # Project notes and task progress are learner data too.
        project = dict(projectId='public-micrograd-ops', notes='note-7f3a', reviewed=[0], updatedAt=1,
                       tasks={'accumulate': dict(notes='note-7f3a')})
        for token in ('', 'wrong'):
            with self.subTest(path='/api/project/state', token=token):
                self.assertEqual(self.server.request('/api/project/state', token=token, body=project)[0], 403)
        self.assertNotIn(b'note-7f3a', self.server.request('/api/portfolio')[2])

    def test_only_health_is_public_and_book_files_need_the_token(self):
        self.assertEqual(self.server.request('/api/health', token='')[0], 200)
        # Figures and the original file, which a book ID alone would otherwise give to any local program.
        for path in ('/api/library/fixture/asset/' + self.book['assets'][0]['path'], '/api/library/fixture/asset/source.epub'):
            for token in ('', 'wrong'):
                with self.subTest(path=path, token=token):
                    status, _, body = self.server.request(path, token=token)
                    self.assertEqual(status, 403)
                    self.assertEqual(json.loads(body)['code'], 'session-expired')
            status, headers, body = self.server.request(path)
            self.assertEqual(status, 200)
            self.assertIn('sandbox', headers['Content-Security-Policy'])
        self.assertEqual(body, (self.data / 'library/fixture/source.epub').read_bytes())
        # The Host and Origin checks still apply to public routes.
        request = urllib.request.Request(self.server.url + '/api/health', headers={'Origin': 'https://example.com'})
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(request, timeout=10)
        self.assertEqual(error.exception.code, 403)

    def test_token_header_is_compared_as_bytes(self):
        token = self.server.token.encode()
        for value in ('é'.encode(), b'\xff\xfe', token + 'é'.encode(), token[:-1] + b'\xe9'):
            for head in (b'GET /api/state HTTP/1.0\r\nHost: HOST\r\nX-Workshop-Token: %s\r\n\r\n' % value,
                         b'POST /api/run HTTP/1.0\r\nHost: HOST\r\nX-Workshop-Token: %s\r\nContent-Type: application/json\r\nContent-Length: 2\r\n\r\n{}' % value):
                with self.subTest(value=value, request=head[:4]):
                    self.assertEqual(self.server.raw(head), b'HTTP/1.0 403 Forbidden')
        self.assertEqual(self.server.raw(b'GET /api/state HTTP/1.0\r\nHost: HOST\r\nX-Workshop-Token: %s\r\n\r\n' % token), b'HTTP/1.0 200 OK')

    def test_bad_paths_get_400_instead_of_a_dropped_connection(self):
        for path in (b'/%00', b'/books/%00x', b'/assets/a%00.js'):
            with self.subTest(path=path):
                self.assertEqual(self.server.raw(b'GET %s HTTP/1.0\r\nHost: HOST\r\n\r\n' % path), b'HTTP/1.0 400 Bad Request')
        # The server keeps answering afterwards.
        self.assertEqual(self.server.request('/api/health')[0], 200)

    @unittest.skipUnless(POSIX, 'POSIX file modes')
    def test_data_files_are_private(self):
        backup = json.loads(self.server.request('/api/backup', body={})[2])['filename']
        self.assertEqual(mode(self.data), 0o700)
        for path in [self.data / 'session-token', self.data / 'workshop.sqlite3', self.data / 'backups' / backup]:
            with self.subTest(path=path.name):
                self.assertEqual(mode(path), 0o600)

    def test_backup_download_needs_the_token_and_old_backups_are_pruned(self):
        folder = self.data / 'backups'
        folder.mkdir(exist_ok=True)
        old = [f'ml-workshop-2020010{day}-000000-000000.json' for day in range(1, 10)] + ['ml-workshop-20200110-000000-000000.json', 'ml-workshop-20200111-000000-000000.json', 'ml-workshop-20200112-000000-000000.json']
        others = ['ml-workshop-my-copy.json', 'notes.json', 'ml-workshop-20200101-000000-000000.json.bak', 'ml-workshop-20200101-000000.json']
        for name in old + others:
            (folder / name).write_text('{}')
        status, _, body = self.server.request('/api/backup', body={})
        self.assertEqual(status, 200)
        backup = json.loads(body)
        self.assertEqual(self.server.request(backup['url'], token='')[0], 403)
        status, headers, body = self.server.request(backup['url'])
        self.assertEqual(status, 200)
        self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(headers['Content-Disposition'], f'attachment; filename="{backup["filename"]}"')
        self.assertEqual(json.loads(body)['app'], 'ml-workshop')
        made = sorted(p.name for p in folder.iterdir() if re.fullmatch(r'ml-workshop-\d{8}-\d{6}-\d{6}\.json', p.name))
        self.assertEqual(len(made), 10)
        self.assertEqual(made[-1], backup['filename'])
        self.assertNotIn(old[0], made)
        for name in others:
            self.assertTrue((folder / name).exists(), name)


class BackupNameTests(unittest.TestCase):
    def test_backups_in_the_same_microsecond_get_a_suffix(self):
        script = '''
import json, sys
from datetime import datetime, timezone
sys.path.insert(0, sys.argv[1])
import server
server.open_data()
class Frozen(datetime):
    @classmethod
    def now(cls, tz=None):return datetime(2026, 1, 2, 3, 4, 5, 678901, tzinfo=timezone.utc)
server.datetime = Frozen
names = [server.save_backup() for _ in range(3)]
server.prune_backups(server.DATA / 'backups', keep=2)
print(json.dumps([names, sorted(p.name for p in (server.DATA / 'backups').iterdir())]))
'''
        with tempfile.TemporaryDirectory(prefix='ml-backup-name-test-') as directory:
            result = subprocess.run([sys.executable, '-c', script, str(ROOT / 'backend')], capture_output=True, text=True, timeout=60,
                                    env={**os.environ, 'ML_WORKSHOP_DATA_DIR': directory})
        self.assertEqual(result.returncode, 0, result.stderr)
        names, kept = json.loads(result.stdout)
        stamp = 'ml-workshop-20260102-030405-678901'
        self.assertEqual(names, [f'{stamp}.json', f'{stamp}-1.json', f'{stamp}-2.json'])
        # Pruning keeps the newest two, in the order they were written.
        self.assertEqual(kept, [f'{stamp}-1.json', f'{stamp}-2.json'])


class RestartTests(unittest.TestCase):
    def test_token_survives_restarts_and_changes_only_when_the_file_is_missing(self):
        with tempfile.TemporaryDirectory(prefix='ml-restart-test-') as directory:
            first = LocalServer(directory)
            first.stop()
            second = LocalServer(directory)
            try:
                self.assertEqual(second.token, first.token)
                self.assertEqual(second.request('/api/state')[0], 200)
                if POSIX:
                    self.assertEqual(second.request('/api/backup', body={})[0], 200)
                    self.assertEqual(mode(Path(directory) / 'backups'), 0o700)
            finally:
                second.stop()
            (Path(directory) / 'session-token').unlink()
            third = LocalServer(directory)
            try:
                self.assertNotEqual(third.token, first.token)
                self.assertEqual(third.request('/api/state', token=first.token)[0], 403)
                self.assertEqual(third.request('/api/state')[0], 200)
            finally:
                third.stop()


class CommandLineTests(unittest.TestCase):
    def test_help_changes_nothing_on_disk(self):
        with tempfile.TemporaryDirectory(prefix='ml-help-test-') as directory:
            data = Path(directory) / 'data'
            result = subprocess.run([sys.executable, str(ROOT / 'backend/server.py'), '--help'], capture_output=True, text=True, timeout=60,
                                    env={**os.environ, 'ML_WORKSHOP_DATA_DIR': str(data)})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('--port', result.stdout)
            self.assertFalse(data.exists())


class TimeoutTests(unittest.TestCase):
    def test_stalled_connections_are_closed(self):
        # Use the real Handler with a 1-second timeout in a separate process, so this test does not wait 15 seconds.
        script = '''
import socket, sys, threading, time
sys.path.insert(0, sys.argv[1])
import server
assert server.Handler.timeout == 15, server.Handler.timeout
server.Handler.timeout = 1
httpd = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
with socket.create_connection(httpd.server_address, timeout=10) as sock:
    sock.sendall(b'GET /api/health HTTP/1.0\\r\\nHost: 127.0.0.1\\r\\n')
    started = time.monotonic()
    print(repr(sock.recv(100)), time.monotonic() - started < 5)
'''
        with tempfile.TemporaryDirectory(prefix='ml-timeout-test-') as directory:
            result = subprocess.run([sys.executable, '-c', script, str(ROOT / 'backend')], capture_output=True, text=True, timeout=60,
                                    env={**os.environ, 'ML_WORKSHOP_DATA_DIR': directory})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.split(), ["b''", 'True'])


if __name__ == '__main__':
    unittest.main()
