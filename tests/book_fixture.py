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
