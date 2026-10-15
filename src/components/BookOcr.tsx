import { useEffect, useRef, useState } from 'react'
import { ScanText } from 'lucide-react'
import { ocrPage } from '../api'
import type { Book, OcrStatus } from '../libraryTypes'

/** For a PDF or image without a text layer: says that search is not available, and offers OCR with a local
 * Tesseract. Pages are read in order, one request each, and the text is stored for search as it arrives. */
export default function BookOcr({ book, ocr, onBook }: { book: Book; ocr?: OcrStatus; onBook: (book: Book) => void }) {
  const [running, setRunning] = useState(false)
  const [page, setPage] = useState(0)
  const [error, setError] = useState('')
  const stopped = useRef(false)
  useEffect(() => () => { stopped.current = true }, [])
  useEffect(() => { stopped.current = true; setError('') }, [book.id])
  const total = Math.min(book.count, ocr?.maxPages || 300)
  const done = book.ocrPages || 0
  const canRead = book.format === 'pdf' || book.format === 'image'
  const note = book.format === 'pdf' ? 'This PDF has no text layer, so search is not available.'
    : book.format === 'image' ? 'This image has no text layer, so search is not available.'
    : 'This file has no text, so search is not available.'

  async function run() {
    stopped.current = false; setRunning(true); setError('')
    let renderer: { render: (page: number) => Promise<Blob>; close: () => void } | undefined
    try {
      const { pageRenderer } = await import('./PdfPage')
      renderer = await pageRenderer(book)
      for (let next = done + 1; next <= total && !stopped.current; next++) {
        setPage(next)
        const result = await ocrPage(book.id, next, await renderer.render(next))
        onBook(result.book)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'OCR stopped. Try again.')
    } finally {
      renderer?.close(); setRunning(false)
    }
  }

  if (done >= total && !running) return <p className="book-ocr-done">Search uses text read by OCR.</p>
  if (!canRead) return <p className="book-no-text">{note}</p>
  return <div className={done ? 'book-ocr-progress' : 'book-no-text'}>
    {done ? <p>OCR has read {done} of {total} pages. Search covers those pages.</p> : <p>{note}</p>}
    {!ocr?.available ? <small>{ocr?.install || 'Install Tesseract, then restart Workshop, to add OCR search.'}</small>
      : running ? <div className="book-ocr-running" role="status" aria-live="polite">
          <span>Reading page {page} of {total}…</span>
          <progress max={total} value={Math.max(0, page - 1)} aria-label="OCR progress" />
          <button className="text-button" onClick={() => { stopped.current = true }}>Stop</button>
        </div>
      : <>
          <button className="secondary-button book-ocr-button" onClick={() => void run()}><ScanText size={16} aria-hidden="true" />{done ? 'Continue OCR' : 'Make searchable (OCR)'}</button>
          <small>Tesseract reads the pages on this computer{book.count > total ? `, up to page ${total}` : ''}.</small>
        </>}
    {error && <p className="book-ocr-error" role="alert">{error}</p>}
  </div>
}
