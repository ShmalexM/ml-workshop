import * as THREE from 'three'
import {mat,glow} from '../three/materials'

export type EnemyKind='wolf'|'ghoul'|'skeleton'|'archer'|'spider'|'imp'|'hellhound'|'wraith'|'infernal'|'dreadknight'|'demon'|'dummy'
export type Archetype={name:string;hp:number;dmg:number;speed:number;range:number;interval:number;radius:number;ranged?:string;floats?:boolean}
export const ARCHETYPES:Record<EnemyKind,Archetype>={
 wolf:{name:'Blight Wolf',hp:120,dmg:9,speed:4.6,range:1.6,interval:1,radius:.55},
 ghoul:{name:'Ghoul',hp:160,dmg:11,speed:3.2,range:1.7,interval:1.2,radius:.5},
 skeleton:{name:'Skeleton Warrior',hp:110,dmg:10,speed:3.4,range:1.8,interval:1.2,radius:.45},
 archer:{name:'Skeleton Archer',hp:90,dmg:9,speed:3.2,range:7.5,interval:1.8,radius:.45,ranged:'#e8e0c8'},
 spider:{name:'Silkweb Spider',hp:100,dmg:8,speed:4.8,range:1.5,interval:.9,radius:.55},
 imp:{name:'Imp',hp:85,dmg:9,speed:3.6,range:7,interval:1.7,radius:.4,ranged:'#ff7a2a'},
 hellhound:{name:'Hellhound',hp:150,dmg:12,speed:5,range:1.6,interval:1,radius:.6},
 wraith:{name:'Void Wraith',hp:140,dmg:12,speed:3.4,range:6.5,interval:1.6,radius:.5,ranged:'#b06cff',floats:true},
 infernal:{name:'Brimstone Golem',hp:260,dmg:18,speed:2.6,range:2,interval:1.6,radius:.8},
 dreadknight:{name:'Dreadknight',hp:220,dmg:15,speed:3.2,range:2,interval:1.3,radius:.55},
 demon:{name:'Doom Fiend',hp:300,dmg:20,speed:3,range:2.2,interval:1.4,radius:.8},
 // The practice arena's target: it never moves or attacks.
 dummy:{name:'Training dummy',hp:1,dmg:0,speed:0,range:0,interval:999,radius:.7},
}

export type Theme='outskirts'|'bonefield'|'webwood'|'crypt'|'ember'|'kennels'|'void'|'foundry'|'citadel'|'gate'|'abyss'
export type StageDef={theme:Theme;minions:EnemyKind[];boss:{kind:EnemyKind;scale:number;variant:string}}
const STAGES:StageDef[]=[
 {theme:'outskirts',minions:['wolf','ghoul'],boss:{kind:'wolf',scale:2.6,variant:'alpha'}},
 {theme:'bonefield',minions:['skeleton','archer'],boss:{kind:'skeleton',scale:2.5,variant:'king'}},
 {theme:'webwood',minions:['spider'],boss:{kind:'spider',scale:3,variant:'brood'}},
 {theme:'crypt',minions:['ghoul','skeleton'],boss:{kind:'ghoul',scale:2.9,variant:'abomination'}},
 {theme:'ember',minions:['imp'],boss:{kind:'imp',scale:3.2,variant:'pyrelord'}},
 {theme:'kennels',minions:['hellhound'],boss:{kind:'hellhound',scale:2.6,variant:'twin'}},
 {theme:'void',minions:['wraith'],boss:{kind:'wraith',scale:2.9,variant:'unmaker'}},
 {theme:'foundry',minions:['infernal','imp'],boss:{kind:'infernal',scale:2.4,variant:'colossus'}},
 {theme:'citadel',minions:['dreadknight','imp'],boss:{kind:'demon',scale:2.2,variant:'dread'}},
 {theme:'gate',minions:['demon','hellhound','imp'],boss:{kind:'demon',scale:2.8,variant:'azgaroth'}},
]
export function stageDef(stage:number):StageDef{
 if(stage<=10)return STAGES[stage-1]
 return {theme:'abyss',minions:['demon','wraith','hellhound','infernal'],boss:{kind:(['demon','infernal','wraith','hellhound','dreadknight'] as EnemyKind[])[(stage-11)%5],scale:2.7,variant:'abyssal'}}
}
/** Enemy health and damage scale per stage; boss health itself comes from the server. */
export const stageHp=(s:number)=>s<=10?1.42**(s-1):1.42**9*1.25**(s-10)
export const stageDmg=(s:number)=>s<=10?1.3**(s-1):1.3**9*1.15**(s-10)

