import {authorized} from '../api'

export type ChatRequest={pageKind:'lesson'|'page';page:string;mode:'chat'|'explain';messages:{role:'user'|'assistant';content:string}[];context:{id:string;label:string;text:string}[]}
export type StreamEvent={type:'meta';id:string;model:string;host:string;local:boolean}|{type:'delta';text:string}|{type:'done';stopped?:boolean;truncated?:boolean}|{type:'error';message:string}|{type:'thinking'}|{type:'ping'}

/** Split streamed bytes into JSON lines. Returns the events and the unfinished rest of the text. */
export function readLines(buffer:string):[StreamEvent[],string]{
 const events:StreamEvent[]=[];let index:number
 while((index=buffer.indexOf('\n'))>=0){
  const line=buffer.slice(0,index).trim();buffer=buffer.slice(index+1)
  if(line){try{events.push(JSON.parse(line))}catch{/* a damaged line is skipped */}}
 }
 return [events,buffer]
}

/**
 * POST the question and call onEvent for each line of the streamed answer.
 * fetch is used instead of EventSource, which cannot POST or send the session token.
 */
export async function streamChat(body:ChatRequest,signal:AbortSignal,onEvent:(event:StreamEvent)=>void){
 const response=await authorized('/api/assistant/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal})
 if(!response.ok){
  const data=await response.json().catch(()=>null)
  throw Object.assign(new Error(data?.error||`The local server answered HTTP ${response.status}.`),{status:response.status})
 }
 if(!response.body)throw new Error('This browser cannot read a streamed answer.')
 const reader=response.body.getReader();const decoder=new TextDecoder();let rest=''
 for(;;){
  const {done,value}=await reader.read()
  if(done)break
  const [events,left]=readLines(rest+decoder.decode(value,{stream:true}));rest=left
  events.forEach(onEvent)
 }
 readLines(rest+decoder.decode()+'\n')[0].forEach(onEvent)
}
