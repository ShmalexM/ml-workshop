import {useEffect,useMemo,useRef,useState,type CSSProperties} from 'react'
import {ArrowLeft,ChevronsRight,CircleDot,Crosshair,Heart,Pause,Play,RotateCw,Shield,Sparkles,Swords,Target,TrendingUp,Triangle,Undo2,Zap,Bot,Flag} from 'lucide-react'
import ChestArt from '../ChestArt'
import {appearanceOf} from '../three/hero'
import {webglAvailable} from '../three/scene'
import {classOf,equipped,heroStats} from '../stats'
import {gameApi} from '../gameApi'
import {KITS,type AbilityKind} from './kits'
import {BattleEngine,type BattleEnd,type Hud,type Key} from './engine'
import type {Battle,BattleResult,GameState} from '../types'
import {useBattleGuard} from '../../assistant/store'

const ICON:Record<AbilityKind,typeof Swords>={projectile:Crosshair,nova:CircleDot,ground:Target,dash:ChevronsRight,blink:Sparkles,heal:Heart,shield:Shield,buff:TrendingUp,spin:RotateCw,cone:Triangle,chain:Zap,leap:ChevronsRight,spree:Swords,disengage:Undo2}
type Phase='ready'|'starting'|'fighting'|'saving'|'result'
type Banner={text:string;tone:'info'|'boss'|'danger'|'good';n:number}
const fmt=(s:number)=>`${Math.floor(s/60)}:${String(Math.floor(s%60)).padStart(2,'0')}`

