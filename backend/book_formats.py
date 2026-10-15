"""Imports for Markdown, plain text, HTML, Word (.docx), Jupyter notebooks and images.

Every format becomes ElementTree blocks, and then chapters through the same sanitizer as EPUB
(library.sanitized_html): an allowlist of tags, book classes and ids prefixed with `bk-`, links
only to http(s) or to other sections, and images only from files stored with the book. Nothing
in an imported file runs, and nothing loads from the network. Every file is untrusted, so each
format has size, count and nesting limits, and a failed import leaves nothing behind
(library.import_book removes the temporary folder).
"""
import base64
import binascii
import codecs
from html import escape
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import posixpath
import re
import struct
from urllib.parse import unquote
from xml.etree import ElementTree as ET
import zipfile

import library as lib
from book_markdown import Builder, Markdown, append_text, code_block

SECTION_SPLIT = 400_000        # characters of text before a long section is split at a block boundary
TEXT_SECTION = 60_000          # characters in one section of a plain-text file
MAX_INLINE_IMAGE = 10 << 20    # one data: image in HTML, or one notebook output or attachment
MAX_DOC_IMAGE = 32 << 20       # one picture inside a Word file
MAX_IMAGE_PIXELS = 64_000_000  # width × height of any stored image
MAX_HTML_DEPTH = 200
MAX_DOCX_XML = 16 << 20        # word/document.xml, unpacked
MAX_DOCX_PART = 4 << 20        # styles, numbering, relationships and properties, unpacked
MAX_DOCX_DEPTH = 12            # tables inside tables, and content controls
MAX_CELLS = 5000
MAX_OUTPUTS = 50               # outputs shown for one notebook cell
MAX_OUTPUT_TEXT = 50_000       # characters shown from one notebook text output
MAX_OUTPUT_HTML = 1 << 20      # an HTML table output larger than this is shown as plain text
RIGHTS = 'Personal local copy. Rights remain with the original authors; not included in the open-source app.'
EXTENSIONS = {'image/png': '.png', 'image/jpeg': '.jpg', 'image/gif': '.gif', 'image/webp': '.webp'}
HEADINGS = {f'h{n}': n for n in range(1, 7)}
CONTROL = re.compile(r'[\x01-\x08\x0b\x0e-\x1f\x7f]')
ANSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
DATA_IMAGE = re.compile(r'data:(image/(?:png|jpeg|jpg|gif|webp))(?:;[^,;]{0,100})*;base64,', re.I)
WHITESPACE = re.compile(r'\s+')


# Images ---------------------------------------------------------------------------------------

def image_type(raw):
    """The media type of a PNG, JPEG, GIF or WebP file, from its first bytes. SVG is not accepted."""
    if raw.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    if raw.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    if raw[:6] in (b'GIF87a', b'GIF89a'):
        return 'image/gif'
    if raw[:4] == b'RIFF' and raw[8:12] == b'WEBP':
        return 'image/webp'
    return None


def image_size(raw, kind):
    """(width, height) from the image header, or None if it cannot be read."""
    try:
        if kind == 'image/png':
            return struct.unpack('>II', raw[16:24]) if raw[12:16] == b'IHDR' else None
        if kind == 'image/gif':
            return struct.unpack('<HH', raw[6:10])
        if kind == 'image/webp':
            chunk = raw[12:16]
            if chunk == b'VP8X':
                return int.from_bytes(raw[24:27], 'little') + 1, int.from_bytes(raw[27:30], 'little') + 1
            if chunk == b'VP8L':
                bits = int.from_bytes(raw[21:25], 'little')
                return (bits & 0x3fff) + 1, ((bits >> 14) & 0x3fff) + 1
            if chunk == b'VP8 ':
                width, height = struct.unpack('<HH', raw[26:30])
                return width & 0x3fff, height & 0x3fff
            return None
        if kind == 'image/jpeg':
            i = 2
            while i + 9 < len(raw):
                if raw[i] != 0xFF:
                    return None
                marker = raw[i + 1]
                if marker == 0xFF:
                    i += 1
                    continue
                if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                    i += 2
                    continue
                length = struct.unpack('>H', raw[i + 2:i + 4])[0]
                if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                    height, width = struct.unpack('>HH', raw[i + 5:i + 9])
                    return width, height
                if length < 2:
                    return None
                i += 2 + length
    except struct.error:
        return None
    return None


def checked_image(raw):
    """The media type of raw if it is a supported image within the pixel limit, else None."""
    kind = image_type(raw)
    size = image_size(raw, kind) if kind else None
    if not size or not all(size) or size[0] * size[1] > MAX_IMAGE_PIXELS:
        return None
    return kind


