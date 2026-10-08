import type {ClassInfo,GameState,Item,Slot,StatKey} from './types'

export const STAT_KEYS:StatKey[]=['primary','stamina','crit','haste','mastery','versatility','armor','damage']
export const PRIMARY_NAME={str:'Strength',agi:'Agility',int:'Intellect'} as const
export const SECONDARY_NAME:Partial<Record<StatKey,string>>={crit:'Critical Strike',haste:'Haste',mastery:'Mastery',versatility:'Versatility'}

export type HeroStats={
 totals:Record<StatKey,number>;itemLevel:number;level:number
 maxHp:number;power:number;critChance:number;haste:number;mastery:number;versatility:number;damageReduction:number
 effects:string[]
}

/** Rating → percent with diminishing returns, so stacking one stat never breaks the battle game. */
const curve=(rating:number,knee:number,cap:number)=>rating/(rating+knee)*cap

export function equipped(game:GameState):Partial<Record<Slot,Item>>{
 const byId=new Map(game.items.map(item=>[item.id,item]));const result:Partial<Record<Slot,Item>>={}
 for(const [slot,id] of Object.entries(game.equipment)){const item=id===undefined?undefined:byId.get(id);if(item)result[slot as Slot]=item}
 return result
}

export function heroStats(items:Partial<Record<Slot,Item>>,level:number):HeroStats{
 const totals=Object.fromEntries(STAT_KEYS.map(k=>[k,0])) as Record<StatKey,number>
 for(const item of Object.values(items))if(item)for(const k of STAT_KEYS)totals[k]+=item.stats[k]||0
 const main=items.mainhand;const slots=['head','shoulders','back','chest','hands','legs','feet','mainhand','offhand'] as Slot[]
 // Like WoW, a two-hander counts for both hands when averaging item level.
 const levels=slots.map(slot=>slot==='offhand'&&main?.twoHand?main.ilvl:items[slot]?.ilvl||0)
 const offWeapon=items.offhand&&items.offhand.stats.damage>0?items.offhand.stats.damage*.5:0
 const weapon=(main?.stats.damage||0)+offWeapon
 return {
  totals,level,itemLevel:Math.round(levels.reduce((a,b)=>a+b,0)/levels.length),
  maxHp:Math.round(320+level*16+totals.stamina*7),
  power:Math.round(14+level*1.6+totals.primary+weapon*.55),
  critChance:.05+curve(totals.crit,220,.40),
  haste:curve(totals.haste,220,.40),
  mastery:curve(totals.mastery,220,.50),
  versatility:curve(totals.versatility,260,.30),
  // The armor needed for the same reduction grows with level, so plate stays ahead of cloth without making plate wearers untouchable.
  damageReduction:Math.min(.7,totals.armor/(totals.armor+400+30*level)),
  effects:Object.values(items).flatMap(item=>item?.effect?[item.effect.id]:[]),
 }
}

export function classOf(game:GameState):ClassInfo|undefined{return game.catalog.classes.find(c=>c.id===game.hero?.class)}

/** Equipped items that equipping `candidate` takes off the other hand; the item comparison does not show them. */
export function displaced(candidate:Item,items:Partial<Record<Slot,Item>>):Item[]{
 if(candidate.slot==='offhand'&&items.mainhand?.twoHand)return [items.mainhand]
 if(candidate.slot==='mainhand'&&candidate.twoHand&&items.offhand)return [items.offhand]
 return []
}

/** The equipment after putting on `candidate`: it takes its slot, and a two-hander also frees the off hand. */
export function withItem(candidate:Item,items:Partial<Record<Slot,Item>>):Partial<Record<Slot,Item>>{
 const next={...items}
 if(candidate.slot==='mainhand'&&candidate.twoHand)delete next.offhand
 if(candidate.slot==='offhand'&&items.mainhand?.twoHand)delete next.mainhand
 next[candidate.slot]=candidate
 return next
}

export type Gain={power:number;health:number;armor:number;score:number;lostEffects:Item[]}
/** What equipping `candidate` changes. `score` weighs Power and Health by their share of the hero's
 * current values; above 0 counts as an upgrade. `lostEffects` are equipped Legendaries it would replace. */
export function upgradeGain(candidate:Item,items:Partial<Record<Slot,Item>>,level:number):Gain{
 const next=withItem(candidate,items);const before=heroStats(items,level);const after=heroStats(next,level)
 const power=after.power-before.power;const health=after.maxHp-before.maxHp
 const lostEffects=Object.values(items).filter((item):item is Item=>!!item?.effect&&item.id!==candidate.id&&!Object.values(next).includes(item))
 return {power,health,armor:after.totals.armor-before.totals.armor,score:power/Math.max(1,before.power)+health/Math.max(1,before.maxHp),lostEffects}
}
export const isUpgrade=(gain:Gain)=>gain.score>0.0005
const signed=(n:number)=>`${n>=0?'+':'−'}${Math.abs(n).toLocaleString()}`
/** "+12 Power / +80 Health" */
export const gainText=(gain:Gain)=>`${signed(gain.power)} Power / ${signed(gain.health)} Health`

/** The best upgrade for each slot, picked one at a time so two-handers and off-hands are weighed against what is worn by then.
 * Slots holding a Legendary effect are left alone. */
export function bestUpgrades(bag:Item[],items:Partial<Record<Slot,Item>>,level:number){
 let worn={...items};const picks:{item:Item;gain:Gain}[]=[];const used=new Set<number>()
 for(let round=0;round<9;round++){
  let best:{item:Item;gain:Gain}|null=null
  for(const item of bag){if(used.has(item.id))continue;const gain=upgradeGain(item,worn,level);if(!isUpgrade(gain)||gain.lostEffects.length)continue;if(!best||gain.score>best.gain.score)best={item,gain}}
  if(!best)break
  picks.push(best);used.add(best.item.id);worn=withItem(best.item,worn)
 }
 return {picks,worn}
}

/** Short help for the stat sheet. */
export const STAT_HELP:Record<string,string>={
 itemLevel:'The average item level of your gear. Harder lessons give chests with higher item levels.',
 health:'Damage you can take before you fall. Comes from your level and Stamina.',
 power:'The base damage of your attacks and abilities. Comes from your level, your main stat and weapon damage.',
 primary:'Each point adds 1 Power.',
 stamina:'Each point adds 7 Health.',
 crit:'The chance that a hit deals double damage.',
 haste:'You attack faster, and ability cooldowns recover a little faster.',
 mastery:'Your Q, W, E and R abilities deal more damage.',
 versatility:'Raises your damage by this much and lowers the damage you take by half as much.',
 armor:'You take less damage. As you level up, the same armor blocks a little less.',
}
