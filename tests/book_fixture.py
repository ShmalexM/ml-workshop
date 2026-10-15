"""Original synthetic EPUB fixture; no copyrighted books are used by tests."""
import base64
from pathlib import Path
import zipfile

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aWQAAAABJRU5ErkJggg==')

def make_epub(path):
    path = Path(path)
    files = {
        'mimetype': 'application/epub+zip',
        'META-INF/container.xml': '<container><rootfiles><rootfile full-path="OEBPS/book.opf"/></rootfiles></container>',
        'OEBPS/book.opf': '''<package><metadata><title>Fixture Book</title><creator>Test Author</creator><rights>Original test fixture</rights></metadata><manifest>
        <item id="one" href="one.xhtml" media-type="application/xhtml+xml"/>
        <item id="two" href="two.xhtml" media-type="application/xhtml+xml"/>
        <item id="pic" href="figure.png" media-type="image/png"/>
        </manifest><spine><itemref idref="one"/><itemref idref="two"/></spine></package>''',
        'OEBPS/one.xhtml': '''<html><body><h1>Thread mapping</h1><p>A synthetic warp diagram.</p>
        <img src="figure.png" alt="One pixel fixture" onerror="alert(1)"/>
        <a href="two.xhtml#memory">Memory chapter</a><a href="#local">Same chapter</a>
        <a href="https://example.org/reference">External reference</a>
        <script>alert('do not run')</script><iframe src="https://example.org"/>
        <a href="javascript:alert(1)">Bad link</a><img src="https://example.org/tracker.png"/>
        <p id="local" style="color:red" onclick="bad()">Local anchor</p></body></html>''',
        'OEBPS/two.xhtml': '<html><body><h1 id="memory">Memory</h1><p>The warp uses shared memory.</p></body></html>',
        'OEBPS/figure.png': PNG,
    }
    with zipfile.ZipFile(path,'w') as archive:
        for name, content in files.items(): archive.writestr(name,content)
    return path

def make_custom_epub(path, chapters, spine=None, metadata=''):
    """Build a compressed EPUB from {name: xhtml}. spine lists chapter names, repeats allowed."""
    path = Path(path)
    spine = list(chapters) if spine is None else spine
    ids = {name: f'c{i}' for i, name in enumerate(chapters)}
    manifest = ''.join(f'<item id="{ids[name]}" href="{name}" media-type="application/xhtml+xml"/>' for name in chapters)
    itemrefs = ''.join(f'<itemref idref="{ids[name]}"/>' for name in spine)
    opf = (f'<package><metadata><title>Custom Book</title>{metadata}</metadata><manifest>{manifest}</manifest>'
           f'<spine>{itemrefs}</spine></package>')
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('mimetype', 'application/epub+zip')
        archive.writestr('META-INF/container.xml', '<container><rootfiles><rootfile full-path="OEBPS/book.opf"/></rootfiles></container>')
        archive.writestr('OEBPS/book.opf', opf)
        for name, content in chapters.items():
            archive.writestr('OEBPS/' + name, content)
    return path


# Synthetic files for the other formats. All content is written by the tests.

def png(width=1, height=1):
    """A valid PNG of any size, filled with one grey value."""
    import struct, zlib
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    rows = b''.join(b'\x00' + b'\x80' * width for _ in range(height))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 0, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b''))

def write(path, content):
    path = Path(path)
    if isinstance(content, str):
        path.write_text(content, encoding='utf-8')
    else:
        path.write_bytes(content)
    return path

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'

def docx_body(body):
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{W}" xmlns:r="{R}" '
            'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">'
            f'<w:body>{body}</w:body></w:document>')

def para(text, style=None, numbering=None, runs=None):
    props = ''
    if style or numbering:
        props = '<w:pPr>' + (f'<w:pStyle w:val="{style}"/>' if style else '')
        if numbering:
            props += f'<w:numPr><w:ilvl w:val="{numbering[0]}"/><w:numId w:val="{numbering[1]}"/></w:numPr>'
        props += '</w:pPr>'
    return f'<w:p>{props}{runs if runs is not None else f"<w:r><w:t xml:space=\"preserve\">{text}</w:t></w:r>"}</w:p>'

def make_docx(path, body, rels='', files=None, document=None, core=None):
    """A Word file. body is WordprocessingML inside <w:body>; rels adds relationships of word/document.xml."""
    styles = (f'<w:styles xmlns:w="{W}"><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/></w:style>'
              '<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/></w:style>'
              '<w:style w:type="paragraph" w:styleId="Code"><w:name w:val="Code"/></w:style></w:styles>')
    numbering = (f'<w:numbering xmlns:w="{W}"><w:abstractNum w:abstractNumId="0"><w:lvl w:ilvl="0"><w:numFmt w:val="bullet"/></w:lvl>'
                 '<w:lvl w:ilvl="1"><w:numFmt w:val="bullet"/></w:lvl></w:abstractNum>'
                 '<w:abstractNum w:abstractNumId="1"><w:lvl w:ilvl="0"><w:numFmt w:val="decimal"/></w:lvl></w:abstractNum>'
                 '<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num><w:num w:numId="2"><w:abstractNumId w:val="1"/></w:num></w:numbering>')
    relationships = ('<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                     '<Relationship Id="rStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
                     '<Relationship Id="rNumbering" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>'
                     f'{rels}</Relationships>')
    entries = {
        '[Content_Types].xml': '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
        '_rels/.rels': '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        'word/document.xml': document if document is not None else docx_body(body),
        'word/_rels/document.xml.rels': relationships,
        'word/styles.xml': styles,
        'word/numbering.xml': numbering,
        'docProps/core.xml': core if core is not None else '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Fixture Report</dc:title><dc:creator>Test Author</dc:creator></cp:coreProperties>',
        **(files or {}),
    }
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return Path(path)

def make_ipynb(path, cells, metadata=None):
    import json
    notebook = {'nbformat': 4, 'nbformat_minor': 5, 'cells': cells,
                'metadata': metadata if metadata is not None else {'kernelspec': {'language': 'python', 'name': 'python3'}}}
    return write(path, json.dumps(notebook))

def make_no_text_pdf(path, pages=2, outline=False):
    """A PDF whose pages hold only vector shapes and an image, with no text layer."""
    from pypdf import PdfWriter
    from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, NameObject, NumberObject, StreamObject
    import zlib
    writer = PdfWriter()
    for number in range(pages):
        page = writer.add_blank_page(width=300, height=400)
        image = StreamObject()
        image._data = zlib.compress(b'\x40\x80\xc0\xff' * 4)
        image.update({NameObject('/Type'): NameObject('/XObject'), NameObject('/Subtype'): NameObject('/Image'),
                      NameObject('/Width'): NumberObject(4), NameObject('/Height'): NumberObject(4),
                      NameObject('/ColorSpace'): NameObject('/DeviceGray'), NameObject('/BitsPerComponent'): NumberObject(8),
                      NameObject('/Filter'): NameObject('/FlateDecode')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/XObject'): DictionaryObject({NameObject('/Im1'): writer._add_object(image)})})
        content = DecodedStreamObject()
        content.set_data(f'0 0 1 rg 20 20 260 {100 + number * 10} re f q 100 0 0 100 100 250 cm /Im1 Do Q'.encode())
        page[NameObject('/Contents')] = writer._add_object(content)
    if outline:
        writer.add_outline_item('Cover art', 0)
        writer.add_outline_item('Back page', pages - 1)
    writer.write(path)
    return Path(path)