class Images:
    """Images stored with one book. Each is checked, counted against the book's image limits and
    written once, named by its hash. `assets` maps the name used in the chapter to the stored file."""
    def __init__(self, folder):
        self.folder = Path(folder)
        self.paths = {}
        self.records = []
        self.assets = {}
        self.bytes = 0

    def add(self, name, raw):
        kind = checked_image(raw)
        if not kind:
            return None
        digest = hashlib.sha256(raw).hexdigest()
        path = self.paths.get(digest)
        if path is None:
            if len(self.records) >= lib.MAX_IMAGES:
                raise ValueError(f'This file has more than {lib.MAX_IMAGES:,} images, which is over the import limit.')
            self.bytes += len(raw)
            if self.bytes > lib.MAX_IMAGE_BYTES:
                raise ValueError(f'The images in this file are larger than {lib.megabytes(lib.MAX_IMAGE_BYTES)} in total, which is over the import limit.')
            path = f'assets/{digest[:16]}{EXTENSIONS[kind]}'
            (self.folder/'assets').mkdir(exist_ok=True)
            (self.folder/path).write_bytes(raw)
            self.paths[digest] = path
            self.records.append(dict(source=name[:200], path=path, sha256=digest, bytes=len(raw), mediaType=kind))
        self.assets[name] = path
        return name


def decoded_image(value, limit=None):
    """Bytes of a base64 image, or None if it is not valid base64 or is larger than limit."""
    limit = limit or MAX_INLINE_IMAGE
    value = WHITESPACE.sub('', value)
    if not value or len(value) > limit * 4 // 3 + 4:
        return None
    try:
        return base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        return None


def data_image(src):
    """Bytes of a data:image/...;base64 URL, or None."""
    match = DATA_IMAGE.match(src)
    return decoded_image(src[match.end():]) if match else None


# Text and chapters ----------------------------------------------------------------------------

def read_text(source, kind):
    """Decode a text file: UTF-8 (with or without a BOM), UTF-16 with a BOM, or Windows-1252."""
    raw = Path(source).read_bytes()
    if raw.startswith(codecs.BOM_UTF8):
        text = raw[3:].decode('utf-8', 'replace')
    elif raw.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        text = raw.decode('utf-16', 'replace')
    else:
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError:
            text = raw.decode('cp1252', 'replace')
    if '\x00' in text:
        raise ValueError(f'This file does not look like {kind}. It may be a binary file with the wrong extension.')
    return CONTROL.sub('', text.replace('\x0c', '\n\n'))


def text_length(element):
    return sum(len(part) for part in element.itertext())


def heading_level(block):
    """The heading level that starts this block: an h1-h6, or a section whose first child is one."""
    level = HEADINGS.get(block.tag)
    if level or block.tag not in ('section', 'article', 'div', 'header', 'main'):
        return level
    for first in block:
        return HEADINGS.get(first.tag)
    return None


def split_sections(blocks):
    """Split a document at its top-level headings, then split very long sections by size.

    A document with one title heading and several headings below it splits at the second level.
    """
    levels = [heading_level(block) for block in blocks]
    present = sorted({level for level in levels if level})
    split = None
    if present:
        top = present[0]
        split = top if levels.count(top) >= 2 else (present[1] if len(present) > 1 else None)
    sections, current = [], []
    for block, level in zip(blocks, levels):
        if split and level == split and current:
            sections.append(current)
            current = []
        current.append(block)
    if current:
        sections.append(current)
    out = []
    for section in sections:
        part, size = [], 0
        for block in section:
            length = text_length(block)
            if part and size + length > SECTION_SPLIT:
                out.append(part)
                part, size = [], 0
            part.append(block)
            size += length
        out.append(part)
    return out


def section_title(blocks):
    for block in blocks:
        for node in block.iter():
            if node.tag in ('h1', 'h2', 'h3'):
                title = lib.normalized(''.join(node.itertext()))
                if title:
                    return title
    return ''


def relink(sections):
    """Point #fragment links at the section that holds the fragment, so they work across sections."""
    where = {}
    for number, blocks in enumerate(sections, 1):
        for block in blocks:
            for node in block.iter():
                value = node.get('id')
                if value:
                    where.setdefault(value, number)
    for number, blocks in enumerate(sections, 1):
        for block in blocks:
            for node in block.iter('a'):
                href = node.get('href', '')
                target = where.get(unquote(href[1:])) if href.startswith('#') and len(href) > 1 else None
                if target:
                    node.set('href', f'section-{target}.html{href}')


def write_chapters(sections, folder, book_id, images, title):
    """Sanitize and write each section as a chapter. Returns the contents and the count of sections with text."""
    if len(sections) > lib.MAX_SECTIONS:
        raise ValueError(f'This file has more than {lib.MAX_SECTIONS:,} sections, which is over the import limit.')
    relink(sections)
    names = {f'section-{n}.html': n for n in range(1, len(sections) + 1)}
    writer = lib.ChapterWriter(folder, f'This file is larger than {lib.megabytes(lib.MAX_OUTPUT_BYTES)} of text and markup after import, which is over the import limit.',
                               section_limit=lib.MAX_SECTION_BYTES)
    toc = []
    for number, blocks in enumerate(sections, 1):
        body = ET.Element('body')
        body.extend(blocks)
        heading = section_title(blocks)
        item = dict(location=number, title=(heading or (title if number == 1 else f'Section {number}'))[:lib.MAX_TITLE], label=str(number))
        toc.append({**item, 'depth': 0})
        writer.add({**item, 'text': lib.normalized(' '.join(body.itertext())),
                    'html': lib.sanitized_html(body, f'section-{number}.html', book_id, names, images.assets)})
    return toc, writer.text_pages


