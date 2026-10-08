import {useEffect,useMemo,useRef,useState} from 'react'
import {Crosshair,Gift,Network,Swords,Trash2} from 'lucide-react'
import HeroViewer from './HeroViewer'
import ItemIcon,{lookOf} from './ItemIcon'
import ItemTooltip,{FloatingTip} from './ItemTooltip'
import ChestArt from './ChestArt'
import {appearanceOf} from './three/hero'
import {RARITY_INDEX,SLOT_NAME} from './rarity'
import {PRIMARY_NAME,STAT_HELP,bestUpgrades,classOf,displaced,equipped,gainText,heroStats,isUpgrade,passiveMods,upgradeGain} from './stats'
import {gameApi} from './gameApi'
import type {Chest,GameState,Item,Slot} from './types'

const LEFT:Slot[]=['head','shoulders','back','chest'];const RIGHT:Slot[]=['hands','legs','feet'];const BOTTOM:Slot[]=['mainhand','offhand']
type Tab='chests'|'bags'|'campaign'|'stats'
const pct=(n:number)=>`${(n*100).toFixed(1)}%`
// The server takes up to 200 items per discard.
const DISCARD_BATCH=200

export default function Armory({game,onGame,onOpenChest,onFight,onTree,onPractice,flash}:{game:GameState;onGame:(g:GameState,flash?:Item)=>void;onOpenChest:(c:Chest)=>void;onFight:()=>void;onTree:()=>void;onPractice:()=>void;flash:{color:string;n:number}|null}){
 const hero=game.hero!;const cls=classOf(game)!;const race=game.catalog.races.find(r=>r.id===hero.race)
 const gear=useMemo(()=>equipped(game),[game]);const mods=useMemo(()=>passiveMods(game),[game]);const stats=useMemo(()=>heroStats(gear,hero.level,mods),[gear,hero.level,mods])
 const look=useMemo(()=>appearanceOf(hero.race,hero.class,cls.role,gear),[hero.race,hero.class,cls.role,gear])
 const [tab,setTab]=useState<Tab>(game.chests.unopened.length?'chests':'bags')
 const [selected,setSelected]=useState<Item|null>(null);const [hover,setHover]=useState<{item:Item;x:number;y:number}|null>(null)
 const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [sort,setSort]=useState<'new'|'ilvl'|'rarity'>('new')
 // Confirm steps: replacing a Legendary effect, the two bulk actions, and fighting with chests still closed.
 const [replacing,setReplacing]=useState<Item|null>(null);const [bulk,setBulk]=useState<'equip'|'discard'|null>(null);const [fightAsk,setFightAsk]=useState(false)
 // Selecting an item moves focus to its first action; closing the panel returns focus to the item.
 const firstAction=useRef<HTMLButtonElement>(null);const opener=useRef<HTMLElement|null>(null)
 useEffect(()=>{if(selected)firstAction.current?.focus()},[selected])
 const select=(item:Item,from:HTMLElement)=>{opener.current=from;setReplacing(null);setSelected(item)}
 const closeDetail=()=>{setSelected(null);setReplacing(null);if(opener.current?.isConnected)opener.current.focus()}
 const bags=useMemo(()=>game.items.filter(i=>!i.equipped),[game.items])
 const gains=useMemo(()=>new Map(bags.map(item=>[item.id,upgradeGain(item,gear,hero.level,mods)])),[bags,gear,hero.level,mods])
 const plan=useMemo(()=>bestUpgrades(bags,gear,hero.level,mods),[bags,gear,hero.level,mods])
 const planGain=useMemo(()=>{const a=heroStats(gear,hero.level,mods),b=heroStats(plan.worn,hero.level,mods);return {power:b.power-a.power,health:b.maxHp-a.maxHp,armor:0,score:1,lostEffects:[]}},[gear,plan,hero.level,mods])
 const junk=useMemo(()=>bags.filter(item=>!item.effect&&!isUpgrade(gains.get(item.id)!)),[bags,gains])
 const unopened=game.chests.unopened
 const points=game.passives?.points.available||0
 const treePicks=useMemo(()=>{const byId=new Map(game.catalog.tree.nodes.map(n=>[n.id,n]));return (game.passives?.allocated||[]).map(id=>byId.get(id)).filter(n=>n&&(n.kind==='notable'||n.kind==='keystone')).map(n=>n!.name)},[game])
 const sorted=[...bags].sort((a,b)=>sort==='ilvl'?b.ilvl-a.ilvl:sort==='rarity'?RARITY_INDEX[b.rarity]-RARITY_INDEX[a.rarity]||b.ilvl-a.ilvl:b.id-a.id)
 const c=game.campaign;const siege=c.bossHp?c.bossDamage/c.bossHp:0
 async function act(fn:()=>Promise<{game:GameState}>,flashItem?:Item){
  if(busy)return;setBusy(true);setError('')
  try{const r=await fn();onGame(r.game,flashItem);closeDetail();setBulk(null)}catch(e){setError((e as Error).message)}finally{setBusy(false)}
 }
 /** Equip at once, unless it would take off a Legendary effect: then ask first. */
 function equip(item:Item,from?:HTMLElement){
  if(upgradeGain(item,gear,hero.level,mods).lostEffects.length){if(from)opener.current=from;setSelected(item);setReplacing(item);return}
  void act(()=>gameApi.equip(item.id),item)
 }
 async function discardJunk(){
  const ids=junk.map(i=>i.id)
  await act(async()=>{let last:{game:GameState}|null=null;for(let i=0;i<ids.length;i+=DISCARD_BATCH)last=await gameApi.discard(ids.slice(i,i+DISCARD_BATCH));return last!})
 }
 const slotCell=(slot:Slot)=>{const item=gear[slot];const blocked=slot==='offhand'&&gear.mainhand?.twoHand
  return <button key={slot} className={`doll-slot${selected?.id===item?.id&&item?' active':''}`} onClick={e=>item&&select(item,e.currentTarget)} onMouseEnter={e=>item&&setHover({item,x:e.clientX,y:e.clientY})} onMouseMove={e=>item&&setHover({item,x:e.clientX,y:e.clientY})} onMouseLeave={()=>setHover(null)} aria-label={item?`${SLOT_NAME[slot]}: ${item.name}`:`${SLOT_NAME[slot]}: empty`}>
   <ItemIcon look={item?lookOf(item):blocked&&gear.mainhand?lookOf(gear.mainhand):null} empty={slot} dim={!!blocked} size={50}/>
   <span className="doll-text"><small>{SLOT_NAME[slot]}</small>{item?<strong className={`rt-${item.rarity}`}>{item.name}</strong>:<em>{blocked?'Two-hander equipped':'Empty'}</em>}</span>
  </button>}
 return <div className="g-wrap armory">
  <header className="hero-bar">
   <div className="hero-id"><span className="class-crest" style={{background:cls.color}} aria-hidden/><div><h1>{hero.name}</h1><p>Level {hero.level} {race?.name} <span style={{color:cls.color}}>{cls.name}</span> · Item level {stats.itemLevel}</p><div className="g-bar xp" title={`${Math.round(hero.levelProgress*100)}% to level ${hero.level+1}`}><span style={{width:`${hero.level>=60?100:hero.levelProgress*100}%`}}/></div></div></div>
   <div className="hero-siege"><span className="g-eyebrow">Stage {c.stage} · {c.stageName}</span><strong>{c.bossName}</strong><div className="g-bar" aria-label={`Boss health ${Math.round((1-siege)*100)}% remaining`}><span style={{width:`${(1-siege)*100}%`}}/></div><small>{c.bossRemaining.toLocaleString()} / {c.bossHp.toLocaleString()} health left</small></div>
   <div className="hero-actions">
    {unopened.length>0&&<button className="g-button fight-button" onClick={()=>onOpenChest(unopened[0])}><Gift size={17}/>Open chests ({unopened.length})</button>}
    <button className={`g-button fight-button${unopened.length?' ghost':''}`} onClick={()=>unopened.length?setFightAsk(true):onFight()} disabled={game.battles.available<1} title={game.battles.available<1?'Finish a lesson, project walkthrough or reading to earn a battle.':undefined}><Swords size={17}/>Fight{game.battles.available>0?` (${game.battles.available})`:''}</button>
    <button className={`g-button fight-button${points>0?'':' ghost'}`} onClick={onTree} title={points>0?`${points} passive ${points===1?'point':'points'} to spend`:'Passive skill tree'}><Network size={17}/>Skill tree{points>0?` (${points})`:''}</button>
    <button className="g-button ghost fight-button" onClick={onPractice} title="Test your build against a training dummy. Free, and saves nothing."><Crosshair size={17}/>Practice</button>
   </div>
  </header>
  {fightAsk&&unopened.length>0&&<div className="g-confirm" role="alertdialog" aria-label="Open chests before fighting">
   <p>You have {unopened.length} unopened {unopened.length===1?'chest':'chests'}. Open {unopened.length===1?'it':'them'} first: new gear can make this fight easier.</p>
   <div><button className="g-button small" onClick={()=>{setFightAsk(false);onOpenChest(unopened[0])}}><Gift size={14}/>Open chests</button><button className="g-button ghost small" onClick={()=>{setFightAsk(false);onFight()}}>Fight anyway</button></div>
  </div>}
  {error&&<div className="g-error" role="alert"><span>{error}</span><button onClick={()=>setError('')}>Dismiss</button></div>}
  <div className="armory-grid">
   <section className="doll g-panel" aria-label="Equipped gear">
    <div className="doll-col">{LEFT.map(slotCell)}</div>
    <div className="doll-center"><HeroViewer look={look} accent={cls.color} flash={flash} label={`${hero.name}, ${race?.name} ${cls.name}, wearing ${Object.values(gear).filter(Boolean).length} items`}/></div>
    <div className="doll-col">{RIGHT.map(slotCell)}<div className="doll-weapons">{BOTTOM.map(slotCell)}</div></div>
   </section>
   <section className="side g-panel">
    <div className="side-tabs" role="tablist" aria-label="Armory">
     {([['chests',`Chests${game.chests.unopened.length?` (${game.chests.unopened.length})`:''}`],['bags',`Bags (${bags.length})`],['campaign','Campaign'],['stats','Stats']] as [Tab,string][]).map(([id,text])=><button key={id} role="tab" aria-selected={tab===id} className={tab===id?'active':''} onClick={()=>setTab(id)}>{text}</button>)}
    </div>
    {tab==='chests'&&<div className="chest-list">
     {game.chests.unopened.length===0?<div className="g-empty"><ChestArt tier={1} size={70}/><p>No chests waiting. Finish a lesson to earn the next one. Harder lessons give better chests. A lesson passed after Show solution gives a chest one tier lower.</p></div>
     :game.chests.unopened.map(chest=><button key={chest.source} className="chest-row" onClick={()=>onOpenChest(chest)}>
      <ChestArt tier={chest.tier} size={58}/>
      <span><strong className={`tier-title tier-${chest.tier}`}>{chest.tierName}</strong><small>{chest.title}{chest.subtitle?` · ${chest.subtitle}`:''}</small></span>
      <span className="chest-open-tag">Open</span>
     </button>)}
     {game.chests.opened.length>0&&<details className="opened-history"><summary>Opened ({game.chests.opened.length})</summary>{game.chests.opened.map(ch=><div key={ch.source}><span className={`tier-title tier-${ch.tier}`}>{ch.tierName}</span> <small>{ch.title}</small></div>)}</details>}
    </div>}
    {tab==='bags'&&<div className="bags">
     <div className="bags-tools"><label>Sort <select value={sort} onChange={e=>setSort(e.target.value as typeof sort)}><option value="new">Newest</option><option value="ilvl">Item level</option><option value="rarity">Rarity</option></select></label>{bags.length>0&&<small>Select an item to equip or discard it. ▲ marks an upgrade.</small>}</div>
     {bags.length>0&&<div className="bulk-actions">
      <button className="g-button small" disabled={busy||!plan.picks.length} onClick={()=>setBulk('equip')}>Equip all upgrades ({plan.picks.length})</button>
      <button className="g-button ghost small" disabled={busy||!junk.length} onClick={()=>setBulk('discard')}><Trash2 size={14}/>Discard all non-upgrades ({junk.length})</button>
     </div>}
     {bulk==='equip'&&plan.picks.length>0&&<div className="g-confirm" role="alertdialog" aria-label="Confirm equip all upgrades">
      <p>Equip {plan.picks.length} {plan.picks.length===1?'upgrade':'upgrades'}? Together: {gainText(planGain)}.</p>
      <ul>{plan.picks.map(({item,gain})=><li key={item.id}><span>{SLOT_NAME[item.slot]}</span> <span className={`rt-${item.rarity}`}>{item.name}</span> <em>{gainText(gain)}</em></li>)}</ul>
      {Object.values(gear).some(i=>i?.effect)&&<small>Gear with a Legendary effect stays on.</small>}
      <div><button className="g-button small" disabled={busy} onClick={()=>act(()=>gameApi.equipMany(plan.picks.map(p=>p.item.id)),plan.picks[0].item)}>Equip {plan.picks.length}</button><button className="g-button ghost small" onClick={()=>setBulk(null)}>Cancel</button></div>
     </div>}
     {bulk==='discard'&&junk.length>0&&<div className="g-confirm" role="alertdialog" aria-label="Confirm discard all non-upgrades">
      <p>Discard {junk.length} {junk.length===1?'item that is':'items that are'} not an upgrade for your hero? Items with a Legendary effect stay. This can't be undone.</p>
      <div><button className="g-button danger small" disabled={busy} onClick={discardJunk}><Trash2 size={14}/>Discard {junk.length}</button><button className="g-button ghost small" onClick={()=>setBulk(null)}>Cancel</button></div>
     </div>}
     {bags.length===0?<p className="g-empty">Your bags are empty. Items you take off or don't equip land here.</p>:<div className="bag-grid">{sorted.map(item=>{const gain=gains.get(item.id)!;const up=isUpgrade(gain)
      return <button key={item.id} className={`bag-cell${selected?.id===item.id?' active':''}`} onClick={e=>select(item,e.currentTarget)} onDoubleClick={e=>equip(item,e.currentTarget)} onMouseEnter={e=>setHover({item,x:e.clientX,y:e.clientY})} onMouseMove={e=>setHover({item,x:e.clientX,y:e.clientY})} onMouseLeave={()=>setHover(null)} aria-label={`${item.name}, item level ${item.ilvl}${up?`, upgrade: ${gainText(gain)}`:''}`}>
       <ItemIcon look={lookOf(item)} size={54}/>{up&&<span className="bag-up" title={gainText(gain)} aria-hidden>▲</span>}
      </button>})}</div>}
    </div>}
    {tab==='campaign'&&<div className="campaign">
     <p>Every finished task gives you one fight. Boss damage carries over between fights.</p>
     <ol className="stage-list">{c.stages.map(st=><li key={st.stage} className={st.stage<c.stage?'done':st.stage===c.stage?'current':''}><span>{st.stage}</span><div><strong>{st.name}</strong><small>{st.boss}</small></div>{st.stage===c.stage&&<em>{Math.round(siege*100)}%</em>}</li>)}
      {c.stage>10&&<li className="current"><span>{c.stage}</span><div><strong>{c.stageName}</strong><small>{c.bossName}</small></div><em>{Math.round(siege*100)}%</em></li>}</ol>
     <div className="lifetime"><span><strong>{game.lifetime.fights}</strong>fights</span><span><strong>{game.lifetime.victories}</strong>bosses slain</span><span><strong>{game.lifetime.kills}</strong>kills</span><span><strong>{game.lifetime.bestDamage.toLocaleString()}</strong>best boss damage</span></div>
     {game.history.length>0&&<details className="opened-history"><summary>Recent fights</summary>{game.history.map(h=><div key={h.id}><span className={h.outcome==='victory'?'rt-legendary':''}>{h.outcome==='victory'?'Victory':h.outcome==='retreat'?'Retreated':h.outcome==='abandoned'?'Abandoned':'Defeat'}</span> <small>Stage {h.stage} · {h.damage.toLocaleString()} damage · {h.kills} kills · {h.seconds}s</small></div>)}</details>}
    </div>}
    {tab==='stats'&&<dl className="stat-sheet">
     {([['Item level',stats.itemLevel,'itemLevel'],['Health',stats.maxHp.toLocaleString(),'health'],['Power',stats.power,'power'],[PRIMARY_NAME[cls.primary],stats.totals.primary,'primary'],['Stamina',stats.totals.stamina,'stamina'],['Critical strike',pct(stats.critChance),'crit'],['Haste',pct(stats.haste),'haste'],['Mastery',pct(stats.mastery),'mastery'],['Versatility',pct(stats.versatility),'versatility'],['Armor',`${stats.totals.armor} (${pct(stats.damageReduction)} less damage)`,'armor']] as [string,string|number,string][]).map(([k,v,help])=><div key={k}><dt>{k}<small>{STAT_HELP[help]}</small></dt><dd>{v}</dd></div>)}
     {Object.values(gear).filter(i=>i?.effect).map(i=><div key={i!.id} className="stat-effect"><dt className="rt-legendary">{i!.effect!.name}</dt><dd>{i!.effect!.text}</dd></div>)}
     {game.passives&&<div className="stat-effect"><dt>Skill tree<small>{game.passives.points.spent} of {game.passives.points.earned} passive points spent. The numbers above include them.</small></dt>
      <dd>{treePicks.length?treePicks.join(', '):'No notables or keystones yet.'} <button className="g-button ghost small" onClick={onTree}>Open skill tree</button></dd></div>}
    </dl>}
   </section>
  </div>
  {selected&&<div className="item-detail g-panel" role="region" aria-label="Selected item">
   <ItemTooltip item={selected} compare={selected.equipped?null:gear[selected.slot]} gain={selected.equipped?null:upgradeGain(selected,gear,hero.level,mods)} source={sourceText(selected,game)}/>
   {replacing?.id===selected.id&&<div className="g-confirm inline" role="alertdialog" aria-label="Replace a Legendary effect">
    <p>Equipping this takes off {upgradeGain(selected,gear,hero.level,mods).lostEffects.map(i=>`${i.name} and its ${i.effect!.name} effect`).join(', ')}.</p>
    <div><button className="g-button small" disabled={busy} onClick={()=>act(()=>gameApi.equip(selected.id),selected)}>Replace</button><button className="g-button ghost small" onClick={()=>setReplacing(null)}>Keep it</button></div>
   </div>}
   <div className="item-actions">
    {selected.equipped?<button ref={firstAction} className="g-button ghost small" disabled={busy} onClick={()=>act(()=>gameApi.unequip(selected.slot))}>Unequip</button>
    :<><button ref={firstAction} className="g-button small" disabled={busy} onClick={()=>equip(selected)}>Equip</button>
     {displaced(selected,gear).map(other=><small key={other.id} className="item-replaces">{selected.slot==='offhand'?'Replaces':'Also takes off'} <span className={`rt-${other.rarity}`}>{other.name}</span></small>)}
     <button className="g-button danger small" disabled={busy} onClick={()=>{if(confirm(`Discard ${selected.name}? This can't be undone.`))act(()=>gameApi.discard([selected.id]))}}><Trash2 size={14}/>Discard</button></>}
    <button className="g-button ghost small" onClick={closeDetail}>Close</button>
   </div>
  </div>}
  {hover&&!selected&&<FloatingTip x={hover.x} y={hover.y}><ItemTooltip item={hover.item} compare={hover.item.equipped?null:gear[hover.item.slot]} gain={hover.item.equipped?null:gains.get(hover.item.id)}/></FloatingTip>}
  {flash&&<span className="sr-only" aria-live="polite">Equipped</span>}
 </div>
}

function sourceText(item:Item,game:GameState){
 const chest=[...game.chests.opened].find(c=>c.source===item.source)
 if(item.source==='starter')return 'Starter gear'
 return chest?`From ${chest.tierName} · ${chest.title}`:undefined
}
