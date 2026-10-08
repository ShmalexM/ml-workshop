"""Local-only EPUB/PDF imports. Originals and extracted content live under data/.

Each book folder holds book.json (the summary: metadata, contents and assets) and
chapters/<n>.json (one page or section each). The server caches summaries only.
"""
from html import escape
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit, unquote, quote
from xml.etree import ElementTree as ET
import hashlib
import json
import logging
import os
import posixpath
import pyexpat
import re
import secrets
import shutil
import tempfile
import threading
import unicodedata
import zipfile

MAX_BOOK_BYTES = 100 * 1024 * 1024
# Version 2: one file per chapter, repeated spine entries dropped, book class names and ids prefixed.
IMPORT_VERSION = 2
BOOK_ID = re.compile(r'^[a-z0-9][a-z0-9-]{0,79}$')
TAGS = {'p','h1','h2','h3','h4','h5','h6','div','section','article','span','strong','em','b','i','u','s','small','sup','sub','blockquote','pre','code','ul','ol','li','dl','dt','dd','table','thead','tbody','tfoot','tr','th','td','caption','figure','figcaption','hr','br','a','img'}
DROP = {'script','style','iframe','object','embed','form','input','button','link','meta','base'}
IMAGE_TYPES = {'image/png','image/jpeg','image/gif','image/webp','image/svg+xml'}

# Import limits. A small EPUB can unpack to far more text than its file size suggests,
# so sizes are counted while reading and writing, not only from the zip headers.
MAX_ARCHIVE_ENTRIES = 10000
MAX_EXPANDED_BYTES = 250 * 1024 * 1024
MAX_SECTIONS = 2000
MAX_SECTION_BYTES = 8 * 1024 * 1024
MAX_PDF_PAGES = 10000
MAX_OUTPUT_BYTES = 64 * 1024 * 1024
# Images are copied unchanged, so they get their own budget: a well-illustrated book can hold more
# than 64 MB of pictures. The count bounds the files one book adds to the data folder.
MAX_IMAGES = 2000
MAX_IMAGE_BYTES = 150 * 1024 * 1024
MAX_TITLE = 300
MAX_FIELD = 2000

# Book class names and ids get this prefix, so book HTML can never use the app's own CSS classes.
BOOK_PREFIX = 'bk-'
CLASS_NAME = re.compile(r'^[A-Za-z0-9_-]{1,64}$')
ATTRIBUTES = {'id','class','colspan','rowspan','src','alt','loading','tabindex','role','href','target','rel'}

def normalized(text):
    return ' '.join(unicodedata.normalize('NFKC', text).replace('­','').split())

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def megabytes(limit):
    return f'{limit / (1 << 20):g} MB'

def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')

def web_url(value):
    """Keep a source link only if it is an http(s) URL; dc:source can hold any text."""
    value = (value or '').strip()
    if not value or len(value) > MAX_FIELD or any(c.isspace() or ord(c) < 32 for c in value):
        return ''
    try:
        parts = urlsplit(value)
    except ValueError:
        return ''
    return value if parts.scheme in ('http','https') and parts.netloc else ''

def local_name(tag):
    return tag.rsplit('}', 1)[-1].lower()

def archive_path(base, relative):
    parsed = urlsplit(relative)
    if parsed.scheme or parsed.netloc:
        raise ValueError('Expected a local EPUB path')
    name = posixpath.normpath(posixpath.join(base, unquote(parsed.path)))
    if name.startswith('/') or name == '..' or name.startswith('../') or '\\' in name:
        raise ValueError('Unsafe EPUB path')
    return name

def read_member(archive, name):
    """Read one EPUB file, counting bytes as they are unpacked instead of trusting the zip header."""
    limit = MAX_SECTION_BYTES
    message = f'A file inside this EPUB is larger than {megabytes(limit)} when unpacked, which is over the import limit.'
    if archive.getinfo(name).file_size > limit:
        raise ValueError(message)
    with archive.open(name) as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError(message)
    return raw

class _RootElement(Exception):
    pass

