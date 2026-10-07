import { useEffect, useRef, useState } from 'react'
import { getDocument, GlobalWorkerOptions, type PDFDocumentProxy } from 'pdfjs-dist'
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

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
      url: `/api/library/${bookId}/asset/source.pdf`,
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