def summary(title, kind, toc, images, text_pages, attribution, author='', **extra):
    return dict(title=lib.normalized(title)[:lib.MAX_TITLE] or 'Untitled', author=lib.normalized(author)[:lib.MAX_TITLE], format=kind,
                rights=RIGHTS, sourceUrl='', attribution=attribution, count=len(toc), toc=toc,
                assets=images.records, textPages=text_pages, **extra)


# Markdown -------------------------------------------------------------------------------------

def front_matter(text):
    """Remove a YAML front matter block and return (title, text)."""
    if not text.startswith('---\n'):
        return '', text
    end = text.find('\n---', 4, 65536)
    if end < 0:
        return '', text
    title = ''
    for line in text[4:end].split('\n'):
        if line.startswith('title:'):
            title = line[6:].strip().strip('"\'')
    return title, text[end + 4:].lstrip('-').lstrip('\n')


def import_markdown(source, folder, book_id, name):
    title, text = front_matter(read_text(source, 'Markdown').replace('\r\n', '\n'))
    blocks = Markdown(Builder()).convert(text)
    title = title or next((''.join(block.itertext()) for block in blocks if block.tag == 'h1'), '') or name
    images = Images(folder)
    toc, text_pages = write_chapters(split_sections(blocks), folder, book_id, images, title)
    return summary(title, 'markdown', toc, images, text_pages,
                   'Converted from the supplied Markdown file. Raw HTML, scripts and images from outside the file are not included.')


# Plain text -----------------------------------------------------------------------------------

def pieces(paragraph, limit):
    """Split one very long paragraph at line breaks, or every `limit` characters if it has none."""
    if len(paragraph) <= limit:
        yield paragraph
        return
    part, size = [], 0
    for line in paragraph.split('\n'):
        while len(line) > limit:
            if part:
                yield '\n'.join(part)
                part, size = [], 0
            yield line[:limit]
            line = line[limit:]
        if part and size + len(line) > limit:
            yield '\n'.join(part)
            part, size = [], 0
        part.append(line)
        size += len(line) + 1
    if part:
        yield '\n'.join(part)


def first_line(text, limit=80):
    line = text.strip().split('\n', 1)[0].strip()
    if len(line) > limit:
        line = line[:limit].rsplit(' ', 1)[0] + '…'
    return line


def import_text(source, folder, book_id, name):
    """Paragraphs separated by blank lines, in sections of about TEXT_SECTION characters.

    The text keeps its line breaks; the reader shows them in monospace mode.
    """
    text = read_text(source, 'text').replace('\r\n', '\n').replace('\r', '\n')
    sections, current, size = [], [], 0
    for paragraph in re.split(r'\n[ \t]*\n', text):
        paragraph = paragraph.strip('\n')
        if not paragraph.strip():
            continue
        for piece in pieces(paragraph.rstrip(), TEXT_SECTION):
            if current and size + len(piece) > TEXT_SECTION:
                sections.append(current)
                current, size = [], 0
            current.append(piece)
            size += len(piece)
    if current:
        sections.append(current)
    if len(sections) > lib.MAX_SECTIONS:
        raise ValueError(f'This file has more than {lib.MAX_SECTIONS:,} sections, which is over the import limit.')
    writer = lib.ChapterWriter(folder, f'This file is larger than {lib.megabytes(lib.MAX_OUTPUT_BYTES)} of text after import, which is over the import limit.',
                               section_limit=lib.MAX_SECTION_BYTES)
    toc = []
    for number, paragraphs in enumerate(sections, 1):
        # Plain text has no markup of its own: every character is escaped into a paragraph.
        item = dict(location=number, title=(first_line(paragraphs[0]) or f'Section {number}')[:lib.MAX_TITLE], label=str(number))
        toc.append({**item, 'depth': 0})
        writer.add({**item, 'text': lib.normalized(' '.join(paragraphs)),
                    'html': ''.join(f'<p>{escape(paragraph, quote=False)}</p>' for paragraph in paragraphs)})
    images = Images(folder)
    return summary(name, 'text', toc, images, writer.text_pages, 'Plain text from the supplied file. Line breaks are kept for monospace reading.')


# HTML -----------------------------------------------------------------------------------------

