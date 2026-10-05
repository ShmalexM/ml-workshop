"""Book ingestion, source preservation, and safe offline rendering."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from library import Library, import_book
from book_fixture import make_epub, PNG

class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.source=make_epub(self.root/'test.epub')
        self.data=self.root/'data'
    def tearDown(self):self.tmp.cleanup()
    def test_original_bytes_sanitization_and_cross_chapter_links(self):
        book=import_book(self.source,self.data,'fixture')
        library=Library(self.data)
        self.assertEqual(book['count'],2)
        self.assertEqual((library.root/'fixture/source.epub').read_bytes(),self.source.read_bytes())
        image=book['assets'][0]
        self.assertEqual((library.root/'fixture'/image['path']).read_bytes(),PNG)
        self.assertEqual(image['sha256'],hashlib.sha256(PNG).hexdigest())
        html=library.chapter('fixture',1)['html']
        for forbidden in ('<script','<iframe','onerror=','onclick=','style=','javascript:','tracker.png'):
            self.assertNotIn(forbidden,html)
        self.assertIn('href="#books/fixture/2/memory"',html)
        self.assertIn('href="#books/fixture/1/local"',html)
        self.assertIn('tabindex="0"',html)
        self.assertIn('https://example.org/reference',html)
        self.assertEqual(len(library.search('WARP')),2)
        self.assertNotIn('documents',library.catalog()[0])
        for name in ('../book.json','book.json','assets/../../source.epub'):
            with self.assertRaises(KeyError):library.asset('fixture',name)
    def test_reimport_is_idempotent_and_reindexes_older_format(self):
        original=import_book(self.source,self.data,'fixture')
        self.assertEqual(import_book(self.source,self.data,'fixture'),original)
        path=self.data/'library/fixture/book.json'
        old={**original,'importVersion':0,'documents':[]};path.write_text(json.dumps(old))
        updated=import_book(self.source,self.data,'fixture')
        self.assertEqual(updated,original)
        with zipfile.ZipFile(self.source,'a') as archive:archive.writestr('new.txt','different edition')
        with self.assertRaisesRegex(ValueError,'different edition'):import_book(self.source,self.data,'fixture')
        self.assertEqual(json.loads(path.read_text()),original)
    def test_bad_archive_paths_and_ids_leave_no_partial_book(self):
        with zipfile.ZipFile(self.source,'a') as archive:archive.writestr('../escape.txt','unsafe')
        with self.assertRaisesRegex(ValueError,'Unsafe'):import_book(self.source,self.data,'fixture')
        self.assertFalse((self.data/'library/fixture').exists())
        self.assertEqual(list((self.data/'library').iterdir()),[])
        with self.assertRaises(ValueError):import_book(self.source,self.data,'../bad')
    def test_pdf_keeps_original_vectors_and_outline_without_rasterizing(self):
        from pypdf import PdfWriter
        from pypdf.generic import DecodedStreamObject, NameObject
        writer=PdfWriter()
        page=writer.add_blank_page(width=432,height=648)
        stream=DecodedStreamObject();stream.set_data(b'0 0 1 RG 20 20 m 100 100 l S')
        page[NameObject('/Contents')]=writer._add_object(stream)
        writer.add_blank_page(width=432,height=648)
        writer.add_metadata({'/Title':'Vector fixture','/Author':'Test Author'})
        writer.add_outline_item('Vector diagram',0)
        source=self.root/'vector.pdf';writer.write(source)
        book=import_book(source,self.data,'pdf-fixture')
        self.assertEqual(book['count'],2);self.assertEqual(book['toc'][0]['location'],1)
        self.assertEqual(book['title'],'Vector fixture')
        self.assertEqual((self.data/'library/pdf-fixture/source.pdf').read_bytes(),source.read_bytes())
        self.assertEqual(book['assets'],[])

if __name__=='__main__':unittest.main()
