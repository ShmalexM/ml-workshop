"""Book ingestion, source preservation, and safe offline rendering."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
import library
from library import Library, import_book
from book_fixture import make_epub, make_custom_epub, PNG

def page(body):
    return f'<html><body>{body}</body></html>'

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

class ImportLimitTests(unittest.TestCase):
    """Small EPUBs that unpack to huge books (security review 2026-10-08, finding 2)."""
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.data=self.root/'data'
    def tearDown(self):self.tmp.cleanup()
    def assertNothingPublished(self):
        self.assertEqual(list((self.data/'library').iterdir()),[])
    def test_highly_compressible_chapter_is_rejected_before_parsing(self):
        # 80 MB of XHTML compresses to well under 1 MB.
        source=make_custom_epub(self.root/'bomb.epub',{'big.xhtml':page(('<p>'+'a'*1000+'</p>')*(80*1024))})
        self.assertLess(source.stat().st_size,1024*1024)
        with self.assertRaisesRegex(ValueError,'larger than 8 MB when unpacked'):import_book(source,self.data,'bomb')
        self.assertNothingPublished()
    def test_repeated_spine_entries_become_one_section(self):
        source=make_custom_epub(self.root/'repeat.epub',{'one.xhtml':page('<h1>Only</h1>'+('<p>'+'b'*1000+'</p>')*1024)},spine=['one.xhtml']*60)
        self.assertLess(source.stat().st_size,10000)
        book=import_book(source,self.data,'repeat')
        self.assertEqual(book['count'],1);self.assertEqual(len(book['toc']),1)
        folder=self.data/'library/repeat'
        self.assertEqual([p.name for p in (folder/'chapters').iterdir()],['1.json'])
        self.assertLess(sum(p.stat().st_size for p in folder.rglob('*')),4*1024*1024)
    def test_per_chapter_size_cap(self):
        chapter=page('<p>'+'c'*(8*1024*1024)+'</p>')
        source=make_custom_epub(self.root/'large.epub',{'one.xhtml':page('<p>small</p>'),'two.xhtml':chapter})
        with self.assertRaisesRegex(ValueError,'larger than 8 MB when unpacked'):import_book(source,self.data,'large')
        self.assertNothingPublished()
        # The same rule counts the bytes actually read, so it applies below the header check too.
        with patch.object(library,'MAX_SECTION_BYTES',1000):
            source=make_custom_epub(self.root/'small.epub',{'one.xhtml':page('<p>'+'d'*2000+'</p>')})
            with self.assertRaisesRegex(ValueError,'over the import limit'):import_book(source,self.data,'small')
        self.assertNothingPublished()
    def test_section_count_and_total_output_caps(self):
        chapters={f's{i}.xhtml':page(f'<p>Section {i}</p>') for i in range(2001)}
        with self.assertRaisesRegex(ValueError,'more than 2,000 sections'):
            import_book(make_custom_epub(self.root/'many.epub',chapters),self.data,'many')
        self.assertNothingPublished()
        chapters={f's{i}.xhtml':page('<p>'+'e'*3000+'</p>') for i in range(5)}
        with patch.object(library,'MAX_OUTPUT_BYTES',10000):
            with self.assertRaisesRegex(ValueError,'more than .* of text and markup'):
                import_book(make_custom_epub(self.root/'output.epub',chapters),self.data,'output')
        self.assertNothingPublished()
        self.assertEqual(import_book(make_custom_epub(self.root/'fits.epub',chapters),self.data,'fits')['count'],5)
    def test_nested_entities_are_refused_and_plain_ones_work(self):
        nested='<!DOCTYPE html [<!ENTITY a "xxxxxxxxxxxx"><!ENTITY b "&a;&a;&a;&a;">]>'+page('<p>&b;</p>')
        with self.assertRaisesRegex(ValueError,'XML entities'):
            import_book(make_custom_epub(self.root/'nested.epub',{'one.xhtml':nested}),self.data,'nested')
        plain='<!DOCTYPE html [<!ENTITY nbsp "&#160;">]>'+page('<p>a&nbsp;b</p>')
        book=import_book(make_custom_epub(self.root/'plain.epub',{'one.xhtml':plain}),self.data,'plain')
        self.assertIn('a\xa0b',Library(self.data).chapter('plain',1)['html'])
    def test_pdf_page_cap(self):
        from pypdf import PdfWriter
        writer=PdfWriter();writer.add_blank_page(width=100,height=100);writer.add_blank_page(width=100,height=100)
        source=self.root/'pages.pdf';writer.write(source)
        with patch.object(library,'MAX_PDF_PAGES',1):
            with self.assertRaisesRegex(ValueError,'more than 1 pages'):import_book(source,self.data,'pages')
        self.assertNothingPublished()
        book=import_book(source,self.data,'pages')
        self.assertEqual(book['count'],2)
        self.assertEqual(Library(self.data).chapter('pages',2)['label'],'2')

class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.data=self.root/'data'
        self.book=import_book(make_epub(self.root/'test.epub'),self.data,'fixture')
        self.folder=self.data/'library/fixture'
    def tearDown(self):self.tmp.cleanup()
    def test_summary_and_chapters_are_stored_separately(self):
        stored=json.loads((self.folder/'book.json').read_text())
        self.assertNotIn('documents',stored);self.assertEqual(stored['importVersion'],2)
        self.assertEqual(sorted(p.name for p in (self.folder/'chapters').iterdir()),['1.json','2.json'])
        self.assertEqual(Library(self.data).chapter('fixture',2)['title'],'Memory')
        for location in (0,3):
            with self.assertRaises(KeyError):Library(self.data).chapter('fixture',location)
    def test_version_1_book_is_split_once(self):
        documents=[json.loads((self.folder/f'chapters/{n}.json').read_text()) for n in (1,2)]
        legacy={**self.book,'importVersion':1,'documents':documents}
        shutil.rmtree(self.folder/'chapters');(self.folder/'book.json').write_text(json.dumps(legacy))
        library_=Library(self.data)
        self.assertEqual(library_.catalog()[0]['count'],2)
        stored=json.loads((self.folder/'book.json').read_text())
        self.assertNotIn('documents',stored);self.assertEqual(stored['count'],2)
        self.assertEqual(library_.chapter('fixture',1),documents[0])
        self.assertEqual(library_.chapter('fixture',2)['title'],'Memory')
        self.assertEqual([hit['location'] for hit in library_.search('warp')],[1,2])
        self.assertEqual(list(self.folder.glob('.*')),[])
        # A command-line reimport rebuilds the old index with the current importer.
        self.assertEqual(import_book(self.root/'test.epub',self.data,'fixture')['importVersion'],2)
    def test_remove_deletes_only_that_book_folder(self):
        import_book(make_epub(self.root/'other.epub'),self.data,'other')
        outside=self.root/'outside';outside.mkdir();(outside/'book.json').write_text(json.dumps({**self.book,'id':'linked'}))
        os.symlink(outside,self.data/'library/linked')
        library_=Library(self.data)
        for book_id in ('linked','../outside','..','',None,'missing','fixture/../other'):
            with self.subTest(book_id=book_id),self.assertRaises(KeyError):library_.remove(book_id)
        self.assertTrue((outside/'book.json').is_file())
        library_.remove('fixture')
        self.assertFalse(self.folder.exists())
        self.assertEqual(sorted(p.name for p in (self.data/'library').iterdir()),['linked','other'])
        self.assertTrue((self.data/'library/other/chapters/1.json').is_file())
        self.assertNotIn('fixture',{book['id'] for book in library_.catalog()})
        with self.assertRaises(KeyError):library_.chapter('fixture',1)
        self.assertEqual(list((self.data/'library').glob('.*')),[])

if __name__=='__main__':unittest.main()
