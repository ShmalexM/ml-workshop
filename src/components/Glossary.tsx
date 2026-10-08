import {useEffect,useId,useLayoutEffect,useMemo,useRef,useState,type Ref} from 'react'
import {Search} from 'lucide-react'
import type {GlossaryEntry} from '../types'
import type {TextPiece} from '../glossary'
import './glossary.css'

type TermLinks={onGlossary:(term:string)=>void;onLesson:(id:string)=>void;label:(id:string)=>string;current:string}

/** A linked term: a dotted-underline button that opens its definition. One definition is open at a time. */
function Term({text,entry,links}:{text:string;entry:GlossaryEntry;links:TermLinks}){
 const [open,setOpen]=useState(false);const id=useId()
 const wrap=useRef<HTMLSpanElement>(null);const button=useRef<HTMLButtonElement>(null);const pop=useRef<HTMLSpanElement>(null)
 useEffect(()=>{if(!open)return
  const onOther=(e:Event)=>{if((e as CustomEvent<string>).detail!==id)setOpen(false)}
  const onPointer=(e:PointerEvent)=>{if(!wrap.current?.contains(e.target as Node))setOpen(false)}
  const onKey=(e:KeyboardEvent)=>{if(e.key!=='Escape')return;e.stopPropagation();setOpen(false);if(!document.activeElement||document.activeElement===document.body||wrap.current?.contains(document.activeElement))button.current?.focus()}
  document.addEventListener('glossary-open',onOther);document.addEventListener('pointerdown',onPointer);document.addEventListener('keydown',onKey,true)
  return()=>{document.removeEventListener('glossary-open',onOther);document.removeEventListener('pointerdown',onPointer);document.removeEventListener('keydown',onKey,true)}},[open,id])
 // Keep the definition inside the lesson text, shifting it left near the right edge.
 useLayoutEffect(()=>{const box=pop.current;if(!open||!box)return;box.style.left='0px'
  const rect=box.getBoundingClientRect(),bound=(wrap.current?.closest('.lesson-content')||document.body).getBoundingClientRect()
  const right=Math.min(bound.right,innerWidth-8),left=Math.max(bound.left,8)
  let shift=rect.right>right?right-rect.right:0;if(rect.left+shift<left)shift=left-rect.left
  box.style.left=shift+'px'},[open])
 function toggle(){if(!open)document.dispatchEvent(new CustomEvent('glossary-open',{detail:id}));setOpen(!open)}
 const teaches=entry.lesson&&entry.lesson!==links.current?entry.lesson:null
 return <span className="term-wrap" ref={wrap}><button type="button" ref={button} className="term" aria-expanded={open} aria-controls={open?id:undefined} onClick={toggle}>{text}</button>{open&&<span className="term-pop" id={id} ref={pop} role="dialog" aria-label={entry.term}><strong>{entry.term}{entry.sense&&<small> · {entry.sense}</small>}</strong><span>{entry.definition}</span><span className="term-pop-links">{teaches&&<button type="button" onClick={()=>links.onLesson(teaches)}>{links.label(teaches)}</button>}<button type="button" onClick={()=>{setOpen(false);links.onGlossary(entry.term)}}>All terms</button></span></span>}</span>
}

/** Lesson text with its glossary terms linked. */
export function LinkedText({pieces,links}:{pieces:TextPiece[];links:TermLinks}){
 return <>{pieces.map((piece,i)=>typeof piece==='string'?piece:<Term key={i} text={piece.text} entry={piece.entry} links={links}/>)}</>
}

const compare=(a:GlossaryEntry,b:GlossaryEntry)=>a.term.localeCompare(b.term,undefined,{sensitivity:'base'})||(a.sense??'').localeCompare(b.sense??'')

/** The searchable list of every term, shown in the lesson drawer. */
export function GlossaryList({entries,query,onQuery,onLesson,label,search}:{entries:GlossaryEntry[];query:string;onQuery:(query:string)=>void;onLesson:(id:string)=>void;label:(id:string)=>string;search:Ref<HTMLInputElement>}){
 const sorted=useMemo(()=>[...entries].sort(compare),[entries])
 const words=query.trim().toLowerCase()
 // A term whose name matches comes before one that only mentions the words in its definition.
 const shown=words?[...sorted.filter(e=>e.term.toLowerCase().includes(words)),...sorted.filter(e=>!e.term.toLowerCase().includes(words)&&((e.sense??'')+' '+e.definition).toLowerCase().includes(words))]:sorted
 return <div className="glossary-panel"><label className="glossary-search"><Search size={15} aria-hidden="true"/><input ref={search} type="search" value={query} onChange={e=>onQuery(e.target.value)} placeholder="Search terms" aria-label="Search the glossary"/></label><p className="glossary-count" role="status">{shown.length===sorted.length?`${sorted.length} terms`:`${shown.length} of ${sorted.length} terms`}</p>{shown.length?<dl className="glossary-list">{shown.map(entry=><div key={entry.id}><dt>{entry.term}{entry.sense&&<small>{entry.sense}</small>}</dt><dd>{entry.definition}</dd>{entry.lesson&&<dd className="glossary-lesson"><button type="button" onClick={()=>onLesson(entry.lesson!)}>{label(entry.lesson)}</button></dd>}</div>)}</dl>:<p className="glossary-empty">No term matches “{query.trim()}”.</p>}</div>
}