def parse_xml(raw):
    """Parse EPUB XML. Only short, plain entities such as nbsp are accepted.

    Nested or long entity declarations can expand a few lines into gigabytes.
    """
    scanner = pyexpat.ParserCreate()
    def declared(name, is_parameter, value, *_):
        if is_parameter or value is None or len(value)>16 or '&' in value:
            raise ValueError('This EPUB declares XML entities that the importer does not accept.')
    def root(*_):
        raise _RootElement  # Entities can only be declared before the root element.
    scanner.EntityDeclHandler = declared
    scanner.StartElementHandler = root
    try:
        scanner.Parse(raw, True)
    except _RootElement:
        pass
    return ET.fromstring(raw)

def book_classes(value):
    return ' '.join(BOOK_PREFIX + name for name in value.split()[:16] if CLASS_NAME.fullmatch(name))

def book_attributes(pairs):
    """Prefix book ids and class names; keep only attributes the reader uses."""
    attrs = {}
    for key, value in pairs:
        value = value or ''
        if key not in ATTRIBUTES:
            continue
        if key == 'id':
            if 0 < len(value) <= 200:
                attrs['id'] = BOOK_PREFIX + value
        elif key == 'class':
            classes = book_classes(value)
            if classes:
                attrs['class'] = classes
        else:
            attrs[key] = value
    return attrs

def start_tag(tag, attrs):
    return f'<{tag}' + ''.join(f' {key}="{escape(str(value), quote=True)}"' for key,value in attrs.items()) + '>'

def sanitized_html(element, chapter_path, book_id, chapters, assets):
    """Whitelist book markup; never execute ebook scripts or retain remote media."""
    tag = local_name(element.tag)
    if tag in DROP:
        return ''
    children = escape(element.text or '') + ''.join(
        sanitized_html(child, chapter_path, book_id, chapters, assets) + escape(child.tail or '')
        for child in element
    )
    if tag not in TAGS:
        return children
    # Source classes stay usable for captions (as bk-caption), not for app styles.
    attrs = book_attributes((key, element.get(key)) for key in ('id','class'))
    for key in ('colspan','rowspan'):
        if element.get(key, '').isdigit():
            attrs[key] = element.get(key)
    if tag == 'img':
        try:
            name = archive_path(posixpath.dirname(chapter_path), element.get('src',''))
        except ValueError:
            return f'<p class="{BOOK_PREFIX}unavailable-media">Remote image omitted from this offline copy.</p>'
        if name not in assets:
            return f'<p class="{BOOK_PREFIX}unavailable-media">Image was not included in the source EPUB.</p>'
        attrs.update(src=f'/api/library/{book_id}/asset/{quote(assets[name], safe="/")}',
                     alt=element.get('alt','Book illustration'), loading='lazy', tabindex='0', role='button')
    elif tag == 'a':
        href = element.get('href','')
        parsed = urlsplit(href)
        if parsed.scheme in ('https','http'):
            attrs.update(href=href, target='_blank', rel='noreferrer noopener')
        elif not parsed.scheme and not parsed.netloc:
            try:
                target = archive_path(posixpath.dirname(chapter_path), parsed.path) if parsed.path else chapter_path
            except ValueError:
                target = ''
            if target in chapters:
                # The fragment stays unprefixed in the link; the reader adds the prefix when it scrolls.
                attrs['href'] = f'#books/{book_id}/{chapters[target]}'
                if parsed.fragment:
                    attrs['href'] += '/' + quote(unquote(parsed.fragment), safe='')
    return start_tag(tag, attrs) + ('' if tag in ('img','br','hr') else children + f'</{tag}>')

class _StoredHtml(HTMLParser):
    """Rewrite HTML saved by import version 1 with the current id and class rules."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag in TAGS:
            self.parts.append(start_tag(tag, book_attributes(attrs)))
    handle_startendtag = handle_starttag
    def handle_endtag(self, tag):
        if tag in TAGS and tag not in ('img','br','hr'):
            self.parts.append(f'</{tag}>')
    def handle_data(self, data):
        self.parts.append(escape(data))

def prefix_stored_html(html):
    parser = _StoredHtml()
    parser.feed(html)
    parser.close()
    return ''.join(parser.parts)

class ChapterWriter:
    """Write chapters/<n>.json one at a time, and stop when the book's output limit is reached."""
    def __init__(self, folder, message):
        self.folder = Path(folder)/'chapters'
        self.folder.mkdir()
        self.message = message
        self.total = 0
    def add(self, document):
        raw = json.dumps(document, ensure_ascii=False).encode('utf-8')
        self.total += len(raw)
        if self.total > MAX_OUTPUT_BYTES:
            raise ValueError(self.message)
        (self.folder/f"{document['location']}.json").write_bytes(raw)

