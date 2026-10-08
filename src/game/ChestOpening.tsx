import {useEffect,useRef,useState} from 'react'
import {X} from 'lucide-react'
import ChestArt from './ChestArt'
import ItemIcon,{lookOf} from './ItemIcon'
import ItemTooltip,{FloatingTip} from './ItemTooltip'
import {RARITY_COLOR,RARITY_INDEX,RARITY_NAME,SLOT_NAME,BASE_NAME,TIER_LABEL} from './rarity'
import {reducedMotion} from './three/scene'
import {equipped,gainText,isUpgrade,upgradeGain} from './stats'
import {gameApi} from './gameApi'
import type {Chest,GameState,Item} from './types'

type Phase='ready'|'opening'|'revealed'

/** Modal that opens one chest: shake while the server rolls, then reveal items one by one. */
export default function ChestOpening({chest,game,onGame,onClose,onNext,nextCount}:{chest:Chest;game:GameState;onGame:(g:GameState,flash?:Item)=>void;onClose:()=>void;onNext:()=>void;nextCount:number}){
 const dialog=useRef<HTMLDialogElement>(null);const openButton=useRef<HTMLButtonElement>(null)
 const [phase,setPhase]=useState<Phase>('ready');const [items,setItems]=useState<Item[]>([]);const [shown,setShown]=useState(0);const [error,setError]=useState('')
 const [hover,setHover]=useState<{item:Item;rect:DOMRect}|null>(null);const [replacing,setReplacing]=useState<number|null>(null)
 const still=reducedMotion()
 useEffect(()=>{const d=dialog.current;d?.showModal();openButton.current?.focus();return ()=>{if(d?.open)d.close()}},[])
 useEffect(()=>{if(phase!=='revealed'||shown>=items.length)return;const t=setTimeout(()=>setShown(n=>n+1),still?0:shown===0?650:480);return ()=>clearTimeout(t)},[phase,shown,items.length,still])
 const best=items.reduce<Item|null>((a,b)=>!a||RARITY_INDEX[b.rarity]>RARITY_INDEX[a.rarity]?b:a,null)
 async function open(){
  if(phase!=='ready')return;setPhase('opening');setError('')
  try{
   const [result]=await Promise.all([gameApi.open(chest.source),new Promise(r=>setTimeout(r,still?0:900))])
   const ordered=[...result.items].sort((a,b)=>RARITY_INDEX[a.rarity]-RARITY_INDEX[b.rarity])
   setItems(ordered);setShown(0);setPhase('revealed');onGame(result.game)
  }catch(e){setError((e as Error).message);setPhase('ready')}
 }
 async function equip(item:Item,confirmed=false){
  // Taking off a Legendary effect needs a second click.
  if(!confirmed&&upgradeGain(item,gear,level).lostEffects.length){setReplacing(item.id);return}
  setReplacing(null)
  try{const r=await gameApi.equip(item.id);onGame(r.game,item)}catch(e){setError((e as Error).message)}
 }
 // Read from the current equipment, so an item replaced by a later Equip shows its button again.
 const gear=equipped(game);const level=game.hero?.level||1;const worn=new Set(Object.values(game.equipment));const legendary=best?.rarity==='legendary'&&shown>=items.length
 const tierName=chest.tierName||TIER_LABEL[chest.tier]
 return <dialog ref={dialog} className={`chest-dialog game${legendary?' legendary-burst':''}`} aria-labelledby="chest-title" onCancel={e=>{if(phase==='opening')e.preventDefault();else onClose()}}>
  <button className="chest-close" aria-label="Close" onClick={onClose} disabled={phase==='opening'}><X size={18}/></button>
  <span className="g-eyebrow">{chest.kind==='boss'?'Boss loot':chest.subtitle||'Reward'}</span>
  <h2 id="chest-title" className={`tier-title tier-${chest.tier}`}>{tierName}</h2>
  <p className="chest-for">{chest.title}</p>
  <div className={`chest-stage${phase==='opening'&&!still?' shaking':''}`}>
   <ChestArt tier={chest.tier} open={phase==='revealed'} beam={best?RARITY_COLOR[best.rarity].glow:undefined} size={220} className={phase==='opening'&&!still?'shake':''}/>
  </div>
  {phase!=='revealed'&&<div className="chest-actions">
   <button ref={openButton} className="g-button" onClick={open} disabled={phase==='opening'}>{phase==='opening'?'Opening…':'Open'}</button>
   <small>{chest.tier>=4?'Guaranteed Rare or better.':`Tier ${chest.tier} of 5.`}</small>
  </div>}
  {phase==='revealed'&&<ul className="loot-list" aria-live="polite">
   {items.slice(0,shown).map(item=>{const gain=upgradeGain(item,gear,level);const done=worn.has(item.id)
    const show=(e:{currentTarget:HTMLElement})=>setHover({item,rect:e.currentTarget.getBoundingClientRect()})
    return <li key={item.id} className={`loot-card lc-${item.rarity}`} onMouseEnter={show} onMouseLeave={()=>setHover(h=>h?.item===item?null:h)}>
     <ItemIcon look={lookOf(item)} size={64}/>
     <div className="loot-text"><strong className={`rt-${item.rarity}`}>{item.name}</strong><span>{RARITY_NAME[item.rarity]} · Item Level {item.ilvl} · {SLOT_NAME[item.slot]}{item.slot==='mainhand'||item.slot==='offhand'?` · ${BASE_NAME[item.base]}`:''}</span>{item.effect&&<span className="loot-effect">{item.effect.name}</span>}
      {replacing===item.id&&!done&&<span className="loot-warn" role="alert">Takes off {gain.lostEffects.map(i=>`${i.effect!.name} (${i.name})`).join(', ')}. <button className="g-button small" onClick={()=>equip(item,true)}>Replace</button> <button className="g-button ghost small" onClick={()=>setReplacing(null)}>Keep</button></span>}</div>
     <div className="loot-act">{isUpgrade(gain)&&!done&&<span className="upgrade">▲ {gainText(gain)}</span>}{done?<span className="equipped-note">Equipped</span>:<button className="g-button small" onFocus={show} onBlur={()=>setHover(null)} onClick={()=>equip(item)}>Equip</button>}</div>
    </li>})}
  </ul>}
  {hover&&phase==='revealed'&&<FloatingTip x={hover.rect.right} y={hover.rect.top} avoid={hover.rect}><ItemTooltip item={hover.item} compare={gear[hover.item.slot]} gain={worn.has(hover.item.id)?null:upgradeGain(hover.item,gear,level)}/></FloatingTip>}
  {error&&<div className="g-error" role="alert"><span>{error}</span></div>}
  {phase==='revealed'&&shown>=items.length&&<div className="chest-actions">
   {nextCount>0&&<button className="g-button" onClick={onNext}>Open next chest ({nextCount} left)</button>}
   <button className="g-button ghost" onClick={onClose}>Done</button>
  </div>}
 </dialog>
}
