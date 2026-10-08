"""Session token, private files, bad requests and backups, on disposable servers and data folders."""
import json
import os
from pathlib import Path
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

    def test_health_and_book_files_stay_public(self):
        self.assertEqual(self.server.request('/api/health', token='')[0], 200)
        asset = '/api/library/fixture/asset/' + self.book['assets'][0]['path']
        self.assertEqual(self.server.request(asset, token='')[0], 200)
        # The Host and Origin checks still apply to public routes.
        request = urllib.request.Request(self.server.url + '/api/health', headers={'Origin': 'https://example.com'})
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(request, timeout=10)
        self.assertEqual(error.exception.code, 403)

    @unittest.skipUnless(POSIX, 'POSIX file modes')
    def test_data_files_are_private(self):
        backup = json.loads(self.server.request('/api/backup', body={})[2])['filename']
        self.assertEqual(mode(self.data), 0o700)
        for path in [self.data / 'session-token', self.data / 'workshop.sqlite3', self.data / 'backups' / backup]:
            with self.subTest(path=path.name):
                self.assertEqual(mode(path), 0o600)


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


if __name__ == '__main__':
    unittest.main()
