import {useEffect,useMemo,useRef,useState} from 'react'
import {X} from 'lucide-react'
import ItemIcon,{lookOf} from './ItemIcon'
import {RARITY_INDEX,RARITY_NAME,SLOT_NAME,BASE_NAME} from './rarity'
import {equipped,gainText,isUpgrade,passiveMods,upgradeGain} from './stats'
import {gameApi} from './gameApi'
import type {GameState,Item,Rarity} from './types'

/** What Open all dropped, in one list with the best rarity first. There is no animation per chest. */
export default function ChestSummary({chests,items,game,onGame,onClose}:{chests:number;items:Item[];game:GameState;onGame:(g:GameState,flash?:Item)=>void;onClose:()=>void}){
 const dialog=useRef<HTMLDialogElement>(null);const firstAction=useRef<HTMLButtonElement>(null);const doneButton=useRef<HTMLButtonElement>(null)
 const [error,setError]=useState('');const [replacing,setReplacing]=useState<number|null>(null)
 const ordered=useMemo(()=>[...items].sort((a,b)=>RARITY_INDEX[b.rarity]-RARITY_INDEX[a.rarity]||b.ilvl-a.ilvl),[items])
 const counts=useMemo(()=>{const by=new Map<Rarity,number>();ordered.forEach(item=>by.set(item.rarity,(by.get(item.rarity)||0)+1));return [...by].map(([rarity,n])=>`${n} ${RARITY_NAME[rarity]}`).join(' · ')},[ordered])
 // Focus the first Equip button, or Done when nothing is left to equip.
 useEffect(()=>{const d=dialog.current;d?.showModal();(firstAction.current||doneButton.current)?.focus();return ()=>{if(d?.open)d.close()}},[])
 const gear=equipped(game);const level=game.hero?.level||1;const mods=passiveMods(game);const worn=new Set(Object.values(game.equipment))
 async function equip(item:Item,confirmed=false){
  // Taking off a Legendary effect needs a second click.
  if(!confirmed&&upgradeGain(item,gear,level,mods).lostEffects.length){setReplacing(item.id);return}
  setReplacing(null);setError('')
  try{const r=await gameApi.equip(item.id);onGame(r.game,item)}catch(e){setError((e as Error).message)}
 }
 let first=true
 return <dialog ref={dialog} className="chest-dialog chest-summary game" aria-labelledby="chest-summary-title" onCancel={onClose}>
  <button className="chest-close" aria-label="Close" onClick={onClose}><X size={18}/></button>
  <span className="g-eyebrow">Open all</span>
  <h2 id="chest-summary-title">{chests} {chests===1?'chest':'chests'} opened</h2>
  <p className="chest-for">{ordered.length} {ordered.length===1?'item':'items'}{counts?`: ${counts}`:''}</p>
  <ul className="loot-list">
   {ordered.map(item=>{const gain=upgradeGain(item,gear,level,mods);const done=worn.has(item.id);const ref=!done&&first?firstAction:undefined;if(!done)first=false
    return <li key={item.id} className={`loot-card lc-${item.rarity}`}>
     <ItemIcon look={lookOf(item)} size={52}/>
     <div className="loot-text"><strong className={`rt-${item.rarity}`}>{item.name}</strong><span>{RARITY_NAME[item.rarity]} · Item Level {item.ilvl} · {SLOT_NAME[item.slot]}{item.slot==='mainhand'||item.slot==='offhand'?` · ${BASE_NAME[item.base]}`:''}</span>{item.effect&&<span className="loot-effect">{item.effect.name}</span>}
      {replacing===item.id&&!done&&<span className="loot-warn" role="alert">Takes off {gain.lostEffects.map(i=>`${i.effect!.name} (${i.name})`).join(', ')}. <button className="g-button small" onClick={()=>equip(item,true)}>Replace</button> <button className="g-button ghost small" onClick={()=>setReplacing(null)}>Keep</button></span>}</div>
     <div className="loot-act">{isUpgrade(gain)&&!done&&<span className="upgrade">▲ {gainText(gain)}</span>}{done?<span className="equipped-note">Equipped</span>:<button ref={ref} className="g-button small" onClick={()=>equip(item)}>Equip</button>}</div>
    </li>})}
  </ul>
  {error&&<div className="g-error" role="alert"><span>{error}</span></div>}
  <div className="chest-actions"><button ref={doneButton} className="g-button ghost" onClick={onClose}>Done</button></div>
 </dialog>
}
