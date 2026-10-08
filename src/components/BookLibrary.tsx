import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { ArrowLeft, ArrowRight, Bookmark, BookOpen, BookX, Check, ExternalLink, Search, X, ZoomIn } from 'lucide-react'
import { api } from '../api'
import { bookLink, type BookImportResult, type BookLocation, type Chapter, type LibraryData, type ReadingState, type SearchHit, type StudyGuide } from '../libraryTypes'
import BookImports, { RemoveBook } from './BookImports'
const PdfPage = lazy(() => import('./PdfPage'))
const cacheKey = 'ml-workshop-reading-v1'
const emptyState = (): ReadingState => ({ location: 1, notes: '', bookmarks: [], completed: [], updatedAt: 0 })

function restoredState(data: LibraryData): Record<string, ReadingState> {
  try {
    const cached = JSON.parse(localStorage.getItem(cacheKey) || '{}')
    return Object.fromEntries(data.books.map(book => {
      const server = data.readingState[book.id] || emptyState()
      const local = cached?.[book.id]
      return [book.id, local && local.updatedAt > server.updatedAt ? local : server]
    }))
  } catch { return data.readingState }
}

function FigureViewer({ src, alt, onClose }: { src: string; alt: string; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null)
  const [zoom, setZoom] = useState(1)
  const [size, setSize] = useState('')
  useEffect(() => { dialog.current?.showModal() }, [])
  return <dialog ref={dialog} className="figure-dialog" onCancel={onClose} onClick={e => { if (e.target === e.currentTarget) onClose() }}>
    <header><div><strong>Figure</strong><small>{size} · full resolution</small></div><div className="figure-tools">
      <label>Zoom <select aria-label="Figure zoom" value={zoom} onChange={e => setZoom(Number(e.target.value))}><option value={1}>Fit</option><option value={1.5}>150%</option><option value={2}>200%</option><option value={3}>300%</option></select></label>
      <a href={src} target="_blank" rel="noreferrer">Open image <ExternalLink size={15} /></a>
      <button className="icon-button" aria-label="Close figure" onClick={onClose}><X size={20} /></button>
    </div></header>
    <div className="figure-pan"><img src={src} alt={alt} className={zoom === 1 ? 'figure-fit' : ''} style={{ width: `${zoom * 100}%`, maxWidth: 'none' }} onLoad={e => setSize(`${e.currentTarget.naturalWidth} × ${e.currentTarget.naturalHeight} pixels`)} /></div>
    <p>{alt}</p>
  </dialog>
}

function Guide({ guide, done, onToggle, onLesson }: { guide: StudyGuide; done: boolean; onToggle: () => void; onLesson: (id: string) => void }) {
  return <section className="study-guide">
    <h3>{guide.title}</h3><p>{guide.focus}</p>
    <div className="guide-readings">{guide.readings.map(reading => <a key={`${reading.location}-${reading.title}`} href={bookLink(guide.bookId, reading.location)}><BookOpen size={15} />{reading.title}<ArrowRight size={14} /></a>)}</div>
    <p className="guide-question"><strong>Reading question</strong>{guide.question}</p>
    <div className="guide-actions"><button className={'small-button ' + (done ? 'guide-done' : '')} onClick={onToggle}>{done && <Check size={14} />}{done ? 'Reviewed' : 'Mark reviewed'}</button>
      <button className="text-button" onClick={() => onLesson(guide.lessons[0])}>Open related lesson <ArrowRight size={14} /></button></div>
  </section>
}