export default function BattleScreen({game,onGame,onExit}:{game:GameState;onGame:(g:GameState)=>void;onExit:()=>void}){
 useBattleGuard() // no assistant drawer or shortcut during a fight
 const hero=game.hero!;const cls=classOf(game)!;const kit=KITS[cls.id]||KITS.warrior
 const gear=useMemo(()=>equipped(game),[game]);const stats=useMemo(()=>heroStats(gear,hero.level),[gear,hero.level])
 const [phase,setPhase]=useState<Phase>('ready');const [battle,setBattle]=useState<Battle|null>(null);const [error,setError]=useState('')
 const [hud,setHud]=useState<Hud|null>(null);const [banner,setBanner]=useState<Banner|null>(null);const [end,setEnd]=useState<BattleEnd|null>(null);const [result,setResult]=useState<BattleResult|null>(null)
 const canvas=useRef<HTMLCanvasElement>(null);const overlay=useRef<HTMLDivElement>(null);const engine=useRef<BattleEngine|null>(null)
 const campaign=game.campaign;const before=useRef({damage:campaign.bossDamage,hp:campaign.bossHp})
 const gl=useMemo(()=>webglAvailable(),[])

 async function begin(){
  setError('');setPhase('starting')
  try{const r=await gameApi.startBattle();onGame(r.game);setBattle(r.battle);before.current={damage:r.battle.bossDamage,hp:r.battle.bossHp};setEnd(null);setResult(null);setHud(null);setPhase('fighting')}
  catch(e){setError((e as Error).message);setPhase('ready')}
 }
 useEffect(()=>{
  if(phase!=='fighting'||!battle||!canvas.current||!overlay.current)return
  const e=new BattleEngine(canvas.current,overlay.current,{appearance:appearanceOf(hero.race,hero.class,cls.role,gear),classColor:cls.color,stats,name:hero.name,stage:battle.stage,stageName:battle.stageName,bossName:battle.bossName,bossHp:battle.bossHp,bossRemaining:battle.bossRemaining,seed:battle.id*7919+battle.stage},{
   hud:setHud,banner:(text,tone)=>setBanner(b=>({text,tone,n:(b?.n||0)+1})),end:r=>setEnd(r)})
  engine.current=e;e.start();canvas.current.focus()
  // Leaving a fight without an ending (another page, reload, closed tab) saves it as a retreat, so its boss damage is kept.
  const save=(left:BattleEnd|null,keepalive=false)=>left?gameApi.finishBattle({battleId:battle.id,outcome:left.outcome,bossDamage:left.bossDamage,kills:left.kills,seconds:left.seconds},{keepalive}):null
  let left=false
  const hide=()=>{const result=e.abandon();if(result){left=true;void save(result,true)?.catch(()=>{})}}
  // A page restored from the back-forward cache shows a fight that was already saved; go back to the armory.
  const show=(ev:PageTransitionEvent)=>{if(ev.persisted&&left){void gameApi.state().then(onGame).catch(()=>{});onExit()}}
  addEventListener('pagehide',hide);addEventListener('pageshow',show)
  return ()=>{removeEventListener('pagehide',hide);removeEventListener('pageshow',show);const result=e.abandon();e.dispose();engine.current=null;void save(result)?.then(r=>onGame(r.game)).catch(()=>{})}
 // The engine is created once per fight.
 // eslint-disable-next-line react-hooks/exhaustive-deps
 },[phase,battle])
 useEffect(()=>{if(!banner)return;const t=setTimeout(()=>setBanner(b=>b?.n===banner.n?null:b),2600);return ()=>clearTimeout(t)},[banner])
 useEffect(()=>{
  if(!end||!battle)return;setPhase('saving')
  gameApi.finishBattle({battleId:battle.id,outcome:end.outcome,bossDamage:end.bossDamage,kills:end.kills,seconds:end.seconds})
   .then(r=>{onGame(r.game);setResult(r.result);setPhase('result')})
   .catch(e=>{setError((e as Error).message);setPhase('result')})
 // eslint-disable-next-line react-hooks/exhaustive-deps
 },[end])

 if(phase==='ready'||phase==='starting'){
  const left=campaign.bossRemaining/campaign.bossHp
  return <div className="g-wrap battle-ready">
   <button className="g-button ghost small back-armory" onClick={onExit}><ArrowLeft size={15}/>Armory</button>
   <section className="ready-card g-panel">
    <span className="g-eyebrow">Stage {campaign.stage}</span>
    <h1>{campaign.stageName}</h1>
    <p className="ready-boss"><strong>{campaign.bossName}</strong> · {campaign.bossRemaining.toLocaleString()} of {campaign.bossHp.toLocaleString()} health left</p>
    <div className="g-bar siege"><span style={{width:`${left*100}%`}}/></div>
    <p>One fight uses one battle. Two waves come first, then the boss. Boss damage carries over between fights. The boss enrages at 2:30, and the fight ends at 4:00.</p>
    <dl className="ready-stats"><div><dt>Level</dt><dd>{hero.level}</dd></div><div><dt>Item level</dt><dd>{stats.itemLevel}</dd></div><div><dt>Health</dt><dd>{stats.maxHp.toLocaleString()}</dd></div><div><dt>Power</dt><dd>{stats.power}</dd></div></dl>
    <div className="ready-kit">{kit.abilities.map(a=>{const Icon=ICON[a.kind];return <div key={a.key} className="kit-row"><span className="kit-key" style={{color:a.color}}><Icon size={16}/>{a.key}</span><div><strong>{a.name}</strong><small>{a.text}</small></div></div>})}</div>
    <p className="ready-controls">Click the ground to move and click an enemy to attack (left or right button). Abilities aim at the cursor. Arrow keys also move. T turns auto-battle on and off. Esc pauses.</p>
    {!gl&&<div className="g-error" role="alert"><span>Battles need WebGL, which this browser has turned off.</span></div>}
    {error&&<div className="g-error" role="alert"><span>{error}</span></div>}
    <div className="ready-actions">
     <button className="g-button" onClick={begin} disabled={phase==='starting'||game.battles.available<1||!gl}><Swords size={17}/>{phase==='starting'?'Starting…':'Start fight'}</button>
     <span>{game.battles.available} {game.battles.available===1?'battle':'battles'} left</span>
    </div>
    {game.battles.available<1&&<p className="ready-none">Finish a lesson, project walkthrough or reading to earn your next battle.</p>}
   </section>
  </div>
 }

 const boss=hud&&hud.bossSeen?hud:null
 return <div className="battle" onContextMenu={e=>e.preventDefault()}>
  <canvas ref={canvas} className="battle-canvas" tabIndex={0} aria-label={`Battle at ${battle?.stageName}`}/>
  <div ref={overlay} className="battle-overlay" aria-hidden/>
  {boss&&<div className={`boss-bar${boss.enraged?' enraged':''}`}><strong>{battle?.bossName}{boss.enraged?' · Enraged':''}</strong><div className="g-bar"><span style={{width:`${boss.bossHp/boss.bossMax*100}%`}}/><i style={{left:`${(before.current.hp-before.current.damage)/before.current.hp*100}%`}}/></div><small>{boss.bossHp.toLocaleString()} / {boss.bossMax.toLocaleString()}</small></div>}
  <div className="battle-top-left"><span>{fmt(hud?.time||0)}</span><span>{hud?.kills||0} kills</span>{hud&&hud.bossDamage>0&&<span>{hud.bossDamage.toLocaleString()} boss damage</span>}</div>
  {banner&&<div key={banner.n} className={`battle-banner tone-${banner.tone}`}>{banner.text}</div>}
  {hud&&<div className="battle-hud">
   <div className="hud-hero">
    <span className="hud-crest" style={{background:cls.color}}>{hero.level}</span>
    <div className="hud-bars"><strong>{hero.name}</strong><div className="hud-hp"><span style={{width:`${hud.hp/hud.maxHp*100}%`}}/>{hud.shield>0&&<i style={{width:`${Math.min(100,hud.shield/hud.maxHp*100)}%`}}/>}<em>{hud.hp.toLocaleString()} / {hud.maxHp.toLocaleString()}</em></div>
     <div className="hud-buffs">{hud.buffs.map((b,i)=><span key={i} style={{borderColor:b.color,color:b.color}}>{b.name} {Math.ceil(b.left)}</span>)}</div></div>
   </div>
   <div className="hud-abilities">{kit.abilities.map(a=>{const Icon=ICON[a.kind];const cd=hud.cds[a.key as Key];const total=a.cd
    // detail is 0 when the button is pressed with the keyboard, so the ability aims at the target instead of the cursor.
    return <button key={a.key} className={`ability${cd>0?' cooling':''}`} title={`${a.name} (${a.key}): ${a.text}`} aria-label={`${a.name} (${a.key})`} onClick={ev=>engine.current?.cast(a.key as Key,ev.detail===0)} style={{'--ab':a.color,'--cd':`${Math.min(1,cd/total)*360}deg`} as CSSProperties}>
     <Icon size={22}/><span className="ab-key">{a.key}</span>{cd>0&&<span className="ab-cd">{Math.ceil(cd)}</span>}</button>})}</div>
   <div className="hud-actions">
    <button className={`g-button ghost small${hud.auto?' on':''}`} onClick={()=>engine.current?.setAuto(!hud.auto)} aria-pressed={hud.auto}><Bot size={15}/>Auto</button>
    <button className="g-button ghost small" onClick={()=>engine.current?.setPaused(!hud.paused)}>{hud.paused?<Play size={15}/>:<Pause size={15}/>}{hud.paused?'Resume':'Pause'}</button>
    <button className="g-button danger small" onClick={()=>engine.current?.retreat()} disabled={phase!=='fighting'}><Flag size={15}/>Retreat</button>
   </div>
  </div>}
  {hud?.paused&&phase==='fighting'&&<div className="battle-pause"><h2>Paused</h2><button className="g-button" onClick={()=>engine.current?.setPaused(false)}><Play size={16}/>Resume</button><button className="g-button danger" onClick={()=>engine.current?.retreat()}><Flag size={16}/>Retreat</button></div>}
  {(phase==='saving'||phase==='result')&&end&&<div className="battle-result">
   <section className={`result-card g-panel outcome-${result?.outcome||end.outcome}`}>
    <span className="g-eyebrow">Stage {battle?.stage} · {battle?.stageName}</span>
    <h1>{(result?.outcome||end.outcome)==='victory'?'Victory':(result?.outcome||end.outcome)==='retreat'?'Retreated':end.timeUp?'Time ran out':'Defeated'}</h1>
    <p>You dealt <strong>{(result?.damage??end.bossDamage).toLocaleString()}</strong> damage to {battle?.bossName} and defeated {end.kills} {end.kills===1?'enemy':'enemies'} in {fmt(end.seconds)}.</p>
    {battle&&<div className="siege-change"><div className="g-bar siege"><span style={{width:`${Math.max(0,(battle.bossRemaining-(result?.damage??end.bossDamage))/battle.bossHp*100)}%`}}/><i style={{left:`${battle.bossRemaining/battle.bossHp*100}%`}}/></div><small>{result?.stageCleared?'Boss defeated':`${Math.max(0,battle.bossRemaining-(result?.damage??end.bossDamage)).toLocaleString()} health left`}</small></div>}
    {result?.stageCleared&&<div className="result-loot">{result.chest&&<ChestArt tier={result.chest.tier} size={84}/>}<div><strong>Stage {battle?.stage} cleared</strong><span>{result.chest?`${result.chest.tierName} is waiting in the armory.`:'The next stage is open.'} Next: {game.campaign.stageName}.</span></div></div>}
    {!result?.stageCleared&&result&&<p className="result-hint">{game.battles.available>0?'Each fight keeps the damage you deal.':'Finish another lesson to earn your next battle.'} Better gear from chests makes the next fight easier.</p>}
    {phase==='saving'&&<p>Saving the result…</p>}
    {error&&<div className="g-error" role="alert"><span>{error}</span></div>}
    <div className="ready-actions">
     {phase==='result'&&game.battles.available>0&&<button className="g-button" onClick={begin}><Swords size={16}/>Fight again ({game.battles.available})</button>}
     <button className="g-button ghost" onClick={onExit} disabled={phase==='saving'}>Back to armory</button>
    </div>
   </section>
  </div>}
 </div>
}
