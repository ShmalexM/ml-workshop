import {memo,useEffect,useMemo,useRef,useSyncExternalStore,type KeyboardEvent,type RefObject} from 'react'
import {Check,Eraser,SendHorizontal,Square,X} from 'lucide-react'
import Markdown from './Markdown'
import {buildChips,type AssistantContext} from './context'
import {clearConversation,closeAssistant,conversation,sendMessage,setChip,setDraft,stopAnswer,useAssistant,type Message} from './store'

// Below 1280px the drawer opens over the page (assistant.css), so it acts as a modal dialog there.
const overlayQuery='(max-width:1279px)'
function useOverlay(){
 return useSyncExternalStore(change=>{const query=matchMedia(overlayQuery);query.addEventListener('change',change);return()=>query.removeEventListener('change',change)},()=>matchMedia(overlayQuery).matches)
}
const focusable=(root:HTMLElement)=>Array.from(root.querySelectorAll<HTMLElement>('a[href],button:not([disabled]),textarea:not([disabled]),input:not([disabled]),select:not([disabled]),summary,[tabindex]:not([tabindex="-1"])')).filter(el=>el.getClientRects().length>0)

/** While the drawer covers the page, Tab and Shift+Tab stay in it and Escape closes it from anywhere.
 * closeAssistant() returns focus to the control that opened the drawer. */
function useFocusTrap(drawer:RefObject<HTMLElement|null>,on:boolean){
 useEffect(()=>{
  const root=drawer.current
  if(!on||!root)return
  if(!root.contains(document.activeElement))focusable(root)[0]?.focus()
  const onKey=(e:globalThis.KeyboardEvent)=>{
   // A modal dialog on top, such as Settings, handles its own keys.
   if(document.querySelector('dialog[open]'))return
   const inside=root.contains(document.activeElement)
   if(e.key==='Escape'&&!inside){closeAssistant();return}
   if(e.key!=='Tab')return
   const items=focusable(root);if(!items.length)return
   const first=items[0],last=items[items.length-1]
   if(!inside||(e.shiftKey&&document.activeElement===first)||(!e.shiftKey&&document.activeElement===last)){e.preventDefault();(e.shiftKey?last:first).focus()}
  }
  document.addEventListener('keydown',onKey)
  return()=>document.removeEventListener('keydown',onKey)
 },[drawer,on])
}

const size=(text:string)=>{const bytes=new TextEncoder().encode(text).length;return bytes<1024?`${bytes} B`:`${(bytes/1024).toFixed(1)} KB`}

// The store keeps a message object until that message changes, so only the streaming reply renders again.
const Reply=memo(function Reply({message}:{message:Message}){
 return <>{message.text?<Markdown text={message.text}/>:message.streaming?<p className="assistant-waiting">{message.thinking?'The model is thinking…':'Waiting for the model…'}</p>:null}
  {message.error&&<p className="assistant-error" role="alert">{message.error}</p>}
  {message.stopped&&<p className="assistant-note">Stopped.</p>}
  {message.truncated&&<p className="assistant-note">The answer reached the 64 KB limit and was cut.</p>}</>
})

