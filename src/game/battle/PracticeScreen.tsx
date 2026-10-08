import {useEffect,useMemo,useRef,useState} from 'react'
import {ArrowLeft,Bot,Crosshair,LogOut,Network,Pause,Play,RotateCcw,Users} from 'lucide-react'
import {appearanceOf} from '../three/hero'
import {webglAvailable} from '../three/scene'
import {classOf,equipped,heroStats,passiveMods} from '../stats'
import {KITS} from './kits'
import {BattleEngine,type BattleEnd,type Hud} from './engine'
import {HeroHud,KitList,fmt} from './Hud'
import type {GameState} from '../types'
import {useBattleGuard} from '../../assistant/store'

type Phase='ready'|'fighting'|'down'
type Banner={text:string;n:number}

/** Practice arena: a training dummy and optional waves. It costs no battle, earns nothing and saves nothing,
 * so a build can be tried before a real fight. `passives` may be an unsaved tree draft. */
export default function PracticeScreen({game,passives,draft,onExit,onTree}:{game:GameState;passives:string[];draft:boolean;onExit:()=>void;onTree:()=>void}){
 useBattleGuard() // no assistant drawer or shortcut in the arena, as in a real fight
 const hero=game.hero!;const cls=classOf(game)!;const kit=KITS[cls.id]||KITS.warrior
 const gear=useMemo(()=>equipped(game),[game]);const mods=useMemo(()=>passiveMods(game,passives),[game,passives])
 const stats=useMemo(()=>heroStats(gear,hero.level,mods),[gear,hero.level,mods])
 const stages=game.campaign.practice||[]
 const [stage,setStage]=useState(Math.min(game.campaign.stage,stages.length||1))
 const [waves,setWaves]=useState(true)
 const [phase,setPhase]=useState<Phase>('ready');const [run,setRun]=useState(0)
 const [hud,setHud]=useState<Hud|null>(null);const [banner,setBanner]=useState<Banner|null>(null);const [end,setEnd]=useState<BattleEnd|null>(null)
 const canvas=useRef<HTMLCanvasElement>(null);const overlay=useRef<HTMLDivElement>(null);const engine=useRef<BattleEngine|null>(null)
 const gl=useMemo(()=>webglAvailable(),[])
 const strength=stages.find(s=>s.stage===stage)

 useEffect(()=>{
  if(phase==='ready'||!canvas.current||!overlay.current||!strength)return
  const e=new BattleEngine(canvas.current,overlay.current,{appearance:appearanceOf(hero.race,hero.class,cls.role,gear),classColor:cls.color,stats,name:hero.name,
   stage,stageName:'Practice arena',bossName:'Training dummy',bossHp:strength.bossHp,bossRemaining:strength.bossHp,seed:(Date.now()>>>0)^run,
   enemyHealth:strength.enemyHealth,enemyDamage:strength.enemyDamage,practice:true},{
   hud:setHud,banner:text=>setBanner(b=>({text,n:(b?.n||0)+1})),end:r=>{setEnd(r);setPhase('down')}})
  engine.current=e;e.setWaves(waves);e.start();canvas.current.focus()
  return ()=>{e.dispose();engine.current=null}
 // One engine per run. It stays after a defeat so the arena shows behind the result; waves change through setWaves.
 // eslint-disable-next-line react-hooks/exhaustive-deps
 },[phase==='ready',run])
 useEffect(()=>{if(!banner)return;const t=setTimeout(()=>setBanner(b=>b?.n===banner.n?null:b),2200);return ()=>clearTimeout(t)},[banner])
 const begin=()=>{setEnd(null);setHud(null);setRun(n=>n+1);setPhase('fighting')}
 const toggleWaves=()=>{const next=!waves;setWaves(next);engine.current?.setWaves(next)}

 if(phase==='ready')return <div className="g-wrap battle-ready">
  <button className="g-button ghost small back-armory" onClick={onExit}><ArrowLeft size={15}/>Armory</button>
  <section className="ready-card g-panel">
   <span className="g-eyebrow">Practice arena</span>
   <h1>Training grounds</h1>
   <p>Hit a training dummy that never falls, with or without waves of enemies. Practice is free: it uses no battles, earns nothing and saves nothing. The dummy counts as a boss, so boss effects apply to it.</p>
   <dl className="ready-stats"><div><dt>Level</dt><dd>{hero.level}</dd></div><div><dt>Item level</dt><dd>{stats.itemLevel}</dd></div><div><dt>Health</dt><dd>{stats.maxHp.toLocaleString()}</dd></div><div><dt>Power</dt><dd>{stats.power}</dd></div></dl>
   <p className="practice-build">{draft?'Using your unsaved skill tree draft.':'Using your saved skill tree build.'} {passives.length-1} passive {passives.length===2?'point':'points'} spent.</p>
   <div className="practice-options">
    <label>Enemy strength <select value={stage} onChange={e=>setStage(Number(e.target.value))}>{stages.map(s=><option key={s.stage} value={s.stage}>Stage {s.stage} · {s.stageName}</option>)}</select></label>
    <label className="practice-check"><input type="checkbox" checked={waves} onChange={e=>setWaves(e.target.checked)}/>Waves of enemies every 14 sec</label>
   </div>
   <KitList kit={kit}/>
   <p className="ready-controls">Click the ground to move and click an enemy to attack. Q, W, E and R use abilities. T turns auto-battle on and off. Esc pauses.</p>
   {!gl&&<div className="g-error" role="alert"><span>Practice needs WebGL, which this browser has turned off.</span></div>}
   <div className="ready-actions">
    <button className="g-button" onClick={begin} disabled={!gl||!strength}><Crosshair size={17}/>Start practice</button>
    <button className="g-button ghost" onClick={onTree}><Network size={16}/>Skill tree</button>
   </div>
  </section>
 </div>

 const meter=hud?.practice
 return <div className="battle" onContextMenu={e=>e.preventDefault()}>
  <canvas key={run} ref={canvas} className="battle-canvas" tabIndex={0} aria-label="Practice arena"/>
  <div ref={overlay} className="battle-overlay" aria-hidden/>
  <div className="practice-meter" role="status" aria-live="off">
   <strong>Training dummy</strong>
   <div><span><b>{(meter?.dps||0).toLocaleString()}</b> damage per second</span><span><b>{(meter?.damage||0).toLocaleString()}</b> total</span></div>
   <small>Last 10 sec · Stage {stage} enemies{meter?.waves?` · wave ${meter.wave}`:' · waves off'}</small>
  </div>
  <div className="battle-top-left"><span>{fmt(hud?.time||0)}</span><span>{hud?.kills||0} kills</span></div>
  {banner&&<div key={banner.n} className="battle-banner tone-info">{banner.text}</div>}
  {hud&&<HeroHud hero={hero} cls={cls} kit={kit} hud={hud} onCast={(key,keyboard)=>engine.current?.cast(key,keyboard)}>
   <button className={`g-button ghost small${hud.auto?' on':''}`} onClick={()=>engine.current?.setAuto(!hud.auto)} aria-pressed={hud.auto}><Bot size={15}/>Auto</button>
   <button className={`g-button ghost small${meter?.waves?' on':''}`} onClick={toggleWaves} aria-pressed={!!meter?.waves}><Users size={15}/>Waves</button>
   <button className="g-button ghost small" onClick={()=>engine.current?.resetMeter()}><RotateCcw size={15}/>Reset meter</button>
   <button className="g-button ghost small" onClick={()=>engine.current?.setPaused(!hud.paused)}>{hud.paused?<Play size={15}/>:<Pause size={15}/>}{hud.paused?'Resume':'Pause'}</button>
   <button className="g-button ghost small" onClick={()=>setPhase('ready')}><LogOut size={15}/>Leave</button>
  </HeroHud>}
  {hud?.paused&&phase==='fighting'&&<div className="battle-pause"><h2>Paused</h2><button className="g-button" onClick={()=>engine.current?.setPaused(false)}><Play size={16}/>Resume</button><button className="g-button ghost" onClick={()=>setPhase('ready')}><LogOut size={16}/>Leave practice</button></div>}
  {phase==='down'&&<div className="battle-result">
   <section className="result-card g-panel outcome-defeat">
    <span className="g-eyebrow">Practice arena · Stage {stage} enemies</span>
    <h1>You fell</h1>
    <p>You lasted {fmt(end?.seconds||0)}, defeated {end?.kills||0} {end?.kills===1?'enemy':'enemies'} and dealt <strong>{(meter?.damage||0).toLocaleString()}</strong> damage to the dummy. Nothing was saved and no battle was used.</p>
    <div className="ready-actions">
     <button className="g-button" onClick={begin}><RotateCcw size={16}/>Try again</button>
     <button className="g-button ghost" onClick={onTree}><Network size={16}/>Skill tree</button>
     <button className="g-button ghost" onClick={()=>setPhase('ready')}>Change settings</button>
    </div>
   </section>
  </div>}
 </div>
}