export type EnemyModel={object:THREE.Group;legs:THREE.Object3D[];arms:THREE.Object3D[];wings:THREE.Object3D[];head:THREE.Object3D|null;height:number;floats:boolean;emit:THREE.Object3D|null;emitColor:string|null}
const mesh=(geo:THREE.BufferGeometry,m:THREE.Material,parent:THREE.Object3D,x=0,y=0,z=0)=>{const o=new THREE.Mesh(geo,m);o.position.set(x,y,z);o.castShadow=true;parent.add(o);return o}
const pivot=(parent:THREE.Object3D,x:number,y:number,z:number)=>{const g=new THREE.Group();g.position.set(x,y,z);parent.add(g);return g}
const eyes=(head:THREE.Object3D,color:string,x:number,y:number,z:number,size=.05)=>{for(const s of [-1,1]){mesh(new THREE.BoxGeometry(size,size*.6,size*.4),mat(color,{emissive:color,glow:2.5}),head,s*x,y,z)}}

function quadruped(fur:string,belly:string,eye:string,opts:{flames?:boolean;heads?:number;mane?:string;maneGlow?:boolean}={}):EnemyModel{
 const g=new THREE.Group();const body=pivot(g,0,.62,0);const m=mat(fur,{rough:.85});const b=mat(belly,{rough:.9})
 // Rounded chest and haunch read as an animal; a single box reads as furniture.
 const chest=mesh(new THREE.IcosahedronGeometry(.32,1),m,body,0,.04,.22);chest.scale.set(.85,.9,1.1)
 const haunch=mesh(new THREE.IcosahedronGeometry(.27,1),m,body,0,0,-.3);haunch.scale.set(.85,.85,1.05)
 mesh(new THREE.CylinderGeometry(.2,.22,.5,7),m,body,0,0,-.04).rotation.x=Math.PI/2
 mesh(new THREE.IcosahedronGeometry(.2,1),b,body,0,-.16,.12).scale.set(.9,.6,1.4)
 const legs:THREE.Object3D[]=[]
 for(const [x,z] of [[-.16,.3],[.16,.3],[-.15,-.34],[.15,-.34]]){const leg=pivot(body,x,-.1,z);mesh(new THREE.CylinderGeometry(.065,.04,.56,6),m,leg,0,-.27,0);mesh(new THREE.BoxGeometry(.09,.05,.14),mat('#1e1a18'),leg,0,-.55,.03);legs.push(leg)}
 const heads=opts.heads||1;let head:THREE.Object3D|null=null
 for(let i=0;i<heads;i++){const off=heads>1?(i?.16:-.16):0;const h=pivot(body,off,.24,.52);h.rotation.y=off*-1.2
  mesh(new THREE.IcosahedronGeometry(.17,1),m,h).scale.set(1,.95,1.1)
  const snout=mesh(new THREE.ConeGeometry(.1,.3,6),m,h,0,-.04,.24);snout.rotation.x=Math.PI/2
  mesh(new THREE.IcosahedronGeometry(.04,0),mat('#141414'),h,0,-.02,.39)
  const jaw=mesh(new THREE.BoxGeometry(.12,.04,.2),b,h,0,-.11,.17);jaw.rotation.x=.15
  for(const s of [-1,1]){const ear=mesh(new THREE.ConeGeometry(.055,.17,4),m,h,s*.1,.17,-.02);ear.rotation.z=-s*.25}
  eyes(h,eye,.075,.04,.13);if(!head)head=h}
 const tail=pivot(body,0,.08,-.52);tail.rotation.x=-.8;mesh(new THREE.CylinderGeometry(.025,.07,.48,6),m,tail,0,-.22,0)
 if(opts.mane){const maneMat=opts.maneGlow?glow(opts.mane,.85):mat(opts.mane,{rough:.9});for(let i=0;i<6;i++){const sp=mesh(new THREE.ConeGeometry(opts.maneGlow?.07:.06,opts.maneGlow?.3:.2,4),maneMat,body,0,.26-i*.01,.38-i*.13);sp.rotation.x=-.5}}
 return {object:g,legs,arms:[],wings:[],head,height:1.1,floats:false,emit:opts.flames?body:null,emitColor:opts.flames?opts.mane||'#ff6a1a':null}
}

