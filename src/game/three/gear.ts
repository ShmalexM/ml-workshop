import * as THREE from 'three'
import {mat,glow,mailMap} from './materials'
import {palette,seeded,RARITY_INDEX} from '../rarity'
import type {GearLook} from '../types'
import type {Dims,JointName} from './rig'

export type GearPart={joint:JointName;object:THREE.Object3D;side?:'L'|'R'}
export type FxSpec={kind:'embers'|'sparks'|'motes'|'snow'|'shards';color:string;rate:number;spread:number}

/** Legendary effects each get their own particle signature on top of the gold base. */
export const EFFECT_FX:Record<string,FxSpec>={
 inferno:{kind:'embers',color:'#ff6a1a',rate:26,spread:.12},stormcall:{kind:'sparks',color:'#9ad8ff',rate:22,spread:.14},
 bloodsong:{kind:'motes',color:'#ff2a4a',rate:16,spread:.16},riftwalk:{kind:'shards',color:'#b06cff',rate:18,spread:.16},
 dawnfire:{kind:'motes',color:'#ffe08a',rate:20,spread:.15},wintergrasp:{kind:'snow',color:'#bfefff',rate:20,spread:.18},
 phoenix:{kind:'embers',color:'#ff9a3a',rate:30,spread:.14},galeforce:{kind:'motes',color:'#c8ffe0',rate:18,spread:.2},
 kingslayer:{kind:'sparks',color:'#ff4040',rate:18,spread:.12},starward:{kind:'motes',color:'#e8f0ff',rate:16,spread:.18},
}

function kit(look:GearLook){
 const p=palette(look.rarity,look.seed);const ri=RARITY_INDEX[look.rarity];const rand=seeded(look.seed^0x9e3779b9)
 const metal=mat(p.metal,{metal:[.5,.7,.85,.75,.9][ri],rough:[.7,.45,.28,.35,.22][ri]})
 const dark=mat(p.metalDark,{metal:.6,rough:.5})
 const trim=ri>=3?mat(p.trim,{emissive:p.trim,glow:p.emissive*.9,metal:.5,rough:.4}):mat(p.trim,{metal:ri>=1?.85:.1,rough:ri>=1?.35:.8})
 const gem=mat(p.gem,{emissive:p.gem,glow:ri>=2?1.8:.35,rough:.15,metal:.1})
 const rune=mat(p.glow,{emissive:p.glow,glow:Math.max(1,p.emissive*1.4)})
 const fabric=mat(p.fabric,{rough:.95}),fabricDark=mat(p.fabricDark,{rough:.95})
 const leather=mat(p.leather,{rough:.8}),wood=mat(p.wood,{rough:.85})
 const mail=mat(p.metal,{map:mailMap(),metal:.7,rough:.45})
 const fx:FxSpec|null=look.effect&&EFFECT_FX[look.effect]?EFFECT_FX[look.effect]:ri===3?{kind:'embers',color:p.glow,rate:7,spread:.1}:null
 return {p,ri,rand,metal,dark,trim,gem,rune,fabric,fabricDark,leather,wood,mail,fx,look}
}
type Kit=ReturnType<typeof kit>

const mesh=(geo:THREE.BufferGeometry,m:THREE.Material,parent:THREE.Object3D,x=0,y=0,z=0)=>{const o=new THREE.Mesh(geo,m);o.position.set(x,y,z);o.castShadow=true;parent.add(o);return o}
const cyl=(rt:number,rb:number,h:number,seg=8,open=false)=>new THREE.CylinderGeometry(rt,rb,h,seg,1,open)
function extrude(shape:THREE.Shape,depth:number,bevel=.004){const g=new THREE.ExtrudeGeometry(shape,{depth,bevelEnabled:bevel>0,bevelThickness:bevel,bevelSize:bevel,bevelSegments:1,curveSegments:5});g.translate(0,0,-depth/2);return g}
function tagFx(o:THREE.Object3D,k:Kit){if(k.fx)o.userData.fx=k.fx}
function spikes(parent:THREE.Object3D,m:THREE.Material,points:[number,number,number][],len:number,r:number){for(const [x,y,z] of points){const c=mesh(new THREE.ConeGeometry(r,len,5),m,parent,x,y,z);const dir=new THREE.Vector3(x,y,z).normalize();c.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),dir)}}

// Blade outlines: plain → leaf → serrated / flamberge as rarity climbs.
function bladeShape(len:number,w:number,style:'plain'|'leaf'|'serrated'|'flame'){
 const s=new THREE.Shape();const half=w/2;const pts:[number,number][]=[]
 const steps=12
 for(let i=0;i<=steps;i++){
  const t=i/steps;const y=t*len*.86;let x=half
  if(style==='leaf')x=half*(1+.35*Math.sin(t*Math.PI*.95))
  if(style==='serrated')x=half*(i%2?1.28:1)
  if(style==='flame')x=half*(1+.22*Math.sin(t*Math.PI*5))*(1-t*.15)
  pts.push([-x,y])
 }
 s.moveTo(pts[0][0],0);for(const [x,y] of pts)s.lineTo(x,y);s.lineTo(0,len)
 for(let i=pts.length-1;i>=0;i--)s.lineTo(-pts[i][0],pts[i][1])
 s.closePath();return s
}

