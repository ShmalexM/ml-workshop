"""Browser uploads use synthetic books and disposable server/data directories."""
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.parse import urlencode
import urllib.error
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'backend'))
from book_import import import_upload, sweep_staging
from book_study import study_guides, INFERENCE_GUIDE_EDITION
from library import Library
from book_fixture import make_custom_epub, make_epub
from server_fixture import server_token


class UploadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='book-upload-test-')
        cls.root = Path(cls.tmp.name)
        cls.data = cls.root/'data'
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0)); cls.port = sock.getsockname()[1]
        cls.url = f'http://127.0.0.1:{cls.port}'
        cls.proc = subprocess.Popen([sys.executable, str(ROOT/'backend/server.py'), '--port', str(cls.port)],
                                   env={**os.environ, 'ML_WORKSHOP_DATA_DIR': str(cls.data)},
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls.token = server_token(cls.url, cls.data, cls.proc)

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate(); cls.proc.wait(); cls.tmp.cleanup()

    def upload(self, raw, filename='book.epub', book='', headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        try:
            connection.request('POST', '/api/library/import?'+urlencode(dict(filename=filename, book=book)), raw,
                               {'Content-Type': 'application/octet-stream', 'X-Workshop-Token': self.token, **(headers or {})})
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally: connection.close()

    def get(self, path):
        return urllib.request.urlopen(urllib.request.Request(self.url+path, headers={'X-Workshop-Token': self.token}), timeout=10)

    def post_json(self, path, payload, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        try:
            connection.request('POST', path, json.dumps(payload).encode(),
                               {'Content-Type': 'application/json', 'X-Workshop-Token': self.token, **(headers or {})})
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally: connection.close()

    def test_remove_book_needs_write_token_and_keeps_notes(self):
        source = make_custom_epub(self.root/'remove.epub', {'one.xhtml': '<html><body><h1>Remove me</h1></body></html>'})
        status, result = self.upload(source.read_bytes(), 'remove.epub')
        self.assertEqual(status, 200, result); book_id = result['book']['id']
        state = dict(bookId=book_id, location=1, notes='Keep these notes', bookmarks=[], completed=[], updatedAt=300)
        self.assertEqual(self.post_json('/api/library/state', state)[0], 200)
        for headers in ({'X-Workshop-Token': 'wrong'}, {'Origin': 'https://example.org'},
                        {'Sec-Fetch-Site': 'cross-site'}, {'Host': 'attacker.example'}):
            with self.subTest(headers=headers):
                self.assertEqual(self.post_json('/api/library/remove', {'bookId': book_id}, headers)[0], 403)
        for bad in ('../library', 'missing-book', 7, None):
            with self.subTest(bad=bad):
                self.assertEqual(self.post_json('/api/library/remove', {'bookId': bad})[0], 404)
        self.assertTrue((self.data/'library'/book_id/'source.epub').is_file())
        self.assertEqual(self.post_json('/api/library/remove', {'bookId': book_id}), (200, {'ok': True}))
        self.assertFalse((self.data/'library'/book_id).exists())
        with self.get('/api/library') as response: library = json.load(response)
        self.assertNotIn(book_id, [book['id'] for book in library['books']])
        self.assertEqual(library['readingState'][book_id]['notes'], 'Keep these notes')
        with self.assertRaises(urllib.error.HTTPError) as error: self.get(f'/api/library/{book_id}/chapter/1')
        self.assertEqual(error.exception.code, 404)
        # Importing the same file again brings back the saved notes.
        status, result = self.upload(source.read_bytes(), 'remove.epub')
        self.assertEqual(status, 200, result); self.assertEqual(result['readingState']['notes'], 'Keep these notes')

    def test_damaged_book_is_listed_separately_and_can_be_removed(self):
        source = make_custom_epub(self.root/'damaged.epub', {'one.xhtml': '<html><body><h1>Damaged later</h1></body></html>'})
        status, result = self.upload(source.read_bytes(), 'damaged.epub')
        self.assertEqual(status, 200, result); book_id = result['book']['id']
        (self.data/'library'/book_id/'book.json').write_text('{"title": "cut off')
        with self.get('/api/library') as response:library = json.load(response)
        self.assertNotIn(book_id, [book['id'] for book in library['books']])
        self.assertIn(book_id, library['unreadable'])
        # Importing the same file again asks for removal first instead of failing with a server error.
        status, result = self.upload(source.read_bytes(), 'damaged.epub')
        self.assertEqual(status, 409, result)
        self.assertIn('Remove it in Books', result['error'])
        self.assertEqual(self.post_json('/api/library/remove', {'bookId': book_id}), (200, {'ok': True}))
        with self.get('/api/library') as response:self.assertNotIn(book_id, json.load(response)['unreadable'])
        status, result = self.upload(source.read_bytes(), 'damaged.epub')
        self.assertEqual((status, result['book']['id']), (200, book_id))

    def test_over_limit_epub_returns_plain_error_and_leaves_nothing(self):
        before = Library(self.data).catalog()
        source = make_custom_epub(self.root/'bomb.epub', {'big.xhtml': '<html><body>' + '<p>' + 'a'*(9 << 20) + '</p></body></html>'})
        status, result = self.upload(source.read_bytes(), 'bomb.epub')
        self.assertEqual(status, 400); self.assertIn('larger than 8 MB when unpacked', result['error'])
        self.assertEqual(Library(self.data).catalog(), before)
        self.assertEqual(list(self.data.glob('.upload-*')) + list(self.data.glob('.parse-*')), [])

    def test_upload_preserves_original_and_duplicate_reading_state(self):
        source = make_epub(self.root/'fixture.epub'); raw = source.read_bytes()
        status, result = self.upload(raw, '図とメモ.epub')
        self.assertEqual(status, 200, result)
        book = result['book']; book_id = book['id']
        self.assertFalse(result['alreadyImported'])
        self.assertEqual((self.data/'library'/book_id/'source.epub').read_bytes(), raw)
        self.assertNotIn('documents', book)
        payload = dict(bookId=book_id, location=2, notes='Keep this observation', bookmarks=[2], completed=[], updatedAt=200)
        request = urllib.request.Request(self.url+'/api/library/state', json.dumps(payload).encode(),
                                         {'Content-Type': 'application/json', 'X-Workshop-Token': self.token})
        with urllib.request.urlopen(request) as response: self.assertEqual(response.status, 200)
        status, again = self.upload(raw, 'renamed.epub')
        self.assertEqual(status, 200); self.assertTrue(again['alreadyImported'])
        self.assertEqual(again['book']['id'], book_id)
        self.assertEqual(again['readingState']['notes'], payload['notes'])
        self.assertEqual(again['readingState']['location'], 2)
        self.assertEqual(again['readingState']['bookmarks'], [2])

    def test_pdf_rendering_source_and_filename_fallback(self):
        from pypdf import PdfWriter
        source = self.root/'source.pdf'
        writer = PdfWriter(); writer.add_blank_page(width=432, height=648); writer.write(source)
        status, result = self.upload(source.read_bytes(), 'Diagrams – 日本語.pdf')
        self.assertEqual(status, 200, result)
        self.assertEqual(result['book']['title'], 'Diagrams – 日本語')
        self.assertEqual(result['book']['format'], 'pdf')
        url = self.url+'/api/library/'+result['book']['id']+'/asset/source.pdf'
        with urllib.request.urlopen(url) as response: self.assertEqual(response.read(), source.read_bytes())
        writer.encrypt('test-only'); writer.write(source)
        status, result = self.upload(source.read_bytes(), 'locked.pdf')
        self.assertEqual(status, 400); self.assertIn('Encrypted', result['error'])

    def test_suggested_book_identity_conflicts_and_other_edition(self):
        source = make_epub(self.root/'suggested.epub')
        status, result = self.upload(source.read_bytes(), 'wrong.epub', 'gpu-glossary')
        self.assertEqual(status, 400); self.assertIn('Choose your copy of GPU Glossary', result['error'])
        with zipfile.ZipFile(source) as archive: files = {n: archive.read(n) for n in archive.namelist()}
        files['OEBPS/book.opf'] = files['OEBPS/book.opf'].replace(b'Fixture Book', b'GPU Glossary')
        with zipfile.ZipFile(source, 'w') as archive:
            for name, raw in files.items(): archive.writestr(name, raw)
        status, result = self.upload(source.read_bytes(), 'GPU Glossary.epub', 'gpu-glossary')
        self.assertEqual(status, 200, result); self.assertEqual(result['book']['id'], 'gpu-glossary')
        original = Library(self.data).book('gpu-glossary')['sha256']
        with zipfile.ZipFile(source, 'a') as archive: archive.writestr('new-edition.txt', 'new edition')
        status, result = self.upload(source.read_bytes(), 'GPU Glossary.epub', 'gpu-glossary')
        self.assertEqual(status, 409); self.assertIn('Add another book', result['error'])
        self.assertEqual(Library(self.data).book('gpu-glossary')['sha256'], original)
        status, result = self.upload(source.read_bytes(), 'GPU Glossary.epub')
        self.assertEqual(status, 200); self.assertNotEqual(result['book']['id'], 'gpu-glossary')

    def test_invalid_uploads_and_guards_leave_library_unchanged(self):
        before = Library(self.data).catalog()
        cases = [
            (b'bad', 'bad.txt', '', {}, 400), (b'', 'empty.pdf', '', {}, 413),
            (b'bad', '../escape.pdf', '', {}, 400), (b'bad', 'bad.pdf', '../escape', {}, 400),
            (b'bad', 'bad.pdf', '', {'Content-Length': str(100*1024*1024+1)}, 413),
            (b'bad', 'bad.pdf', '', {'Content-Type': 'application/json'}, 415),
            (b'bad', 'bad.pdf', '', {'X-Workshop-Token': 'wrong'}, 403),
            (b'bad', 'bad.pdf', '', {'Origin': 'https://example.org'}, 403),
            (b'bad', 'bad.pdf', '', {'Host': 'attacker.example'}, 403),
            (b'bad', 'bad.epub', '', {}, 400), (b'bad', 'bad.pdf', '', {}, 400),
        ]
        for raw, filename, book, headers, expected in cases:
            with self.subTest(filename=filename, headers=headers):
                status, result = self.upload(raw, filename, book, headers)
                self.assertEqual(status, expected, result)
        self.assertEqual(Library(self.data).catalog(), before)
        self.assertEqual(list(self.data.glob('.upload-*')), [])
        self.assertEqual(list(self.data.glob('.parse-*')), [])

    def test_incomplete_upload_releases_lock_without_partial_book(self):
        before = Library(self.data).catalog()
        with socket.create_connection(('127.0.0.1', self.port), timeout=5) as connection:
            connection.sendall((f'POST /api/library/import?filename=interrupted.pdf HTTP/1.0\r\nHost: 127.0.0.1:{self.port}\r\nX-Workshop-Token: {self.token}\r\nContent-Type: application/octet-stream\r\nContent-Length: 100\r\n\r\npartial').encode())
            connection.shutdown(socket.SHUT_WR)
            response = b''
            while chunk := connection.recv(4096): response += chunk
        self.assertIn(b'400 Bad Request', response)
        status, result = self.upload(b'bad', 'retry.pdf')
        self.assertEqual(status, 400, result)  # Not locked after the interrupted upload.
        self.assertEqual(Library(self.data).catalog(), before)

    def test_concurrent_upload_is_rejected_while_other_requests_work(self):
        with socket.create_connection(('127.0.0.1', self.port), timeout=5) as connection:
            connection.sendall((f'POST /api/library/import?filename=slow.pdf HTTP/1.0\r\nHost: 127.0.0.1:{self.port}\r\nX-Workshop-Token: {self.token}\r\nContent-Type: application/octet-stream\r\nContent-Length: 100\r\n\r\npartial').encode())
            for _ in range(50):
                if list(self.data.glob('.upload-*/upload.pdf')): break
                time.sleep(.02)
            else: self.fail('First upload did not begin')
            status, result = self.upload(b'bad', 'second.pdf')
            self.assertEqual(status, 409); self.assertIn('Another book', result['error'])
            with urllib.request.urlopen(self.url+'/api/health') as response: self.assertEqual(response.status, 200)
            connection.shutdown(socket.SHUT_WR)
            while connection.recv(4096): pass


class WorkerTests(unittest.TestCase):
    def test_worker_timeout_never_publishes_partial_book(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); source = make_epub(root/'source.epub')
            with patch('book_import.subprocess.run', side_effect=subprocess.TimeoutExpired('worker', 90)):
                with self.assertRaisesRegex(ValueError, 'too long'): import_upload(source, root, source.name)
            self.assertEqual(Library(root).catalog(), [])
            self.assertEqual(list(root.glob('.parse-*')), [])

    def test_stale_staging_folders_are_swept(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stale = [root/'.upload-old', root/'.parse-old', root/'library/.import-old', root/'library/.removing-old']
            fresh = root/'.upload-fresh'
            for folder in stale + [fresh]: (folder/'partial').mkdir(parents=True)
            old = time.time() - 2*3600
            for folder in stale: os.utime(folder, (old, old))
            sweep_staging(root)
            self.assertEqual([folder for folder in stale if folder.exists()], [])
            self.assertTrue(fresh.is_dir()); self.assertTrue((root/'library').is_dir())

    def test_glossary_guides_match_section_titles_without_source_file_names(self):
        class FixtureLibrary:
            def book(self, book_id):
                if book_id != 'gpu-glossary': raise KeyError(book_id)
                titles = ['What is a CUDA Kernel?', 'What is a Thread Block?', 'Thread Block Grid', 'Unrelated notes']
                return dict(title='GPU Glossary', format='pdf', sha256='any', count=4,
                            toc=[dict(title=t, location=i+1, label=str(i+1), depth=0) for i, t in enumerate(titles)])
        guides = study_guides(FixtureLibrary())
        self.assertEqual([guide['id'] for guide in guides], ['gpu-threads'])
        self.assertEqual([reading['location'] for reading in guides[0]['readings']], [1, 2, 3])

    def test_numeric_guides_only_apply_to_verified_pdf_edition(self):
        class FixtureLibrary:
            def book(self, book_id):
                if book_id != 'inference-engineering': raise KeyError(book_id)
                return dict(title='Inference Engineering', format=self.format, sha256=self.sha, toc=[], count=259)
        library = FixtureLibrary()
        for kind, sha in [('epub', INFERENCE_GUIDE_EDITION), ('pdf', 'different-edition')]:
            library.format, library.sha = kind, sha
            self.assertEqual(study_guides(library), [])
        library.format, library.sha = 'pdf', INFERENCE_GUIDE_EDITION
        self.assertEqual(len(study_guides(library)), 8)


if __name__ == '__main__': unittest.main()
