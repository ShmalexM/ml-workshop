import {useEffect,useState} from 'react'
import {Footprints,Hand,HardHat,Shield,Shirt,Sword,Wand,BookOpen,Circle} from 'lucide-react'
import {cachedIcon,iconKey,itemIcon} from './three/icons'
import type {GearLook,Item,Slot} from './types'

export function lookOf(item:Item):GearLook{return {slot:item.slot,base:item.base,rarity:item.rarity,seed:item.seed,effect:item.effect?.id??null,twoHand:item.twoHand}}

const FALLBACK:Record<Slot,typeof Sword>={head:HardHat,shoulders:Shield,back:Shirt,chest:Shirt,hands:Hand,legs:Shirt,feet:Footprints,mainhand:Sword,offhand:Shield}
const BASE_FALLBACK:Record<string,typeof Sword>={wand:Wand,staff:Wand,tome:BookOpen,orb:Circle}

/** Square item icon: a rendered 3D model inside a frame that gets more ornate with rarity. */
export default function ItemIcon({look,size=52,empty,dim}:{look:GearLook|null;size?:number;empty?:Slot;dim?:boolean}){
 const key=look?iconKey(look):'';const [url,setUrl]=useState(()=>look?cachedIcon(look)||'':'')
 useEffect(()=>{if(!look)return;let live=true;const hit=cachedIcon(look);if(hit){setUrl(hit);return}setUrl('');itemIcon(look).then(u=>{if(live)setUrl(u)});return ()=>{live=false}
 // eslint-disable-next-line react-hooks/exhaustive-deps
 },[key])
 if(!look){const Icon=empty?FALLBACK[empty]:Circle;return <span className="g-icon empty" style={{width:size,height:size}}><Icon size={size*.42}/></span>}
 const Fallback=BASE_FALLBACK[look.base]||FALLBACK[look.slot]
 return <span className={`g-icon r-${look.rarity}${dim?' dim':''}`} style={{width:size,height:size}}>
  {look.rarity==='legendary'&&<span className="g-rays" aria-hidden/>}
  {url?<img src={url} alt="" draggable={false}/>:<Fallback size={size*.45} className="g-icon-fallback"/>}
  {look.rarity==='legendary'&&<><i className="g-ember e1"/><i className="g-ember e2"/><i className="g-ember e3"/></>}
 </span>
}
