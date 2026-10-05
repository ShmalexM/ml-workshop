import {useEffect} from 'react'
import {X} from 'lucide-react'
import ChestArt from './ChestArt'
import './toast.css'
import type {Chest} from './types'

export type LootNotice={chest:Chest|null;battles:number;title:string}

/** Shown after a task is finished: what it earned and a way into the game. No three.js here. */
export default function LootToast({notice,onClose}:{notice:LootNotice;onClose:()=>void}){
 useEffect(()=>{const t=setTimeout(onClose,14000);return ()=>clearTimeout(t)},[notice,onClose])
 const {chest,battles}=notice
 return <div className="loot-toast" role="status">
  {chest&&<ChestArt tier={chest.tier} size={64}/>}
  <div className="loot-toast-text">
   <strong>{notice.title}</strong>
   <span>{chest?`${chest.tierName} earned`:'Reward earned'}{battles>0?` · ${battles} ${battles===1?'battle':'battles'} ready`:''}</span>
   <div className="loot-toast-actions">
    {chest&&<a href="#hero" onClick={onClose}>Open chest</a>}
    {battles>0&&<a href="#hero/battle" onClick={onClose}>Fight</a>}
   </div>
  </div>
  <button className="loot-toast-close" aria-label="Dismiss" onClick={onClose}><X size={16}/></button>
 </div>
}
