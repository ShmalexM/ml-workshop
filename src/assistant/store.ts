import {useEffect,useSyncExternalStore} from 'react'
import {api} from '../api'
import {streamChat,type ChatRequest} from './stream'

// The assistant's state lives outside React, so an answer keeps streaming when the drawer closes or the page changes.
// Conversations are kept in memory for this session only. They are never saved to disk, backups or logs.

export type Provider='ollama'|'lmstudio'|'openrouter'|'openai'|'custom'
export type AssistantConfig={enabled:boolean;provider:Provider;baseUrl:string;model:string;allowSolutions:boolean;hasKey:boolean;keyLast4:string;local:boolean;host:string;ready:boolean;busy:boolean;keyRemoved?:boolean}
export type ChatMode='chat'|'explain'
export type Message={id:number;role:'user'|'assistant';text:string;mode?:ChatMode;sent?:string[];error?:string;stopped?:boolean;truncated?:boolean;streaming?:boolean;thinking?:boolean}
export type Conversation={messages:Message[];draft:string;mode:ChatMode;chips:Record<string,boolean>}
type State={config:AssistantConfig|null;open:boolean;battle:boolean;streaming:string|null;conversations:Record<string,Conversation>;hints:Record<string,number>;focus:number}

const empty:Conversation={messages:[],draft:'',mode:'chat',chips:{}}
let state:State={config:null,open:false,battle:false,streaming:null,conversations:{},hints:{},focus:0}
const listeners=new Set<()=>void>()
function set(next:Partial<State>){state={...state,...next};listeners.forEach(listener=>listener())}
function subscribe(listener:()=>void){listeners.add(listener);return()=>{listeners.delete(listener)}}
export function useAssistant(){return useSyncExternalStore(subscribe,()=>state)}
export function conversation(scope:string){return state.conversations[scope]||empty}
function update(scope:string,change:(c:Conversation)=>Conversation){set({conversations:{...state.conversations,[scope]:change(conversation(scope))}})}
let nextId=1

export async function loadConfig(){try{set({config:await api<AssistantConfig>('/assistant/config')})}catch{/* the assistant stays hidden */}}
export function setConfig(config:AssistantConfig){if(!config.enabled)stopAnswer();set({config,open:config.enabled&&state.open})}
const usable=()=>!!state.config?.enabled&&!state.battle

let opener:HTMLElement|null=null
export function openAssistant(){
 if(!usable())return
 if(!state.open){const active=document.activeElement;opener=active instanceof HTMLElement&&active!==document.body?active:null}
 set({open:true,focus:state.focus+1})
}
export function closeAssistant(){
 if(!state.open)return
 set({open:false})
 const target=opener?.isConnected?opener:document.getElementById('assistant-toggle');opener=null
 requestAnimationFrame(()=>target?.focus())
}
/** Ctrl/Cmd+J: open, move focus into the open drawer, or close it when focus is already there. */
export function toggleAssistant(inside:boolean){if(!state.open)openAssistant();else if(inside)closeAssistant();else set({focus:state.focus+1})}

/** BattleScreen and PracticeScreen call this while mounted: the drawer and its shortcut are off during a fight or practice. */
export function useBattleGuard(){useEffect(()=>{stopAnswer();set({battle:true,open:false});return()=>set({battle:false})},[])}
/** LessonReader reports how many hints are open, for the hints chip. */
export function reportHints(lessonId:string,count:number){if(state.hints[lessonId]!==count)set({hints:{...state.hints,[lessonId]:count}})}

export function setDraft(scope:string,draft:string){update(scope,c=>({...c,draft,mode:draft?c.mode:'chat'}))}
export function setChip(scope:string,id:string,on:boolean){update(scope,c=>({...c,chips:{...c.chips,[id]:on}}))}
export function clearConversation(scope:string){if(state.streaming===scope)stopAnswer();update(scope,c=>({...c,messages:[],mode:'chat'}))}
const explainText={error:'Explain this error. What does it mean, and which line causes it?',checks:'Why does this check fail? Point me to the problem without giving the solution.'}
/** "Explain this error": open the drawer with the code and the run turned on and a question ready to send.
 * For the worked example that is the example's code, not the learner's. */