class HtmlTree(HTMLParser):
    """Build an ElementTree from HTML that need not be well formed.

    Script, style, embedded documents, SVG and form controls are skipped with their content.
    Only attributes the sanitizer reads are kept.
    """
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr', 'keygen'}
    SKIP = {'script', 'style', 'noscript', 'template', 'svg', 'iframe', 'object', 'select', 'textarea', 'button',
            'canvas', 'audio', 'video', 'frameset', 'noframes'}
    IGNORE = {'html', 'head', 'body', 'form', 'input', 'meta', 'link', 'base', 'source', 'track', 'param', 'area', 'col', 'embed', 'keygen', 'wbr'}
    KEEP = {'id', 'class', 'href', 'src', 'alt', 'colspan', 'rowspan'}
    # Elements that an unclosed earlier sibling ends, as browsers do: (closes, up to).
    AUTO_CLOSE = {'li': ({'li'}, {'ul', 'ol'}), 'dt': ({'dt', 'dd'}, {'dl'}), 'dd': ({'dt', 'dd'}, {'dl'}),
                  'tr': ({'tr', 'td', 'th'}, {'table', 'thead', 'tbody', 'tfoot'}), 'td': ({'td', 'th'}, {'tr', 'table'}),
                  'th': ({'td', 'th'}, {'tr', 'table'}), 'thead': ({'thead', 'tbody', 'tr', 'td', 'th'}, {'table'}),
                  'tbody': ({'thead', 'tbody', 'tr', 'td', 'th'}, {'table'})}
    BLOCKS = {'p', 'div', 'ul', 'ol', 'dl', 'table', 'pre', 'blockquote', 'figure', 'section', 'article', 'header', 'footer',
              'aside', 'nav', 'main', 'hr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}

    def __init__(self, builder):
        super().__init__(convert_charrefs=True)
        self.builder = builder
        self.root = builder.element('body')
        self.stack = [self.root]
        self.skipping = None
        self.title = []
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        if self.skipping:
            if tag == self.skipping[0]:
                self.skipping[1] += 1
            return
        if tag == 'title':
            self.in_title = True
            return
        if tag in self.SKIP and tag not in self.VOID:
            self.skipping = [tag, 1]
            return
        if tag in self.IGNORE:
            return
        closes, scope = self.AUTO_CLOSE.get(tag, (None, None))
        if closes:
            found = None
            for index in range(len(self.stack) - 1, 0, -1):
                name = self.stack[index].tag
                if name in scope:
                    break
                if name in closes:
                    found = index
            if found:
                del self.stack[found:]
        elif tag in self.BLOCKS and len(self.stack) > 1 and self.stack[-1].tag == 'p':
            self.stack.pop()
        element = self.builder.element(tag, {key: value or '' for key, value in attrs if key in self.KEEP})
        self.stack[-1].append(element)
        if tag not in self.VOID and len(self.stack) < MAX_HTML_DEPTH:
            self.stack.append(element)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False
            return
        if self.skipping:
            if tag == self.skipping[0]:
                self.skipping[1] -= 1
                if not self.skipping[1]:
                    self.skipping = None
            return
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data):
        if self.in_title:
            self.title.append(data)
        elif not self.skipping:
            append_text(self.stack[-1], data)


def parse_html(text, builder):
    tree = HtmlTree(builder)
    tree.feed(text)
    tree.close()
    return tree


def store_inline_images(root, images, prefix):
    """Keep data:image URLs within the limits as stored files. Every other image source stays as it is,
    so the sanitizer replaces it with a short note: remote and relative images are never loaded."""
    for number, image in enumerate(root.iter('img')):
        src = image.get('src', '')
        if src[:5].lower() == 'data:':
            raw = data_image(src)
            name = f'{prefix}/{number}'
            image.set('src', name if raw and images.add(name, raw) else 'missing')


def content_blocks(root, builder):
    """The children of the element that holds the page content, with any loose leading text."""
    node = root
    while True:
        children = list(node)
        if (len(children) == 1 and children[0].tag in ('div', 'main', 'article', 'section', 'center')
                and not (node.text or '').strip() and not (children[0].tail or '').strip()):
            node = children[0]
        else:
            break
    blocks = list(node)
    if (node.text or '').strip():
        lead = builder.element('p')
        lead.text = node.text
        blocks.insert(0, lead)
    return blocks


def import_html(source, folder, book_id, name):
    builder = Builder()
    tree = parse_html(read_text(source, 'HTML'), builder)
    images = Images(folder)
    store_inline_images(tree.root, images, 'inline')
    blocks = content_blocks(tree.root, builder)
    title = lib.normalized(''.join(tree.title)) or section_title(blocks) or name
    toc, text_pages = write_chapters(split_sections(blocks), folder, book_id, images, title)
    return summary(title, 'html', toc, images, text_pages,
                   'Converted from the supplied HTML file. Scripts, styles, forms, embedded pages and remote images are not included.')


# Word -----------------------------------------------------------------------------------------

def local(tag):
    return tag.rsplit('}', 1)[-1] if isinstance(tag, str) else ''


def attribute(element, name):
    """An attribute by its local name, whatever its namespace."""
    for key, value in element.attrib.items():
        if key.rsplit('}', 1)[-1] == name:
            return value
    return None


def child(element, name):
    return next((node for node in element if local(node.tag) == name), None)


def is_on(element):
    return attribute(element, 'val') not in ('0', 'false', 'off', 'none')


