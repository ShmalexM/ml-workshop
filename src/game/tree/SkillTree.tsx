import {useEffect,useMemo,useRef,useState,type CSSProperties,type KeyboardEvent,type PointerEvent as ReactPointerEvent} from 'react'
import {ArrowLeft,Check,Crosshair,List,LocateFixed,Map as MapIcon,Minus,Plus,RotateCcw,Undo2} from 'lucide-react'
import {classOf,equipped,heroStats,passiveMods,type HeroStats} from '../stats'
import {gameApi} from '../gameApi'
import {branchOf,frontier,graphOf,landmarks,pathTo,sameSet,startOf,type Graph} from './graph'
import type {GameState,TreeMods,TreeNode} from '../types'

const SECTOR_TINT:Record<string,string>={vanguard:'#d39563',skirmisher:'#e6d36d',wilds:'#78d488',arcane:'#a097f4'}
const KIND_NAME={start:'Class start',small:'Small node',notable:'Notable',keystone:'Keystone'} as const
const RADIUS={start:20,small:9,notable:16,keystone:24} as const
const ZOOM_MAX=2.2
const DIRS:Record<string,[number,number]>={ArrowRight:[1,0],ArrowLeft:[-1,0],ArrowUp:[0,-1],ArrowDown:[0,1]}

type View={x:number;y:number;k:number}
/** What clicking a node does: buy the path to it, refund it (or its branch), or nothing and why. */
type Action={kind:'buy';path:string[]}|{kind:'short';cost:number}|{kind:'refund';branch:string[]}|{kind:'root'}|{kind:'blocked'}

const pct=(n:number)=>`${(n*100).toFixed(1)}%`
const octagon=(r:number)=>Array.from({length:8},(_,i)=>{const a=Math.PI/8+i*Math.PI/4;return `${(Math.cos(a)*r).toFixed(1)},${(Math.sin(a)*r).toFixed(1)}`}).join(' ')