function bladeWeapon(k:Kit,len:number,w:number,gripLen:number){
 const g=new THREE.Group();const {ri,rand}=k
 const style=ri<=1?'plain':ri===2?'leaf':ri===3?(rand()<.5?'serrated':'flame'):'flame'
 const blade=mesh(extrude(bladeShape(len,w*(1+ri*.08),style),.016,.005),k.metal,g,0,gripLen/2+.035,0)
 if(ri>=1)mesh(new THREE.BoxGeometry(w*.18,len*.7,.02),ri>=3?k.rune:k.dark,blade,0,len*.38,0)
 const guardW=w*(2.6+ri*.45)
 const guard=mesh(new THREE.BoxGeometry(guardW,.035,.05),ri>=1?k.trim:k.dark,g,0,gripLen/2+.02,0)
 if(ri>=2)for(const s of [-1,1]){const tip=mesh(new THREE.ConeGeometry(.018,.07,5),k.trim,guard,s*guardW/2,.02,0);tip.rotation.z=-s*.8}
 if(ri>=3)spikes(guard,k.trim,[[-guardW*.3,-.03,0],[guardW*.3,-.03,0]],.07,.015)
 if(ri>=4)for(const s of [-1,1]){const wing=new THREE.Shape();wing.moveTo(0,0);wing.quadraticCurveTo(s*.09,.02,s*.16,.12);wing.quadraticCurveTo(s*.08,.05,0,.04);mesh(extrude(wing,.012,.003),k.metal,g,s*.02,gripLen/2+.03,0)}
 if(ri>=2)mesh(new THREE.OctahedronGeometry(.022*(1+ri*.12)),k.gem,guard,0,0,.03)
 mesh(cyl(.019,.021,gripLen,6),k.leather,g)
 if(ri>=1)for(let i=0;i<3;i++)mesh(new THREE.TorusGeometry(.021,.005,4,8),k.trim,g,0,-gripLen/2+gripLen*(i+.5)/3,0).rotation.x=Math.PI/2
 mesh(ri>=2?new THREE.OctahedronGeometry(.032):new THREE.IcosahedronGeometry(.028,0),ri>=2?k.gem:k.dark,g,0,-gripLen/2-.025,0)
 tagFx(blade,k);return g
}

function hafted(k:Kit,length:number,head:(top:THREE.Group)=>void){
 const g=new THREE.Group();mesh(cyl(.022,.026,length,6),k.ri>=3?k.dark:k.wood,g,0,length/2-.25,0)
 if(k.ri>=1)for(const y of [length-.32,-.18])mesh(cyl(.028,.028,.05,6),k.trim,g,0,y,0)
 const top=new THREE.Group();top.position.y=length-.25;g.add(top);head(top);tagFx(top,k);return g
}

function axeHead(k:Kit,top:THREE.Group,size:number,double:boolean){
 const s=new THREE.Shape();s.moveTo(0,-size*.25);s.quadraticCurveTo(size*.55,-size*.7,size*.85,-size*.45);s.quadraticCurveTo(size*1.05,0,size*.85,size*.45);s.quadraticCurveTo(size*.55,size*.7,0,size*.25);s.closePath()
 const sides=double?[1,-1]:[1]
 for(const side of sides){const blade=mesh(extrude(s,.02,.006),k.metal,top,side*.02,-size*.15,0);blade.scale.x=side;if(k.ri>=3){const edge=mesh(extrude(s,.008,0),k.rune,top,side*.024,-size*.15,0);edge.scale.set(side*1.06,1.06,1)}}
 mesh(new THREE.BoxGeometry(.06,size*.5,.06),k.dark,top,0,-size*.15,0)
 if(k.ri>=3&&!double)spikes(top,k.trim,[[-.12,-size*.15,0]],.12,.02)
 if(k.ri>=2)mesh(new THREE.OctahedronGeometry(.025),k.gem,top,0,-size*.1,.04)
 if(k.ri>=4)mesh(new THREE.TorusGeometry(size*.55,.008,4,24),glow(k.p.glow,.6),top,0,-size*.15,0)
}

function maceHead(k:Kit,top:THREE.Group,size:number){
 const {ri}=k
 const ball=mesh(new THREE.IcosahedronGeometry(size*.55,ri>=2?1:0),ri===4?k.metal:ri>=3?k.dark:k.metal,top,0,0,0)
 if(ri>=1&&ri<3)for(let i=0;i<6;i++){const f=mesh(new THREE.BoxGeometry(.012,size*1.1,size*.5),k.metal,top);f.rotation.y=i*Math.PI/3;f.position.set(Math.cos(i*Math.PI/3)*.0,0,0)}
 if(ri>=3){const pos=(ball.geometry as THREE.BufferGeometry).getAttribute('position');const seen=new Set<string>();const pts:[number,number,number][]=[]
  for(let i=0;i<pos.count;i++){const v=[pos.getX(i),pos.getY(i),pos.getZ(i)] as [number,number,number];const key=v.map(n=>n.toFixed(2)).join();if(!seen.has(key)){seen.add(key);pts.push(v)}}
  spikes(top,ri===4?k.metal:k.trim,pts.slice(0,ri===4?20:12).map(([x,y,z])=>[x*1.05,y*1.05,z*1.05]),size*.4,size*.07)}
 if(ri>=2)mesh(new THREE.OctahedronGeometry(size*.22),k.gem,top,0,size*.55,0)
 if(ri>=3)mesh(new THREE.IcosahedronGeometry(size*.6,0),glow(k.p.glow,.25),top)
 if(ri>=4){const halo=mesh(new THREE.TorusGeometry(size*.95,.01,4,28),glow(k.p.glow,.85),top);halo.rotation.x=Math.PI/2;halo.userData.spin=1.4}
}