def copy_image(archive, name, folder, limit):
    """Copy an image byte-for-byte without holding it in memory; the file is named by its hash.

    Stops with an error once more than `limit` bytes are unpacked.
    """
    (folder/'assets').mkdir(exist_ok=True)
    partial = folder/'assets'/'.partial'
    h = hashlib.sha256()
    size = 0
    with archive.open(name) as stream, partial.open('wb') as out:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            size += len(block)
            if size > limit:
                raise ValueError(f'The images in this EPUB are larger than {megabytes(MAX_IMAGE_BYTES)} in total, which is over the import limit.')
            h.update(block); out.write(block)
    target = 'assets/' + h.hexdigest()[:16] + PurePosixPath(name).suffix.lower()
    partial.replace(folder/target)
    return target, h.hexdigest(), size

def import_epub(source, folder, book_id):
    with zipfile.ZipFile(source) as archive:
        entries = archive.infolist()
        if len(entries)>MAX_ARCHIVE_ENTRIES or sum(e.file_size for e in entries)>MAX_EXPANDED_BYTES:
            raise ValueError('EPUB expands beyond the local import limit')
        for entry in entries:
            archive_path('',entry.filename)
        container = parse_xml(read_member(archive,'META-INF/container.xml'))
        opf_path = next(e.get('full-path') for e in container.iter() if local_name(e.tag)=='rootfile')
        opf_path = archive_path('',opf_path)
        package = parse_xml(read_member(archive,opf_path))
        base = posixpath.dirname(opf_path)
        metadata = next(e for e in package if local_name(e.tag)=='metadata')
        def field(name, fallback='', limit=MAX_TITLE):
            return next((''.join(e.itertext()).strip() for e in metadata if local_name(e.tag)==name),fallback)[:limit]
        manifest = {e.get('id'):e for e in package.iter() if local_name(e.tag)=='item'}
        spine = [manifest[e.get('idref')] for e in package.iter() if local_name(e.tag)=='itemref']
        pages = [archive_path(base,e.get('href')) for e in spine if 'nav' not in e.get('properties','').split() and e.get('id')!='cover']
        # A spine may list one file many times. Each file becomes one section.
        pages = list(dict.fromkeys(pages))
        if len(pages)>MAX_SECTIONS:
            raise ValueError(f'This EPUB has more than {MAX_SECTIONS:,} sections, which is over the import limit.')
        chapters = {name:i+1 for i,name in enumerate(pages)}
        images = {}
        for item in manifest.values():
            if item.get('media-type','') in IMAGE_TYPES:
                images.setdefault(archive_path(base,item.get('href')),item.get('media-type'))
        if len(images)>MAX_IMAGES:
            raise ValueError(f'This EPUB has more than {MAX_IMAGES:,} images, which is over the import limit.')
        assets = {}
        image_records = []
        budget = MAX_IMAGE_BYTES
        for name,media_type in images.items():
            target, sha256, size = copy_image(archive, name, folder, budget)
            budget -= size
            assets[name] = target
            image_records.append(dict(source=name,path=target,sha256=sha256,bytes=size,mediaType=media_type))
        writer = ChapterWriter(folder, f'This EPUB unpacks to more than {megabytes(MAX_OUTPUT_BYTES)} of text and markup, which is over the import limit.')
        toc = []
        for number,name in enumerate(pages,1):
            root = parse_xml(read_member(archive,name))
            body = next(e for e in root.iter() if local_name(e.tag)=='body')
            title = next((''.join(e.itertext()).strip() for e in body.iter() if local_name(e.tag) in ('h1','h2')),f'Section {number}')[:MAX_TITLE]
            key = PurePosixPath(name).stem[:200]
            item = dict(location=number,title=title,key=key,label=str(number))
            toc.append({**item, 'depth':1 if '--' in key else 0})
            writer.add({**item,'text':normalized(' '.join(body.itertext())),
                        'html':sanitized_html(body,name,book_id,chapters,assets)})
            del root, body
        return dict(title=field('title',source.stem),author=field('creator'),format='epub',
                    rights=field('rights','Rights remain with the source authors.',MAX_FIELD),sourceUrl=web_url(field('source',limit=MAX_FIELD)),
                    attribution='Original text, diagrams, captions, and attributions from the supplied EPUB. Reader layout adapted; image files unchanged.',
                    count=len(toc),toc=toc,assets=image_records,
                    cover=assets.get(next((archive_path(base,e.get('href')) for e in manifest.values() if 'cover-image' in e.get('properties','').split()),'')))