class Docx:
    """Read word/document.xml into blocks: headings, paragraphs, lists, tables and pictures.

    Headers, footers, footnotes, comments and deleted text are not included.
    """
    def __init__(self, archive, names, builder, images):
        self.archive, self.names, self.builder, self.images = archive, names, builder, images
        self.rels, self.levels, self.code_styles, self.numbering, self.pictures = {}, {}, set(), {}, {}

    def xml(self, name, limit=MAX_DOCX_PART):
        if name not in self.names:
            return None
        return lib.parse_xml(lib.read_member(self.archive, self.names[name], limit, 'Word file'), 'Word file')

    def target(self, base, value):
        """A relationship target inside the package, or None for anything that leaves it."""
        if not value:
            return None
        try:
            path = lib.archive_path('', value.lstrip('/')) if value.startswith('/') else lib.archive_path(base, value)
        except ValueError:
            return None
        return path if path in self.names else None

    def read_relationships(self, root, base):
        for rel in root.iter() if root is not None else ():
            if local(rel.tag) != 'Relationship' or not rel.get('Id'):
                continue
            kind = rel.get('Type', '').rsplit('/', 1)[-1]
            value = rel.get('Target', '')
            if rel.get('TargetMode') == 'External':
                self.rels[rel.get('Id')] = (kind, lib.web_url(value) or 'missing', True)
            else:
                self.rels[rel.get('Id')] = (kind, self.target(base, value), False)

    def read_styles(self, root):
        for style in root.iter() if root is not None else ():
            if local(style.tag) != 'style':
                continue
            style_id = attribute(style, 'styleId')
            name, level = '', None
            for node in style:
                if local(node.tag) == 'name':
                    name = (attribute(node, 'val') or '').lower()
                elif local(node.tag) == 'pPr':
                    outline = child(node, 'outlineLvl')
                    value = attribute(outline, 'val') if outline is not None else None
                    level = int(value) + 1 if value and value.isdigit() else None
            match = re.fullmatch(r'heading ([1-9])', name)
            if match:
                level = int(match.group(1))
            elif name == 'title':
                level = 1
            if style_id and level and level <= 6:
                self.levels[style_id] = level
            if style_id and ('code' in name or name in ('html preformatted', 'source code')):
                self.code_styles.add(style_id)

    def read_numbering(self, root):
        if root is None:
            return
        abstract = {}
        for node in root:
            if local(node.tag) == 'abstractNum':
                levels = {}
                for level in node:
                    index = attribute(level, 'ilvl') if local(level.tag) == 'lvl' else None
                    if index and index.isdigit():
                        format_node = child(level, 'numFmt')
                        levels[int(index)] = (attribute(format_node, 'val') if format_node is not None else 'bullet') not in ('bullet', 'none')
                abstract[attribute(node, 'abstractNumId')] = levels
        for node in root:
            if local(node.tag) == 'num':
                reference = child(node, 'abstractNumId')
                if reference is not None:
                    self.numbering[attribute(node, 'numId')] = abstract.get(attribute(reference, 'val'), {})

    def picture_source(self, rel_id):
        rel = self.rels.get(rel_id)
        if not rel or not rel[1]:
            return 'missing'
        kind, target, external = rel
        if external:
            return target
        if target not in self.pictures:
            name = 'missing'
            if self.archive.getinfo(self.names[target]).file_size <= MAX_DOC_IMAGE:
                raw = lib.read_member(self.archive, self.names[target], MAX_DOC_IMAGE, 'Word file')
                if self.images.add(target, raw):
                    name = target
            self.pictures[target] = name
        return self.pictures[target]

    def picture(self, out, node, depth):
        # Text boxes hold their own paragraphs, read below; their pictures are found there.
        boxes = [d for d in node.iter() if local(d.tag) == 'txbxContent']
        inside = {id(item) for box in boxes for item in box.iter() if item is not box}
        seen = set()
        description = next((attribute(d, 'descr') or attribute(d, 'title') for d in node.iter() if local(d.tag) == 'docPr'), '') or 'Picture'
        for d in node.iter():
            if id(d) in inside:
                continue
            name = local(d.tag)
            rel_id = (attribute(d, 'embed') or attribute(d, 'link')) if name == 'blip' else attribute(d, 'id') if name == 'imagedata' else None
            if rel_id and rel_id not in seen:
                seen.add(rel_id)
                self.builder.child(out, 'img', {'src': self.picture_source(rel_id), 'alt': description[:300]})
            if name == 'txbxContent' and depth < MAX_DOCX_DEPTH:
                for paragraph in d:
                    if local(paragraph.tag) == 'p':
                        self.builder.child(out, 'br')
                        self.inline(out, paragraph, depth + 1)

    def run(self, out, run, depth):
        target = out
        props = child(run, 'rPr')
        for node in props if props is not None else ():
            name = local(node.tag)
            tag = {'b': 'strong', 'i': 'em', 'u': 'u', 'strike': 's', 'dstrike': 's'}.get(name)
            if name == 'vertAlign':
                tag = {'superscript': 'sup', 'subscript': 'sub'}.get(attribute(node, 'val'))
            if tag and (name == 'vertAlign' or is_on(node)):
                target = self.builder.child(target, tag)
        for node in run:
            name = local(node.tag)
            if name == 't':
                append_text(target, node.text or '')
            elif name in ('tab', 'ptab'):
                append_text(target, '\t')
            elif name in ('br', 'cr') and attribute(node, 'type') in (None, 'textWrapping'):
                self.builder.child(target, 'br')
            elif name == 'noBreakHyphen':
                append_text(target, '‑')
            elif name in ('drawing', 'pict', 'object'):
                self.picture(target, node, depth)
            elif name == 'AlternateContent':
                choice = child(node, 'Choice')
                choice = choice if choice is not None else child(node, 'Fallback')
                if choice is not None and depth < MAX_DOCX_DEPTH:
                    self.run(target, choice, depth + 1)

    def inline(self, out, node, depth):
        for part in node:
            name = local(part.tag)
            if name == 'r':
                self.run(out, part, depth)
            elif name == 'hyperlink' and depth < MAX_DOCX_DEPTH:
                rel = self.rels.get(attribute(part, 'id') or '')
                anchor = attribute(part, 'anchor')
                href = rel[1] if rel and rel[2] else ('#' + anchor if anchor else None)
                self.inline(self.builder.child(out, 'a', {'href': href}) if href else out, part, depth + 1)
            elif name in ('ins', 'smartTag', 'fldSimple', 'customXml', 'moveTo', 'dir', 'bdo') and depth < MAX_DOCX_DEPTH:
                self.inline(out, part, depth + 1)
            elif name == 'sdt' and depth < MAX_DOCX_DEPTH:
                content = child(part, 'sdtContent')
                if content is not None:
                    self.inline(out, content, depth + 1)
            elif name == 'bookmarkStart':
                bookmark = attribute(part, 'name')
                if bookmark and bookmark != '_GoBack':
                    self.builder.child(out, 'a', {'id': bookmark})

    def paragraph(self, node, depth):
        props = child(node, 'pPr')
        style = level = numbering = None
        for part in props if props is not None else ():
            name = local(part.tag)
            if name == 'pStyle':
                style = attribute(part, 'val')
            elif name == 'outlineLvl':
                value = attribute(part, 'val')
                level = int(value) + 1 if value and value.isdigit() else None
            elif name == 'numPr':
                index, number = child(part, 'ilvl'), child(part, 'numId')
                index = attribute(index, 'val') if index is not None else '0'
                number = attribute(number, 'val') if number is not None else None
                if number and number != '0':
                    numbering = (min(int(index), 8) if index and index.isdigit() else 0, number)
        heading = self.levels.get(style) or level
        if not heading and style:
            match = re.fullmatch(r'(?i)heading([1-6])', style)
            heading = int(match.group(1)) if match else (1 if style.lower() == 'title' else None)
        element = self.builder.element(f'h{heading}' if heading and heading <= 6 else 'p')
        self.inline(element, node, depth)
        if not ''.join(element.itertext()).strip() and not any(item.tag == 'img' for item in element.iter()):
            return None, None
        if style in self.code_styles:
            return element, 'code'
        if numbering and element.tag == 'p':
            return element, (numbering[0], self.numbering.get(numbering[1], {}).get(numbering[0], False))
        return element, None

    def table(self, node, depth):
        table = self.builder.element('table')
        body = self.builder.child(table, 'tbody')
        for row in node:
            if local(row.tag) != 'tr':
                continue
            props = child(row, 'trPr')
            header = props is not None and child(props, 'tblHeader') is not None
            line = self.builder.child(body, 'tr')
            for cell in row:
                if local(cell.tag) != 'tc':
                    continue
                attrs, continued = {}, False
                cell_props = child(cell, 'tcPr')
                for part in cell_props if cell_props is not None else ():
                    if local(part.tag) == 'gridSpan' and (attribute(part, 'val') or '').isdigit() and 1 < int(attribute(part, 'val')) <= 64:
                        attrs['colspan'] = attribute(part, 'val')
                    elif local(part.tag) == 'vMerge' and attribute(part, 'val') != 'restart':
                        continued = True
                item = self.builder.child(line, 'th' if header else 'td', attrs)
                if not continued:
                    item.extend(self.blocks(cell, depth + 1))
        return table

    def items(self, container, depth):
        for node in container:
            name = local(node.tag)
            if name == 'p':
                element, kind = self.paragraph(node, depth)
                if element is not None:
                    yield element, kind
            elif name == 'tbl' and depth < MAX_DOCX_DEPTH:
                yield self.table(node, depth + 1), None
            elif name in ('sdt', 'customXml', 'ins', 'moveTo', 'smartTag') and depth < MAX_DOCX_DEPTH:
                content = child(node, 'sdtContent') if name == 'sdt' else node
                if content is not None:
                    yield from self.items(content, depth + 1)

    def blocks(self, container, depth=0):
        """Group list paragraphs into nested lists, and code-styled paragraphs into one code block."""
        out, lists, code = [], [], None
        b = self.builder
        for element, kind in self.items(container, depth):
            if kind == 'code':
                lists = []
                text = ''.join(element.itertext())
                if code is None:
                    pre = b.element('pre')
                    code = b.child(pre, 'code')
                    out.append(pre)
                    code.text = text
                else:
                    code.text += '\n' + text
                continue
            code = None
            if kind is None:
                lists = []
                out.append(element)
                continue
            level, ordered = kind
            while lists and lists[-1][0] > level:
                lists.pop()
            if lists and lists[-1][0] == level and lists[-1][2] != ordered:
                lists.pop()
            if not lists or lists[-1][0] < level:
                container_list = b.element('ol' if ordered else 'ul')
                if lists:
                    parent = lists[-1][1]
                    (parent[-1] if len(parent) else b.child(parent, 'li')).append(container_list)
                else:
                    out.append(container_list)
                lists.append((level, container_list, ordered))
            item = b.child(lists[-1][1], 'li')
            item.text = element.text
            item.extend(list(element))
        return out


