import {useMemo,useState,type CSSProperties} from 'react'
import HeroViewer from './HeroViewer'
import ChestArt from './ChestArt'
import type {Appearance} from './three/hero'
import type {Catalog,ClassInfo,GameState,GearLook,Slot} from './types'

/** Mirrors the backend starter kit so the preview shows what the hero will actually wear. */
const STARTER:Record<string,string[]>={warrior:['sword','shield'],paladin:['mace','shield'],deathknight:['greatsword'],hunter:['bow'],shaman:['mace','shield'],rogue:['dagger','dagger'],monk:['staff'],druid:['staff'],demonhunter:['warglaive','warglaive'],priest:['staff'],mage:['staff'],warlock:['staff']}

export function starterLook(race:string,cls:ClassInfo):Appearance{
 const gear:Partial<Record<Slot,GearLook>>={}
 for(const slot of ['chest','legs','feet'] as const)gear[slot]={slot,base:cls.armor,rarity:'basic',seed:7+slot.length,effect:null,twoHand:false}
 const [main,off]=STARTER[cls.id]||['sword']
 gear.mainhand={slot:'mainhand',base:main,rarity:'basic',seed:11,effect:null,twoHand:['greatsword','staff','bow'].includes(main)}
 if(off)gear.offhand={slot:'offhand',base:off,rarity:'basic',seed:13,effect:null,twoHand:false}
 return {race,cls:cls.id,role:cls.role,gear}
}

const NAME=/^[A-Za-z][A-Za-z' -]*[A-Za-z]$/

export default function CreateHero({game,onCreate,busy,error}:{game:GameState;onCreate:(name:string,race:string,cls:string)=>void;busy:boolean;error:string}){
 const catalog:Catalog=game.catalog
 const [race,setRace]=useState('orc');const [cls,setCls]=useState('warrior');const [name,setName]=useState('')
 const info=catalog.classes.find(c=>c.id===cls)||catalog.classes[0]
 const look=useMemo(()=>starterLook(race,info),[race,info])
 const trimmed=name.trim();const valid=trimmed.length>=2&&trimmed.length<=16&&NAME.test(trimmed)&&!trimmed.includes('  ')
 const waiting=game.chests.unopened.length
 return <div className="g-wrap create-hero">
  <div className="create-grid">
   <section className="create-preview g-panel">
    <HeroViewer look={look} accent={info.color} label={`Preview of a ${catalog.races.find(r=>r.id===race)?.name} ${info.name}`}/>
    <p className="create-caption">Drag to rotate</p>
   </section>
   <form className="create-form g-panel" onSubmit={e=>{e.preventDefault();if(valid&&!busy)onCreate(trimmed,race,cls)}}>
    <h1>Create a hero</h1>
    <p className="create-intro">Each lesson, project walkthrough, or reading you finish earns a chest and one battle. Chests only hold gear your class can use. Expect to lose your first fights. Damage you deal to a boss carries over, and every finished task makes you stronger.</p>
    {waiting>0&&<div className="create-waiting"><ChestArt tier={Math.max(...game.chests.unopened.map(c=>c.tier))} size={52}/><span>{waiting} {waiting===1?'chest is':'chests are'} already waiting from work you have finished.</span></div>}
    <label className="create-label" htmlFor="hero-name">Name</label>
    <input id="hero-name" className="create-name" value={name} maxLength={16} autoComplete="off" spellCheck={false} placeholder="2–16 letters" onChange={e=>setName(e.target.value)} aria-invalid={name.length>0&&!valid}/>
    {name.length>0&&!valid&&<small className="create-hint">Use 2–16 letters. Spaces, hyphens and apostrophes can go between letters.</small>}
    <fieldset className="create-choices"><legend>Race</legend>
     <div className="race-list">{catalog.races.map(r=><button type="button" key={r.id} aria-pressed={race===r.id} className={race===r.id?'chosen':''} onClick={()=>setRace(r.id)}>{r.name}</button>)}</div>
    </fieldset>
    <fieldset className="create-choices"><legend>Class</legend>
     <div className="class-grid">{catalog.classes.map(c=><button type="button" key={c.id} aria-pressed={cls===c.id} className={cls===c.id?'chosen':''} style={{'--class':c.color} as CSSProperties} onClick={()=>setCls(c.id)}><strong>{c.name}</strong><small>{c.armor[0].toUpperCase()+c.armor.slice(1)} · {c.role==='melee'?'Melee':c.role==='ranged'?'Ranged':'Caster'}</small></button>)}</div>
    </fieldset>
    {error&&<div className="g-error" role="alert"><span>{error}</span></div>}
    <button className="g-button create-submit" disabled={!valid||busy}>{busy?'Creating…':`Create ${info.name}`}</button>
    <p className="create-notice">Race and class names are a nod to World of Warcraft. Not affiliated with or endorsed by Blizzard Entertainment.</p>
   </form>
  </div>
 </div>
}