def import_pdf(source, folder, book_id):
    from pypdf import PdfReader
    reader = PdfReader(source)
    if reader.is_encrypted:
        raise ValueError('Encrypted PDFs are not supported')
    # pypdf itself caps the page tree at 100,000 entries and each decompressed stream at 75 MB.
    count = len(reader.pages)
    if count>MAX_PDF_PAGES:
        raise ValueError(f'This PDF has more than {MAX_PDF_PAGES:,} pages, which is over the import limit.')
    labels = [str(label)[:60] for label in reader.page_labels]
    writer = ChapterWriter(folder, f'The text in this PDF is larger than {megabytes(MAX_OUTPUT_BYTES)}, which is over the import limit.')
    for i,page in enumerate(reader.pages):
        writer.add(dict(location=i+1,label=labels[i],title=f'Page {labels[i]}',text=normalized(page.extract_text() or '')))
    toc = []
    def walk(outline,depth=0):
        for item in outline:
            if len(toc)>=MAX_PDF_PAGES:
                return
            if isinstance(item,list):
                walk(item,depth+1)
            else:
                page = reader.get_destination_page_number(item)+1
                if 1<=page<=count:
                    toc.append(dict(title=str(item.title)[:MAX_TITLE],location=page,label=labels[page-1],depth=max(depth-1,0)))
    walk(reader.outline)
    if not toc:
        toc = [dict(title=f'Page {label}',location=i+1,label=label,depth=0) for i,label in enumerate(labels[:count])]
    meta = reader.metadata or {}
    # PDF vectors, embedded fonts and original image streams remain in source.pdf.
    return dict(title=str(meta.get('/Title') or source.stem)[:MAX_TITLE],author=str(meta.get('/Author') or '')[:MAX_TITLE],format='pdf',
                rights='Personal local copy. Copyright remains with the publisher; not included in the open-source app.',
                sourceUrl='',attribution='Original PDF preserved unchanged, including vector diagrams, embedded fonts, pictures, and page labels.',
                count=count,toc=toc,assets=[])

