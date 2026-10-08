// Just enough DOM for the battle engine to run in Node: no drawing, and timers on a simulated clock.
const ctx:any=new Proxy({},{get:(t:any,k)=>k in t?t[k]:k==='createRadialGradient'||k==='createLinearGradient'?()=>({addColorStop(){}}):k==='measureText'?()=>({width:0}):()=>{},set:(t:any,k,v)=>{t[k]=v;return true}})
const element=(tag:string):any=>({tag,style:{},className:'',innerHTML:'',textContent:'',width:0,height:0,firstChild:{style:{}},getContext:()=>ctx,remove(){},appendChild(){},replaceChildren(){},addEventListener(){},removeEventListener(){}})
const g=globalThis as any
g.document??={createElement:element}
g.window??={devicePixelRatio:1}
g.ResizeObserver??=class{observe(){}disconnect(){}}
g.requestAnimationFrame=()=>0
g.cancelAnimationFrame=()=>{}
g.addEventListener??=()=>{}
g.removeEventListener??=()=>{}
// Reduced motion keeps camera shake off; nothing is drawn anyway.
g.matchMedia=()=>({matches:true})

/** The engine delays melee hits with setTimeout; the simulation swaps in this clock while a fight runs. */
export const clock={now:0,queue:[] as {at:number;fn:()=>void}[]}
export function simulatedTimeout(fn:()=>void,ms=0){clock.queue.push({at:clock.now+ms/1000,fn});return 0}
export function runDue(){
 if(!clock.queue.some(t=>t.at<=clock.now))return
 const due=clock.queue.filter(t=>t.at<=clock.now);clock.queue=clock.queue.filter(t=>t.at>clock.now)
 for(const t of due)t.fn()
}
export function canvas(){return {clientWidth:1280,clientHeight:720,addEventListener(){},removeEventListener(){},focus(){},getBoundingClientRect(){return {left:0,top:0,width:1280,height:720}}} as any}
export const overlay={appendChild(){},replaceChildren(){}} as any
