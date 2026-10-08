import type {Rarity,Slot} from './types'

export const RARITIES:Rarity[]=['basic','common','rare','epic','legendary']
export const RARITY_INDEX:Record<Rarity,number>={basic:0,common:1,rare:2,epic:3,legendary:4}
export const RARITY_NAME:Record<Rarity,string>={basic:'Basic',common:'Common',rare:'Rare',epic:'Epic',legendary:'Legendary'}
/** Text colors tuned for the dark game theme; `glow` drives borders, beams and emissive light. */
export const RARITY_COLOR:Record<Rarity,{text:string;glow:string;deep:string}>={
 basic:{text:'#f1f1f1',glow:'#d9dde3',deep:'#5b6170'},
 common:{text:'#3ee03e',glow:'#1eff00',deep:'#1d5c1d'},
 rare:{text:'#4ea7ff',glow:'#2f8cff',deep:'#123d78'},
 epic:{text:'#c77dff',glow:'#a64df0',deep:'#3d1466'},
 legendary:{text:'#ffa233',glow:'#ff8a00',deep:'#7a3600'},
}

export const SLOT_NAME:Record<Slot,string>={head:'Head',shoulders:'Shoulders',back:'Back',chest:'Chest',hands:'Hands',legs:'Legs',feet:'Feet',mainhand:'Main Hand',offhand:'Off Hand'}
export const BASE_NAME:Record<string,string>={cloth:'Cloth',leather:'Leather',mail:'Mail',plate:'Plate',cloak:'Cloak',sword:'Sword',greatsword:'Greatsword',axe:'Axe',greataxe:'Greataxe',mace:'Mace',warhammer:'Warhammer',dagger:'Dagger',fist:'Fist Weapon',warglaive:'Warglaive',polearm:'Polearm',staff:'Staff',wand:'Wand',bow:'Bow',crossbow:'Crossbow',gun:'Gun',shield:'Shield',tome:'Held In Off-hand',orb:'Held In Off-hand'}

/** Deterministic PRNG so an item always looks the same everywhere it is drawn. */
export function seeded(seed:number){let s=(seed>>>0)||1;return ()=>{s^=s<<13;s^=s>>>17;s^=s<<5;return (s>>>0)/4294967296}}

export type Palette={metal:string;metalDark:string;metalLight:string;trim:string;gem:string;glow:string;fabric:string;fabricDark:string;leather:string;wood:string;emissive:number}

const FABRICS:Record<Rarity,string[]>={
 basic:['#8b7d6b','#7d7468','#6f6a62'],
 common:['#4d6a8a','#5d7a4a','#7a4a46','#6a5a8a','#7a6a46'],
 rare:['#2f4f9f','#4b2f8f','#1f5f74','#6b1f3f','#2d5d3d'],
 epic:['#2a1238','#1f0f2e','#1b1022','#301440'],
 legendary:['#f1e3bd','#3b1d5e','#5e1a12','#13233f'],
}
const LEATHERS:Record<Rarity,string>={basic:'#6b4a2f',common:'#7b5534',rare:'#4a3326',epic:'#26172e',legendary:'#5a3416'}

/** Materials get better with rarity: dull iron → steel → polished silver → dreadsteel with runes → radiant gold. */
export function palette(rarity:Rarity,seed:number):Palette{
 const rand=seeded(seed);const fabrics=FABRICS[rarity];const fabric=fabrics[Math.floor(rand()*fabrics.length)]
 const base={
  basic:{metal:'#7f848b',metalDark:'#4f535a',metalLight:'#a7abb1',trim:'#6b4a2f',gem:'#9aa0a6',glow:'#d9dde3',emissive:0},
  common:{metal:'#aab3bd',metalDark:'#5e6772',metalLight:'#dfe5ea',trim:'#b08d57',gem:'#38d838',glow:'#1eff00',emissive:.15},
  rare:{metal:'#c8d7e8',metalDark:'#5a6f8e',metalLight:'#f4f8ff',trim:'#9fc4ff',gem:'#2f8cff',glow:'#2f8cff',emissive:.55},
  epic:{metal:'#463a52',metalDark:'#1a1420',metalLight:'#857296',trim:'#b45cff',gem:'#a64df0',glow:'#a64df0',emissive:1.4},
  legendary:{metal:'#f2c45a',metalDark:'#9a6417',metalLight:'#fff1c2',trim:'#ff9a1f',gem:'#ffb340',glow:'#ff8a00',emissive:2.2},
 }[rarity]
 return {...base,fabric,fabricDark:shade(fabric,-.35),leather:LEATHERS[rarity],wood:rarity==='basic'?'#6b4b2e':rarity==='legendary'?'#4a2a10':rarity==='epic'?'#241a2b':'#7a5532'}
}

export function shade(hex:string,amount:number){
 const n=parseInt(hex.slice(1),16);const f=(c:number)=>Math.round(Math.min(255,Math.max(0,amount<0?c*(1+amount):c+(255-c)*amount)))
 return '#'+[n>>16&255,n>>8&255,n&255].map(c=>f(c).toString(16).padStart(2,'0')).join('')
}

export const TIER_COLOR=['#9b7a52','#9b7a52','#8c97a6','#4ea7ff','#b46bff','#ffb340']
export const TIER_LABEL=['','Novice','Apprentice','Adept','Expert','Master']
