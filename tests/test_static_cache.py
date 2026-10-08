"""Built front-end files: hashed assets are cached for good, the rest are revalidated."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'


@unittest.skipUnless((DIST / 'index.html').is_file(), 'Run npm run build first.')
class StaticCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='ml-static-test-', ignore_cleanup_errors=True)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            cls.port = sock.getsockname()[1]
        cls.url = f'http://127.0.0.1:{cls.port}'
        cls.proc = subprocess.Popen([sys.executable, str(ROOT / 'backend/server.py'), '--port', str(cls.port)],
                                    env={**os.environ, 'ML_WORKSHOP_DATA_DIR': cls.tmp.name},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                urllib.request.urlopen(cls.url + '/api/health').close()
                break
            except OSError:
                time.sleep(.1)
        else:
            raise RuntimeError('Test server unavailable')

    @classmethod
    def tearDownClass(cls):
        # Windows keeps workshop.sqlite3 locked until the server has exited.
        cls.proc.terminate()
        try:
            cls.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            cls.proc.kill()
            cls.proc.wait()
        cls.tmp.cleanup()

    def get(self, path, headers=None):
        try:
            with urllib.request.urlopen(urllib.request.Request(self.url + path, headers=headers or {})) as r:
                return r.status, r.headers, r.read()
        except urllib.error.HTTPError as error:
            return error.code, error.headers, error.read()

    def test_hashed_assets_are_immutable(self):
        asset = next((DIST / 'assets').glob('index-*.js'))
        status, headers, body = self.get('/assets/' + asset.name)
        self.assertEqual(status, 200)
        self.assertEqual(headers['Cache-Control'], 'public, max-age=31536000, immutable')
        self.assertEqual(body, asset.read_bytes())

    def test_unchanged_files_answer_304(self):
        for path in ('/', '/index.html', '/THIRD_PARTY_LICENSES.txt', '/assets/' + next((DIST / 'assets').glob('*.css')).name):
            with self.subTest(path=path):
                status, headers, body = self.get(path)
                self.assertEqual(status, 200)
                self.assertTrue(body)
                etag = headers['ETag']
                if not path.startswith('/assets/'):
                    self.assertEqual(headers['Cache-Control'], 'no-cache')
                    self.assertIn("default-src 'self'", headers['Content-Security-Policy'])
                status, headers, body = self.get(path, {'If-None-Match': etag})
                self.assertEqual((status, body, headers['ETag']), (304, b'', etag))
                status, _, body = self.get(path, {'If-None-Match': '"stale"'})
                self.assertEqual(status, 200)
                self.assertTrue(body)

    def test_app_routes_still_fall_back_to_the_page(self):
        status, headers, body = self.get('/no-such-file')
        self.assertEqual(status, 200)
        self.assertEqual(body, (DIST / 'index.html').read_bytes())
        self.assertEqual(headers['Cache-Control'], 'no-cache')


if __name__ == '__main__':
    unittest.main()