function humanoid(skin:string,eye:string,opts:{hunch?:number;bones?:boolean;armor?:string;horns?:string;wings?:string;weapon?:'sword'|'bow'|'claws'|'hook'|'flamesword';crown?:boolean;fat?:boolean;tail?:boolean;height?:number}={}):EnemyModel{
 const g=new THREE.Group();const h=opts.height||1;const m=mat(skin,{rough:.8});const arm=opts.armor?mat(opts.armor,{metal:.7,rough:.4}):m
 const hips=pivot(g,0,.8*h,0)
 const legs:THREE.Object3D[]=[]
 for(const s of [-1,1]){const leg=pivot(hips,s*.12,0,0);mesh(new THREE.CylinderGeometry(opts.bones?.035:.08,opts.bones?.03:.06,.8*h,5),arm,leg,0,-.4*h,0);mesh(new THREE.BoxGeometry(.12,.06,.2),arm,leg,0,-.8*h,.04);legs.push(leg)}
 const spine=pivot(hips,0,0,0);spine.rotation.x=opts.hunch||0
 if(opts.bones){for(let i=0;i<4;i++)mesh(new THREE.TorusGeometry(.16-i*.015,.02,4,10),m,spine,0,.2+i*.11,0).rotation.x=Math.PI/2;mesh(new THREE.CylinderGeometry(.03,.03,.55,5),m,spine,0,.3,-.1)}
 else{const torso=mesh(new THREE.CylinderGeometry(opts.fat?.36:.24,opts.fat?.4:.18,.6,7),arm,spine,0,.32,0);torso.scale.z=opts.fat?1:.72;if(opts.fat)mesh(new THREE.IcosahedronGeometry(.42,1),m,spine,0,.2,.08)}
 const headP=pivot(spine,0,.75,0);mesh(new THREE.IcosahedronGeometry(.17,1),opts.bones?m:opts.armor?arm:m,headP);eyes(headP,eye,.065,.02,.15)
 if(opts.horns)for(const s of [-1,1]){const horn=mesh(new THREE.ConeGeometry(.05,.32,5),mat(opts.horns,{rough:.5}),headP,s*.12,.18,0);horn.rotation.z=-s*.5}
 if(opts.crown)for(let i=0;i<5;i++){const a=i/5*Math.PI*2;mesh(new THREE.ConeGeometry(.035,.14,4),mat('#d4a640',{metal:.9,rough:.3,emissive:'#7a5a10',glow:.4}),headP,Math.cos(a)*.13,.18,Math.sin(a)*.13)}
 const arms:THREE.Object3D[]=[]
 for(const s of [-1,1]){const shoulder=pivot(spine,s*(opts.fat?.42:.28),.55,0);shoulder.rotation.z=s*.15
  mesh(new THREE.CylinderGeometry(opts.bones?.03:.06,opts.bones?.025:.05,.62,5),arm,shoulder,0,-.31,0)
  const hand=pivot(shoulder,0,-.64,0);arms.push(shoulder)
  const w=opts.weapon;if(s===1&&(w==='sword'||w==='flamesword')){const blade=mesh(new THREE.BoxGeometry(.05,w==='flamesword'?1.1:.75,.02),w==='flamesword'?mat('#3a1a10',{emissive:'#ff5a1a',glow:1.8}):mat('#9aa0a8',{metal:.8,rough:.35}),hand,0,0,.4);blade.rotation.x=Math.PI/2}
  if(s===-1&&w==='bow'){const bow=mesh(new THREE.TorusGeometry(.35,.02,4,10,Math.PI),mat('#6b4b2e'),hand,0,0,.1);bow.rotation.y=Math.PI/2}
  if(w==='claws'||w==='hook')mesh(new THREE.ConeGeometry(.05,.22,4),mat('#d8d0c0'),hand,0,-.06,.08).rotation.x=Math.PI/2}
 const wings:THREE.Object3D[]=[]
 if(opts.wings)for(const s of [-1,1]){const wp=pivot(spine,s*.15,.55,-.15);const shape=new THREE.Shape();shape.moveTo(0,0);shape.lineTo(s*.9,.5);shape.lineTo(s*1.1,-.1);shape.lineTo(s*.7,-.3);shape.lineTo(s*.5,-.1);shape.closePath()
  mesh(new THREE.ShapeGeometry(shape),mat(opts.wings,{rough:.7,side:THREE.DoubleSide}),wp);wp.rotation.y=s*.5;wings.push(wp)}
 if(opts.tail){const t=pivot(hips,0,0,-.15);t.rotation.x=-1;mesh(new THREE.CylinderGeometry(.02,.06,.7,5),m,t,0,-.35,0)}
 return {object:g,legs,arms,wings,head:headP,height:1.75*h,floats:false,emit:opts.weapon==='flamesword'?arms[1]:null,emitColor:opts.weapon==='flamesword'?'#ff6a1a':null}
}