function staffTop(k:Kit,top:THREE.Group){
 const {ri}=k
 if(ri===0){mesh(new THREE.IcosahedronGeometry(.05,0),k.wood,top,0,.03,0);return}
 if(ri===1){const curl=mesh(new THREE.TorusGeometry(.07,.018,5,10,Math.PI*1.5),k.wood,top,.03,.09,0);curl.rotation.z=-.5;mesh(new THREE.OctahedronGeometry(.03),k.gem,top,0,.09,0);return}
 const n=ri>=3?4:3
 for(let i=0;i<n;i++){const a=i/n*Math.PI*2;const prong=mesh(cyl(.006,.014,.2,5),ri===4?k.metal:ri===3?k.dark:k.trim,top,Math.cos(a)*.05,.1,Math.sin(a)*.05);prong.rotation.set(Math.sin(a)*-.35,0,Math.cos(a)*.35)}
 const orb=mesh(ri===2?new THREE.OctahedronGeometry(.06):new THREE.IcosahedronGeometry(ri===4?.08:.065,1),k.gem,top,0,.16,0);orb.userData.float=1
 mesh(new THREE.IcosahedronGeometry(ri===4?.16:.11,1),glow(k.p.glow,ri===4?.35:.22),top,0,.16,0)
 if(ri>=3)for(let i=0;i<(ri===4?5:3);i++){const shard=mesh(new THREE.OctahedronGeometry(.018),ri===4?k.gem:k.rune,top,Math.cos(i*2.1)*.13,.16+Math.sin(i*1.7)*.05,Math.sin(i*2.1)*.13);shard.userData.orbit={r:.13,speed:1.6,phase:i*1.25,y:.16}}
 if(ri===4){for(const tilt of [0,1]){const ring=mesh(new THREE.TorusGeometry(.17,.006,4,32),glow(k.p.glow,.9),top,0,.16,0);ring.rotation.set(Math.PI/2+tilt*.6,0,tilt*.4);ring.userData.spin=tilt?-.9:1.1}}
}

function bow(k:Kit,height:number){
 const g=new THREE.Group();const {ri}=k;const h=height/2
 // One curved stave through the grip; recurve tips get more pronounced with rarity.
 const curl=.02+ri*.012
 const curve=new THREE.CatmullRomCurve3([new THREE.Vector3(curl,h,0),new THREE.Vector3(-.1,h*.62,0),new THREE.Vector3(-.17,h*.22,0),new THREE.Vector3(-.18,0,0),new THREE.Vector3(-.17,-h*.22,0),new THREE.Vector3(-.1,-h*.62,0),new THREE.Vector3(curl,-h,0)])
 mesh(new THREE.TubeGeometry(curve,28,.016+ri*.003,5),ri>=3?k.dark:k.wood,g)
 const string=mesh(cyl(.0035,.0035,height*.99,4),ri>=3?k.rune:mat('#ddd6c4'),g,curl,0,0)
 if(ri>=1)for(const s of [1,-1])mesh(new THREE.IcosahedronGeometry(.022,0),k.trim,g,curl,s*h,0)
 if(ri>=2)for(const s of [1,-1])mesh(new THREE.ConeGeometry(.016,.09,5),k.trim,g,curl+.02,s*(h+.04),0).rotation.z=s>0?-.35:Math.PI+.35
 if(ri>=3)for(const s of [1,-1])for(let i=1;i<=2;i++){const sp=mesh(new THREE.ConeGeometry(.013,.08,4),k.trim,g,-.17-.02,s*h*(.25+i*.18),0);sp.rotation.z=Math.PI/2}
 if(ri>=4){string.scale.x=2.4;for(const s of [1,-1]){const wing=new THREE.Shape();wing.moveTo(0,0);wing.quadraticCurveTo(-.2,.08,-.16,.34);wing.quadraticCurveTo(-.08,.14,0,.06);const m=mesh(extrude(wing,.01,.003),k.metal,g,-.12,s*h*.45,0);m.scale.y=s}}
 mesh(cyl(.026,.026,.14,6),k.leather,g,-.18,0,0)
 if(ri>=2)mesh(new THREE.OctahedronGeometry(.026),k.gem,g,-.2,.09,0)
 tagFx(g,k);return g
}

