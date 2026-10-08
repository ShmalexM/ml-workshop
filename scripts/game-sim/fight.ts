// Runs the real battle engine headless, one fight per JSON line on stdin, one result per line on stdout.
import {canvas,clock,overlay,runDue,simulatedTimeout} from './stubs'
import * as readline from 'node:readline'
import {BattleEngine} from '../../src/game/battle/engine'
import {heroStats,sumMods} from '../../src/game/stats'
import {appearanceOf} from '../../src/game/three/hero'

const ROLE:Record<string,'melee'|'ranged'|'caster'>={warrior:'melee',paladin:'melee',deathknight:'melee',hunter:'ranged',shaman:'caster',rogue:'melee',monk:'melee',druid:'caster',demonhunter:'melee',priest:'caster',mage:'caster',warlock:'caster'}

/** `passives` are the allocated tree nodes (only their `mods` are read), summed the way the armory sums them.
 * `scale` multiplies Power and Health, which calibrates what a build is worth in stage-target terms. */
type Request={race?:string;cls:string;level:number;gear:Record<string,any>;stage:number;bossHp:number;bossRemaining:number;seed:number;auto?:boolean;dodge?:boolean;dt?:number;setup?:Record<string,unknown>;trace?:boolean;passives?:{mods:Record<string,number>}[];scale?:number}

export function fight(r:Request){
 const race=r.race||'human';const stats=heroStats(r.gear as any,r.level,sumMods(r.passives||[]))
 if(r.scale){stats.power=Math.round(stats.power*r.scale);stats.maxHp=Math.round(stats.maxHp*r.scale)}
 clock.now=0;clock.queue=[]
 const g=globalThis as any;const realTimeout=g.setTimeout;g.setTimeout=simulatedTimeout
 let end:any=null
 const e:any=new BattleEngine(canvas(),overlay,{appearance:appearanceOf(race,r.cls,ROLE[r.cls],r.gear as any),classColor:'#ffffff',stats,name:'Sim',stage:r.stage,stageName:'Stage',bossName:'Boss',bossHp:r.bossHp,bossRemaining:r.bossRemaining,seed:r.seed,...r.setup},{hud:()=>{},banner:()=>{},end:(x:any)=>{end=x}})
 try{
  const born=new Map<number,number>();const lives:number[]=[];let bossSpawnT=-1
  const makeUnit=e.makeUnit.bind(e);e.makeUnit=(...a:any[])=>{const u=makeUnit(...a);born.set(u.id,e.time);if(u.boss)bossSpawnT=e.time;return u}
  const kill=e.kill.bind(e);e.kill=(u:any)=>{if(!u.dead&&!u.boss&&!e.over)lives.push(e.time-(born.get(u.id)??e.time));kill(u)}
  e.setAuto(r.auto!==false)
  // trace: one line per second and one per cast, for debugging the Auto policy.
  const trace:string[]=[];const at=()=>`${e.time.toFixed(1)}s hp ${Math.round(e.hp)} at ${e.heroPos.x.toFixed(1)},${e.heroPos.z.toFixed(1)}`
  if(r.trace){const cast=e.tryCast.bind(e);e.tryCast=(k:string)=>{const before=e.cds[k];cast(k);if(e.cds[k]>before)trace.push(`${at()} cast ${e.kit.abilities.find((a:any)=>a.key===k).name}`)}}
  let nextTrace=0
  const dt=r.dt??1/60;let steps=0;let deathT=-1;let atDeath=0;let hpMin=1;let stunned=0;let bossAlive=0;let maxBurns=0
  while(!end&&steps<300*60){
   clock.now+=dt;runDue()
   if(r.dodge&&!e.hero.dead)dodge(e)
   e.update(dt);steps++
   if(r.trace&&e.time>=nextTrace){nextTrace+=1;trace.push(`${at()} enemies ${e.units.filter((u:any)=>!u.dead).map((u:any)=>`${u.boss?'B':''}${Math.round(Math.hypot(u.pos.x-e.heroPos.x,u.pos.z-e.heroPos.z))}`).join(' ')} boss ${Math.round(e.bossDamage)}`)}
   hpMin=Math.min(hpMin,e.hp/e.maxHp)
   if(deathT<0&&e.hero.dead){deathT=e.time;atDeath=e.bossDamage}
   const boss=e.boss;if(boss&&!boss.dead&&!e.over){bossAlive+=dt;if(boss.stun>0)stunned+=dt;const own=new Map<string,number>();for(const b of boss.burn)own.set(b.source??'?',(own.get(b.source??'?')||0)+1);maxBurns=Math.max(maxBurns,...own.values(),0)}
  }
  const bossTime=bossSpawnT>=0?(deathT>=0?deathT:e.time)-bossSpawnT:0
  return {outcome:end?.outcome??'defeat',bossDamage:Math.round(e.bossDamage),kills:e.kills,seconds:Math.round(e.time),deathT,bossSpawnT,bossTime,
   bossDps:bossTime>0?Math.round(e.bossDamage/bossTime):0,minionLife:lives.length?lives.reduce((a,b)=>a+b,0)/lives.length:null,hpMin,
   stunnedShare:bossAlive>0?stunned/bossAlive:0,maxBurnsPerSource:maxBurns,damageAfterDeath:deathT>=0?Math.round(e.bossDamage-atDeath):0,
   stats:{maxHp:stats.maxHp,power:stats.power,ilvl:stats.itemLevel,effects:stats.effects},trace:r.trace?trace:undefined}
 }finally{e.dispose();g.setTimeout=realTimeout}
}

/** The "dodge" policy: step out of any boss telegraph the hero stands in, as an attentive player would. */
function dodge(e:any){
 for(const z of e.zones){
  if(z.fromHero)continue
  if(z.line){const b=z.line.boss;const rel=e.heroPos.clone().sub(b.pos);rel.y=0;const along=rel.dot(z.line.dir);const side=rel.clone().sub(z.line.dir.clone().multiplyScalar(along))
   if(along>-1&&along<z.line.length+1&&side.length()<z.line.width/2+1){const out=side.lengthSq()>1e-3?side.normalize():new e.heroPos.constructor(-z.line.dir.z,0,z.line.dir.x);e.moveTo=e.clampArena(e.heroPos.clone().add(out.multiplyScalar(z.line.width/2+1.5)));e.target=null}}
  else{const rel=e.heroPos.clone().sub(z.pos);rel.y=0;if(rel.length()<z.radius+.6){const out=rel.lengthSq()>1e-3?rel.normalize():new e.heroPos.constructor(1,0,0);e.moveTo=e.clampArena(z.pos.clone().add(out.multiplyScalar(z.radius+1.2)));e.target=null}}
 }
}

const lines=readline.createInterface({input:process.stdin})
lines.on('line',line=>{
 if(!line.trim())return
 let out:unknown
 try{out=fight(JSON.parse(line))}catch(err){out={error:String((err as Error).stack||err)}}
 process.stdout.write(JSON.stringify(out)+'\n')
})