def import_docx(source, folder, book_id, name):
    try:
        archive = zipfile.ZipFile(source)
    except (zipfile.BadZipFile, OSError):
        raise ValueError('This Word file could not be opened. Save it again as .docx and retry. Older .doc files and password-protected files are not supported.') from None
    with archive:
        entries = archive.infolist()
        if len(entries) > lib.MAX_ARCHIVE_ENTRIES or sum(e.file_size for e in entries) > lib.MAX_EXPANDED_BYTES:
            raise ValueError('This Word file expands beyond the local import limit.')
        names = {}
        for entry in entries:
            try:
                names.setdefault(lib.archive_path('', entry.filename), entry.filename)
            except ValueError:
                raise ValueError('This Word file contains an unsafe file path, so it was not imported.') from None
        reader = Docx(archive, names, Builder(), Images(folder))
        main = 'word/document.xml'
        package = reader.xml('_rels/.rels')
        for rel in package.iter() if package is not None else ():
            if local(rel.tag) == 'Relationship' and rel.get('Type', '').endswith('/officeDocument') and rel.get('TargetMode') != 'External':
                main = reader.target('', rel.get('Target', '')) or main
                break
        if main not in names:
            raise ValueError('This file has no Word document inside. Save it again as .docx and retry.')
        document = reader.xml(main, MAX_DOCX_XML)
        base = posixpath.dirname(main)
        reader.read_relationships(reader.xml(posixpath.join(base, '_rels', posixpath.basename(main) + '.rels')), base)
        styles_target = next((target for kind, target, external in reader.rels.values() if kind == 'styles' and not external), None)
        numbering_target = next((target for kind, target, external in reader.rels.values() if kind == 'numbering' and not external), None)
        reader.read_styles(reader.xml(styles_target) if styles_target else None)
        reader.read_numbering(reader.xml(numbering_target) if numbering_target else None)
        core = reader.xml('docProps/core.xml', 1 << 20)
        title = author = ''
        for node in core.iter() if core is not None else ():
            if local(node.tag) == 'title' and not title:
                title = ''.join(node.itertext()).strip()
            elif local(node.tag) == 'creator' and not author:
                author = ''.join(node.itertext()).strip()
        body = child(document, 'body')
        blocks = reader.blocks(body) if body is not None else []
        del document
        title = title or section_title(blocks) or name
        toc, text_pages = write_chapters(split_sections(blocks), folder, book_id, reader.images, title)
    return summary(title, 'docx', toc, reader.images, text_pages,
                   'Converted from the supplied Word file: headings, paragraphs, lists, tables and pictures. Page layout, headers, footnotes and comments are not included.',
                   author=author)