function shield(k:Kit){
 const g=new THREE.Group();const {ri}=k
 if(ri<=1){mesh(cyl(.26,.26,.04,ri?10:8),ri?k.metal:k.wood,g).rotation.x=Math.PI/2;mesh(new THREE.TorusGeometry(.26,.02,4,ri?12:8),k.dark,g);mesh(new THREE.IcosahedronGeometry(.06,0),k.dark,g,0,0,.03)}
 else{
  const s=new THREE.Shape();s.moveTo(-.25,.3);s.lineTo(.25,.3);s.quadraticCurveTo(.27,-.05,0,-.36);s.quadraticCurveTo(-.27,-.05,-.25,.3)
  mesh(extrude(s,.035,.012),k.metal,g)
  const rim=mesh(extrude(s,.02,0),ri>=3?k.trim:k.dark,g,0,0,-.012);rim.scale.set(1.08,1.06,1)
  const emblem=new THREE.Shape();emblem.moveTo(0,.16);emblem.lineTo(.1,0);emblem.lineTo(0,-.18);emblem.lineTo(-.1,0);emblem.closePath()
  mesh(extrude(emblem,.012,.004),ri>=3?k.rune:k.trim,g,0,.02,.03)
  mesh(new THREE.OctahedronGeometry(.04),k.gem,g,0,.02,.045)
  if(ri>=3)spikes(g,ri===4?k.metal:k.trim,[[-.27,.26,0],[.27,.26,0],[0,-.38,0]],.12,.025)
  if(ri>=4)for(let i=0;i<8;i++){const ray=mesh(new THREE.BoxGeometry(.012,.12,.006),glow(k.p.glow,.9),g,0,.02,.05);ray.rotation.z=i*Math.PI/4;ray.translateY(.14)}
 }
 tagFx(g,k);return g
}

function tome(k:Kit){
 const g=new THREE.Group();const {ri}=k
 mesh(new THREE.BoxGeometry(.2,.26,.012),ri>=3?k.dark:k.leather,g,0,0,.031)
 mesh(new THREE.BoxGeometry(.2,.26,.012),ri>=3?k.dark:k.leather,g,0,0,-.031)
 mesh(new THREE.BoxGeometry(.016,.26,.074),ri>=3?k.dark:k.leather,g,-.1,0,0)
 // Pages sit inside the cover and show only along the open edge.
 mesh(new THREE.BoxGeometry(.18,.235,.05),mat('#efe6cf',{rough:.9}),g,.014,0,0)
 if(ri>=1)for(const [x,y] of [[-.09,.12],[-.09,-.12],[.09,.12],[.09,-.12]])mesh(new THREE.BoxGeometry(.04,.04,.08),k.trim,g,x,y,0)
 if(ri>=2)mesh(new THREE.OctahedronGeometry(.035),k.gem,g,0,0,.045)
 if(ri>=3){const sigil=mesh(new THREE.TorusGeometry(.06,.006,4,6),k.rune,g,0,0,.04);sigil.userData.spin=.6}
 if(ri>=4){const ring=mesh(new THREE.TorusGeometry(.22,.006,4,32),glow(k.p.glow,.85),g);ring.rotation.x=Math.PI/2.4;ring.userData.spin=.8}
 g.userData.float=1;tagFx(g,k);return g
}

function orb(k:Kit){
 const g=new THREE.Group();const {ri}=k
 const glass=mesh(new THREE.IcosahedronGeometry(.09,ri>=2?2:1),mat(k.p.gem,{emissive:k.p.gem,glow:.8+ri*.5,rough:.1,opacity:.85}),g);glass.userData.float=1
 mesh(new THREE.IcosahedronGeometry(.14+ri*.02,1),glow(k.p.glow,.18+ri*.06),g)
 for(let i=0;i<(ri>=3?4:3);i++){const a=i/(ri>=3?4:3)*Math.PI*2;const claw=mesh(new THREE.ConeGeometry(.012,.11,4),ri===4?k.metal:k.dark,g,Math.cos(a)*.08,-.07,Math.sin(a)*.08);claw.rotation.set(Math.sin(a)*.6,0,-Math.cos(a)*.6)}
 if(ri>=4)for(let i=0;i<4;i++){const mote=mesh(new THREE.OctahedronGeometry(.016),k.gem,g);mote.userData.orbit={r:.17,speed:2,phase:i*Math.PI/2,y:0}}
 tagFx(g,k);return g
}

