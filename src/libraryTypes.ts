export type BookLocation = { bookId: string; location: number; anchor?: string }
export type BookEntry = { title: string; location: number; label: string; depth: number; key?: string }
export type BookFormat = 'pdf' | 'epub' | 'markdown' | 'text' | 'html' | 'docx' | 'ipynb' | 'image'
/** textPages: pages or sections with searchable text (0 for a PDF or image without a text layer). ocrPages: pages read by OCR, from page 1. */
export type Book = { id: string; title: string; author: string; format: BookFormat; count: number; toc: BookEntry[]; rights: string; attribution: string; sha256: string; cover?: string; assets: { path: string; bytes: number; sha256: string; mediaType: string }[]; textPages?: number; ocrPages?: number; sourceExtension?: string; printedLabels?: boolean }
/** OCR with a local Tesseract: whether it is installed, how to install it, and the page limit per book. */
export type OcrStatus = { available: boolean; install: string; maxPages: number }
export type ReadingState = { location: number; notes: string; bookmarks: number[]; completed: string[]; updatedAt: number }
export type StudyGuide = { id: string; bookId: string; bookTitle: string; title: string; focus: string; question: string; readings: { location: number; title: string }[]; lessons: string[] }
/** unreadable: IDs of books whose saved summary (book.json) could not be read. */
export type LibraryData = { books: Book[]; unreadable?: string[]; guides: StudyGuide[]; readingState: Record<string, ReadingState>; ocr?: OcrStatus }
export type BookImportResult = { book: Book; guides: StudyGuide[]; readingState: ReadingState | null; alreadyImported: boolean }
export type Chapter = { location: number; title: string; label: string; text: string; html?: string; ocr?: boolean }
export type SearchHit = { bookId: string; bookTitle: string; location: number; label: string; title: string; excerpt: string }

export function bookLink(bookId: string, location: number) { return `#books/${bookId}/${location}` }

/** Format badges and the file types the importer accepts. Keep in step with FORMATS and INPUT_LIMITS in backend/library.py. */
export const formatLabels: Record<BookFormat, string> = { pdf: 'PDF', epub: 'EPUB', markdown: 'Markdown', text: 'Text', html: 'HTML', docx: 'Word', ipynb: 'Notebook', image: 'Image' }
const MB = 1024 * 1024
export const importTypes: Record<string, { format: BookFormat; limit: number }> = {
  pdf: { format: 'pdf', limit: 100 * MB }, epub: { format: 'epub', limit: 100 * MB }, docx: { format: 'docx', limit: 100 * MB },
  md: { format: 'markdown', limit: 16 * MB }, markdown: { format: 'markdown', limit: 16 * MB }, txt: { format: 'text', limit: 16 * MB },
  html: { format: 'html', limit: 32 * MB }, htm: { format: 'html', limit: 32 * MB }, ipynb: { format: 'ipynb', limit: 50 * MB },
  png: { format: 'image', limit: 50 * MB }, jpg: { format: 'image', limit: 50 * MB }, jpeg: { format: 'image', limit: 50 * MB },
  webp: { format: 'image', limit: 50 * MB }, gif: { format: 'image', limit: 50 * MB },
}
export const importAccept = Object.keys(importTypes).map(extension => '.' + extension).join(',')
export const supportedTypes = 'PDF, EPUB, Word (.docx), Markdown (.md), plain text (.txt), HTML (.html), Jupyter notebooks (.ipynb) and images (PNG, JPEG, WebP, GIF)'
/** True for page labels that are page numbers, such as 12 or iv, and false for names such as Cover. */
export function isPageNumber(label: string) { return /\d/.test(label) || /^[ivxlcdm]+$/i.test(label) }
/** How a search result or bookmark names one location: "printed page 5" only when the PDF has printed page labels. */
export function locationLabel(book: Pick<Book, 'format' | 'printedLabels'> | undefined, location: number, label: string) {
  if (book?.format === 'pdf') {
    if (book.printedLabels === false || !label) return `page ${location}`
    return isPageNumber(label) ? `printed page ${label}` : label
  }
  return `${book?.format === 'image' ? 'page' : 'section'} ${label}`
}
/** True for books read as pages (PDF and images) rather than as sections. */
export function pageBook(book: Pick<Book, 'format'>) { return book.format === 'pdf' || book.format === 'image' }
/** A PDF or image without a text layer, and no OCR text yet: search finds nothing in it. */
export function withoutText(book: Pick<Book, 'format' | 'textPages' | 'ocrPages'>) { return book.textPages === 0 && !book.ocrPages }