/** The passive skill tree: edit a draft on the map or in the list, then Apply. Respec is free outside fights. */
export default function SkillTree({game,onGame,draft,onDraft,onBack,onPractice}:{game:GameState;onGame:(g:GameState)=>void;draft:string[]|null;onDraft:(d:string[]|null)=>void;onBack:()=>void;onPractice:()=>void}){
 const hero=game.hero!;const cls=classOf(game)!;const passives=game.passives!
 const g=useMemo(()=>graphOf(game.catalog.tree),[game.catalog.tree])
 const start=startOf(g,hero.class)
 const saved=useMemo(()=>new Set(passives.allocated),[passives.allocated])
 const chosen=useMemo(()=>new Set(draft??passives.allocated),[draft,passives.allocated])
 const dirty=!sameSet(chosen,saved)
 const earned=passives.points.earned;const spent=chosen.size-1;const available=earned-spent
 const open=useMemo(()=>frontier(g,start,chosen),[g,start,chosen])
 const gear=useMemo(()=>equipped(game),[game])
 const before=useMemo(()=>heroStats(gear,hero.level,passiveMods(game)),[gear,hero.level,game])
 const afterMods=useMemo(()=>passiveMods(game,chosen),[game,chosen])
 const after=useMemo(()=>heroStats(gear,hero.level,afterMods),[gear,hero.level,afterMods])

 const [mode,setMode]=useState<'map'|'list'>('map')
 const [view,setView]=useState<View>({x:0,y:0,k:1})
 const [size,setSize]=useState({w:800,h:600})
 const [hover,setHover]=useState<string|null>(null)
 const [cursor,setCursor]=useState<string|null>(null)
 // The node card with buttons is for touch and keyboard; a mouse click acts at once.
 const [cardOn,setCardOn]=useState(false)
 const [shift,setShift]=useState(false)
 const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [note,setNote]=useState('')
 const box=useRef<HTMLDivElement>(null)
 const minZoom=Math.min(.6,Math.min(size.w,size.h)/(game.catalog.tree.radius*2.3))

 const setChosen=(next:Set<string>)=>{setNote('');onDraft(sameSet(next,saved)?null:[...next])}
 function action(id:string):Action{
  if(id===start)return {kind:'root'}
  if(chosen.has(id))return {kind:'refund',branch:branchOf(g,start,chosen,id)}
  const path=pathTo(g,start,chosen,id)
  if(!path)return {kind:'blocked'}
  return path.length<=available?{kind:'buy',path}:{kind:'short',cost:path.length}
 }
 function act(id:string,wholeBranch=false){
  const a=action(id);const node=g.byId.get(id)!
  if(a.kind==='buy'){setChosen(new Set([...chosen,...a.path]));return}
  if(a.kind==='short'){setNote(`${node.name} needs ${a.cost} ${a.cost===1?'point':'points'}. You have ${available}.`);return}
  if(a.kind==='refund'){
   if(a.branch.length>1&&!wholeBranch){setNote(`${a.branch.length-1} other ${a.branch.length===2?'node depends':'nodes depend'} on ${node.name}. Refund ${a.branch.length===2?'it':'them'} first, or use Refund branch.`);return}
   const next=new Set(chosen);for(const n of a.branch)next.delete(n);setChosen(next)
  }
 }
 function actionText(id:string){
  const a=action(id)
  switch(a.kind){
   case 'root':return 'Your class starts here.'
   case 'blocked':return "Another class's starting node."
   case 'buy':return a.path.length===1?'Allocate: 1 point.':`Path: ${a.path.length} points.`
   case 'short':return `Needs ${a.cost} points. You have ${available}.`
   case 'refund':return a.branch.length===1?'Allocated. Refund to get 1 point back.':`Allocated. ${a.branch.length-1} more ${a.branch.length===2?'node depends':'nodes depend'} on it.`
  }
 }

 // ---------- view ----------
 const center=(id=start,k=view.k)=>{const n=g.byId.get(id)!;const d=Math.hypot(n.x,n.y);const pull=n.kind==='start'?.78:1;setView({x:d?n.x*pull:0,y:d?n.y*pull:0,k})}
 useEffect(()=>{const el=box.current;if(!el)return;const ro=new ResizeObserver(()=>setSize({w:el.clientWidth,h:el.clientHeight}));ro.observe(el);setSize({w:el.clientWidth,h:el.clientHeight});return ()=>ro.disconnect()},[mode])
 // Open on your own class.
 const first=useRef(true)
 useEffect(()=>{if(!first.current||!size.w)return;first.current=false;center(start,size.w<600?.7:1)
 // Only once, when the map first has a size.
 // eslint-disable-next-line react-hooks/exhaustive-deps
 },[size.w])
 const toScreen=(n:TreeNode)=>({x:(n.x-view.x)*view.k+size.w/2,y:(n.y-view.y)*view.k+size.h/2})
 const zoomAt=(k:number,sx=size.w/2,sy=size.h/2)=>setView(v=>{const nk=Math.min(ZOOM_MAX,Math.max(minZoom,k));const tx=(sx-size.w/2)/v.k+v.x,ty=(sy-size.h/2)/v.k+v.y;return {k:nk,x:tx-(sx-size.w/2)/nk,y:ty-(sy-size.h/2)/nk}})
 useEffect(()=>{
  const el=box.current;if(!el)return
  const wheel=(e:WheelEvent)=>{e.preventDefault();const r=el.getBoundingClientRect();zoomAt(view.k*Math.exp(-e.deltaY*.0015),e.clientX-r.left,e.clientY-r.top)}
  el.addEventListener('wheel',wheel,{passive:false});return ()=>el.removeEventListener('wheel',wheel)
 })
 // Drag to pan, pinch to zoom; a press that does not move is a click on the node under it.
 const pointers=useRef(new Map<number,{x:number;y:number}>());const drag=useRef<{x:number;y:number;moved:boolean;pinch:number;node:string|null}|null>(null)
 const down=(e:ReactPointerEvent)=>{
  if(e.button!==0)return
  // Read the node before capturing the pointer: captured events all target the map.
  const node=(e.target as Element).closest?.('[data-node]')?.getAttribute('data-node')??null
  ;(e.currentTarget as Element).setPointerCapture(e.pointerId);pointers.current.set(e.pointerId,{x:e.clientX,y:e.clientY})
  const pts=[...pointers.current.values()]
  drag.current={x:e.clientX,y:e.clientY,moved:pts.length>1,pinch:pts.length>1?Math.hypot(pts[0].x-pts[1].x,pts[0].y-pts[1].y):0,node}
 }
 const move=(e:ReactPointerEvent)=>{
  const d=drag.current;if(!d||!pointers.current.has(e.pointerId))return
  pointers.current.set(e.pointerId,{x:e.clientX,y:e.clientY})
  const pts=[...pointers.current.values()]
  if(pts.length>1&&d.pinch){const dist=Math.hypot(pts[0].x-pts[1].x,pts[0].y-pts[1].y);const r=box.current!.getBoundingClientRect();zoomAt(view.k*dist/d.pinch,(pts[0].x+pts[1].x)/2-r.left,(pts[0].y+pts[1].y)/2-r.top);d.pinch=dist;return}
  const dx=e.clientX-d.x,dy=e.clientY-d.y
  if(!d.moved&&Math.hypot(dx,dy)<5)return
  d.moved=true;d.x=e.clientX;d.y=e.clientY;setView(v=>({...v,x:v.x-dx/v.k,y:v.y-dy/v.k}))
 }
 const up=(e:ReactPointerEvent)=>{
  const d=drag.current;pointers.current.delete(e.pointerId)
  if(pointers.current.size)return
  drag.current=null
  if(!d||d.moved)return
  const id=d.node
  if(!id){setCursor(null);return}
  // A mouse click acts at once; a tap first shows the node and its buttons.
  if(e.pointerType==='mouse'){setCursor(null);setCardOn(false);act(id,e.shiftKey)}
  else{setCursor(id);setCardOn(true);const p=toScreen(g.byId.get(id)!);if(p.y>size.h*.5)setView(v=>({...v,y:v.y+(p.y-size.h*.32)/v.k}))}
 }

 // ---------- keyboard ----------
 const announce=(id:string|null)=>{if(!id)return '';const n=g.byId.get(id)!;const near=n.kind==='small'?landmarks(g,id).map(x=>label(g.byId.get(x)!)):[];return `${label(n)}${near.length?`, between ${near.join(' and ')}`:''}. ${n.text.join('. ')}${n.text.length?'. ':''}${actionText(id)}`}
 function keyDown(e:KeyboardEvent){
  setShift(e.shiftKey)
  const dir=DIRS[e.key]
  if(dir){
   e.preventDefault()
   const from=g.byId.get(cursor??start)!
   let best:string|null=null,score=-Infinity
   for(const id of g.adj.get(from.id)||[]){const n=g.byId.get(id)!;const vx=n.x-from.x,vy=n.y-from.y;const len=Math.hypot(vx,vy)||1;const cos=(vx*dir[0]+vy*dir[1])/len;if(cos>score){score=cos;best=id}}
   if(best&&score>-.2){setCursor(best);setCardOn(true);keepVisible(best)}
   return
  }
  if(e.key==='Enter'||e.key===' '){e.preventDefault();if(cursor)act(cursor,e.shiftKey);return}
  if(e.key==='Home'){e.preventDefault();setCursor(start);setCardOn(true);center(start);return}
  if(e.key==='+'||e.key==='='){e.preventDefault();zoomAt(view.k*1.2);return}
  if(e.key==='-'){e.preventDefault();zoomAt(view.k/1.2);return}
  if(e.key==='Escape'){setCursor(null);setNote('')}
 }
 function keepVisible(id:string){const p=toScreen(g.byId.get(id)!);const m=70;if(p.x<m||p.y<m||p.x>size.w-m||p.y>size.h-m)center(id)}

 // ---------- apply ----------
 async function apply(){
  if(busy)return;setBusy(true);setError('')
  try{const r=await gameApi.passives([...chosen]);onGame(r.game);onDraft(null)}catch(e){setError((e as Error).message)}finally{setBusy(false)}
 }

 // ---------- drawing ----------
 const focus=hover??cursor
 const preview=useMemo(()=>{
  if(!focus)return {path:new Set<string>(),branch:new Set<string>()}
  const a=action(focus)
  return {path:new Set(a.kind==='buy'||a.kind==='short'?pathTo(g,start,chosen,focus)||[]:[]),branch:new Set(a.kind==='refund'&&(shift||a.branch.length===1)?a.branch:[])}
 // action() reads only what is listed here.
 // eslint-disable-next-line react-hooks/exhaustive-deps
 },[focus,chosen,g,start,shift,available])
 const links=useMemo(()=>{const out:[TreeNode,TreeNode][]=[];for(const n of g.nodes)for(const id of n.links)if(n.id<id)out.push([n,g.byId.get(id)!]);return out},[g])
 const R=game.catalog.tree.radius
 const label=(n:TreeNode)=>n.kind==='start'?(game.catalog.classes.find(c=>c.id===n.class)?.name||'')+' start':n.name
 const nodeClass=(n:TreeNode)=>{
  const mine=chosen.has(n.id)
  return ['tree-node',`k-${n.kind}`,mine?'on':open.has(n.id)?'open':'',n.kind==='start'&&n.id!==start?'other':'',preview.path.has(n.id)?'path':'',preview.branch.has(n.id)?'cut':'',cursor===n.id?'cursor':''].filter(Boolean).join(' ')
 }
 const tip=hover&&mode==='map'?g.byId.get(hover):null
 const card=cursor&&cardOn?g.byId.get(cursor):null
 const cardAction=card?action(card.id):null
 const statRows=compareRows(before,after,passiveMods(game),afterMods)
 const picked=[...chosen].map(id=>g.byId.get(id)!).filter(n=>n.kind==='keystone'||n.kind==='notable').sort((a,b)=>a.kind===b.kind?a.name.localeCompare(b.name):a.kind==='keystone'?-1:1)
 const levelPoints=hero.level-1

 return <div className="g-wrap tree-page" style={{'--class':cls.color} as CSSProperties}>
  <header className="tree-head">
   <button className="g-button ghost small" onClick={onBack}><ArrowLeft size={15}/>Armory</button>
   <div><h1>Skill tree</h1><p>{hero.name} · <span style={{color:cls.color}}>{cls.name}</span> · Changes are free outside fights. Fights use the build you apply.</p></div>
   <button className="g-button ghost small" onClick={onPractice} title={dirty?'Practice with this unsaved build':'Practice with this build'}><Crosshair size={15}/>Practice{dirty?' this draft':''}</button>
  </header>
  {passives.refunded&&!dirty&&<div className="g-confirm" role="status"><p>{passives.refunded==='points'?'Your saved build needed more points than you have now, so all of its points were refunded.':'The skill tree changed since your build was saved, so all of its points were refunded.'} Allocate them again and press Apply.</p></div>}
  <div className="tree-grid">
   <section className="tree-map-wrap g-panel" aria-label="Passive tree">
    <div className="tree-tools">
     <div className="tree-mode" role="group" aria-label="View">
      <button className={mode==='map'?'active':''} aria-pressed={mode==='map'} onClick={()=>setMode('map')}><MapIcon size={14}/>Map</button>
      <button className={mode==='list'?'active':''} aria-pressed={mode==='list'} onClick={()=>setMode('list')}><List size={14}/>List</button>
     </div>
     {mode==='map'&&<>
      <button className="g-button ghost small" onClick={()=>{setCursor(start);center(start)}} aria-label="Center on my class"><LocateFixed size={14}/><span>Center<span className="wide-only"> on my class</span></span></button>
      <button className="g-button ghost small icon" aria-label="Zoom out" onClick={()=>zoomAt(view.k/1.25)}><Minus size={14}/></button>
      <button className="g-button ghost small icon" aria-label="Zoom in" onClick={()=>zoomAt(view.k*1.25)}><Plus size={14}/></button>
     </>}
     <span className="tree-left"><strong>{available}</strong> {available===1?'point':'points'} left</span>
    </div>
    {mode==='map'?<div ref={box} className="tree-map" tabIndex={0} role="application" aria-roledescription="skill tree map"
     aria-label="Passive skill tree. Arrow keys follow the links from your class start. Enter allocates the path to a node or refunds it; Shift Enter refunds a whole branch. Home returns to your class. The List view has the same nodes as a list."
     onKeyDown={keyDown} onKeyUp={e=>setShift(e.shiftKey)} onFocus={e=>{if(!cursor&&e.currentTarget.matches(':focus-visible')){setCursor(start);setCardOn(true)}}}
     onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={e=>{pointers.current.delete(e.pointerId);drag.current=null}}>
     <svg width={size.w} height={size.h} aria-hidden>
      <defs>
       <radialGradient id="tree-floor"><stop offset="0" stopColor="#20253a"/><stop offset="1" stopColor="#0d1018"/></radialGradient>
      </defs>
      <g transform={`translate(${size.w/2-view.x*view.k} ${size.h/2-view.y*view.k}) scale(${view.k})`}>
       <circle r={R*1.12} fill="url(#tree-floor)"/>
       {game.catalog.tree.sectors.map(s=>{const a0=(s.angle-45)*Math.PI/180,a1=(s.angle+45)*Math.PI/180;const ro=R*1.1,ri=R*.16
        const d=`M${Math.cos(a0)*ri} ${Math.sin(a0)*ri} L${Math.cos(a0)*ro} ${Math.sin(a0)*ro} A${ro} ${ro} 0 0 1 ${Math.cos(a1)*ro} ${Math.sin(a1)*ro} L${Math.cos(a1)*ri} ${Math.sin(a1)*ri} A${ri} ${ri} 0 0 0 ${Math.cos(a0)*ri} ${Math.sin(a0)*ri}Z`
        // Side sectors put their name above the class row, so it never covers a start node.
        const side=Math.abs(Math.cos(s.angle*Math.PI/180))>.5;const lx=side?Math.sign(Math.cos(s.angle*Math.PI/180))*R*1.02:0;const ly=side?-R*.62:Math.sign(Math.sin(s.angle*Math.PI/180))*R*1.17
        return <g key={s.id}><path d={d} fill={SECTOR_TINT[s.id]} opacity={.05} stroke={SECTOR_TINT[s.id]} strokeOpacity={.12}/>
         <text className="tree-sector" x={lx} y={ly} fill={SECTOR_TINT[s.id]} textAnchor="middle" dominantBaseline="middle">{s.name}</text></g>})}
       <circle r={R*.16} className="tree-hub"/><circle r={R*.1} className="tree-hub inner"/>
       {links.map(([a,b])=>{const on=chosen.has(a.id)&&chosen.has(b.id);const path=(preview.path.has(a.id)||chosen.has(a.id))&&(preview.path.has(b.id)||chosen.has(b.id))&&!on;const cut=preview.branch.has(a.id)||preview.branch.has(b.id)
        return <line key={a.id+b.id} x1={a.x} y1={a.y} x2={b.x} y2={b.y} className={`tree-link${on?' on':''}${path?' path':''}${cut&&on?' cut':''}`}/>})}
       {g.nodes.map(n=>{const r=RADIUS[n.kind];const mine=chosen.has(n.id);const color=n.kind==='start'?game.catalog.classes.find(c=>c.id===n.class)?.color||'#888':mine?cls.color:undefined
        return <g key={n.id} data-node={n.id} className={nodeClass(n)} transform={`translate(${n.x} ${n.y})`}
         onPointerEnter={e=>{if(e.pointerType==='mouse')setHover(n.id)}} onPointerLeave={e=>{if(e.pointerType==='mouse')setHover(h=>h===n.id?null:h)}}>
         <circle r={r+12} className="hit"/>
         {n.kind==='keystone'?<polygon className="shape" points={octagon(r)} style={mine?{fill:color}:undefined}/>:<circle className="shape" r={r} style={color?{fill:color}:undefined}/>}
         {n.kind==='notable'&&<circle r={r-5} className="inner"/>}
         {n.kind==='keystone'&&<polygon points={octagon(r-7)} className="inner"/>}
         {cursor===n.id&&<circle r={r+6} className="ring"/>}
         {(n.kind!=='small')&&<NodeLabel node={n} r={r} text={label(n)} sectorAngle={game.catalog.tree.sectors.find(s=>s.id===n.sector)?.angle} R={R}/>}
        </g>})}
      </g>
     </svg>
     {tip&&(()=>{const p=toScreen(tip);const left=Math.max(8,Math.min(p.x+RADIUS[tip.kind]*view.k+14,size.w-292));const top=Math.max(8,Math.min(p.y-24,size.h-170))
      return <div className="tree-tip" style={{left,top}}><NodeText node={tip} label={label(tip)} sector={sectorName(game,tip)}/><span className={`tree-status s-${action(tip.id).kind}`}>{actionText(tip.id)}</span>{action(tip.id).kind==='refund'&&(action(tip.id) as {branch:string[]}).branch.length>1&&<small>Shift-click to refund all {(action(tip.id) as {branch:string[]}).branch.length}.</small>}</div>})()}
     {card&&cardAction&&<div className="tree-card" onPointerDown={e=>e.stopPropagation()} onPointerUp={e=>e.stopPropagation()}>
      <NodeText node={card} label={label(card)} sector={sectorName(game,card)}/>
      <span className={`tree-status s-${cardAction.kind}`}>{actionText(card.id)}</span>
      <div>
       {cardAction.kind==='buy'&&<button className="g-button small" onClick={()=>act(card.id)}><Check size={14}/>Allocate ({cardAction.path.length})</button>}
       {cardAction.kind==='refund'&&cardAction.branch.length===1&&<button className="g-button ghost small" onClick={()=>act(card.id)}><Undo2 size={14}/>Refund</button>}
       {cardAction.kind==='refund'&&cardAction.branch.length>1&&<button className="g-button ghost small" onClick={()=>act(card.id,true)}><Undo2 size={14}/>Refund branch ({cardAction.branch.length})</button>}
       <button className="g-button ghost small" onClick={()=>setCursor(null)}>Close</button>
      </div>
     </div>}
     <span className="sr-only" aria-live="polite">{note||announce(cursor)}</span>
    </div>:<TreeList game={game} g={g} label={label} action={action} actionText={actionText} act={act} chosen={chosen}/>}
    {note&&<p className="tree-note" role="status">{note}</p>}
   </section>
   <aside className="tree-side g-panel" aria-label="Build summary">
    <div className="tree-points">
     <div><strong>{available}</strong><span>left</span></div><div><strong>{spent}</strong><span>spent</span></div><div><strong>{earned}</strong><span>earned</span></div>
    </div>
    <p className="tree-earn">One point per level after the first ({levelPoints}) and one per mastered learning path ({earned-levelPoints}).</p>
    <table className="tree-stats"><caption>{dirty?'Saved build → this draft':'Your stats with this build'}</caption><tbody>
     {statRows.map(([name,a,b,better])=><tr key={name}><th scope="row">{name}</th><td>{a}</td>{dirty&&<td className={a===b?'same':better?'up':'down'}>{a===b?'':'→ '+b}</td>}</tr>)}
    </tbody></table>
    <h2>Notables and keystones</h2>
    {picked.length?<ul className="tree-picked">{picked.map(n=><li key={n.id} className={`k-${n.kind}`}><strong>{n.name}</strong><span>{n.text.join('. ')}.</span></li>)}</ul>:<p className="tree-empty">None yet. Notables are the larger circles on the map; keystones are the octagons near the middle.</p>}
    {error&&<div className="g-error" role="alert"><span>{error}</span></div>}
    <div className="tree-actions">
     <button className="g-button" disabled={!dirty||busy} onClick={apply}><Check size={15}/>{busy?'Saving…':'Apply'}</button>
     <button className="g-button ghost" disabled={!dirty||busy} onClick={()=>{onDraft(null);setNote('')}}><RotateCcw size={15}/>Reset</button>
     <button className="g-button ghost" disabled={busy||chosen.size<=1} onClick={()=>setChosen(new Set([start]))}><Undo2 size={15}/>Refund all</button>
    </div>
    {dirty&&<p className="tree-earn">Unsaved: fights still use your saved build until you press Apply.</p>}
   </aside>
  </div>
 </div>
}