export default function AssistantDrawer({context}:{context:AssistantContext}){
 const s=useAssistant();const config=s.config!
 const scope=context.kind==='lesson'?'lesson:'+context.lesson.id:'page:'+context.name
 const chat=s.conversations[scope]||conversation(scope)
 const hints=context.kind==='lesson'?s.hints[context.lesson.id]||0:0
 const chips=useMemo(()=>buildChips(context,hints,chat.chips),[context,hints,chat.chips])
 const input=useRef<HTMLTextAreaElement>(null);const log=useRef<HTMLDivElement>(null);const drawer=useRef<HTMLElement>(null)
 const streaming=s.streaming!==null
 const overlay=useOverlay()
 useEffect(()=>{input.current?.focus()},[s.focus])
 useFocusTrap(drawer,overlay)
 // Follow a streaming answer unless the learner has scrolled up to read.
 const last=chat.messages[chat.messages.length-1]
 useEffect(()=>{const el=log.current;if(el&&el.scrollHeight-el.scrollTop-el.clientHeight<160)el.scrollTop=el.scrollHeight},[last?.text,chat.messages.length])
 const sent=chips.filter(c=>c.on)
 function send(){
  if(!chat.draft.trim()||streaming)return
  void sendMessage(scope,{pageKind:context.kind==='lesson'?'lesson':'page',page:context.kind==='lesson'?'Learn':context.name,context:sent.map(({id,label,text})=>({id,label,text}))},chat.draft,sent.map(c=>c.label))
 }
 function onKey(e:KeyboardEvent<HTMLTextAreaElement>){if(e.key==='Enter'&&!e.shiftKey&&!e.nativeEvent.isComposing){e.preventDefault();send()}}
 const tutor=context.kind==='lesson'&&!config.allowSolutions
 const destination=config.local?`On this computer · ${config.model||'no model'}`:`Sending to ${config.host} · ${config.model||'no model'}`
 return <aside ref={drawer} className="assistant-drawer" id="assistant-drawer" aria-labelledby="assistant-title" role={overlay?'dialog':undefined} aria-modal={overlay||undefined} onKeyDown={e=>{if(e.key==='Escape'){e.stopPropagation();closeAssistant()}}}>
  <div className="assistant-header"><div><h2 id="assistant-title">Assistant</h2><p>{destination}</p></div><div className="assistant-header-actions"><button type="button" className="assistant-text-button" onClick={()=>clearConversation(scope)} disabled={!chat.messages.length}><Eraser size={15}/>Clear</button><button type="button" className="icon-button" onClick={closeAssistant} aria-label="Close assistant"><X size={18}/></button></div></div>
  <div className="assistant-log" ref={log} role="log" aria-live="polite" aria-relevant="additions text">
   {chat.messages.length===0&&<div className="assistant-empty"><p>{context.kind==='lesson'?'Ask about this lesson, your code or an error.':'Ask a question. Only the name of this page is sent with it.'}</p>{tutor&&<p>Tutor mode: one hint at a time, without the full solution. The solution is behind Show solution in the lesson.</p>}</div>}
   {chat.messages.map(m=><div key={m.id} className={'assistant-message '+m.role}>{m.role==='user'?<><p className="assistant-question">{m.text}</p>{m.sent&&m.sent.length>0&&<p className="assistant-sent">Sent with: {m.sent.join(', ')}</p>}</>:<Reply message={m}/>}</div>)}
  </div>
  <div className="assistant-compose">
   <div className="assistant-chips" role="group" aria-label="Context sent with your next message">
    {chips.map(c=><button key={c.id} type="button" className={'assistant-chip'+(c.on?' on':'')} aria-pressed={c.on} onClick={()=>setChip(scope,c.id,!c.on)}>{c.on&&<Check size={12} aria-hidden="true"/>}<span>{c.label}</span><small>{size(c.text)}{c.truncated?' · cut':''}</small></button>)}
   </div>
   <details className="assistant-preview"><summary>{sent.length?`What is sent with your question (${size(sent.map(c=>c.text).join(''))})`:'No page context is sent'}</summary>{sent.map(c=><div key={c.id}><strong>{c.label}{c.truncated?' (cut)':''}</strong><pre>{c.text}</pre></div>)}</details>
   {config.ready?<form className="assistant-form" onSubmit={e=>{e.preventDefault();send()}}>
    <textarea ref={input} rows={3} value={chat.draft} maxLength={4000} onChange={e=>setDraft(scope,e.target.value)} onKeyDown={onKey} aria-label="Question for the assistant" placeholder={context.kind==='lesson'?'Ask about this lesson':'Ask a question'}/>
    <div className="assistant-form-row"><small>Enter sends · Shift+Enter adds a line</small>{streaming?<button type="button" className="secondary-button" onClick={stopAnswer}><Square size={13}/>Stop</button>:<button type="submit" className="primary-button" disabled={!chat.draft.trim()}><SendHorizontal size={14}/>Send</button>}</div>
   </form>:<p className="assistant-setup">Choose a model in Settings → AI assistant.</p>}
  </div>
 </aside>
}
