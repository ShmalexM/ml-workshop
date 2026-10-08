import { useRef, useState, type DragEvent, type ReactNode } from 'react'
import { ArrowRight, BookOpen, Check, ExternalLink, FileUp, LoaderCircle, Trash2 } from 'lucide-react'
import { importBook, removeBook } from '../api'
import type { Book, BookImportResult, ReadingState } from '../libraryTypes'

const suggestedBooks = [
  {id: 'gpu-glossary', title: 'GPU Glossary', author: 'Modal', tag: 'GPU FUNDAMENTALS',
    description: 'Connect GPU hardware, CUDA, and performance concepts.',
    url: 'https://modal.com/gpu-glossary', link: 'Read on Modal',
    hint: 'Modal publishes the glossary as a website, with its Markdown source on GitHub under CC BY 4.0. There is no official EPUB or PDF. If you made your own copy, add it here to read offline.'},
  {id: 'inference-engineering', title: 'Inference Engineering', author: 'Philip Kiely · Baseten', tag: 'MODELS IN PRODUCTION',
    description: 'Explore how models are optimized and served in production.',
    url: 'https://www.baseten.co/inference-engineering/', link: 'Get a free copy',
    hint: 'Baseten offers the book as a free PDF or EPUB. Download your copy there, then add it here. Use the PDF for the printed page layout and the reading guides.'},
]

function DropZone({label, disabled, busy, percent, error, onFiles}: {
  label: string; disabled: boolean; busy: boolean; percent: number; error?: string;
  onFiles: (files: File[]) => void;
}) {
  const input = useRef<HTMLInputElement>(null)
  const depth = useRef(0)
  const [dragging, setDragging] = useState(false)
  function drag(event: DragEvent) { event.preventDefault(); event.stopPropagation() }
  return <div className={'book-drop ' + (dragging && !disabled ? 'book-drop-active' : '')}
    onDragEnter={event => { drag(event); if (event.dataTransfer.types.includes('Files')) { depth.current++; setDragging(true) } }}
    onDragOver={event => { drag(event); event.dataTransfer.dropEffect = disabled ? 'none' : 'copy' }}
    onDragLeave={event => { drag(event); if (--depth.current <= 0) { depth.current = 0; setDragging(false) } }}
    onDrop={event => { drag(event); depth.current = 0; setDragging(false); if (!disabled) onFiles(Array.from(event.dataTransfer.files)) }}>
    <input ref={input} type="file" accept=".pdf,.epub,application/pdf,application/epub+zip" hidden
      aria-label={`Choose file for ${label}`} disabled={disabled}
      onChange={event => { const files = Array.from(event.target.files || []); event.target.value = ''; if (files.length) onFiles(files) }} />
    {busy ? <div className="book-import-progress" role="status" aria-live="polite">
      <LoaderCircle size={23} className="book-import-spinner" aria-hidden="true" />
      <strong>{percent < 100 ? `Uploading file · ${percent}%` : 'Preparing your book…'}</strong>
      <p>{percent < 100 ? 'Copying to your local library.' : 'Building chapters and search. Large books can take up to 90 seconds.'}</p>
      <progress max={100} value={percent < 100 ? percent : undefined} aria-label={percent < 100 ? 'File upload progress' : 'Preparing book'} />
    </div> : <>
      <FileUp size={24} aria-hidden="true" /><strong>Drop your PDF or EPUB here</strong>
      <span>or choose a file from your computer</span>
      <button className="secondary-button" disabled={disabled} onClick={() => input.current?.click()} aria-label={`Choose file for ${label}`}>Choose file</button>
      <small>One book at a time · Up to 100 MB</small>
    </>}
    {error && <p className="book-import-error" role="alert">{error}</p>}
  </div>
}

/** Two-step removal. The confirm step is inline because the Mac app's web view has no confirm() dialog. */
export function RemoveBook({book, onRemoved}: {book: Pick<Book, 'id' | 'title'>; onRemoved: (id: string) => void}) {
  const [confirming, setConfirming] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function remove() {
    setBusy(true); setError('')
    try { await removeBook(book.id); onRemoved(book.id) }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not remove this book. Try again.'); setBusy(false) }
  }
  if (!confirming) return <button className="text-button book-remove" onClick={() => setConfirming(true)}><Trash2 size={14} aria-hidden="true" />Remove book</button>
  return <div className="book-remove-confirm" role="group" aria-label={`Remove ${book.title}`}>
    <p>Remove “{book.title}” from your library? This deletes the copy stored by Workshop, not the file you imported. Your notes and reading position are kept.</p>
    <div className="book-remove-actions">
      <button className="book-danger" disabled={busy} onClick={() => void remove()}>{busy ? 'Removing…' : 'Remove'}</button>
      <button className="secondary-button" disabled={busy} autoFocus onClick={() => { setConfirming(false); setError('') }}>Cancel</button>
    </div>
    {error && <p className="book-remove-error" role="alert">{error}</p>}
  </div>
}

