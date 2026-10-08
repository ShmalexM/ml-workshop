import type {Course,GlossaryEntry,Lesson} from './types'

/** A piece of lesson text: plain text, or a glossary term to link. */
export type TextPiece = string | {text:string;entry:GlossaryEntry}

const escape=(text:string)=>text.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')

// The same expression as backend/glossary.py: text in double quotes is skipped, and forms
// match whole words, longest first, so that the browser links the terms the server listed.
function pattern(entries:GlossaryEntry[]){
 const owner=new Map<string,GlossaryEntry>()
 for(const entry of entries)for(const form of entry.match)owner.set(form,entry)
 const forms=[...owner.keys()].sort((a,b)=>b.length-a.length).map(escape)
 return {owner,regex:new RegExp('"[^"\\n]*"|(?<![A-Za-z0-9_-])(?:'+forms.join('|')+')(?![A-Za-z0-9_-])','g')}
}

/** Split each text into pieces, linking the first appearance of each entry across all the texts. */
export function linkTerms(texts:string[],entries:GlossaryEntry[]):TextPiece[][]{
 if(!entries.length)return texts.map(text=>[text])
 const {owner,regex}=pattern(entries);const seen=new Set<string>()
 return texts.map(text=>{
  const pieces:TextPiece[]=[];let last=0
  for(const match of text.matchAll(regex)){
   const entry=owner.get(match[0])
   if(!entry||seen.has(entry.id))continue
   seen.add(entry.id);pieces.push(text.slice(last,match.index),{text:match[0],entry});last=match.index+match[0].length
  }
  pieces.push(text.slice(last))
  return pieces
 })
}

/** "Python from zero 3: Functions: def and return" for a lesson id. */
export function lessonLabel(id:string,lessons:Lesson[],courses:Course[]){
 const lesson=lessons.find(l=>l.id===id);if(!lesson)return id
 const number=lessons.filter(l=>l.course===lesson.course).indexOf(lesson)+1
 return `${courses.find(c=>c.id===lesson.course)?.title??lesson.course} ${number}: ${lesson.title}`
}
