import {BASE_NAME,SLOT_NAME} from './rarity'
import {PRIMARY_NAME,SECONDARY_NAME,STAT_KEYS} from './stats'
import type {Item,StatKey} from './types'

function slotLine(item:Item):[string,string]{
 if(item.slot==='mainhand')return [item.twoHand?'Two-Hand':item.base==='wand'?'Main Hand':'One-Hand',BASE_NAME[item.base]||item.base]
 if(item.slot==='offhand')return item.base==='tome'||item.base==='orb'?['Held In Off-hand','']:['Off Hand',BASE_NAME[item.base]||item.base]
 return [SLOT_NAME[item.slot],BASE_NAME[item.base]||item.base]
}
const label=(k:StatKey,item:Item)=>k==='primary'?PRIMARY_NAME[item.primaryStat]:k==='stamina'?'Stamina':SECONDARY_NAME[k]||k

/** Reads like an in-game tooltip. `compare` is the item currently in the same slot, if any. */
export default function ItemTooltip({item,compare,source}:{item:Item;compare?:Item|null;source?:string}){
 const [slot,kind]=slotLine(item)
 const delta=(k:StatKey)=>compare&&compare.id!==item.id?item.stats[k]-compare.stats[k]:0
 const ilvlDelta=compare&&compare.id!==item.id?item.ilvl-compare.ilvl:0
 return <div className={`item-tooltip tt-${item.rarity}`}>
  <strong className={`tt-name rt-${item.rarity}`}>{item.name}</strong>
  <span className="tt-ilvl">Item Level {item.ilvl}{ilvlDelta!==0&&<em className={ilvlDelta>0?'up':'down'}> ({ilvlDelta>0?'+':''}{ilvlDelta})</em>}</span>
  <span className="tt-row"><span>{slot}</span><span>{kind}</span></span>
  {item.stats.damage>0&&<span>{item.stats.damage} Damage</span>}
  {item.stats.armor>0&&<span>{item.stats.armor} Armor</span>}
  {STAT_KEYS.filter(k=>k!=='armor'&&k!=='damage'&&item.stats[k]>0).map(k=><span key={k} className={k==='primary'||k==='stamina'?'':'tt-secondary'}>+{item.stats[k]} {label(k,item)}{delta(k)!==0&&<em className={delta(k)>0?'up':'down'}> ({delta(k)>0?'+':''}{delta(k)})</em>}</span>)}
  {item.effect&&<span className="tt-effect"><b>{item.effect.name}.</b> {item.effect.text}</span>}
  {item.flavor&&<span className="tt-flavor">“{item.flavor}”</span>}
  {source&&<span className="tt-source">{source}</span>}
  {item.equipped&&<span className="tt-equipped">Equipped</span>}
 </div>
}