const PROFILE:Record<string,(k:Kit)=>THREE.Group>={
 sword:k=>bladeWeapon(k,.72,.07,.16),greatsword:k=>bladeWeapon(k,1.15,.135,.34),dagger:k=>bladeWeapon(k,.32,.055,.1),
 axe:k=>hafted(k,.72,top=>axeHead(k,top,.2,k.ri>=4)),greataxe:k=>hafted(k,1.25,top=>axeHead(k,top,.3,true)),
 mace:k=>hafted(k,.62,top=>maceHead(k,top,.16)),
 warhammer:k=>hafted(k,1.15,top=>{mesh(new THREE.BoxGeometry(.32,.16,.16),k.ri>=3?k.dark:k.metal,top,0,0,0);if(k.ri>=1)for(const s of [-1,1])mesh(new THREE.BoxGeometry(.04,.19,.19),k.trim,top,s*.13,0,0);if(k.ri>=2)mesh(new THREE.OctahedronGeometry(.04),k.gem,top,0,0,.09);if(k.ri>=3)spikes(top,k.trim,[[0,.12,0]],.16,.03);if(k.ri>=4){for(const s of [-1,1]){const w=new THREE.Shape();w.moveTo(0,0);w.quadraticCurveTo(.08,.12,.2,.16);w.quadraticCurveTo(.1,.05,0,.04);mesh(extrude(w,.012,.003),k.metal,top,s*.16,.04,0).scale.x=s}}}),
 polearm:k=>hafted(k,1.7,top=>{const tip=new THREE.Shape();tip.moveTo(-.035,0);tip.lineTo(0,.3+k.ri*.04);tip.lineTo(.035,0);tip.closePath();mesh(extrude(tip,.016,.005),k.metal,top,0,.04,0);if(k.ri>=2)axeHead(k,top,.18+k.ri*.03,k.ri>=4);if(k.ri>=1)mesh(cyl(.035,.035,.06,6),k.trim,top,0,.02,0)}),
 staff:k=>hafted(k,1.55,top=>staffTop(k,top)),
 wand:k=>{const g=hafted(k,.36,top=>{mesh(k.ri>=2?new THREE.OctahedronGeometry(.035+k.ri*.006):new THREE.IcosahedronGeometry(.025,0),k.gem,top,0,.03,0);if(k.ri>=3)mesh(new THREE.IcosahedronGeometry(.07,1),glow(k.p.glow,.3),top,0,.03,0);if(k.ri>=4){const r=mesh(new THREE.TorusGeometry(.07,.004,4,20),glow(k.p.glow,.9),top,0,.03,0);r.userData.spin=2}});g.position.y=.18;return g},
 fist:k=>{const g=new THREE.Group();mesh(new THREE.BoxGeometry(.12,.05,.05),k.ri>=3?k.dark:k.metal,g);for(const x of [-.04,0,.04]){const c=new THREE.Shape();c.moveTo(0,0);c.quadraticCurveTo(.03,.12,0,.22+k.ri*.03);c.quadraticCurveTo(-.01,.1,-.02,0);c.closePath();mesh(extrude(c,.012,.003),k.metal,g,x,.02,0)}if(k.ri>=2)mesh(new THREE.OctahedronGeometry(.022),k.gem,g,0,0,.03);if(k.ri>=3)mesh(new THREE.BoxGeometry(.13,.012,.02),k.rune,g,0,.02,.026);tagFx(g,k);return g},
 warglaive:k=>{const g=new THREE.Group();const c=new THREE.Shape();const R=.3+k.ri*.03;c.absarc(0,0,R,-.2,Math.PI+.2,false);c.absarc(0,-.06,R*.78,Math.PI+.1,-.1,true);c.closePath();mesh(extrude(c,.016,.005),k.metal,g,0,.05,0);mesh(cyl(.02,.02,.16,6),k.leather,g,0,.0,0).rotation.z=Math.PI/2;if(k.ri>=2)mesh(new THREE.OctahedronGeometry(.03),k.gem,g,0,.06,.02);if(k.ri>=3){const e=mesh(extrude(c,.006,0),k.rune,g,0,.05,0);e.scale.setScalar(1.04)}tagFx(g,k);return g},
 bow:k=>bow(k,1.15),
 crossbow:k=>{const g=new THREE.Group();mesh(new THREE.BoxGeometry(.06,.07,.55),k.wood,g,0,0,.1);const arms=bow(k,.6);arms.rotation.set(0,Math.PI/2,Math.PI/2);arms.position.z=.32;g.add(arms);return g},
 gun:k=>{const g=new THREE.Group();mesh(cyl(.025,.03,.6,7),k.metal,g,0,.04,.25).rotation.x=Math.PI/2;mesh(new THREE.BoxGeometry(.06,.12,.32),k.wood,g,0,-.02,-.08);if(k.ri>=1)mesh(cyl(.035,.035,.05,7),k.trim,g,0,.04,.5).rotation.x=Math.PI/2;if(k.ri>=2){mesh(cyl(.018,.018,.16,6),k.dark,g,0,.1,.12).rotation.x=Math.PI/2;mesh(new THREE.OctahedronGeometry(.02),k.gem,g,0,.1,.21)}if(k.ri>=3)mesh(new THREE.BoxGeometry(.012,.02,.5),k.rune,g,.03,.04,.25);tagFx(g,k);return g},
 shield,tome,orb,
}

/** How each weapon sits in the hand joint (weapon local +Y is its business end). */
function holdWeapon(base:string,obj:THREE.Object3D,hand:'L'|'R'){
 const two=['greatsword','greataxe','warhammer'].includes(base)
 if(base==='staff'||base==='polearm'){obj.rotation.set(.12,0,0);obj.position.set(0,-.02,0);return}
 if(base==='bow'){obj.rotation.set(0,Math.PI/2,0);return}
 if(base==='gun'||base==='crossbow'){obj.rotation.set(-Math.PI/2+.1,0,0);obj.position.set(0,-.05,.05);return}
 if(base==='shield'){obj.position.set(hand==='L'?-.09:.09,-.12,0);obj.rotation.set(0,hand==='L'?-Math.PI/2:Math.PI/2,0);return}
 if(base==='tome'||base==='orb'){obj.position.set(hand==='L'?-.06:.06,-.08,.18);return}
 if(base==='fist'){obj.rotation.set(Math.PI/2,0,0);obj.position.set(0,-.06,.02);return}
 if(base==='warglaive'){obj.rotation.set(Math.PI/2,0,0);obj.position.set(0,-.04,.04);return}
 obj.rotation.set(Math.PI/2-(two?.25:.35),0,0);obj.position.set(0,-.04,0)
}

