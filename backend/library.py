"""Local-only EPUB/PDF imports. Originals and extracted content live under data/."""
from functools import lru_cache
from html import escape
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit, unquote, quote
from xml.etree import ElementTree as ET
import hashlib
import json
import posixpath
import re
import shutil
import tempfile
import unicodedata
import zipfile

MAX_BOOK_BYTES = 100 * 1024 * 1024
IMPORT_VERSION = 1
BOOK_ID = re.compile(r'^[a-z0-9][a-z0-9-]{0,79}$')
TAGS = {'p','h1','h2','h3','h4','h5','h6','div','section','article','span','strong','em','b','i','u','s','small','sup','sub','blockquote','pre','code','ul','ol','li','dl','dt','dd','table','thead','tbody','tfoot','tr','th','td','caption','figure','figcaption','hr','br','a','img'}
DROP = {'script','style','iframe','object','embed','form','input','button','link','meta','base'}
IMAGE_TYPES = {'image/png','image/jpeg','image/gif','image/webp','image/svg+xml'}

def normalized(text):
    return ' '.join(unicodedata.normalize('NFKC', text).replace('\u00ad','').split())

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

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
    attrs = {}
    if element.get('id'):
        attrs['id'] = element.get('id')
    # Keep semantic classes used by the source for figure captions, not source CSS.
    if element.get('class'):
        attrs['class'] = element.get('class')
    for key in ('colspan','rowspan'):
        if element.get(key, '').isdigit():
            attrs[key] = element.get(key)
    if tag == 'img':
        try:
            name = archive_path(posixpath.dirname(chapter_path), element.get('src',''))
        except ValueError:
            return '<p class="unavailable-media">Remote image omitted from this offline copy.</p>'
        if name not in assets:
            return '<p class="unavailable-media">Image was not included in the source EPUB.</p>'
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
                attrs['href'] = f'#books/{book_id}/{chapters[target]}'
                if parsed.fragment:
                    attrs['href'] += '/' + quote(unquote(parsed.fragment), safe='')
    rendered = ''.join(f' {key}="{escape(str(value), quote=True)}"' for key,value in attrs.items())
    return f'<{tag}{rendered}>' + ('' if tag in ('img','br','hr') else children + f'</{tag}>')

def import_epub(source, folder, book_id):
    with zipfile.ZipFile(source) as archive:
        entries = archive.infolist()
        if len(entries)>10000 or sum(e.file_size for e in entries)>250*1024*1024:
            raise ValueError('EPUB expands beyond the local import limit')
        for entry in entries:
            archive_path('',entry.filename)
        container = ET.fromstring(archive.read('META-INF/container.xml'))
        opf_path = next(e.get('full-path') for e in container.iter() if local_name(e.tag)=='rootfile')
        opf_path = archive_path('',opf_path)
        package = ET.fromstring(archive.read(opf_path))
        base = posixpath.dirname(opf_path)
        metadata = next(e for e in package if local_name(e.tag)=='metadata')
        def field(name, fallback=''):
            return next((''.join(e.itertext()).strip() for e in metadata if local_name(e.tag)==name),fallback)
        manifest = {e.get('id'):e for e in package.iter() if local_name(e.tag)=='item'}
        spine = [manifest[e.get('idref')] for e in package.iter() if local_name(e.tag)=='itemref']
        pages = [archive_path(base,e.get('href')) for e in spine if 'nav' not in e.get('properties','').split() and e.get('id')!='cover']
        chapters = {name:i+1 for i,name in enumerate(pages)}
        assets = {}
        image_records = []
        for item in manifest.values():
            media_type = item.get('media-type','')
            if media_type not in IMAGE_TYPES:
                continue
            name = archive_path(base,item.get('href'))
            raw = archive.read(name)
            target = 'assets/' + hashlib.sha256(raw).hexdigest()[:16] + PurePosixPath(name).suffix.lower()
            (folder/target).parent.mkdir(exist_ok=True)
            (folder/target).write_bytes(raw)
            assets[name] = target
            image_records.append(dict(source=name,path=target,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),mediaType=media_type))
        toc = []
        documents = []
        for number,name in enumerate(pages,1):
            root = ET.fromstring(archive.read(name))
            body = next(e for e in root.iter() if local_name(e.tag)=='body')
            title = next((''.join(e.itertext()).strip() for e in body.iter() if local_name(e.tag) in ('h1','h2')),f'Section {number}')
            key = PurePosixPath(name).stem
            item = dict(location=number,title=title,key=key,label=str(number))
            toc.append({**item, 'depth':1 if '--' in key else 0})
            documents.append({**item,'text':normalized(' '.join(body.itertext())),
                              'html':sanitized_html(body,name,book_id,chapters,assets)})
        return dict(title=field('title',source.stem),author=field('creator'),format='epub',
                    rights=field('rights','Rights remain with the source authors.'),sourceUrl=field('source'),
                    attribution='Original text, diagrams, captions, and attributions from the supplied EPUB. Reader layout adapted; image files unchanged.',
                    count=len(documents),toc=toc,documents=documents,assets=image_records,
                    cover=assets.get(next((archive_path(base,e.get('href')) for e in manifest.values() if 'cover-image' in e.get('properties','').split()),'')))