# Jupyter notebooks ----------------------------------------------------------------------------

LANGUAGE_NAMES = {'python': 'Python', 'r': 'R', 'julia': 'Julia', 'javascript': 'JavaScript', 'typescript': 'TypeScript',
                  'scala': 'Scala', 'c++': 'C++', 'bash': 'Bash', 'sql': 'SQL', 'rust': 'Rust', 'go': 'Go'}


def joined(value, separator=''):
    """Notebook text is a string or a list of strings. Anything else counts as empty."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return separator.join(item for item in value if isinstance(item, str))
    return ''


def mapping(value):
    return value if isinstance(value, dict) else {}


class Notebook:
    """Show a notebook as it was saved. Cells never run, and HTML or JavaScript outputs never run:
    HTML tables pass through the sanitizer, and other rich outputs show their plain text."""
    def __init__(self, folder, language):
        self.builder = Builder()
        self.markdown = Markdown(self.builder)
        self.images = Images(folder)
        self.language = language

    def text_output(self, parent, text, error=False):
        text = ANSI.sub('', text)
        if len(text) > MAX_OUTPUT_TEXT:
            text = text[:MAX_OUTPUT_TEXT] + f'\n… {len(text) - MAX_OUTPUT_TEXT:,} more characters not shown.'
        if text.strip():
            self.builder.child(parent, 'pre', {'class': 'cell-error' if error else 'cell-output'}).text = text

    def image_output(self, parent, data, name):
        for mime in ('image/png', 'image/jpeg', 'image/gif', 'image/webp'):
            raw = decoded_image(joined(data.get(mime))) if data.get(mime) else None
            if raw and self.images.add(name, raw):
                self.builder.child(parent, 'img', {'src': name, 'alt': 'Cell output'})
                return True
        return False

    def output(self, parent, output, name):
        output = mapping(output)
        kind = output.get('output_type')
        if kind == 'stream':
            self.text_output(parent, joined(output.get('text')), output.get('name') == 'stderr')
        elif kind == 'error':
            trace = joined(output.get('traceback'), '\n') or f"{joined(output.get('ename'))}: {joined(output.get('evalue'))}"
            self.text_output(parent, trace, True)
        elif kind in ('execute_result', 'display_data'):
            data = mapping(output.get('data'))
            if self.image_output(parent, data, name):
                return
            html = joined(data.get('text/html'))
            if html and '<table' in html.lower() and len(html) <= MAX_OUTPUT_HTML:
                tree = parse_html(html, self.builder)
                store_inline_images(tree.root, self.images, name)
                wrapper = self.builder.child(parent, 'div', {'class': 'cell-html'})
                wrapper.text = tree.root.text
                wrapper.extend(list(tree.root))
                return
            markdown = joined(data.get('text/markdown'))
            if markdown:
                parent.extend(self.markdown.convert(markdown[:MAX_OUTPUT_TEXT]))
                return
            text = joined(data.get('text/plain'))
            if text:
                self.text_output(parent, text)
            elif data:
                self.builder.child(parent, 'p', {'class': 'cell-note'}).text = 'This output is interactive and is not shown here.'

    def attachments(self, blocks, attachments, index):
        """Markdown cells can show images saved in the cell (attachment:name)."""
        for number, image in enumerate(item for block in blocks for item in block.iter('img')):
            src = image.get('src', '')
            if not src.startswith('attachment:'):
                continue
            stored = 'missing'
            data = mapping(mapping(attachments).get(unquote(src[11:])))
            if self.image_output(ET.Element('div'), data, f'attachment/{index}/{number}'):
                stored = f'attachment/{index}/{number}'
            image.set('src', stored)

    def cells(self, cells):
        blocks = []
        language = LANGUAGE_NAMES.get(self.language.lower(), self.language)
        for index, cell in enumerate(cells):
            cell = mapping(cell)
            kind = cell.get('cell_type')
            text = joined(cell.get('source'))
            if kind == 'markdown':
                cell_blocks = self.markdown.convert(text)
                self.attachments(cell_blocks, cell.get('attachments'), index)
                blocks.extend(cell_blocks)
            elif kind == 'code':
                count = cell.get('execution_count')
                label = f'In [{count}]' if type(count) is int and 0 <= count < 10 ** 9 else 'In [ ]'
                wrapper = self.builder.element('div', {'class': 'notebook-cell'})
                wrapper.append(code_block(self.builder, text, self.language.lower(), f'{label} · {language}' if language else label))
                outputs = cell.get('outputs') if isinstance(cell.get('outputs'), list) else []
                for number, output in enumerate(outputs[:MAX_OUTPUTS]):
                    self.output(wrapper, output, f'output/{index}/{number}')
                if len(outputs) > MAX_OUTPUTS:
                    self.builder.child(wrapper, 'p', {'class': 'cell-note'}).text = f'{len(outputs) - MAX_OUTPUTS:,} more outputs are not shown.'
                blocks.append(wrapper)
            elif kind == 'raw' and text.strip():
                blocks.append(code_block(self.builder, text, '', 'Raw cell'))
        return blocks


def import_ipynb(source, folder, book_id, name):
    try:
        notebook = json.loads(Path(source).read_bytes().decode('utf-8-sig'))
    except RecursionError:
        raise ValueError('This notebook is nested too deeply to import.') from None
    except (UnicodeDecodeError, ValueError):
        raise ValueError('This notebook is not valid JSON. Open it in Jupyter, save it again and retry.') from None
    if not isinstance(notebook, dict):
        raise ValueError('This file is not a Jupyter notebook.')
    cells = notebook.get('cells')
    if not isinstance(cells, list):
        raise ValueError('Only notebook format 4 is supported. Open it in Jupyter, save it again and retry.'
                         if 'worksheets' in notebook else 'This file is not a Jupyter notebook.')
    if len(cells) > MAX_CELLS:
        raise ValueError(f'This notebook has more than {MAX_CELLS:,} cells, which is over the import limit.')
    metadata = mapping(notebook.get('metadata'))
    language = joined(mapping(metadata.get('kernelspec')).get('language')) or joined(mapping(metadata.get('language_info')).get('name')) or 'python'
    language = language if re.fullmatch(r'[A-Za-z0-9_+#.-]{1,40}', language) else ''
    reader = Notebook(folder, language)
    blocks = reader.cells(cells)
    del notebook, cells
    title = joined(metadata.get('title')) or next((''.join(block.itertext()) for block in blocks if block.tag == 'h1'), '') or name
    toc, text_pages = write_chapters(split_sections(blocks), folder, book_id, reader.images, title)
    return summary(title, 'ipynb', toc, reader.images, text_pages,
                   'Shown from the supplied notebook as it was saved. Cells never run here; HTML and JavaScript outputs are not run.')


# Images ---------------------------------------------------------------------------------------

def import_image(source, folder, book_id, name):
    """One image as a one-page book. The original file is the page."""
    raw = Path(source).read_bytes()
    kind = image_type(raw)
    if not kind:
        raise ValueError('This file is not a PNG, JPEG, WebP or GIF image.')
    size = image_size(raw, kind)
    if not size or not all(size):
        raise ValueError('The size of this image could not be read. Save it again and retry.')
    if size[0] * size[1] > MAX_IMAGE_PIXELS:
        raise ValueError(f'This image is larger than {MAX_IMAGE_PIXELS // 1_000_000} megapixels, which is over the import limit.')
    original = 'source' + Path(source).suffix.lower()
    builder = Builder()
    figure = builder.element('figure')
    builder.child(figure, 'img', {'src': 'image', 'alt': name[:300] or 'Image'})
    images = Images(folder)
    images.assets['image'] = original
    toc, text_pages = write_chapters([[figure]], folder, book_id, images, name)
    toc[0]['label'] = '1'
    return summary(name, 'image', toc, images, text_pages,
                   f'The supplied image, unchanged: {size[0]:,} × {size[1]:,} pixels.', cover=original, sourceType=kind)


IMPORTERS = {'markdown': import_markdown, 'text': import_text, 'html': import_html, 'docx': import_docx,
             'ipynb': import_ipynb, 'image': import_image}