/** Under the node. In the top and bottom sectors the two deep notables sit side by side, so their names go outward. */
function NodeLabel({node,r,text,sectorAngle,R}:{node:TreeNode;r:number;text:string;sectorAngle?:number;R:number}){
 if(node.kind==='notable'&&sectorAngle!==undefined&&Math.abs(Math.sin(sectorAngle*Math.PI/180))>.5&&Math.hypot(node.x,node.y)<R*.4){
  const side=Math.sign(node.x)||1
  return <text className="tree-label" x={side*(r+6)} y={5} textAnchor={side>0?'start':'end'}>{text}</text>
 }
 return <text className="tree-label" y={r+17} textAnchor="middle">{text}</text>
}

function sectorName(game:GameState,n:TreeNode){
 const sectors=game.catalog.tree.sectors
 if(n.kind==='keystone')return (n.between||[]).map(id=>sectors.find(s=>s.id===id)?.name).join(' and ')
 return sectors.find(s=>s.id===n.sector)?.name||''
}

function NodeText({node,label,sector}:{node:TreeNode;label:string;sector:string}){
 return <>
  <strong className={`tree-name k-${node.kind}`}>{label}</strong>
  <span className="tree-kind">{KIND_NAME[node.kind]}{sector?` · ${sector}`:''}</span>
  {node.text.length>0&&<ul>{node.text.map(t=><li key={t}>{t}</li>)}</ul>}
 </>
}