export function weaponModel(look:GearLook){const k=kit(look);const build=PROFILE[look.base]||PROFILE.sword;return build(k)}

function armorMaterial(k:Kit){const t=k.look.base;return t==='plate'?k.metal:t==='mail'?k.mail:t==='leather'?k.leather:k.fabric}

/** Returns gear meshes with the joint each one attaches to. Symmetric slots produce L and R parts. */
export function gearParts(look:GearLook,d:Dims):GearPart[]{
 const k=kit(look);const {ri}=k;const type=look.base;const main=armorMaterial(k)
 const parts:GearPart[]=[]
 const add=(joint:JointName,object:THREE.Object3D,side?:'L'|'R')=>{parts.push({joint,object,side});return object}
 if(look.slot==='mainhand'||look.slot==='offhand'){
  const hand=look.slot==='offhand'||look.base==='bow'?'L':'R'
  const obj=weaponModel(look);holdWeapon(look.base,obj,hand)
  const joint:JointName=look.base==='shield'?(hand==='L'?'elbowL':'elbowR'):hand==='L'?'handL':'handR'
  if(look.base==='shield')obj.position.y-=d.foreArm*.45
  add(joint,obj,hand);return parts
 }
 if(look.slot==='head'){
  const g=new THREE.Group();const r=d.headR
  if(type==='cloth'){const hood=mesh(new THREE.SphereGeometry(r*1.18,8,6,0,Math.PI*2,0,Math.PI*.62),main,g,0,r*.05,-r*.05);hood.rotation.x=-.25
   if(ri>=1)mesh(new THREE.TorusGeometry(r*1.02,r*.07,4,14),k.trim,g,0,r*.32,r*.05).rotation.x=Math.PI/2.3
   if(ri>=2)mesh(new THREE.OctahedronGeometry(r*.16),k.gem,g,0,r*.48,r*.95)
   if(ri>=3)spikes(g,k.trim,[[-r*.6,r*1.05,0],[0,r*1.2,0],[r*.6,r*1.05,0]],r*.5,r*.07)}
  else{
   const helm=mesh(new THREE.SphereGeometry(r*1.16,9,7,0,Math.PI*2,0,Math.PI*(type==='plate'?.78:.6)),main,g,0,r*.08,0)
   if(type==='plate'){mesh(new THREE.BoxGeometry(r*1.4,r*.12,r*.2),mat('#0b0b0d'),g,0,r*.1,r*1.06);if(ri>=3)mesh(new THREE.BoxGeometry(r*1.2,r*.07,r*.06),k.rune,g,0,r*.1,r*1.15);mesh(new THREE.BoxGeometry(r*.14,r*.7,r*.12),ri>=1?k.trim:k.dark,g,0,r*.65,r*.98)}
   if(type==='mail')mesh(cyl(r*1.05,r*1.25,r*.6,9,true),main,g,0,-r*.55,-r*.05)
   if(type==='leather'){mesh(new THREE.BoxGeometry(r*1.5,r*.16,r*.25),k.dark,g,0,r*.32,r*.95)}
   if(ri>=1)mesh(new THREE.TorusGeometry(r*1.15,r*.06,4,16),k.trim,g,0,r*.12,0).rotation.x=Math.PI/2
   if(ri>=2&&type!=='plate')mesh(new THREE.OctahedronGeometry(r*.16),k.gem,g,0,r*.55,r*1.02)
   if(ri===2){const crest=mesh(new THREE.BoxGeometry(r*.12,r*.45,r*1.5),type==='plate'?k.fabric:k.trim,g,0,r*1.15,-r*.1);crest.rotation.x=.15}
   if(ri>=3)for(const s of [-1,1]){const horn=mesh(new THREE.TorusGeometry(r*.75,r*.11,5,8,Math.PI*.7),ri===4?k.metal:k.dark,g,s*r*1.05,r*.55,0);horn.rotation.set(0,s*Math.PI/2,Math.PI*.1)}
  }
  if(ri>=4){for(let i=0;i<5;i++){const a=(i-2)*.38;mesh(new THREE.ConeGeometry(r*.09,r*(.55-Math.abs(i-2)*.08),4),k.metal,g,Math.sin(a)*r*1.05,r*1.05,Math.cos(a)*r*.6)}
   const halo=mesh(new THREE.TorusGeometry(r*.85,r*.035,4,32),glow(k.p.glow,.9),g,0,r*1.75,-r*.15);halo.rotation.x=Math.PI/2.2;halo.userData.spin=.5}
  tagFx(g,k);add('head',g);return parts
 }
 if(look.slot==='shoulders'){
  for(const side of ['L','R'] as const){
   const s=side==='L'?-1:1;const g=new THREE.Group();const size=d.armR*(2.2+ri*.35)*(type==='plate'?1.15:1)
   const dome=mesh(new THREE.SphereGeometry(size,8,5,0,Math.PI*2,0,Math.PI*.5),main,g,0,0,0);dome.scale.set(1.1,.75,1)
   if(type==='plate'||type==='mail')for(let i=1;i<=(ri>=2?2:1);i++){const layer=mesh(new THREE.SphereGeometry(size*(1-i*.1),8,4,0,Math.PI*2,Math.PI*.35,Math.PI*.15),main,g,s*size*.08*i,-size*.08*i,0);layer.scale.set(1.15,.9,1.05)}
   if(type==='cloth')mesh(cyl(size*.95,size*1.1,size*.35,8,true),k.fabricDark,g,0,-size*.15,0)
   if(ri>=1)mesh(new THREE.TorusGeometry(size*.98,size*.07,4,14),k.trim,g,0,0,0).rotation.x=Math.PI/2
   if(ri>=2)mesh(new THREE.OctahedronGeometry(size*.2),k.gem,g,s*size*.55,size*.38,size*.2)
   if(ri>=3)spikes(g,ri===4?k.metal:k.trim,[[s*size*.2,size*.7,0],[s*size*.6,size*.45,-size*.2],[s*size*.6,size*.45,size*.2]],size*(ri===4?1.1:.8),size*.12)
   if(ri>=4){const flame=mesh(new THREE.ConeGeometry(size*.5,size*1.3,6,1,true),glow(k.p.glow,.45),g,s*size*.25,size*.85,0);flame.userData.flicker=1}
   g.position.set(s*d.armR*.3,d.armR*.55,0);tagFx(g,k);add(side==='L'?'shoulderL':'shoulderR',g,side)
  }
  return parts
 }
 if(look.slot==='chest'){
  const g=new THREE.Group()
  const shell=mesh(cyl(d.chestR*1.1,d.waistR*1.12,d.torso*.98,9),main,g,0,d.torso/2,0);shell.scale.z=.78
  mesh(new THREE.TorusGeometry(d.chestR*.62,d.chestR*.09,4,12),ri>=1?k.trim:main,g,0,d.torso*.98,0).rotation.x=Math.PI/2
  mesh(cyl(d.waistR*1.18,d.waistR*1.18,.07,9),type==='plate'?k.dark:k.leather,g,0,.03,0).scale.z=.8
  if(type==='cloth'){const skirt=mesh(cyl(d.waistR*1.15,d.waistR*1.7,d.leg*.62,9,true),main,g,0,-d.leg*.28,0);skirt.scale.z=.85;(skirt.material as THREE.Material).side=THREE.DoubleSide
   if(ri>=1)mesh(cyl(d.waistR*1.72,d.waistR*1.74,.04,9,true),k.trim,g,0,-d.leg*.58,0).scale.z=.85}
  if(type==='mail'){const skirt=mesh(cyl(d.waistR*1.15,d.waistR*1.4,d.leg*.3,9,true),main,g,0,-d.leg*.12,0);skirt.scale.z=.85}
  if(type==='leather')for(const s of [-1,1]){const strap=mesh(new THREE.BoxGeometry(.035,d.torso*1.05,.02),k.dark,g,0,d.torso*.52,d.chestR*.78);strap.rotation.z=s*.55}
  if(type==='plate'){mesh(new THREE.BoxGeometry(.04,d.torso*.6,.04),ri>=1?k.trim:k.dark,g,0,d.torso*.62,d.chestR*.82);for(let i=0;i<3;i++)mesh(new THREE.BoxGeometry(d.waistR*1.3,.05,.04),k.dark,g,0,d.torso*(.12+i*.09),d.waistR*.86)}
  if(ri>=2){const emblem=mesh(new THREE.OctahedronGeometry(d.chestR*.16),k.gem,g,0,d.torso*.72,d.chestR*.86);emblem.scale.z=.5}
  if(ri>=3)for(const s of [-1,1]){const r=mesh(new THREE.BoxGeometry(.02,d.torso*.55,.012),k.rune,g,s*d.chestR*.42,d.torso*.5,d.chestR*.8);r.rotation.z=s*.12}
  if(ri>=4){const core=mesh(new THREE.IcosahedronGeometry(d.chestR*.2,1),glow(k.p.glow,.7),g,0,d.torso*.72,d.chestR*.9);core.userData.pulse=1}
  tagFx(g,k);add('spine',g);return parts
 }
 if(look.slot==='hands'){
  for(const side of ['L','R'] as const){
   const glove=new THREE.Group();mesh(new THREE.IcosahedronGeometry(.072*Math.sqrt(d.bulk)*(1+ri*.05),0),type==='plate'?k.metal:main,glove,0,-.02,0)
   if(ri>=2)mesh(new THREE.OctahedronGeometry(.022),k.gem,glove,0,-.01,.06)
   if(ri>=3)spikes(glove,k.trim,[[0,0,.07],[side==='L'?-.05:.05,0,.05]],.07,.012)
   if(ri>=4)mesh(new THREE.IcosahedronGeometry(.1,1),glow(k.p.glow,.3),glove,0,-.02,0)
   const bracer=new THREE.Group();mesh(cyl(d.foreR*1.3,d.foreR*1.15+ri*.006,d.foreArm*.55,8),main,bracer,0,-d.foreArm*.7,0)
   if(ri>=1)mesh(new THREE.TorusGeometry(d.foreR*1.32,.012,4,10),k.trim,bracer,0,-d.foreArm*.44,0).rotation.x=Math.PI/2
   if(ri>=3)mesh(new THREE.BoxGeometry(.015,d.foreArm*.4,.01),k.rune,bracer,0,-d.foreArm*.7,d.foreR*1.3)
   tagFx(glove,k);add(side==='L'?'handL':'handR',glove,side);add(side==='L'?'elbowL':'elbowR',bracer,side)
  }
  return parts
 }
 if(look.slot==='legs'){
  for(const side of ['L','R'] as const){
   const thigh=new THREE.Group();mesh(cyl(d.legR*1.18,d.legR*1.05,d.leg*.5,8),main,thigh,0,-d.leg*.25,0)
   const shin=new THREE.Group();mesh(cyl(d.shinR*1.2,d.shinR*1.05,d.leg*.42,8),main,shin,0,-d.leg*.2,0)
   if(type==='plate'||type==='mail'){mesh(new THREE.IcosahedronGeometry(d.shinR*1.25,0),ri>=1?k.trim:k.dark,shin,0,0,d.shinR*.5)}
   if(ri>=2)mesh(new THREE.OctahedronGeometry(.02),k.gem,shin,0,0,d.shinR*1.3)
   if(ri>=3)spikes(shin,k.trim,[[0,0,d.shinR*1.2]],.08,.015)
   if(ri>=3)mesh(new THREE.BoxGeometry(.015,d.leg*.35,.01),k.rune,thigh,0,-d.leg*.25,d.legR*1.15)
   add(side==='L'?'hipL':'hipR',thigh,side);add(side==='L'?'kneeL':'kneeR',shin,side)
  }
  const belt=new THREE.Group();mesh(cyl(d.waistR*1.16,d.waistR*1.16,.07,9),type==='cloth'?k.fabricDark:k.leather,belt,0,.04,0).scale.z=.8
  mesh(new THREE.BoxGeometry(.07,.06,.02),ri>=1?k.trim:k.dark,belt,0,.04,d.waistR*.95);tagFx(belt,k);add('hips',belt)
  return parts
 }
 if(look.slot==='feet'){
  for(const side of ['L','R'] as const){
   const g=new THREE.Group();const s=Math.sqrt(d.bulk)
   mesh(new THREE.BoxGeometry(.13*s,.09,.25),type==='plate'?k.metal:main,g,0,.045,.05)
   mesh(cyl(d.shinR*1.25,d.shinR*1.15,.2,8),main,g,0,.15,0)
   if(ri>=1)mesh(cyl(d.shinR*1.35,d.shinR*1.35,.035,8),k.trim,g,0,.25,0)
   if(ri>=2)mesh(new THREE.OctahedronGeometry(.02),k.gem,g,0,.12,d.shinR*1.2)
   if(ri>=3)spikes(g,k.trim,[[0,.12,-d.shinR*1.2]],.08,.014)
   if(ri>=4)for(const w of [-1,1]){const wing=new THREE.Shape();wing.moveTo(0,0);wing.quadraticCurveTo(.05,.05,.12,.14);wing.quadraticCurveTo(.05,.03,0,.05);const m=mesh(extrude(wing,.008,.002),k.metal,g,w*d.shinR*1.1,.17,-.02);m.rotation.y=w*Math.PI/2;m.scale.x=-1}
   tagFx(g,k);add(side==='L'?'footL':'footR',g,side)
  }
  return parts
 }
 if(look.slot==='back'){
  const g=new THREE.Group();const w=d.chestR*2.1,h=d.torso*.9+d.leg*(.55+ri*.06)
  const geo=new THREE.PlaneGeometry(w,h,4,6);const pos=geo.getAttribute('position')
  for(let i=0;i<pos.count;i++){const x=pos.getX(i),y=pos.getY(i);const t=(h/2-y)/h;pos.setZ(i,-Math.cos(x/w*Math.PI)*.04-t*.12);pos.setX(i,x*(1+t*.25));if(ri>=3&&t>.95)pos.setY(i,y+(i%2?.08:0))}
  geo.computeVertexNormals();const cloth=mesh(geo,mat(k.p.fabric,{rough:.95,side:THREE.DoubleSide}),g,0,-h/2,0)
  cloth.userData.cloak=1
  if(ri>=1)mesh(new THREE.BoxGeometry(w*1.22,.03,.012),ri>=3?k.rune:k.trim,g,0,-h+.02,-.13)
  mesh(new THREE.IcosahedronGeometry(.035,0),ri>=2?k.gem:k.trim,g,0,.02,.04)
  if(ri>=3){const sigil=mesh(new THREE.TorusGeometry(.08,.008,4,6),k.rune,g,0,-h*.35,-.06);sigil.rotation.y=Math.PI}
  if(ri>=4){const hem=mesh(new THREE.BoxGeometry(w*1.25,.06,.01),glow(k.p.glow,.8),g,0,-h+.02,-.14);hem.userData.flicker=1}
  tagFx(g,k);add('back',g);return parts
 }
 return parts
}

/** Plain trousers so an unequipped hero is never bare-legged. */
export function underclothes(d:Dims):GearPart[]{
 const m=mat('#4a4038',{rough:.95});const parts:GearPart[]=[]
 for(const side of ['L','R'] as const){const g=new THREE.Group();mesh(cyl(d.legR*1.1,d.legR*1.02,d.leg*.48,7),m,g,0,-d.leg*.24,0);parts.push({joint:side==='L'?'hipL':'hipR',object:g,side})}
 return parts
}