def import_pdf(source, folder, book_id):
    from pypdf import PdfReader
    reader = PdfReader(source)
    if reader.is_encrypted:
        raise ValueError('Encrypted PDFs are not supported')
    labels = reader.page_labels
    documents = [dict(location=i+1,label=labels[i],title=f'Page {labels[i]}',text=normalized(page.extract_text() or '')) for i,page in enumerate(reader.pages)]
    toc = []
    def walk(outline,depth=0):
        for item in outline:
            if isinstance(item,list):
                walk(item,depth+1)
            else:
                page = reader.get_destination_page_number(item)+1
                if 1<=page<=len(documents):
                    toc.append(dict(title=str(item.title),location=page,label=labels[page-1],depth=max(depth-1,0)))
    walk(reader.outline)
    if not toc:
        toc = [dict(title=d['title'],location=d['location'],label=d['label'],depth=0) for d in documents]
    meta = reader.metadata or {}
    # PDF vectors, embedded fonts and original image streams remain in source.pdf.
    return dict(title=str(meta.get('/Title') or source.stem),author=str(meta.get('/Author') or ''),format='pdf',
                rights='Personal local copy. Copyright remains with the publisher; not included in the open-source app.',
                sourceUrl='',attribution='Original PDF preserved unchanged, including vector diagrams, embedded fonts, pictures, and page labels.',
                count=len(documents),toc=toc,documents=documents,assets=[])

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
        existing = json.loads((target/'book.json').read_text(encoding='utf-8'))
        if existing['sha256']==checksum:
            if existing.get('importVersion') == IMPORT_VERSION:
                return existing
            refresh = True
        else:
            raise ValueError('This book ID already contains a different edition; choose a new ID')
    with tempfile.TemporaryDirectory(prefix='.import-',dir=root) as temporary:
        folder = Path(temporary)
        extension = source.suffix.lower()
        shutil.copyfile(source,folder/('source'+extension))
        result = (import_epub if extension=='.epub' else import_pdf)(source,folder,book_id)
        if not result['count']:
            raise ValueError('The book has no readable pages or sections')
        result.update(id=book_id,sha256=checksum,sourceFile='source'+extension,bytes=source.stat().st_size,importVersion=IMPORT_VERSION)
        (folder/'book.json').write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
        # Rename only a complete import into the visible library. No partially loaded books.
        if refresh:
            # Re-index the identical edition without touching reading state or source.
            for asset_path in {asset['path'] for asset in result['assets']}:
                destination = target/asset_path
                destination.parent.mkdir(exist_ok=True)
                (folder/asset_path).replace(destination)
            (folder/'book.json').replace(target/'book.json')
        else:
            folder.rename(target)
    return result

@lru_cache(maxsize=16)
def _read_book(path,mtime):
    return json.loads(Path(path).read_text(encoding='utf-8'))

class Library:
    def __init__(self,data_dir):
        self.root = Path(data_dir)/'library'

    def book(self,book_id):
        if not BOOK_ID.fullmatch(book_id):
            raise KeyError('Unknown book')
        path = self.root/book_id/'book.json'
        if not path.is_file():
            raise KeyError('Unknown book')
        return _read_book(str(path),path.stat().st_mtime_ns)

    def summary(self,book_id):
        return {key:value for key,value in self.book(book_id).items() if key not in ('documents','sourceFile')}

    def catalog(self):
        if not self.root.exists():
            return []
        return [self.summary(path.parent.name) for path in sorted(self.root.glob('*/book.json')) if BOOK_ID.fullmatch(path.parent.name)]

    def chapter(self,book_id,location):
        book = self.book(book_id)
        if not 1<=location<=book['count']:
            raise KeyError('Unknown page or section')
        return book['documents'][location-1]

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

    def search(self,query,book_id=None):
        query = normalized(query).casefold()
        if not 2<=len(query)<=160:
            return []
        books = [self.summary(book_id)] if book_id else self.catalog()
        matches = []
        for summary in books:
            for chapter in self.book(summary['id'])['documents']:
                text = chapter['text'];start = text.casefold().find(query)
                if start>=0:
                    matches.append(dict(bookId=summary['id'],bookTitle=summary['title'],location=chapter['location'],label=chapter['label'],title=chapter['title'],excerpt=('…' if start>75 else '')+text[max(0,start-75):start+len(query)+180]))
                    if len(matches)==60:
                        return matches
        return matches