def import_book(source, data_dir, book_id):
    source = Path(source).expanduser().resolve()
    if not BOOK_ID.fullmatch(book_id):
        raise ValueError('Use a lowercase book ID with letters, numbers and hyphens')
    if source.suffix.lower() not in ('.epub','.pdf') or source.stat().st_size>MAX_BOOK_BYTES:
        raise ValueError('Choose an EPUB or PDF no larger than 100 MB')
    root = Path(data_dir)/'library';root.mkdir(parents=True,exist_ok=True)
    checksum = digest(source)
    target = root/book_id
    refresh = False
    if target.exists():
        try:
            existing = json.loads((target/'book.json').read_text(encoding='utf-8'))
            # A version 1 book.json also holds the chapters. Its checksum is enough to reimport it.
            if not (isinstance(existing,dict) and 'documents' in existing and isinstance(existing.get('sha256'),str)):
                checked_summary(existing,book_id)
        except (OSError,ValueError):
            raise ValueError(f'The book in {target} could not be opened. Remove it, then import again.') from None
        if existing['sha256']==checksum:
            if existing.get('importVersion') == IMPORT_VERSION:
                return existing
            refresh = True
        else:
            raise ValueError('This book ID already contains a different edition; choose a new ID')
    # A failed or over-limit import leaves nothing behind: the temporary folder is removed.
    with tempfile.TemporaryDirectory(prefix='.import-',dir=root) as temporary:
        folder = Path(temporary)
        extension = source.suffix.lower()
        shutil.copyfile(source,folder/('source'+extension))
        result = (import_epub if extension=='.epub' else import_pdf)(source,folder,book_id)
        if not result['count']:
            raise ValueError('The book has no readable pages or sections')
        result.update(id=book_id,sha256=checksum,sourceFile='source'+extension,bytes=source.stat().st_size,importVersion=IMPORT_VERSION)
        write_json(folder/'book.json',result)
        # Rename only a complete import into the visible library. No partially loaded books.
        if refresh:
            # Re-index the identical edition without touching reading state or source.
            for asset_path in {asset['path'] for asset in result['assets']}:
                destination = target/asset_path
                destination.parent.mkdir(exist_ok=True)
                (folder/asset_path).replace(destination)
            if (target/'chapters').exists():
                (target/'chapters').rename(folder/'previous-chapters')
            (folder/'chapters').rename(target/'chapters')
            (folder/'book.json').replace(target/'book.json')
        else:
            folder.rename(target)
    return result

def split_legacy_book(folder, book):
    """Move the chapters of a version 1 book.json, which held the whole book, into chapter files.

    Runs once per book, so later requests read one chapter at a time. Stored HTML gets the
    current id and class prefix, and sourceUrl keeps only web links, as for new imports.
    """
    staging = Path(tempfile.mkdtemp(prefix='.chapters-',dir=folder))
    try:
        for location,document in enumerate(book['documents'],1):
            if 'html' in document:
                document = {**document,'html':prefix_stored_html(document['html'])}
            write_json(staging/f'{location}.json',document)
        summary = {key:value for key,value in book.items() if key!='documents'}
        summary.update(count=len(book['documents']),sourceUrl=web_url(summary.get('sourceUrl')))
        chapters = folder/'chapters'
        if chapters.exists():
            shutil.rmtree(chapters)
        staging.rename(chapters)
        write_json(folder/'.book.json.partial',summary)
        os.replace(folder/'.book.json.partial',folder/'book.json')
        return summary
    finally:
        shutil.rmtree(staging,ignore_errors=True)

# Summaries only, keyed by book.json path and file identity. Chapters are read from disk per request.
# A book.json that cannot be read is cached as None, so its warning is logged once per file version.
_SUMMARIES = {}
_SUMMARY_LOCK = threading.Lock()
LOG = logging.getLogger('library')
# Fields the server and the reader use from book.json.
SUMMARY_FIELDS = {'id':str,'title':str,'format':str,'count':int,'toc':list,'assets':list,'sourceFile':str,'sha256':str}

class UnreadableBook(KeyError):
    """data/library/<id>/book.json exists but cannot be read. The catalog lists the book so it can be removed."""

def checked_summary(book, book_id):
    if not isinstance(book,dict):
        raise ValueError('book.json does not hold an object')
    wrong = [key for key,kind in SUMMARY_FIELDS.items() if not isinstance(book.get(key),kind)]
    if wrong:
        raise ValueError('book.json has missing or invalid fields: ' + ', '.join(wrong))
    if book['id']!=book_id or book['format'] not in ('pdf','epub'):
        raise ValueError('book.json names another book or format')
    return book