export default function BookImports({books, states, onImported, onOpen, onRemoved, children}: {
  books: Book[]; states: Record<string, ReadingState>; onImported: (result: BookImportResult) => void;
  onOpen: (id: string, location: number) => void; onRemoved: (id: string) => void; children?: ReactNode;
}) {
  const [active, setActive] = useState<string | null>(null)
  const activeRef = useRef(false)
  const [percent, setPercent] = useState(0)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [success, setSuccess] = useState<BookImportResult | null>(null)
  async function add(files: File[], id: string) {
    if (activeRef.current) return
    setSuccess(null); setErrors(old => ({...old, [id]: ''}))
    const file = files[0]
    if (files.length !== 1 || !file) { setErrors(old => ({...old, [id]: 'Choose one book at a time.'})); return }
    if (!/\.(pdf|epub)$/i.test(file.name)) { setErrors(old => ({...old, [id]: 'This file type is not supported. Choose a PDF or EPUB.'})); return }
    if (!file.size || file.size > 100 * 1024 * 1024) { setErrors(old => ({...old, [id]: 'Choose a non-empty file no larger than 100 MB.'})); return }
    activeRef.current = true; setActive(id); setPercent(0)
    try {
      const result = await importBook(file, id, setPercent)
      onImported(result); setSuccess(result)
    } catch (error) {
      setErrors(old => ({...old, [id]: error instanceof Error ? error.message : 'Could not import this book. Try again.'}))
    } finally { activeRef.current = false; setActive(null) }
  }
  return <>
    {success && books.some(book => book.id === success.book.id) && <div className="book-import-success" role="status"><Check size={20} aria-hidden="true" /><div><strong>{success.book.title}</strong><span>{success.alreadyImported ? 'Already in your library. Your notes and reading position are unchanged.' : 'Ready to read. Your copy is saved on this computer.'}</span></div>
      <button className="text-button" onClick={() => onOpen(success.book.id, states[success.book.id]?.location || success.readingState?.location || 1)}>Read book<ArrowRight size={16} /></button></div>}
    <div className="book-section-heading"><h2>Suggested reading</h2><span>Add your own copies</span></div>
    <div className="book-suggestions">{suggestedBooks.map(suggestion => {
      const book = books.find(item => item.id === suggestion.id)
      return <section className={'book-import-card ' + suggestion.id} key={suggestion.id} aria-label={suggestion.title}>
        <div className="book-card-heading"><div className="book-card-icon"><BookOpen size={26} aria-hidden="true" /></div><span>{suggestion.tag}</span>{book && <span className="book-ready"><Check size={13} />In your library</span>}</div>
        <h3>{suggestion.title}</h3><p className="book-card-author">{suggestion.author}</p><p className="book-card-description">{suggestion.description}</p>
        {book ? <div className="book-card-ready"><p>{book.count} {book.format === 'pdf' ? 'pages' : 'sections'} · {book.format.toUpperCase()} · Available offline</p>
          <button className="primary-button" onClick={() => onOpen(book.id, states[book.id]?.location || 1)}>{states[book.id]?.updatedAt ? 'Continue reading' : 'Open book'}<ArrowRight size={16} /></button>
          <RemoveBook book={book} onRemoved={onRemoved} /></div>
          : <><a className="book-source-link" href={suggestion.url} target="_blank" rel="noreferrer">{suggestion.link}<ExternalLink size={14} /></a><p className="book-import-hint">{suggestion.hint}</p>
            <DropZone label={suggestion.title} disabled={active !== null} busy={active === suggestion.id} percent={percent} error={errors[suggestion.id]} onFiles={files => void add(files, suggestion.id)} /></>}
      </section>
    })}</div>
    {children}
    <section className="book-add-other" aria-label="Add another book"><div><h2>Add another book</h2><p>Bring any PDF or EPUB, including another edition. Read, search, bookmark, and take notes in one place.</p><small>Your files stay on this computer. They are not sent to an online service.</small></div>
      <DropZone label="another book" disabled={active !== null} busy={active === ''} percent={percent} error={errors['']} onFiles={files => void add(files, '')} /></section>
  </>
}
