import {lazy,Suspense,useCallback,useEffect,useState} from 'react'
import {LoaderCircle} from 'lucide-react'
import './game.css'
import CreateHero from './CreateHero'
import Armory from './Armory'
import ChestOpening from './ChestOpening'
import {gameApi,summarize} from './gameApi'
import {RARITY_COLOR} from './rarity'
import type {Chest,GameState,GameSummary,Item} from './types'

const BattleScreen=lazy(()=>import('./battle/BattleScreen'))
const subRoute=()=>location.hash.startsWith('#hero/battle')?'battle':'armory'

export default function HeroPage({onSummary}:{onSummary:(s:GameSummary)=>void}){
 const [game,setGame]=useState<GameState|null>(null);const [error,setError]=useState('');const [busy,setBusy]=useState(false)
 const [route,setRoute]=useState(subRoute);const [chest,setChest]=useState<Chest|null>(null);const [flash,setFlash]=useState<{color:string;n:number}|null>(null)
 const apply=useCallback((g:GameState,equippedItem?:Item)=>{setGame(g);onSummary(summarize(g));if(equippedItem)setFlash(f=>({color:RARITY_COLOR[equippedItem.rarity].glow,n:(f?.n||0)+1}))},[onSummary])
 useEffect(()=>{let live=true;gameApi.state().then(g=>{if(live)apply(g)}).catch(e=>{if(live)setError((e as Error).message)});return ()=>{live=false}},[apply])
 useEffect(()=>{const sync=()=>setRoute(subRoute());addEventListener('hashchange',sync);return ()=>removeEventListener('hashchange',sync)},[])
 if(!game)return <main className="game"><div className="g-wrap g-loading">{error?<div className="g-error" role="alert"><span>{error}</span><button onClick={()=>location.reload()}>Reload</button></div>:<><LoaderCircle className="spin" size={26}/><p>Loading…</p></>}</div></main>
 if(!game.enabled)return <main className="game"><div className="g-wrap g-off"><h1>The hero game is off</h1><p>Chests and battles still build up from your progress while it's off. Turn it back on to collect them.</p><button className="g-button" disabled={busy} onClick={async()=>{setBusy(true);try{apply((await gameApi.settings(true)).game)}catch(e){setError((e as Error).message)}finally{setBusy(false)}}}>Turn on</button>{error&&<div className="g-error" role="alert"><span>{error}</span></div>}</div></main>
 if(!game.hero)return <main className="game"><CreateHero game={game} busy={busy} error={error} onCreate={async(name,race,cls)=>{setBusy(true);setError('');try{apply((await gameApi.create(name,race,cls)).game)}catch(e){setError((e as Error).message)}finally{setBusy(false)}}}/></main>
 if(route==='battle')return <main className="game battle-host"><Suspense fallback={<div className="g-wrap g-loading"><LoaderCircle className="spin" size={26}/><p>Loading the battlefield…</p></div>}><BattleScreen game={game} onGame={apply} onExit={()=>{location.hash='hero'}}/></Suspense></main>
 const next=(after?:Chest)=>game.chests.unopened.find(c=>c.source!==after?.source)||null
 return <main className="game">
  <Armory game={game} onGame={apply} flash={flash} onOpenChest={setChest} onFight={()=>{location.hash='hero/battle'}}/>
  {chest&&<ChestOpening key={chest.source} chest={chest} game={game} onGame={apply} nextCount={game.chests.unopened.filter(c=>c.source!==chest.source).length} onNext={()=>setChest(next(chest))} onClose={()=>setChest(null)}/>}
 </main>
}
