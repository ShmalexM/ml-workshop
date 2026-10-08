import {useEffect,useState} from 'react'
import {api} from '../api'
import {loadConfig,setConfig,useAssistant,type AssistantConfig,type Provider} from './store'

const providers:{id:Provider;label:string;url:string;key:boolean}[]=[
 {id:'ollama',label:'Ollama (on this computer)',url:'http://127.0.0.1:11434',key:false},
 {id:'lmstudio',label:'LM Studio (on this computer)',url:'http://127.0.0.1:1234/v1',key:false},
 {id:'openrouter',label:'OpenRouter',url:'https://openrouter.ai/api/v1',key:true},
 {id:'openai',label:'OpenAI',url:'https://api.openai.com/v1',key:true},
 {id:'custom',label:'Custom (OpenAI-compatible)',url:'',key:true},
]
type Form={provider:Provider;baseUrl:string;model:string;allowSolutions:boolean}
type Status={text:string;error?:boolean}
const formOf=(c:AssistantConfig):Form=>({provider:c.provider,baseUrl:c.baseUrl,model:c.model,allowSolutions:c.allowSolutions})

/** Settings → AI assistant. Nothing is sent to a provider until the assistant is on and a provider is saved. */
export default function AssistantSettings(){
 const {config}=useAssistant()
 const [enabled,setEnabled]=useState(false);const [form,setForm]=useState<Form|null>(null);const [key,setKey]=useState('')
 const [models,setModels]=useState<string[]>([]);const [status,setStatus]=useState<Status|null>(null);const [busy,setBusy]=useState(false)
 useEffect(()=>{void loadConfig()},[])
 useEffect(()=>{if(config&&!form){setForm(formOf(config));setEnabled(config.enabled)}},[config,form])
 if(!config||!form)return <><h3>AI assistant</h3><p className="setting-note">Loading…</p></>
 const preset=providers.find(p=>p.id===form.provider)!
 const dirty=!config.enabled||key!==''||JSON.stringify(form)!==JSON.stringify(formOf(config))
 const change=(next:Partial<Form>)=>{setForm({...form,...next});setStatus(null)}
 async function run(task:()=>Promise<void>){setBusy(true);setStatus(null);try{await task()}catch(e){setStatus({text:(e as Error).message,error:true})}finally{setBusy(false)}}
 async function save(extra:Record<string,unknown>={}){
  const next=await api<AssistantConfig>('/assistant/config',{enabled:true,...form,...(key?{key}:{}),...extra})
  setConfig(next);setForm(formOf(next));setKey('')
  return next
 }
 async function toggle(on:boolean){
  setEnabled(on);setStatus(null)
  // Turning it on only shows the form. Turning it off saves at once.
  if(!on&&config!.enabled)await run(async()=>{setConfig(await api<AssistantConfig>('/assistant/config',{enabled:false}));setStatus({text:'The assistant is off.'})})
 }
 const saveNow=()=>run(async()=>{const next=await save();setStatus({text:next.keyRemoved?'Saved. The saved key was removed because the address changed.':'Saved.'})})
 const listModels=()=>run(async()=>{if(dirty)await save();const r=await api<{models:string[]}>('/assistant/models',{});setModels(r.models);setStatus({text:r.models.length?`Found ${r.models.length} models. Pick one in the Model field.`:'The provider listed no models.'})})
 const test=()=>run(async()=>{if(dirty)await save();const r=await api<{model:string;seconds:number;reply:string}>('/assistant/test',{});setStatus({text:`Connected. ${r.model} answered in ${r.seconds} s${r.reply?`: “${r.reply.slice(0,60)}”`:'.'}`})})
 const removeKey=()=>run(async()=>{const next=await api<AssistantConfig>('/assistant/config',{enabled:config!.enabled,...formOf(config!),removeKey:true});setConfig(next);setStatus({text:'Key removed.'})})
 return <section className="assistant-settings" aria-labelledby="assistant-settings-title">
  <h3 id="assistant-settings-title">AI assistant</h3>
  <label className="setting-toggle"><input type="checkbox" checked={enabled} disabled={busy} onChange={e=>void toggle(e.target.checked)}/><span>Use an AI assistant in lessons</span></label>
  <p className="setting-note">Off by default. Bring your own: a model on this computer (Ollama, LM Studio) or an API key for a hosted provider.</p>
  {enabled&&<div className="assistant-settings-form">
   <label>Provider<select value={form.provider} disabled={busy} onChange={e=>{const p=providers.find(x=>x.id===e.target.value)!;change({provider:p.id,baseUrl:p.url||form.baseUrl});setModels([])}}>{providers.map(p=><option key={p.id} value={p.id}>{p.label}</option>)}</select></label>
   <label>Base URL<input type="text" inputMode="url" spellCheck={false} autoComplete="off" value={form.baseUrl} disabled={busy} placeholder="https://example.com/v1" onChange={e=>change({baseUrl:e.target.value})}/></label>
   {(preset.key||config.hasKey)&&<label>API key<input type="password" autoComplete="off" spellCheck={false} value={key} disabled={busy} placeholder={config.hasKey?`Saved key ending ${config.keyLast4||'…'}. Paste a new key to replace it.`:'Paste your key'} onChange={e=>{setKey(e.target.value);setStatus(null)}}/></label>}
   {config.hasKey&&<p className="setting-note">Key ending {config.keyLast4||'…'} is saved on this computer. <button type="button" className="text-button" disabled={busy} onClick={()=>void removeKey()}>Remove key</button></p>}
   <label>Model<span className="assistant-model-row"><input type="text" list="assistant-models" spellCheck={false} autoComplete="off" value={form.model} disabled={busy} placeholder={form.provider==='ollama'?'llama3.2':'Model name'} onChange={e=>change({model:e.target.value})}/><button type="button" className="secondary-button" disabled={busy||!form.baseUrl} onClick={()=>void listModels()}>List models</button></span></label>
   <datalist id="assistant-models">{models.map(m=><option key={m} value={m}/>)}</datalist>
   <label className="setting-toggle"><input type="checkbox" checked={form.allowSolutions} disabled={busy} onChange={e=>change({allowSolutions:e.target.checked})}/><span>Allow full solutions</span></label>
   <p className="setting-note">{form.allowSolutions?'The assistant may write the full solution when you ask.':'Off: the assistant gives one hint at a time and points to Show solution.'}</p>
   <p className="assistant-privacy">Your messages and the page context you allow are sent to the provider you choose.{config.local&&!dirty?' This provider runs on this computer.':''}</p>
   <div className="button-row"><button type="button" className="primary-button" disabled={busy||!dirty} onClick={()=>void saveNow()}>Save</button><button type="button" className="secondary-button" disabled={busy||!form.baseUrl||!form.model} onClick={()=>void test()}>Test connection</button></div>
  </div>}
  {status&&<p className={'assistant-settings-status'+(status.error?' error':'')} role={status.error?'alert':'status'}>{status.text}</p>}
 </section>
}
