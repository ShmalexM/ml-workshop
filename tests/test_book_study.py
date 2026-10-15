"""Reading guides link to lessons that exist, and PDF guides link by page number, even without a text layer."""
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
import book_study
from book_study import GUIDES, HARNESS_GUIDE_EDITION, study_guides
from courses import BY_ID
from library import KNOWN_EDITIONS, Library, import_book

HARNESS_GUIDES = ['harness-role', 'harness-instructions', 'harness-disclosure', 'harness-rpi',
                  'harness-subagents', 'harness-choose', 'harness-routing', 'harness-review']


class ScannedGuide:
    """The library summary of a 22-page PDF whose pages have no text: its contents are page numbers only."""
    def __init__(self, sha=HARNESS_GUIDE_EDITION, format='pdf'):
        self.sha, self.format = sha, format

    def book(self, book_id):
        if book_id != 'harness-guide':
            raise KeyError(book_id)
        toc = [dict(title=f'Page {n}', location=n, label=str(n), depth=0) for n in range(1, 23)]
        return dict(title='an_engineers_guide_to_harnesses', format=self.format, sha256=self.sha,
                    count=22, toc=toc)


class BookStudyTests(unittest.TestCase):
    def test_every_guide_links_existing_lessons(self):
        self.assertEqual(len({guide['id'] for guide in GUIDES}), len(GUIDES))
        for guide in GUIDES:
            with self.subTest(guide=guide['id']):
                self.assertTrue(guide['lessons'])
                for lesson_id in guide['lessons']:
                    self.assertIn(lesson_id, BY_ID)

    def test_harness_guide_links_pages_and_every_harness_lesson(self):
        guides = study_guides(ScannedGuide())
        self.assertEqual([guide['id'] for guide in guides], HARNESS_GUIDES)
        linked = {lesson for guide in guides for lesson in guide['lessons']}
        self.assertTrue({f'harness-{n}' for n in range(1, 9)} <= linked)
        by_id = {guide['id']: guide for guide in guides}
        self.assertEqual([r['location'] for r in by_id['harness-rpi']['readings']], [6])
        self.assertEqual(by_id['harness-rpi']['lessons'][0], 'harness-7')
        for guide in guides:
            for reading in guide['readings']:
                # Location n is the PDF page; after the cover, the printed page number is n - 1.
                printed = int(re.search(r'p\. (\d+)$', reading['title']).group(1))
                self.assertEqual(printed, reading['location'] - 1, reading)
                self.assertTrue(1 <= reading['location'] <= 22)

    def test_harness_guides_only_apply_to_the_verified_pdf(self):
        self.assertEqual(study_guides(ScannedGuide(sha='another-edition')), [])
        self.assertEqual(study_guides(ScannedGuide(format='epub')), [])
        self.assertEqual([g['id'] for g in study_guides(ScannedGuide(), 'harness-6')], ['harness-disclosure'])

    def test_guide_edition_is_the_known_edition_of_its_card(self):
        # The importer matches the untitled harness guide PDF to its card by this checksum, and labels
        # PDF page n as printed page n - 1, which is what the reading titles say.
        edition = KNOWN_EDITIONS[HARNESS_GUIDE_EDITION]
        self.assertEqual(edition['book'], 'harness-guide')
        self.assertEqual((edition['pageOffset'], edition['front']), (-1, ['Cover']))

    def test_every_book_card_is_a_suggested_book_with_guides(self):
        from book_import import SUGGESTED
        source = (Path(__file__).resolve().parents[1] / 'src' / 'components' / 'BookImports.tsx').read_text(encoding='utf-8')
        cards = re.findall(r"\{id: '([a-z0-9-]+)', title: '", source)
        self.assertEqual(cards, ['gpu-glossary', 'inference-engineering', 'harness-guide'])
        self.assertEqual(set(cards), set(SUGGESTED))
        self.assertEqual({guide['bookId'] for guide in GUIDES}, set(cards))

    def test_imported_pdf_without_text_still_gets_its_guides(self):
        from pypdf import PdfWriter
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            writer = PdfWriter()
            for _ in range(22):
                writer.add_blank_page(width=612, height=792)
            source = root / 'guide.pdf'
            with source.open('wb') as stream:
                writer.write(stream)
            book = import_book(source, root / 'data', 'harness-guide')
            library = Library(root / 'data')
            self.assertEqual(book['count'], 22)
            self.assertEqual(''.join(chapter['text'] for chapter in library.chapters('harness-guide')), '')
            with patch.dict(book_study.PDF_EDITIONS, {'harness-guide': book['sha256']}):
                guides = study_guides(library)
            self.assertEqual([guide['id'] for guide in guides], HARNESS_GUIDES)
            self.assertEqual(guides[0]['readings'], [dict(location=3, title='What a harness does · p. 2')])


if __name__ == '__main__':
    unittest.main()
