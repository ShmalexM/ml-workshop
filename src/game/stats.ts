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

/** Positive when `candidate` would raise item level in its slot (two-handers compare against both hands). */
export function upgradeDelta(candidate:Item,items:Partial<Record<Slot,Item>>){
 const current=items[candidate.slot]
 if(candidate.slot==='mainhand'&&candidate.twoHand&&items.offhand&&!items.mainhand?.twoHand)return candidate.ilvl-Math.round(((items.mainhand?.ilvl||0)+items.offhand.ilvl)/2)
 // An off-hand takes the place of an equipped two-hander, which counts for both hands.
 if(candidate.slot==='offhand'&&items.mainhand?.twoHand)return candidate.ilvl-2*items.mainhand.ilvl
 if(!current)return candidate.ilvl
 return candidate.ilvl-current.ilvl
}