export default function BookLibrary({ data, selection, onLesson, onState, onImported, onRemoved, onGuidesSaved }: { data: LibraryData; selection: BookLocation | null; onLesson: (id: string) => void; onState: (bookId: string, state: ReadingState) => void; onImported: (result: BookImportResult) => void; onRemoved: (bookId: string) => void; onGuidesSaved?: () => void }) {
  const [states, setStates] = useState(() => restoredState(data))
  const statesRef = useRef(states)
  const timers = useRef<Record<string, ReturnType<typeof setTimeout>>>({})
  const [saveStatus, setSaveStatus] = useState('Saved on this computer')
  const [chapter, setChapter] = useState<Chapter | null>(null)
  const [chapterError, setChapterError] = useState('')
  const [query, setQuery] = useState('')
  const [hits, setHits] = useState<SearchHit[]>([])
  const [searching, setSearching] = useState(false)
  const [searchError, setSearchError] = useState('')
  const [section, setSection] = useState<'contents' | 'study' | 'saved'>('contents')
  const [zoom, setZoom] = useState(1)
  const [figure, setFigure] = useState<{ src: string; alt: string } | null>(null)
  const [pageInput, setPageInput] = useState('1')
  const [unreadable, setUnreadable] = useState(data.unreadable || [])
  const reader = useRef<HTMLDivElement>(null)
  const book = data.books.find(item => item.id === selection?.bookId)
  const position = Math.max(1, Math.min(book?.count || 1, selection?.location || 1))
  const saved = book ? states[book.id] || emptyState() : emptyState()
  useEffect(() => { setSection('contents'); setZoom(1); setFigure(null) }, [book?.id])

  // Books whose reviewed guides changed since the last save; finished guides can earn Hero game rewards.
  const guidesChanged = useRef(new Set<string>())
  async function persist(bookId: string, value: ReadingState) {
    try { await api('/library/state', { bookId, ...value }); setSaveStatus('Saved on this computer'); if (guidesChanged.current.delete(bookId)) onGuidesSaved?.() }
    catch { setSaveStatus('Saved in this browser · server not reachable') }
  }
  function update(bookId: string, patch: Partial<ReadingState>) {
    const old = statesRef.current[bookId] || emptyState()
    const value = { ...old, ...patch, updatedAt: Math.max(Date.now(), old.updatedAt + 1) }
    const next = { ...statesRef.current, [bookId]: value }
    statesRef.current = next; setStates(next); onState(bookId, value)
    try { localStorage.setItem(cacheKey, JSON.stringify(next)); setSaveStatus('Saving…') }
    catch { setSaveStatus('Browser storage unavailable · saving to server') }
    clearTimeout(timers.current[bookId])
    timers.current[bookId] = setTimeout(() => { delete timers.current[bookId]; void persist(bookId, value) }, 350)
  }
  useEffect(() => {
    for (const [id, state] of Object.entries(statesRef.current)) {
      if (state.updatedAt > (data.readingState[id]?.updatedAt || 0)) void persist(id, state)
    }
    return () => {
      for (const id of Object.keys(timers.current)) {
        clearTimeout(timers.current[id]); void persist(id, statesRef.current[id])
      }
    }
  }, [])
  useEffect(() => {
    if (!book) return
    let active = true
    setChapter(null); setChapterError(''); setPageInput(String(position)); setQuery('')
    void api<Chapter>(`/library/${book.id}/chapter/${position}`).then(value => {
      if (!active) return
      setChapter(value); update(book.id, { location: position })
      reader.current?.scrollTo(0, 0)
    }).catch(e => { if (active) setChapterError(e.message) })
    return () => { active = false }
  }, [book?.id, position])
  useEffect(() => {
    if (!chapter || !selection?.anchor || book?.format !== 'epub') return
    // The importer prefixes every id from a book with bk-, so book ids never match the app's own.
    const target = Array.from(reader.current?.querySelectorAll('.epub-page [id]') || []).find(element => element.id === 'bk-' + selection.anchor)
    target?.scrollIntoView({ block: 'start' })
  }, [chapter, selection?.anchor])
  useEffect(() => {
    let active = true
    setHits([]); setSearchError('')
    if (query.trim().length < 2) { setSearching(false); return }
    setSearching(true)
    const timer = setTimeout(() => {
      const suffix = book ? `&book=${encodeURIComponent(book.id)}` : ''
      void api<{ results: SearchHit[] }>(`/library/search?q=${encodeURIComponent(query)}${suffix}`)
        .then(value => { if (active) setHits(value.results) })
        .catch(e => { if (active) setSearchError(e.message) })
        .finally(() => { if (active) setSearching(false) })
    }, 200)
    return () => { active = false; clearTimeout(timer) }
  }, [query, book?.id])

  function removed(bookId: string) {
    // The book's folder is gone, so a pending save would fail. Saved notes stay on the server.
    clearTimeout(timers.current[bookId]); delete timers.current[bookId]
    setUnreadable(old => old.filter(id => id !== bookId)); onRemoved(bookId)
  }
  function open(bookId: string, location: number) { setQuery(''); window.location.hash = bookLink(bookId, location).slice(1) }
  function imported(result: BookImportResult) {
    const current = statesRef.current[result.book.id]
    const incoming = result.readingState || emptyState()
    const next = {...statesRef.current, [result.book.id]: current && current.updatedAt >= incoming.updatedAt ? current : incoming}
    statesRef.current = next; setStates(next); setQuery(''); onImported(result)
  }
  function toggleGuide(guide: StudyGuide) {
    const prior = statesRef.current[guide.bookId] || emptyState()
    guidesChanged.current.add(guide.bookId)
    update(guide.bookId, { completed: prior.completed.includes(guide.id) ? prior.completed.filter(id => id !== guide.id) : [...prior.completed, guide.id] })
  }
  const search = <div className="book-search"><Search size={17} /><input aria-label={book ? 'Search this book' : 'Search all books'} value={query} maxLength={160} onChange={e => setQuery(e.target.value)} placeholder={book ? 'Search this book…' : 'Search your books…'} />{query && <button className="icon-button" aria-label="Clear book search" onClick={() => setQuery('')}><X size={16} /></button>}</div>
  const searchResults = query.trim().length >= 2 && <section className="book-results" aria-live="polite"><h3>{searching ? 'Searching…' : `${hits.length}${hits.length === 60 ? '+' : ''} ${hits.length === 1 ? 'result' : 'results'}`}</h3>{searchError && <p role="alert">{searchError}</p>}{hits.map(hit => <button key={`${hit.bookId}-${hit.location}`} onClick={() => open(hit.bookId, hit.location)}><strong>{hit.title}</strong><small>{hit.bookTitle} · {data.books.find(b => b.id === hit.bookId)?.format === 'pdf' ? 'printed page' : 'section'} {hit.label}</small><span>{hit.excerpt}</span></button>)}</section>

  if (!book) return <main className="book-home" onDragOver={event => { if (event.dataTransfer.types.includes('Files')) event.preventDefault() }} onDrop={event => event.preventDefault()}><h1>Books</h1><p className="book-intro">Build your reading library. Add a PDF or EPUB to read offline, explore diagrams, and keep your notes alongside your lessons.</p>{data.books.length > 0 && search}{searchResults}
    {selection && <p role="alert" className="book-error">This book is not imported on this computer.</p>}
    <BookImports books={data.books} states={states} onImported={imported} onOpen={open} onRemoved={removed}>
    {data.books.filter(item => !['gpu-glossary', 'inference-engineering'].includes(item.id)).map(item => { const state = states[item.id] || emptyState(); const guides = data.guides.filter(g => g.bookId === item.id); return <section className="book-shelf-entry" key={item.id}>
      <div className="book-summary"><div className="book-cover">{item.cover ? <img src={`/api/library/${item.id}/asset/${item.cover}`} alt={`${item.title} cover`} /> : <BookOpen size={43} />}</div><div><h2>{item.title}</h2><p>{item.author}</p><small>{item.count} {item.format === 'pdf' ? 'pages · PDF' : `sections · ${item.assets.length} images`}</small><button className="primary-button" onClick={() => open(item.id, state.location)}>{state.updatedAt ? 'Continue reading' : 'Open book'}<ArrowRight size={16} /></button><RemoveBook book={item} onRemoved={removed} /></div></div>
      {guides.length > 0 && <details className="book-study-overview"><summary>Reading guides · {guides.filter(g => state.completed.includes(g.id)).length} of {guides.length} reviewed</summary><p>Each guide links sections of this book to related lessons.</p>{guides.map(guide => <Guide key={guide.id} guide={guide} done={state.completed.includes(guide.id)} onToggle={() => toggleGuide(guide)} onLesson={onLesson} />)}</details>}
    </section>})}
    {unreadable.map(id => <section className="book-shelf-entry" key={id}><div className="book-summary"><div className="book-cover"><BookX size={43} aria-hidden="true" /></div><div><h2>Could not open this book</h2><p>{id}</p><small>The saved copy in data/library/{id} is damaged. Remove it, then add the PDF or EPUB again. Your notes and reading position are kept.</small><RemoveBook book={{ id, title: id }} onRemoved={removed} /></div></div></section>)}
    </BookImports></main>

  const currentTitle = chapter?.title || `Page ${position}`
  return <div className="book-layout">
    <aside className="book-sidebar"><a className="back-link" href="#books"><ArrowLeft size={16} />All books</a><h2>{book.title}</h2><p className="book-author">{book.author}</p>{search}
      {query.trim().length >= 2 ? searchResults : <><div className="tabs book-tabs" role="tablist" aria-label="Book navigation">{(['contents', 'study', 'saved'] as const).map(tab => <button role="tab" aria-selected={section === tab} className={section === tab ? 'active' : ''} key={tab} onClick={() => setSection(tab)}>{tab === 'contents' ? 'Contents' : tab === 'study' ? 'Reading guides' : 'Saved'}</button>)}</div>
        <div className="book-navigation">{section === 'contents' && book.toc.map((entry, i) => <button className={'toc-entry ' + (entry.location === position ? 'selected' : '')} style={{ paddingLeft: `${12 + Math.min(entry.depth, 2) * 12}px` }} key={`${entry.location}-${i}`} onClick={() => open(book.id, entry.location)}><span>{entry.title}</span>{book.format === 'pdf' && <small>{entry.label}</small>}</button>)}
          {section === 'study' && <>{!data.guides.some(g => g.bookId === book.id) && <p className="book-hint">No reading guides match this edition. You can still read every chapter, search, bookmark, and take notes.</p>}{data.guides.filter(g => g.bookId === book.id).map(guide => <Guide key={guide.id} guide={guide} done={saved.completed.includes(guide.id)} onToggle={() => toggleGuide(guide)} onLesson={onLesson} />)}</>}
          {section === 'saved' && <>{!saved.bookmarks.length && <p className="book-hint">Use the bookmark button above a page or section to save it here.</p>}{saved.bookmarks.map(location => <button className="toc-entry" key={location} onClick={() => open(book.id, location)}><Bookmark size={15} /><span>{book.format === 'pdf' ? `PDF page ${location}` : book.toc.find(item => item.location === location)?.title || `Section ${location}`}</span></button>)}</>}
        </div></>}
      <details className="book-notes"><summary>Reading notes</summary><textarea aria-label="Book notes" value={saved.notes} maxLength={30000} placeholder="Explain an idea, capture a question, or plan an experiment…" onChange={e => update(book.id, { notes: e.target.value })} /><small role="status">{saveStatus}</small></details>
    </aside>
    <main className="book-reader" ref={reader}>
      <div className="book-toolbar"><div className="book-page-controls"><button className="icon-button" aria-label="Previous book page" disabled={position <= 1} onClick={() => open(book.id, position - 1)}><ArrowLeft size={18} /></button><form onSubmit={e => { e.preventDefault(); const value = Number(pageInput); if (Number.isInteger(value) && value >= 1 && value <= book.count) open(book.id, value); else setPageInput(String(position)) }}><label>{book.format === 'pdf' ? 'PDF page' : 'Section'} <input aria-label="Book page number" type="number" min={1} max={book.count} value={pageInput} onChange={e => setPageInput(e.target.value)} onBlur={() => { if (!pageInput) setPageInput(String(position)) }} /></label><span> / {book.count}</span><button className="small-button" type="submit">Go</button></form><button className="icon-button" aria-label="Next book page" disabled={position >= book.count} onClick={() => open(book.id, position + 1)}><ArrowRight size={18} /></button></div>
        <div className="book-view-controls">{book.format === 'pdf' && <label className="pdf-zoom"><ZoomIn size={16} /><select aria-label="PDF zoom" value={zoom} onChange={e => setZoom(Number(e.target.value))}><option value={1}>Fit width</option><option value={1.5}>150%</option><option value={2}>200%</option><option value={3}>300%</option></select></label>}
          <button className={'icon-button ' + (saved.bookmarks.includes(position) ? 'bookmarked' : '')} aria-label={saved.bookmarks.includes(position) ? 'Remove bookmark' : 'Bookmark this page'} aria-pressed={saved.bookmarks.includes(position)} onClick={() => update(book.id, { bookmarks: saved.bookmarks.includes(position) ? saved.bookmarks.filter(n => n !== position) : [...saved.bookmarks, position] })}><Bookmark size={18} /></button>
          <a href={`/api/library/${book.id}/asset/source.${book.format}`} download={`${book.id}.${book.format}`}>Download {book.format.toUpperCase()}<ExternalLink size={14} /></a></div></div>
      {chapterError && <p className="book-error" role="alert">{chapterError}</p>}
      {!chapter && !chapterError && <p className="book-hint" role="status">Loading…</p>}
      {chapter && <>{book.format === 'pdf' ? <><div className="book-quality-note">Printed page {chapter.label}</div><Suspense fallback={<p className="book-hint">Opening PDF reader…</p>}><PdfPage bookId={book.id} page={position} zoom={zoom} /></Suspense><details className="pdf-text"><summary>Selectable page text</summary><p>{chapter.text || 'This page contains artwork without extractable text.'}</p></details></> : <><p className="book-quality-note">Click a figure to enlarge it.</p><article className="epub-page" aria-label={currentTitle} onClick={e => { const image = (e.target as HTMLElement).closest('img'); if (image) setFigure({ src: image.src, alt: image.alt }) }} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { const image = (e.target as HTMLElement).closest('img'); if (image) { e.preventDefault(); setFigure({ src: image.src, alt: image.alt }) } } }} dangerouslySetInnerHTML={{ __html: chapter.html || '' }} /></>}
        <footer className="book-attribution"><p>{book.attribution}</p><small>{book.rights}</small><div className="book-bottom-nav"><button className="secondary-button" disabled={position <= 1} onClick={() => open(book.id, position - 1)}><ArrowLeft size={16} />Previous</button><button className="primary-button" disabled={position >= book.count} onClick={() => open(book.id, position + 1)}>Next<ArrowRight size={16} /></button></div></footer></>}
    </main>{figure && <FigureViewer {...figure} onClose={() => setFigure(null)} />}
  </div>
}