class Library:
    def __init__(self,data_dir):
        self.root = Path(data_dir)/'library'

    def folder(self,book_id):
        if not isinstance(book_id,str) or not BOOK_ID.fullmatch(book_id):
            raise KeyError('Unknown book')
        folder = self.root/book_id
        if not (folder/'book.json').is_file():
            raise KeyError('Unknown book')
        return folder

    def book(self,book_id):
        """The book summary: metadata, contents and assets, without chapter text."""
        folder = self.folder(book_id)
        path = folder/'book.json'
        with _SUMMARY_LOCK:
            try:
                stat = path.stat()
            except FileNotFoundError:
                raise KeyError('Unknown book') from None
            key = (stat.st_mtime_ns,stat.st_size,stat.st_ino)
            cached = _SUMMARIES.get(path)
            if cached and cached[0]==key:
                if cached[1] is None:
                    raise UnreadableBook(book_id)
                return cached[1]
            try:
                book = json.loads(path.read_text(encoding='utf-8'))
                if isinstance(book,dict) and 'documents' in book:
                    book = split_legacy_book(folder,book)
                    stat = path.stat()
                    key = (stat.st_mtime_ns,stat.st_size,stat.st_ino)
                checked_summary(book,book_id)
            except FileNotFoundError:
                raise KeyError('Unknown book') from None
            except (OSError,ValueError,TypeError,KeyError,AttributeError) as error:
                LOG.warning('Could not open the book in %s: %s', folder, error)
                _SUMMARIES[path] = (key,None)
                raise UnreadableBook(book_id) from None
            _SUMMARIES[path] = (key,book)
            return book

    def summary(self,book_id):
        return {key:value for key,value in self.book(book_id).items() if key!='sourceFile'}

    def ids(self):
        if not self.root.exists():
            return []
        return [path.parent.name for path in sorted(self.root.glob('*/book.json')) if BOOK_ID.fullmatch(path.parent.name)]

    def catalog(self):
        """Summaries of the books that open. A damaged book.json is skipped with a warning; see unreadable()."""
        books = []
        for book_id in self.ids():
            try:
                books.append(self.summary(book_id))
            except KeyError:
                pass
        return books

    def unreadable(self):
        """IDs of books whose book.json cannot be read. The Books page offers to remove them."""
        found = []
        for book_id in self.ids():
            try:
                self.book(book_id)
            except UnreadableBook:
                found.append(book_id)
            except KeyError:
                pass
        return found

    def chapter(self,book_id,location):
        book = self.book(book_id)
        if not 1<=location<=book['count']:
            raise KeyError('Unknown page or section')
        try:
            return json.loads((self.root/book_id/'chapters'/f'{location}.json').read_text(encoding='utf-8'))
        except FileNotFoundError:
            raise KeyError('Unknown page or section') from None

    def chapters(self,book_id):
        """Chapters one at a time, so a search never holds a whole book in memory."""
        for location in range(1,self.book(book_id)['count']+1):
            try:
                yield self.chapter(book_id,location)
            except KeyError:
                return

    def asset(self,book_id,name):
        book = self.book(book_id)
        allowed = {item['path']:item['mediaType'] for item in book['assets']}
        allowed[book['sourceFile']] = 'application/pdf' if book['format']=='pdf' else 'application/epub+zip'
        if name not in allowed:
            raise KeyError('Unknown book asset')
        path = (self.root/book_id/name).resolve()
        if not path.is_relative_to((self.root/book_id).resolve()):
            raise KeyError('Unknown book asset')
        return path,allowed[name]

    def remove(self,book_id):
        """Delete one imported book's folder. Notes and reading position live in SQLite and stay."""
        folder = self.folder(book_id)
        if folder.is_symlink() or folder.resolve().parent!=self.root.resolve():
            raise KeyError('Unknown book')
        with _SUMMARY_LOCK:
            # Hide the book first, so a failed delete never leaves a half-removed book in the catalog.
            staging = self.root/f'.removing-{book_id}-{secrets.token_hex(4)}'
            folder.rename(staging)
            _SUMMARIES.pop(folder/'book.json',None)
        shutil.rmtree(staging)

    def search(self,query,book_id=None):
        query = normalized(query).casefold()
        if not 2<=len(query)<=160:
            return []
        books = [self.summary(book_id)] if book_id else self.catalog()
        matches = []
        for summary in books:
            for chapter in self.chapters(summary['id']):
                text = chapter['text'];start = text.casefold().find(query)
                if start>=0:
                    matches.append(dict(bookId=summary['id'],bookTitle=summary['title'],location=chapter['location'],label=chapter['label'],title=chapter['title'],excerpt=('…' if start>75 else '')+text[max(0,start-75):start+len(query)+180]))
                    if len(matches)==60:
                        return matches
        return matches
