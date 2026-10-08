import type {CSSProperties,ReactNode} from 'react'
import {ChevronsRight,CircleDot,Crosshair,Heart,RotateCw,Shield,Sparkles,Swords,Target,TrendingUp,Triangle,Undo2,Zap} from 'lucide-react'
import type {AbilityKind,Kit} from './kits'
import type {Hud,Key} from './engine'
import type {ClassInfo,Hero} from '../types'

export const ICON:Record<AbilityKind,typeof Swords>={projectile:Crosshair,nova:CircleDot,ground:Target,dash:ChevronsRight,blink:Sparkles,heal:Heart,shield:Shield,buff:TrendingUp,spin:RotateCw,cone:Triangle,chain:Zap,leap:ChevronsRight,spree:Swords,disengage:Undo2}
export const fmt=(s:number)=>`${Math.floor(s/60)}:${String(Math.floor(s%60)).padStart(2,'0')}`

/** The class's abilities with their keys, as listed before a fight. */
export function KitList({kit}:{kit:Kit}){
 return <div className="ready-kit">{kit.abilities.map(a=>{const Icon=ICON[a.kind];return <div key={a.key} className="kit-row"><span className="kit-key" style={{color:a.color}}><Icon size={16}/>{a.key}</span><div><strong>{a.name}</strong><small>{a.text}</small></div></div>})}</div>
}

/** Bottom bar of a fight: hero frame, ability buttons, and the screen's own action buttons. */
export function HeroHud({hero,cls,kit,hud,onCast,children}:{hero:Hero;cls:ClassInfo;kit:Kit;hud:Hud;onCast:(key:Key,keyboard:boolean)=>void;children:ReactNode}){
 return <div className="battle-hud">
  <div className="hud-hero">
   <span className="hud-crest" style={{background:cls.color}}>{hero.level}</span>
   <div className="hud-bars"><strong>{hero.name}</strong><div className="hud-hp"><span style={{width:`${hud.hp/hud.maxHp*100}%`}}/>{hud.shield>0&&<i style={{width:`${Math.min(100,hud.shield/hud.maxHp*100)}%`}}/>}<em>{hud.hp.toLocaleString()} / {hud.maxHp.toLocaleString()}</em></div>
    <div className="hud-buffs">{hud.buffs.map((b,i)=><span key={i} style={{borderColor:b.color,color:b.color}}>{b.name} {Math.ceil(b.left)}</span>)}</div></div>
  </div>
  <div className="hud-abilities">{kit.abilities.map(a=>{const Icon=ICON[a.kind];const cd=hud.cds[a.key as Key];const total=a.cd
   // detail is 0 when the button is pressed with the keyboard, so the ability aims at the target instead of the cursor.
   return <button key={a.key} className={`ability${cd>0?' cooling':''}`} title={`${a.name} (${a.key}): ${a.text}`} aria-label={`${a.name} (${a.key})`} onClick={ev=>onCast(a.key as Key,ev.detail===0)} style={{'--ab':a.color,'--cd':`${Math.min(1,cd/total)*360}deg`} as CSSProperties}>
    <Icon size={22}/><span className="ab-key">{a.key}</span>{cd>0&&<span className="ab-cd">{Math.ceil(cd)}</span>}</button>})}</div>
  <div className="hud-actions">{children}</div>
 </div>
}
