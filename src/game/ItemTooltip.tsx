import {useLayoutEffect,useRef,useState,type ReactNode} from 'react'
import {BASE_NAME,SLOT_NAME} from './rarity'
import {PRIMARY_NAME,SECONDARY_NAME,STAT_KEYS,gainText,isUpgrade,type Gain} from './stats'
import type {Item,StatKey} from './types'

function slotLine(item:Item):[string,string]{
 if(item.slot==='mainhand')return [item.twoHand?'Two-Hand':item.base==='wand'?'Main Hand':'One-Hand',BASE_NAME[item.base]||item.base]
 if(item.slot==='offhand')return item.base==='tome'||item.base==='orb'?['Held In Off-hand','']:['Off Hand',BASE_NAME[item.base]||item.base]
 return [SLOT_NAME[item.slot],BASE_NAME[item.base]||item.base]
}
const label=(k:StatKey,item:Item)=>k==='primary'?PRIMARY_NAME[item.primaryStat]:k==='stamina'?'Stamina':SECONDARY_NAME[k]||k
const Delta=({n}:{n:number})=>n===0?null:<em className={n>0?'up':'down'}> ({n>0?'+':''}{n})</em>

/** Reads like an in-game tooltip. `compare` is the item currently in the same slot, if any; `gain` is what equipping this item changes. */
export default function ItemTooltip({item,compare,gain,source}:{item:Item;compare?:Item|null;gain?:Gain|null;source?:string}){
 const [slot,kind]=slotLine(item)
 const delta=(k:StatKey)=>compare&&compare.id!==item.id?item.stats[k]-compare.stats[k]:0
 return <div className={`item-tooltip tt-${item.rarity}`}>
  <strong className={`tt-name rt-${item.rarity}`}>{item.name}</strong>
  <span className="tt-ilvl">Item Level {item.ilvl}</span>
  <span className="tt-row"><span>{slot}</span><span>{kind}</span></span>
  {item.stats.damage>0&&<span>{item.stats.damage} Damage<Delta n={delta('damage')}/></span>}
  {item.stats.armor>0&&<span>{item.stats.armor} Armor<Delta n={delta('armor')}/></span>}
  {STAT_KEYS.filter(k=>k!=='armor'&&k!=='damage'&&item.stats[k]>0).map(k=><span key={k} className={k==='primary'||k==='stamina'?'':'tt-secondary'}>+{item.stats[k]} {label(k,item)}<Delta n={delta(k)}/></span>)}
  {item.effect&&<span className="tt-effect"><b>{item.effect.name}.</b> {item.effect.text}</span>}
  {item.flavor&&<span className="tt-flavor">“{item.flavor}”</span>}
  {gain&&!item.equipped&&<span className={`tt-gain ${isUpgrade(gain)?'up':'down'}`}>If equipped: {gainText(gain)}</span>}
  {gain&&!item.equipped&&gain.lostEffects.map(lost=><span key={lost.id} className="tt-warn">Replaces {lost.name} and its {lost.effect!.name} effect</span>)}
  {source&&<span className="tt-source">{source}</span>}
  {item.equipped&&<span className="tt-equipped">Equipped</span>}
 </div>
}

/** A tooltip beside a point or a box, moved to stay inside the window. */
export function FloatingTip({x,y,avoid,children}:{x:number;y:number;avoid?:DOMRect;children:ReactNode}){
 const box=useRef<HTMLDivElement>(null);const [pos,setPos]=useState({left:x+18,top:y+12})
 useLayoutEffect(()=>{
  const el=box.current;if(!el)return
  const w=el.offsetWidth,h=el.offsetHeight,pad=8
  let left=avoid?avoid.right+12:x+18
  if(left+w>innerWidth-pad)left=avoid?avoid.left-12-w:x-18-w
  if(left<pad)left=Math.max(pad,innerWidth-pad-w)
  const top=Math.max(pad,Math.min((avoid?avoid.top:y+12),innerHeight-pad-h))
  setPos(p=>p.left===left&&p.top===top?p:{left,top})
 },[x,y,avoid,children])
 return <div ref={box} className="floating-tip" style={pos}>{children}</div>
}
