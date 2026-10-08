import {lazy,Suspense,useCallback,useEffect,useRef,useState,type RefObject} from 'react'
import {LoaderCircle} from 'lucide-react'
import './game.css'
import CreateHero from './CreateHero'
import Armory from './Armory'
import ChestOpening from './ChestOpening'
import ChestSummary from './ChestSummary'
import SkillTree from './tree/SkillTree'
import {gameApi,summarize} from './gameApi'
import {RARITY_COLOR} from './rarity'
import type {Chest,GameState,GameSummary,Item} from './types'

const BattleScreen=lazy(()=>import('./battle/BattleScreen'))
const PracticeScreen=lazy(()=>import('./battle/PracticeScreen'))
type Route='armory'|'battle'|'tree'|'practice'
const subRoute=():Route=>{const part=location.hash.slice(1).split(/[/?]/)[1];return part==='battle'||part==='tree'||part==='practice'?part:'armory'}
const go=(route:Route)=>{location.hash=route==='armory'?'hero':'hero/'+route}
/** Move keyboard focus to the screen's heading, or to the first match of `selector`. Lazy screens render it a little later. */
function focusIn(main:RefObject<HTMLElement|null>,selector='h1'){let tries=0;const attempt=()=>{const target=main.current?.querySelector<HTMLElement>(selector)||main.current?.querySelector<HTMLElement>('h1');if(target){if(target.tagName==='H1')target.tabIndex=-1;target.focus({preventScroll:true});return}if(++tries<120)requestAnimationFrame(attempt)};requestAnimationFrame(attempt)}

export default function HeroPage({onSummary}:{onSummary:(s:GameSummary)=>void}){
 const [game,setGame]=useState<GameState|null>(null);const [error,setError]=useState('');const [busy,setBusy]=useState(false)
 const [route,setRoute]=useState(subRoute);const [chest,setChest]=useState<Chest|null>(null);const [flash,setFlash]=useState<{color:string;n:number}|null>(null)
 const [summary,setSummary]=useState<{chests:number;items:Item[]}|null>(null);const main=useRef<HTMLElement>(null)
 // An unsaved skill tree draft survives a trip to the practice arena and back.
 const [draft,setDraft]=useState<string[]|null>(null)
 const savedTree=game?.passives?.allocated.join(',');const heroKey=game?.hero?.createdAt
 useEffect(()=>{setDraft(null)},[savedTree,heroKey])
 const apply=useCallback((g:GameState,equippedItem?:Item)=>{setGame(g);onSummary(summarize(g));if(equippedItem)setFlash(f=>({color:RARITY_COLOR[equippedItem.rarity].glow,n:(f?.n||0)+1}))},[onSummary])
 useEffect(()=>{let live=true;gameApi.state().then(g=>{if(live)apply(g)}).catch(e=>{if(live)setError((e as Error).message)});return ()=>{live=false}},[apply])
 useEffect(()=>{const sync=()=>setRoute(subRoute());addEventListener('hashchange',sync);return ()=>removeEventListener('hashchange',sync)},[])
 // A new screen (Skill tree, Practice, Fight, back to the armory, or the armory after Create hero) takes focus to its heading.
 const screen=!game?'':!game.enabled?'off':!game.hero?'create':route;const shownScreen=useRef('')
 useEffect(()=>{const before=shownScreen.current;shownScreen.current=screen;if(before&&screen&&before!==screen)focusIn(main)},[screen])
 // A closed chest dialog leaves focus on the next action: more chests, or Fight.
 const closeDialog=()=>{setChest(null);setSummary(null);focusIn(main,'.hero-actions .g-button:not(:disabled)')}
 async function openAll(){const r=await gameApi.openAll();apply(r.game);setChest(null);setSummary({chests:r.opened.length,items:r.opened.flatMap(o=>o.items)})}
 if(!game)return <main ref={main} className="game"><div className="g-wrap g-loading">{error?<div className="g-error" role="alert"><span>{error}</span><button onClick={()=>location.reload()}>Reload</button></div>:<><LoaderCircle className="spin" size={26}/><p>Loading…</p></>}</div></main>
 if(!game.enabled)return <main ref={main} className="game"><div className="g-wrap g-off"><h1>The hero game is off</h1><p>Chests and battles still build up from your progress while it's off. Turn it back on to collect them.</p><button className="g-button" disabled={busy} onClick={async()=>{setBusy(true);try{apply((await gameApi.settings(true)).game)}catch(e){setError((e as Error).message)}finally{setBusy(false)}}}>Turn on</button>{error&&<div className="g-error" role="alert"><span>{error}</span></div>}</div></main>
 if(!game.hero)return <main ref={main} className="game"><CreateHero game={game} busy={busy} error={error} onCreate={async(name,race,cls)=>{setBusy(true);setError('');try{apply((await gameApi.create(name,race,cls)).game)}catch(e){setError((e as Error).message)}finally{setBusy(false)}}}/></main>
 if(route==='battle')return <main ref={main} className="game battle-host"><Suspense fallback={<div className="g-wrap g-loading"><LoaderCircle className="spin" size={26}/><p>Loading the battlefield…</p></div>}><BattleScreen game={game} onGame={apply} onExit={()=>go('armory')}/></Suspense></main>
 if(route==='tree'&&game.passives)return <main ref={main} className="game"><SkillTree game={game} onGame={apply} draft={draft} onDraft={setDraft} onBack={()=>go('armory')} onPractice={()=>go('practice')}/></main>
 if(route==='practice'&&game.passives)return <main ref={main} className="game battle-host"><Suspense fallback={<div className="g-wrap g-loading"><LoaderCircle className="spin" size={26}/><p>Loading the practice arena…</p></div>}><PracticeScreen game={game} passives={draft??game.passives.allocated} draft={!!draft} onExit={()=>go('armory')} onTree={()=>go('tree')}/></Suspense></main>
 const next=(after?:Chest)=>game.chests.unopened.find(c=>c.source!==after?.source)||null
 return <main ref={main} className="game">
  <Armory game={game} onGame={apply} flash={flash} onOpenChest={setChest} onOpenAll={openAll} onFight={()=>go('battle')} onTree={()=>go('tree')} onPractice={()=>go('practice')}/>
  {chest&&<ChestOpening key={chest.source} chest={chest} game={game} onGame={apply} nextCount={game.chests.unopened.filter(c=>c.source!==chest.source).length} onNext={()=>setChest(next(chest))} onOpenAll={openAll} onClose={closeDialog}/>}
  {summary&&<ChestSummary chests={summary.chests} items={summary.items} game={game} onGame={apply} onClose={closeDialog}/>}
 </main>
}