export function requestExplain(scope:string,kind:'error'|'checks',source:'practice'|'example'='practice'){
 if(!usable())return
 const chips:Record<string,boolean>=source==='example'?{example:true,run:true}:{code:true,run:true}
 update(scope,c=>({...c,draft:explainText[kind],mode:'explain',chips:{...c.chips,...chips}}))
 openAssistant()
}

// History sent with each question, newest first until this many characters.
const historyBudget=24000
let controller:AbortController|null=null;let streamId=''
export async function sendMessage(scope:string,request:Omit<ChatRequest,'messages'|'mode'>,text:string,sent:string[]){
 const question=text.trim()
 if(!question||state.streaming||!usable())return
 const mode=conversation(scope).mode
 const previous=conversation(scope).messages.filter(m=>m.text.trim())
 const user:Message={id:nextId++,role:'user',text:question,mode,sent};const replyId=nextId++
 update(scope,c=>({...c,draft:'',mode:'chat',messages:[...c.messages,user,{id:replyId,role:'assistant',text:'',streaming:true}]}))
 set({streaming:scope})
 const history:{role:'user'|'assistant';content:string}[]=[];let used=question.length
 for(const m of [...previous].reverse()){if(used+m.text.length>historyBudget)break;history.unshift({role:m.role,content:m.text});used+=m.text.length}
 while(history.length&&history[0].role!=='user')history.shift()
 let buffer='';let timer:ReturnType<typeof setTimeout>|undefined
 const patch=(change:Partial<Message>)=>update(scope,c=>({...c,messages:c.messages.map(m=>m.id===replyId?{...m,...change}:m)}))
 // Re-render at most every 50 ms while text streams in.
 const flush=()=>{timer=undefined;if(!buffer)return;const add=buffer;buffer='';update(scope,c=>({...c,messages:c.messages.map(m=>m.id===replyId?{...m,text:m.text+add}:m)}))}
 const abort=new AbortController();controller=abort;streamId=''
 const body:ChatRequest={...request,mode,messages:[...history,{role:'user',content:question}]}
 try{
  for(let attempt=0;;attempt++){
   try{
    await streamChat(body,abort.signal,event=>{
     if(event.type==='meta')streamId=event.id
     else if(event.type==='delta'){buffer+=event.text;timer??=setTimeout(flush,50)}
     else if(event.type==='thinking')patch({thinking:true})
     else if(event.type==='error'){flush();patch({error:event.message})}
     else if(event.type==='done'){
      flush();patch({stopped:!!event.stopped,truncated:!!event.truncated})
      if(!event.stopped&&!conversation(scope).messages.find(m=>m.id===replyId)?.text)patch({error:'The model sent an empty answer. Ask again, or choose another model.'})
     }
    })
    break
   }catch(e){
    // Stop on the previous answer can leave the server busy for a moment.
    if(attempt===0&&(e as {status?:number}).status===409&&!abort.signal.aborted){await new Promise(r=>setTimeout(r,500));continue}
    throw e
   }
  }
 }catch(e){
  if(abort.signal.aborted)patch({stopped:true})
  else patch({error:(e as Error).message})
 }finally{
  clearTimeout(timer);flush();patch({streaming:false})
  if(controller===abort)controller=null
  set({streaming:null})
 }
}
/** Stop: abort the request, which closes the connection, and tell the server in case the close is not seen. */
export function stopAnswer(){
 if(!controller)return
 controller.abort();controller=null
 // The id makes sure a late Stop never ends a newer answer.
 if(streamId)void api('/assistant/stop',{id:streamId}).catch(()=>{})
 streamId=''
}
