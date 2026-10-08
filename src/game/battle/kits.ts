export type AbilityKind='projectile'|'nova'|'ground'|'dash'|'blink'|'heal'|'shield'|'buff'|'spin'|'cone'|'chain'|'leap'|'spree'|'disengage'
export type Ability={
 key:'Q'|'W'|'E'|'R';name:string;kind:AbilityKind;cd:number;power:number;color:string;text:string
 radius?:number;range?:number;duration?:number;delay?:number;tick?:number
 root?:number;slow?:number;stun?:number;burn?:number;pull?:boolean;knock?:number;heal?:number;hot?:number
 count?:number;spread?:number;bounces?:number;pierce?:boolean;drain?:number;speed?:number;explode?:number
 damageUp?:number;reduce?:number;grow?:number;leech?:number
 /** Ground zones: the first hit, as a multiple of Power; later ticks deal `power`. */
 impact?:number
 /** A shield for 6 sec that absorbs this share of maximum health. */
 barrier?:number
}
export type Kit={auto:{range:number;interval:number;power:number;projectile:string|null;slow?:number};abilities:Ability[]}

/** Every class gets an auto attack and four abilities on Q W E R, cast toward the cursor. */
export const KITS:Record<string,Kit>={
 warrior:{auto:{range:2.3,interval:1.15,power:1.2,projectile:null},abilities:[
  {key:'Q',name:'Charge',kind:'dash',cd:8,power:1.6,range:8,stun:1,color:'#ffcf8a',text:'Rush toward the cursor, hitting and stunning the first enemy in your path.'},
  {key:'W',name:'Whirlwind',kind:'nova',cd:6,power:1.5,radius:3.2,color:'#f0e0c0',text:'Spin once, hitting every enemy around you.'},
  {key:'E',name:'War Cry',kind:'buff',cd:16,power:0,duration:8,damageUp:.25,reduce:.1,hot:.02,color:'#ff8a3a',text:'For 8 sec, deal 25% more damage, take 10% less and heal 2% of your health each second.'},
  {key:'R',name:'Steel Storm',kind:'spin',cd:40,power:.55,radius:3.2,duration:4,tick:.4,color:'#f0e0c0',text:'Become a whirl of steel for 4 sec, hitting everything near you.'}]},
 paladin:{auto:{range:2.3,interval:1.2,power:1.1,projectile:null},abilities:[
  {key:'Q',name:'Judgment',kind:'projectile',cd:5,power:1.9,range:10,speed:22,color:'#ffe58a',text:'Hurl a hammer of light at the cursor.'},
  {key:'W',name:'Consecration',kind:'ground',cd:12,power:.3,radius:3.5,duration:6,tick:.5,range:0,color:'#ffd65a',text:'Bless the ground under you, burning enemies on it for 6 sec.'},
  {key:'E',name:'Light\'s Mending',kind:'heal',cd:16,power:0,heal:.15,color:'#fff1a8',text:'Heal 15% of your maximum health.'},
  {key:'R',name:'Radiant Wings',kind:'buff',cd:50,power:0,duration:10,damageUp:.4,hot:.03,grow:1.15,color:'#ffd24a',text:'For 10 sec, deal 40% more damage and heal 3% of your health each second.'}]},
 deathknight:{auto:{range:2.3,interval:1.2,power:1,projectile:null},abilities:[
  {key:'Q',name:'Grave Grasp',kind:'projectile',cd:10,power:.8,range:10,speed:24,pull:true,stun:.8,color:'#8fd0ff',text:'Pull the first enemy hit to you and stun it.'},
  {key:'W',name:'Death and Decay',kind:'ground',cd:14,power:.4,radius:3.5,duration:7,tick:.5,range:9,slow:.3,color:'#6aff9a',text:'Corrupt the ground at the cursor, damaging and slowing enemies for 7 sec.'},
  {key:'E',name:'Death Strike',kind:'cone',cd:7,power:1.6,radius:3,spread:.9,heal:.05,color:'#b8f0ff',text:'Strike enemies in front of you and heal 5% of your maximum health.'},
  {key:'R',name:'Winter\'s Ring',kind:'spin',cd:45,power:.45,radius:4,duration:6,tick:.5,slow:.4,color:'#a8e8ff',text:'A storm of ice surrounds you for 6 sec, damaging and slowing enemies.'}]},
 hunter:{auto:{range:9,interval:1.3,power:1,projectile:'#e8d9a0'},abilities:[
  {key:'Q',name:'Multi-Shot',kind:'projectile',cd:6,power:.95,range:10,speed:26,count:5,spread:.55,color:'#f2e6b0',text:'Fire five arrows in a fan toward the cursor.'},
  {key:'W',name:'Freezing Trap',kind:'ground',cd:10,power:.5,radius:2.6,duration:.1,range:10,root:4,color:'#9ae6ff',text:'Freeze enemies at the cursor in place for 4 sec.'},
  {key:'E',name:'Disengage',kind:'disengage',cd:10,power:0,range:7,barrier:.2,color:'#d8f0b0',text:'Leap backward, away from the cursor, and absorb damage equal to 20% of your health for 6 sec.'},
  {key:'R',name:'Volley',kind:'ground',cd:40,power:.8,radius:4.5,duration:5,tick:.5,range:11,color:'#f2e6b0',text:'Rain arrows on the cursor area for 5 sec.'}]},
 shaman:{auto:{range:8,interval:1.35,power:1,projectile:'#9ad8ff'},abilities:[
  {key:'Q',name:'Chain Lightning',kind:'chain',cd:6,power:1.6,range:9,bounces:4,color:'#b8e6ff',text:'Lightning leaps between up to five enemies near the cursor.'},
  {key:'W',name:'Earthquake',kind:'ground',cd:15,power:.55,radius:4,duration:6,tick:.5,range:10,slow:.3,color:'#d9b27a',text:'Shake the ground at the cursor for 6 sec, damaging and slowing enemies.'},
  {key:'E',name:'Tidal Mend',kind:'heal',cd:16,power:0,heal:.2,color:'#7affc8',text:'Heal 20% of your maximum health.'},
  {key:'R',name:'Thunderstorm',kind:'nova',cd:35,power:2.4,radius:5,knock:4,stun:1,color:'#a8d8ff',text:'Call a thunderclap that blasts nearby enemies away and stuns them.'}]},
 rogue:{auto:{range:2.2,interval:.95,power:1.15,projectile:null},abilities:[
  {key:'Q',name:'Shadowstep',kind:'blink',cd:8,power:2.2,range:10,stun:.8,color:'#b07aff',text:'Step through the shadows to the enemy nearest the cursor and strike it.'},
  {key:'W',name:'Knife Fan',kind:'nova',cd:6,power:1.6,radius:3.5,slow:.3,color:'#e0e0e0',text:'Throw knives in every direction, slowing enemies hit.'},
  {key:'E',name:'Evasion',kind:'buff',cd:16,power:0,duration:6,reduce:.6,hot:.03,color:'#d0d0ff',text:'For 6 sec, take 60% less damage and heal 3% of your health each second.'},
  {key:'R',name:'Shadow Spree',kind:'spree',cd:40,power:2,range:8,count:6,color:'#c08aff',text:'Teleport between up to six nearby enemies, striking each one.'}]},
 monk:{auto:{range:2.2,interval:1,power:.95,projectile:null},abilities:[
  {key:'Q',name:'Dragon Kick',kind:'dash',cd:8,power:1.5,range:9,pierce:true,color:'#7affd0',text:'Fly toward the cursor, hitting every enemy you pass.'},
  {key:'W',name:'Whirling Kick',kind:'spin',cd:10,power:.6,radius:3,duration:2,tick:.3,color:'#a8ffe0',text:'Spin for 2 sec, kicking enemies around you.'},
  {key:'E',name:'Vivify',kind:'heal',cd:12,power:0,heal:.25,color:'#7affc8',text:'Heal 25% of your maximum health.'},
  {key:'R',name:'Hundred Fists',kind:'cone',cd:30,power:1,radius:4.5,spread:.7,count:5,stun:1.5,color:'#ffe08a',text:'Pummel enemies in front of you five times and stun them.'}]},
 druid:{auto:{range:8,interval:1.35,power:1,projectile:'#b8ff8a'},abilities:[
  {key:'Q',name:'Moon Flare',kind:'projectile',cd:4,power:1.15,range:10,speed:20,burn:.35,color:'#c8a8ff',text:'Strike with lunar fire that keeps burning for 6 sec.'},
  {key:'W',name:'Entangling Roots',kind:'ground',cd:12,power:.4,radius:2.8,duration:.1,range:10,root:3,color:'#7ad86a',text:'Roots hold enemies at the cursor in place for 3 sec.'},
  {key:'E',name:'Regrowth',kind:'heal',cd:12,power:0,heal:.25,hot:.03,duration:6,color:'#8aff9a',text:'Heal 25% of your maximum health, then 3% each second for 6 sec.'},
  {key:'R',name:'Falling Stars',kind:'spin',cd:40,power:.55,radius:5,duration:6,tick:.5,color:'#d8c8ff',text:'Stars rain around you for 6 sec.'}]},
 demonhunter:{auto:{range:2.3,interval:1,power:1.3,projectile:null},abilities:[
  {key:'Q',name:'Burning Dash',kind:'dash',cd:6,power:2,range:8,pierce:true,color:'#7aff5a',text:'Rush toward the cursor, hitting every enemy you pass.'},
  {key:'W',name:'Blade Dance',kind:'nova',cd:7,power:2.2,radius:3.2,color:'#9aff7a',text:'Strike all nearby enemies with a flurry of blades.'},
  {key:'E',name:'Blur',kind:'buff',cd:16,power:0,duration:6,reduce:.4,hot:.04,color:'#9a7aff',text:'For 6 sec, take 40% less damage and heal 4% of your health each second.'},
  {key:'R',name:'Demon Form',kind:'leap',cd:50,power:2,radius:4,range:9,stun:1,duration:12,damageUp:.35,grow:1.25,color:'#6aff3a',text:'Leap to the cursor and transform, then deal 35% more damage for 12 sec.'}]},
 priest:{auto:{range:8,interval:1.35,power:1,projectile:'#fff3b0'},abilities:[
  {key:'Q',name:'Holy Fire',kind:'projectile',cd:6,power:3.1,range:10,speed:20,burn:.3,color:'#ffd27a',text:'Sear an enemy with holy fire that keeps burning.'},
  {key:'W',name:'Ward of Light',kind:'shield',cd:15,power:0,heal:.25,duration:8,color:'#fff4c0',text:'Absorb damage equal to 25% of your maximum health for 8 sec.'},
  {key:'E',name:'Quick Heal',kind:'heal',cd:11,power:0,heal:.22,color:'#fff8d0',text:'Heal 22% of your maximum health.'},
  {key:'R',name:'Choir of Light',kind:'spin',cd:45,power:.6,radius:5,duration:5,tick:.5,hot:.04,color:'#fff0a0',text:'For 5 sec, heal 4% of your health each second and burn nearby enemies.'}]},
 mage:{auto:{range:8.5,interval:1.35,power:1,projectile:'#a8dcff',slow:.1},abilities:[
  {key:'Q',name:'Fireball',kind:'projectile',cd:5,power:3.3,range:11,speed:18,explode:2,color:'#ff8a3a',text:'Launch a fireball that explodes on impact.'},
  {key:'W',name:'Frost Ring',kind:'nova',cd:12,power:.8,radius:4,root:2.5,barrier:.15,color:'#bfefff',text:'Freeze nearby enemies in place for 2.5 sec and gain a barrier that absorbs 15% of your health for 6 sec.'},
  {key:'E',name:'Blink',kind:'blink',cd:12,power:0,range:8,color:'#c8e8ff',text:'Teleport toward the cursor.'},
  {key:'R',name:'Meteor',kind:'ground',cd:35,power:4,radius:4.5,duration:.1,range:12,delay:1.2,burn:.4,color:'#ff6a1a',text:'Call down a meteor at the cursor after a short delay.'}]},
 warlock:{auto:{range:8,interval:1.35,power:1,projectile:'#b07aff'},abilities:[
  {key:'Q',name:'Corruption',kind:'projectile',cd:4,power:.8,range:10,speed:20,burn:.3,color:'#9a5aff',text:'Corrupt an enemy, dealing damage over 6 sec.'},
  {key:'W',name:'Rain of Fire',kind:'ground',cd:14,power:.45,radius:4,duration:6,tick:.5,range:10,color:'#7aff3a',text:'Fire rains on the cursor area for 6 sec.'},
  {key:'E',name:'Drain Life',kind:'projectile',cd:10,power:1.3,range:9,speed:16,drain:.8,color:'#c84aff',text:'Drain an enemy and heal for 80% of the damage dealt.'},
  {key:'R',name:'Hellstone',kind:'ground',cd:40,power:.35,impact:2.5,radius:4,duration:6,tick:.5,range:11,delay:.9,stun:1.5,burn:.4,color:'#7aff3a',text:'A burning stone crashes down at the cursor, stunning enemies and leaving fire behind.'}]},
}