/** The same nodes as a list, grouped by sector, for screen readers and small screens. */
function TreeList({game,g,label,action,actionText,act,chosen}:{game:GameState;g:Graph;label:(n:TreeNode)=>string;action:(id:string)=>Action;actionText:(id:string)=>string;act:(id:string,branch?:boolean)=>void;chosen:Set<string>}){
 const nodes=g.nodes;const order={keystone:0,notable:1,small:2,start:3}
 const place=(n:TreeNode)=>{if(n.kind!=='small')return '';const near=landmarks(g,n.id).map(id=>label(g.byId.get(id)!));return near.length>1?`Between ${near[0]} and ${near[1]}`:near.length?`Next to ${near[0]}`:''}
 const groups=[...game.catalog.tree.sectors.map(s=>({id:s.id,name:s.name,text:s.text,nodes:nodes.filter(n=>n.sector===s.id&&n.kind!=='start')})),
  {id:'keystones',name:'Keystones',text:'Big trade-offs on the borders between sectors.',nodes:nodes.filter(n=>n.kind==='keystone')}]
 return <div className="tree-list">
  {groups.map(gr=><section key={gr.id} aria-labelledby={`tl-${gr.id}`}>
   <h3 id={`tl-${gr.id}`}>{gr.name} <small>{gr.text}</small></h3>
   <ul>{[...gr.nodes].sort((a,b)=>order[a.kind]-order[b.kind]).map(n=>{const a=action(n.id);const on=chosen.has(n.id)
    return <li key={n.id} className={on?'on':''}>
     <div><span><strong className={`tree-name k-${n.kind}`}>{label(n)}</strong> <span className="tree-kind">{KIND_NAME[n.kind]}{place(n)?` · ${place(n)}`:''}</span></span><span className="tree-effect">{n.text.join('. ')}.</span><span className="tree-status">{actionText(n.id)}</span></div>
     {a.kind==='buy'&&<button className="g-button small" onClick={()=>act(n.id)} aria-label={`Allocate ${label(n)}${place(n)?`, ${place(n)}`:''}: ${a.path.length} ${a.path.length===1?'point':'points'}`}>Allocate ({a.path.length})</button>}
     {a.kind==='refund'&&<button className="g-button ghost small" onClick={()=>act(n.id,true)} aria-label={`Refund ${label(n)}${place(n)?`, ${place(n)}`:''}${a.branch.length>1?`, and ${a.branch.length-1} nodes after it`:''}`}>Refund{a.branch.length>1?` (${a.branch.length})`:''}</button>}
    </li>})}</ul>
  </section>)}
 </div>
}

