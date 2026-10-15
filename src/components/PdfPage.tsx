import { useEffect, useRef, useState } from 'react'
import { getDocument, GlobalWorkerOptions, type PDFDocumentProxy } from 'pdfjs-dist'
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
import { authorized, sessionHeaders } from '../api'

GlobalWorkerOptions.workerSrc = workerUrl

export default function PdfPage({ bookId, page, zoom }: { bookId: string; page: number; zoom: number }) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const host = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(720)
  const [pdf, setPdf] = useState<PDFDocumentProxy | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const observer = new ResizeObserver(entries => setWidth(Math.max(240, entries[0].contentRect.width - 32)))
    if (host.current) observer.observe(host.current)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    let active = true
    setPdf(null); setError(''); setLoading(true)
    const task = getDocument({
      // Book files need the session token, like every other route with learner data.
      url: `/api/library/${bookId}/asset/source.pdf`, httpHeaders: sessionHeaders(),
      cMapUrl: '/pdfjs/cmaps/', cMapPacked: true,
      standardFontDataUrl: '/pdfjs/standard_fonts/', wasmUrl: '/pdfjs/wasm/',
      iccUrl: '/pdfjs/iccs/',
      enableXfa: false,
    })
    task.promise.then(value => { if (active) setPdf(value) }).catch(e => { if (active) { setError(e.message); setLoading(false) } })
    return () => { active = false; void task.destroy() }
  }, [bookId])

  useEffect(() => {
    if (!pdf || !canvas.current) return
    let active = true
    let renderTask: ReturnType<Awaited<ReturnType<PDFDocumentProxy['getPage']>>['render']> | undefined
    setLoading(true); setError('')
    const target = canvas.current
    // Give each render its own canvas. A cancelled render never races on the
    // visible canvas when the reader quickly changes pages or zoom level.
    const buffer = document.createElement('canvas')
    void pdf.getPage(page).then(async sheet => {
      if (!active) return
      const base = sheet.getViewport({ scale: 1 })
      const viewport = sheet.getViewport({ scale: Math.min(width, 900) / base.width * zoom })
      const pixels = Math.min(window.devicePixelRatio || 1, 2, Math.sqrt(24_000_000 / (viewport.width * viewport.height)))
      buffer.width = Math.ceil(viewport.width * pixels)
      buffer.height = Math.ceil(viewport.height * pixels)
      renderTask = sheet.render({ canvas: buffer, viewport, transform: [pixels, 0, 0, pixels, 0, 0] })
      await renderTask.promise
      if (!active) return
      target.width = buffer.width; target.height = buffer.height
      target.style.width = `${viewport.width}px`; target.style.height = `${viewport.height}px`
      target.getContext('2d')!.drawImage(buffer, 0, 0)
      setLoading(false)
    }).catch(e => { if (active && e.name !== 'RenderingCancelledException') { setError(e.message); setLoading(false) } })
    return () => { active = false; renderTask?.cancel() }
  }, [pdf, page, zoom, width])

  return <div className="pdf-stage" ref={host} aria-busy={loading}>
    {loading && <p className="pdf-status" role="status">Rendering page…</p>}
    {error && <p className="book-error" role="alert">Could not render this page: {error}. You can still download the PDF above.</p>}
    <div className="pdf-scroll"><canvas ref={canvas} aria-label={`PDF page ${page}`} style={{ visibility: loading || error ? 'hidden' : 'visible' }} /></div>
  </div>
}

const OCR_PIXELS = 16_000_000

function pngOf(canvas: HTMLCanvasElement) {
  return new Promise<Blob>((resolve, reject) => canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error('Could not prepare this page for OCR.')), 'image/png'))
}

/** Renders pages of a PDF or image book as PNG images for OCR: about 300 dpi, at most 16 megapixels. */
export async function pageRenderer(book: { id: string; format: string; cover?: string }) {
  if (book.format === 'image') {
    return {
      async render() {
        const response = await authorized(`/api/library/${book.id}/asset/${book.cover}`, {})
        if (!response.ok) throw new Error('Could not load this image.')
        const bitmap = await createImageBitmap(await response.blob())
        const scale = Math.min(1, Math.sqrt(OCR_PIXELS / (bitmap.width * bitmap.height)))
        const canvas = document.createElement('canvas')
        canvas.width = Math.max(1, Math.round(bitmap.width * scale)); canvas.height = Math.max(1, Math.round(bitmap.height * scale))
        const context = canvas.getContext('2d')!
        context.fillStyle = '#fff'; context.fillRect(0, 0, canvas.width, canvas.height)
        context.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
        bitmap.close()
        return pngOf(canvas)
      },
      close() {},
    }
  }
  const task = getDocument({
    url: `/api/library/${book.id}/asset/source.pdf`, httpHeaders: sessionHeaders(),
    cMapUrl: '/pdfjs/cmaps/', cMapPacked: true, standardFontDataUrl: '/pdfjs/standard_fonts/', wasmUrl: '/pdfjs/wasm/', iccUrl: '/pdfjs/iccs/', enableXfa: false,
  })
  const pdf = await task.promise
  return {
    async render(page: number) {
      const sheet = await pdf.getPage(page)
      const base = sheet.getViewport({ scale: 1 })
      const viewport = sheet.getViewport({ scale: Math.min(300 / 72, Math.sqrt(OCR_PIXELS / (base.width * base.height))) })
      const canvas = document.createElement('canvas')
      canvas.width = Math.ceil(viewport.width); canvas.height = Math.ceil(viewport.height)
      const context = canvas.getContext('2d')!
      context.fillStyle = '#fff'; context.fillRect(0, 0, canvas.width, canvas.height)
      await sheet.render({ canvas, viewport }).promise
      sheet.cleanup()
      return pngOf(canvas)
    },
    close() { void task.destroy() },
  }
}
