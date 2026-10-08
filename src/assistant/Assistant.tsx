import {lazy,Suspense,useEffect} from 'react'
import {MessageCircle,Sparkles} from 'lucide-react'
import {closeAssistant,loadConfig,openAssistant,requestExplain,toggleAssistant,useAssistant} from './store'
import type {AssistantContext} from './context'
import './assistant.css'

// The parts of the optional assistant that every page loads. The drawer itself loads on first open.
const AssistantDrawer=lazy(()=>import('./AssistantDrawer'))
const shortcut=/Mac|iPhone|iPad/.test(navigator.platform)?'⌘J':'Ctrl+J'

/** The header button. Hidden while the assistant is off and during a battle. */
export function AssistantButton(){
 const s=useAssistant()
 if(!s.config?.enabled||s.battle)return null
 return <button id="assistant-toggle" type="button" className={'assistant-toggle'+(s.open?' active':'')} aria-expanded={s.open} aria-controls="assistant-drawer" aria-keyshortcuts="Control+J Meta+J" title={`Assistant (${shortcut})`} onClick={()=>s.open?closeAssistant():openAssistant()}><MessageCircle size={17}/><span>Ask</span></button>
}

/** The docked drawer on the right of the page, and its Ctrl/Cmd+J shortcut. */
export function AssistantDock({context}:{context:AssistantContext}){
 const s=useAssistant();const on=!!s.config?.enabled&&!s.battle
 useEffect(()=>{void loadConfig()},[])
 useEffect(()=>{
  if(!on)return
  const handler=(e:KeyboardEvent)=>{if((e.metaKey||e.ctrlKey)&&!e.altKey&&!e.shiftKey&&e.key.toLowerCase()==='j'){e.preventDefault();toggleAssistant(!!document.getElementById('assistant-drawer')?.contains(document.activeElement))}}
  window.addEventListener('keydown',handler);return()=>window.removeEventListener('keydown',handler)
 },[on])
 if(!on||!s.open)return null
 return <><div className="assistant-scrim" onClick={closeAssistant}/><Suspense fallback={<aside className="assistant-drawer" id="assistant-drawer" aria-label="Assistant"><p className="assistant-setup">Loading the assistant…</p></aside>}><AssistantDrawer context={context}/></Suspense></>
}

/** Shown next to an error or a failed check once a model is set up. Opens the drawer with a question ready to send. */
export function ExplainButton({lessonId,kind}:{lessonId:string;kind:'error'|'checks'}){
 const s=useAssistant()
 if(!s.config?.ready||s.battle)return null
 return <button type="button" className="explain-button" onClick={()=>requestExplain('lesson:'+lessonId,kind)}><Sparkles size={14}/>{kind==='error'?'Explain this error':'Explain the failed check'}</button>
}
