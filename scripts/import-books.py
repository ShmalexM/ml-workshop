"""Import personally supplied ebooks into the ignored local data directory."""
import argparse
import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from library import import_book

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--epub',type=Path,help='Path to the Modal GPU Glossary EPUB')
parser.add_argument('--pdf',type=Path,help='Path to Inference Engineering PDF')
parser.add_argument('--file',type=Path,help='Another local EPUB/PDF (requires --id)')
parser.add_argument('--id',help='Stable lowercase ID for --file')
args = parser.parse_args()
if not any((args.epub,args.pdf,args.file)):
    parser.error('Provide --epub, --pdf, or --file')
if args.file and not args.id:
    parser.error('--file requires --id')
data = Path(os.environ.get('ML_WORKSHOP_DATA_DIR',ROOT/'data'))
for source,book_id in [(args.epub,'gpu-glossary'),(args.pdf,'inference-engineering'),(args.file,args.id)]:
    if source:
        book = import_book(source,data,book_id)
        print(f"{book['title']}: {book['count']} {'pages' if book['format']=='pdf' else 'sections'}, {len(book['assets'])} original image assets. SHA-256: {book['sha256']}")
print('Open Books in Engineering Workshop. Originals and extracted content stay in data/library/ and are ignored by Git.')