function spider(body:string,eye:string):EnemyModel{
 const g=new THREE.Group();const b=pivot(g,0,.45,0);const m=mat(body,{rough:.7})
 mesh(new THREE.IcosahedronGeometry(.28,1),m,b,0,0,.18);const abd=mesh(new THREE.IcosahedronGeometry(.42,1),m,b,0,.08,-.38);abd.scale.set(1,.85,1.15)
 mesh(new THREE.IcosahedronGeometry(.12,0),mat('#b0202a',{emissive:'#7a0010',glow:.6}),b,0,.42,-.4)
 for(const s of [-1,1])for(let i=0;i<4;i++)mesh(new THREE.BoxGeometry(.03,.03,.03),mat(eye,{emissive:eye,glow:2.5}),b,s*(.05+i*.03),.08+i%2*.04,.42)
 const legs:THREE.Object3D[]=[]
 for(const s of [-1,1])for(let i=0;i<4;i++){const leg=pivot(b,s*.2,0,.28-i*.16);leg.rotation.y=s*(.2-i*.25);const up=mesh(new THREE.CylinderGeometry(.025,.03,.5,4),m,leg,s*.22,.12,0);up.rotation.z=-s*1;const low=mesh(new THREE.CylinderGeometry(.02,.012,.55,4),m,leg,s*.48,-.18,0);low.rotation.z=s*.35;legs.push(leg)}
 return {object:g,legs,arms:[],wings:[],head:null,height:.9,floats:false,emit:null,emitColor:null}
}

function wraith(cloak:string,eye:string):EnemyModel{
 const g=new THREE.Group();const body=pivot(g,0,.9,0)
 const robe=mesh(new THREE.ConeGeometry(.45,1.4,8,1,true),mat(cloak,{rough:.9,side:THREE.DoubleSide,emissive:cloak,glow:.25}),body,0,-.05,0);robe.rotation.x=Math.PI
 mesh(new THREE.ConeGeometry(.5,1.5,8,1,true),glow(eye,.12,THREE.DoubleSide),body,0,-.05,0).rotation.x=Math.PI
 const hood=pivot(body,0,.72,0);mesh(new THREE.SphereGeometry(.24,8,6,0,Math.PI*2,0,Math.PI*.65),mat(cloak,{rough:.9,side:THREE.DoubleSide}),hood);mesh(new THREE.SphereGeometry(.18,8,6),mat('#05030a'),hood,0,-.03,.04);eyes(hood,eye,.07,0,.18,.06)
 const arms:THREE.Object3D[]=[]
 for(const s of [-1,1]){const a=pivot(body,s*.32,.45,0);a.rotation.z=s*.4;mesh(new THREE.ConeGeometry(.1,.7,5,1,true),mat(cloak,{side:THREE.DoubleSide}),a,0,-.3,0).rotation.x=Math.PI;arms.push(a)}
 return {object:g,legs:[],arms,wings:[],head:hood,height:1.9,floats:true,emit:body,emitColor:eye}
}

function golem(rock:string,crack:string):EnemyModel{
 const g=new THREE.Group();const body=pivot(g,0,1,0);const r=mat(rock,{rough:.95});const c=mat(crack,{emissive:crack,glow:2})
 const chest=mesh(new THREE.IcosahedronGeometry(.55,0),r,body);chest.scale.set(1.1,.95,.85)
 mesh(new THREE.IcosahedronGeometry(.58,0),glow(crack,.15),body)
 for(let i=0;i<5;i++)mesh(new THREE.BoxGeometry(.04,.3,.02),c,body,(Math.random()-.5)*.6,(Math.random()-.5)*.5,.45).rotation.z=Math.random()*2
 const headP=pivot(body,0,.62,.1);mesh(new THREE.IcosahedronGeometry(.24,0),r,headP);eyes(headP,crack,.09,.03,.2,.07)
 const arms:THREE.Object3D[]=[]
 for(const s of [-1,1]){const a=pivot(body,s*.62,.25,0);mesh(new THREE.IcosahedronGeometry(.22,0),r,a,0,-.15,0);mesh(new THREE.IcosahedronGeometry(.28,0),r,a,0,-.6,0);arms.push(a)}
 const legs:THREE.Object3D[]=[]
 for(const s of [-1,1]){const l=pivot(body,s*.28,-.45,0);mesh(new THREE.IcosahedronGeometry(.24,0),r,l,0,-.3,0);legs.push(l)}
 return {object:g,legs,arms,wings:[],head:headP,height:2,floats:false,emit:body,emitColor:crack}
}