/** Stat sheet rows: [name, saved value, draft value, whether the draft is better]. */
function compareRows(a:HeroStats,b:HeroStats,ma:TreeMods,mb:TreeMods):[string,string,string,boolean][]{
 const rows:[string,string,string,boolean][]=[
  ['Power',String(a.power),String(b.power),b.power>a.power],
  ['Health',a.maxHp.toLocaleString(),b.maxHp.toLocaleString(),b.maxHp>a.maxHp],
  ['Critical strike',pct(a.critChance),pct(b.critChance),b.critChance>a.critChance],
  ['Haste',pct(a.haste),pct(b.haste),b.haste>a.haste],
  ['Mastery',pct(a.mastery),pct(b.mastery),b.mastery>a.mastery],
  ['Versatility',pct(a.versatility),pct(b.versatility),b.versatility>a.versatility],
  ['Armor reduction',pct(a.damageReduction),pct(b.damageReduction),b.damageReduction>a.damageReduction],
 ]
 // Tree-only effects, shown when either build has them.
 const extra:[string,string,boolean][]=[['ability','Ability damage',true],['area','Area of effect',true],['burn','Burn damage',true],['cdr','Cooldown recovery',true],['healing','Healing received',true],['dr','Less damage taken',true]]
 for(const [key,name,up] of extra){const x=ma[key]||0,y=mb[key]||0;if(x||y)rows.push([name,`+${pct(x)}`,`+${pct(y)}`,up?y>x:y<x])}
 return rows
}
