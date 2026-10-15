"""Optional OCR for PDFs and images without a text layer, with a local Tesseract.

The reader renders each page to a PNG with PDF.js and sends it here, one page per request.
Tesseract reads it in a temporary folder with a time limit, and the text is stored for search
(Library.set_ocr_text). Nothing is downloaded: without a `tesseract` executable, OCR is off.
"""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile

from library import MAX_OCR_PAGES, MAX_OCR_TEXT

PAGE_SECONDS = 60
MAX_PAGE_BYTES = 25 << 20
MAX_PAGE_PIXELS = 40_000_000
# The Mac app and some launchers start the server without the shell's PATH.
KNOWN_PATHS = {'darwin': ['/opt/homebrew/bin/tesseract', '/usr/local/bin/tesseract'],
               'win32': [r'C:\Program Files\Tesseract-OCR\tesseract.exe']}
INSTALL = {'darwin': 'To add search, install Tesseract with Homebrew (brew install tesseract), then restart Workshop.',
           'win32': 'To add search, install Tesseract (winget install UB-Mannheim.TesseractOCR), then restart Workshop.'}
LINUX_INSTALL = 'To add search, install Tesseract (for example sudo apt install tesseract-ocr), then restart Workshop.'


def tesseract_command():
    """The command that runs Tesseract, or None when it is not installed."""
    found = shutil.which('tesseract')
    if found:
        return [found]
    for path in KNOWN_PATHS.get(sys.platform, []):
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return [path]
    return None


def status():
    return dict(available=bool(tesseract_command()), install=INSTALL.get(sys.platform, LINUX_INSTALL), maxPages=MAX_OCR_PAGES)


def png_size(raw):
    """(width, height) of a PNG, or None if raw is not one."""
    if not raw.startswith(b'\x89PNG\r\n\x1a\n') or raw[12:16] != b'IHDR' or len(raw) < 24:
        return None
    return int.from_bytes(raw[16:20], 'big'), int.from_bytes(raw[20:24], 'big')


def recognize(raw, work_dir):
    """Read the text of one page image. Raises ValueError with a message for the reader."""
    size = png_size(raw)
    if not size or not all(size) or size[0] * size[1] > MAX_PAGE_PIXELS:
        raise ValueError('Send each page as a PNG image of at most 40 megapixels.')
    command = tesseract_command()
    if not command:
        raise LookupError('Tesseract is not installed.')
    with tempfile.TemporaryDirectory(prefix='.ocr-', dir=work_dir) as temporary:
        image = Path(temporary)/'page.png'
        image.write_bytes(raw)
        try:
            result = subprocess.run([*command, str(image), 'stdout'], cwd=temporary, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=PAGE_SECONDS)
        except subprocess.TimeoutExpired:
            raise ValueError(f'Tesseract took longer than {PAGE_SECONDS} seconds on this page, so OCR stopped.') from None
        except OSError:
            raise ValueError('Tesseract could not be started. Check that it is installed, then restart Workshop.') from None
    if result.returncode:
        raise ValueError('Tesseract could not read this page. Check that its English language data is installed.')
    return result.stdout[:MAX_OCR_TEXT * 4].decode('utf-8', 'replace')