/** A straw training dummy on a post, with a painted target. Its crossbar sways when hit. */
function dummy():EnemyModel{
 const g=new THREE.Group();const wood=mat('#7a5634',{rough:.9});const straw=mat('#c9a65a',{rough:1});const paint=mat('#a8322c',{rough:.9});const pale=mat('#efe4c8',{rough:.9})
 mesh(new THREE.CylinderGeometry(.55,.62,.14,14),wood,g,0,.07,0)
 mesh(new THREE.CylinderGeometry(.08,.1,2.1,8),wood,g,0,1.05,0)
 const body=pivot(g,0,1.2,0)
 mesh(new THREE.CylinderGeometry(.36,.32,.95,12),straw,body)
 for(const [r,m,z] of [[.27,paint,.33],[.18,pale,.345],[.09,paint,.36]] as [number,THREE.Material,number][])mesh(new THREE.CircleGeometry(r,20),m,body,0,.08,z)
 for(const y of [-.38,.38])mesh(new THREE.TorusGeometry(.35,.03,5,18),wood,body,0,y,0).rotation.x=Math.PI/2
 const arms:THREE.Object3D[]=[]
 for(const side of [-1,1]){const arm=pivot(body,side*.3,.32,0);mesh(new THREE.CylinderGeometry(.05,.05,.75,6),wood,arm,side*.36,0,0).rotation.z=Math.PI/2;mesh(new THREE.IcosahedronGeometry(.11,0),straw,arm,side*.76,0,0);arms.push(arm)}
 const head=pivot(g,0,1.98,0);mesh(new THREE.IcosahedronGeometry(.25,1),straw,head);mesh(new THREE.BoxGeometry(.56,.05,.05),wood,head,0,.02,0)
 return {object:g,legs:[],arms,wings:[],head,height:2.3,floats:false,emit:null,emitColor:null}
}

/** Builds the mesh for a minion or (with `variant`) a boss. */
export function buildEnemy(kind:EnemyKind,variant='',scale=1):EnemyModel{
 let model:EnemyModel
 switch(kind){
  case 'wolf':model=variant==='alpha'?quadruped('#3f3a36','#6a625a','#ff3a2a',{mane:'#9a9288'}):quadruped('#5a554e','#8a8076','#ffcf3a');break
  case 'hellhound':model=quadruped('#2a1414','#4a1a14','#ffb03a',{flames:true,mane:'#ff6a1a',maneGlow:true,heads:variant==='twin'?2:1});break
  case 'ghoul':model=variant==='abomination'?humanoid('#8aa08a','#ffe35a',{fat:true,weapon:'hook',hunch:.2,height:1.05}):humanoid('#7d907c','#d8ff5a',{hunch:.45,weapon:'claws'});break
  case 'skeleton':model=humanoid('#b8ae94','#5ad8ff',{bones:true,weapon:'sword',crown:variant==='king'});break
  case 'archer':model=humanoid('#b8ae94','#5ad8ff',{bones:true,weapon:'bow'});break
  case 'spider':model=spider(variant==='brood'?'#2a1530':'#2b2430','#ff3a3a');break
  case 'imp':model=humanoid(variant==='pyrelord'?'#b8341a':'#c8402a','#ffd23a',{horns:'#2a1a14',hunch:.15,height:variant==='pyrelord'?1:.62,weapon:variant==='pyrelord'?'flamesword':'claws',wings:'#5a1a14',tail:true});break
  case 'wraith':model=wraith(variant==='unmaker'?'#1a0f2e':'#2a1a40','#b06cff');break
  case 'infernal':model=golem(variant==='colossus'?'#2a2622':'#3a3430',variant==='colossus'?'#ff6a1a':'#7aff3a');break
  case 'dreadknight':model=humanoid('#2a2630','#ff3a3a',{armor:'#3a3442',weapon:'sword',horns:'#1a1418'});break
  case 'dummy':model=dummy();break
  case 'demon':model=humanoid(variant==='dread'?'#3a2a4a':'#7a1f1a','#ffcf3a',{horns:'#1a1210',wings:variant==='dread'?'#2a1a3a':'#3a1010',tail:true,weapon:variant==='azgaroth'?'flamesword':'claws',crown:variant==='azgaroth',height:1.1});break
 }
 model.object.scale.setScalar(scale);model.height*=scale
 return model
}
