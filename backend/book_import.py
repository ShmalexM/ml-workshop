"""Bounded browser imports. Parsing runs in a disposable worker, then publishes atomically."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from library import Library, UnreadableBook, digest, import_book, normalized

SUGGESTED = {'gpu-glossary': 'GPU Glossary', 'inference-engineering': 'Inference Engineering'}
PARSE_TIMEOUT = 90
# Staging folders older than this belong to a server that stopped mid-import or mid-removal.
STALE_STAGING_SECONDS = 3600
WORKER_MEMORY = 3 << 30


class ImportConflict(ValueError):
    pass


def sweep_staging(data_dir):
    """Delete leftover staging folders, which can hold up to 100 MB each."""
    cutoff = time.time() - STALE_STAGING_SECONDS
    for pattern in ('.upload-*', '.parse-*', 'library/.import-*', 'library/.removing-*'):
        for path in Path(data_dir).glob(pattern):
            try:
                if path.is_dir() and not path.is_symlink() and path.stat().st_mtime < cutoff:
                    shutil.rmtree(path)
            except OSError:
                pass


UNREADABLE = 'Your saved copy of this book could not be opened. Remove it in Books, then add the file again.'


def import_upload(source, data_dir, filename, suggested=''):
    try:
        return import_checked_upload(source, data_dir, filename, suggested)
    except UnreadableBook:
        raise ImportConflict(UNREADABLE) from None


def import_checked_upload(source, data_dir, filename, suggested):
    data_dir = Path(data_dir)
    sweep_staging(data_dir)
    library = Library(data_dir)
    checksum = digest(source)
    book_id = suggested or 'book-' + checksum[:24]
    if suggested and suggested not in SUGGESTED:
        raise ValueError('Unknown suggested book. Use Add another book instead.')
    # Repeated drops return the same book and never reset notes or reading position.
    candidates = [library.book(book_id)] if (library.root/book_id/'book.json').is_file() else []
    if not suggested:
        candidates += library.catalog()
    for book in candidates:
        if book['sha256'] == checksum:
            return book['id'], True
    if candidates and suggested:
        raise ImportConflict('A different edition is already imported. Use Add another book to keep both copies and preserve your notes.')
    with tempfile.TemporaryDirectory(prefix='.parse-', dir=data_dir) as temporary:
        try:
            result = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), str(source), temporary,
                 book_id, filename, SUGGESTED.get(suggested, '')],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=PARSE_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            raise ValueError('This book took too long to process. Try a smaller or repaired PDF or EPUB.') from None
        if result.returncode:
            try:
                message = json.loads(result.stdout)['error']
            except (ValueError, KeyError, TypeError):
                message = 'Could not read this book. Try a fresh, unencrypted PDF or EPUB.'
            raise ValueError(message)
        library.root.mkdir(parents=True, exist_ok=True)
        target = library.root/book_id
        if target.exists():
            # A CLI import may have completed while the worker was parsing.
            if library.book(book_id)['sha256'] == checksum:
                return book_id, True
            raise ImportConflict('A different edition is already imported. Use Add another book to keep both copies.')
        (Path(temporary)/'library'/book_id).rename(target)
    return book_id, False


def parse(source, destination, book_id, filename, expected_title):
    book = import_book(source, destination, book_id)
    if book['title'] == Path(source).stem:
        book['title'] = Path(filename).stem
    if expected_title and normalized(expected_title).casefold() not in normalized(book['title']).casefold():
        raise ValueError(f'This file is titled “{book["title"][:120]}”. Choose your copy of {expected_title}, or use Add another book.')
    (Path(destination)/'library'/book_id/'book.json').write_text(json.dumps(book, ensure_ascii=False), encoding='utf-8')


def limit_memory():
    """Linux enforces an address-space limit; macOS and Windows rely on the import size limits."""
    if not sys.platform.startswith('linux'):
        return
    import resource
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    limit = WORKER_MEMORY if hard == resource.RLIM_INFINITY else min(WORKER_MEMORY, hard)
    resource.setrlimit(resource.RLIMIT_AS, (limit, hard))


if __name__ == '__main__':
    try:
        limit_memory()
        parse(*sys.argv[1:])
    except ValueError as exc:
        print(json.dumps({'error': str(exc)}))
        sys.exit(1)
    except MemoryError:
        print(json.dumps({'error': 'This book needs more memory to import than the import limit allows.'}))
        sys.exit(1)
    except Exception:
        print(json.dumps({'error': 'Could not read this book. Try a fresh, unencrypted PDF or EPUB.'}))
        sys.exit(1)
