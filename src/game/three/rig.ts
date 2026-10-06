import * as THREE from 'three'
import {mat,glow} from './materials'

type Feature='hair'|'bigHair'|'ponytail'|'mohawk'|'topknot'|'beard'|'longEars'|'bigEars'|'horns'|'bullHorns'|'tusks'|'bigTusks'|'tail'|'hooves'|'wolf'|'bull'|'panda'|'bigNose'|'tendrils'|'jaw'
export type RaceShape={height:number;bulk:number;head:number;legs:number;skin:string;skin2?:string;hair:string;eye:string;eyeGlow?:boolean;hunch:number;features:Feature[]}

export const RACES:Record<string,RaceShape>={
 human:{height:1,bulk:1,head:1,legs:1,skin:'#dfa983',hair:'#4b2f1c',eye:'#2a2a2a',hunch:0,features:['hair']},
 dwarf:{height:.74,bulk:1.4,head:1.1,legs:.78,skin:'#dc9f7d',hair:'#a24f1e',eye:'#2a2a2a',hunch:0,features:['hair','beard']},
 nightelf:{height:1.13,bulk:.95,head:.95,legs:1.08,skin:'#9a86d0',hair:'#3fd0b5',eye:'#dff4ff',eyeGlow:true,hunch:0,features:['longEars','hair','ponytail']},
 gnome:{height:.56,bulk:.95,head:1.5,legs:.82,skin:'#f0c4a4',hair:'#ff6fae',eye:'#2a2a2a',hunch:0,features:['bigHair']},
 draenei:{height:1.14,bulk:1.12,head:.98,legs:1.05,skin:'#7fa6e6',hair:'#232a3d',eye:'#e8f4ff',eyeGlow:true,hunch:0,features:['horns','tail','hooves','tendrils']},
 worgen:{height:1.1,bulk:1.22,head:1.06,legs:1,skin:'#5c4a3a',skin2:'#8a7660',hair:'#3b2f24',eye:'#ffd23a',eyeGlow:true,hunch:.2,features:['wolf','tail','longEars']},
 orc:{height:1.02,bulk:1.34,head:1.02,legs:.96,skin:'#5f8f3b',hair:'#1a1a1a',eye:'#c8381a',hunch:.12,features:['tusks','topknot']},
 undead:{height:.98,bulk:.8,head:.95,legs:1,skin:'#8c9a8a',hair:'#34343a',eye:'#ffe35a',eyeGlow:true,hunch:.08,features:['jaw','hair']},
 tauren:{height:1.25,bulk:1.58,head:1.1,legs:.98,skin:'#7a5034',skin2:'#a9825e',hair:'#2f2016',eye:'#1a1a1a',hunch:.1,features:['bull','bullHorns','hooves','tail']},
 troll:{height:1.12,bulk:1.02,head:1,legs:1.08,skin:'#4e8fa0',hair:'#d8432a',eye:'#ffe8a0',hunch:.16,features:['bigTusks','longEars','mohawk','bigNose']},
 bloodelf:{height:1.03,bulk:.9,head:.95,legs:1.05,skin:'#f1d3b5',hair:'#f2d27a',eye:'#7dff7d',eyeGlow:true,hunch:0,features:['longEars','hair']},
 goblin:{height:.62,bulk:.9,head:1.35,legs:.82,skin:'#72a843',hair:'#1a1a1a',eye:'#ffcf3a',hunch:.08,features:['bigEars','bigNose']},
 pandaren:{height:1.08,bulk:1.52,head:1.14,legs:.92,skin:'#f3f0e8',skin2:'#1d1d1f',hair:'#1d1d1f',eye:'#1a1a1a',hunch:0,features:['panda']},
}

export type Dims={bulk:number;leg:number;torso:number;chestR:number;waistR:number;armR:number;foreR:number;legR:number;shinR:number;headR:number;shoulderX:number;hipX:number;upperArm:number;foreArm:number}
export type JointName='root'|'hips'|'spine'|'chest'|'neck'|'head'|'shoulderL'|'shoulderR'|'elbowL'|'elbowR'|'handL'|'handR'|'hipL'|'hipR'|'kneeL'|'kneeR'|'footL'|'footR'|'back'
export type Rig={root:THREE.Group;joints:Record<JointName,THREE.Group>;dims:Dims;race:RaceShape;body:THREE.Object3D[];hooves:boolean}

export function dimsFor(race:RaceShape):Dims{
 const b=race.bulk,l=race.legs
 return {bulk:b,leg:.84*l,torso:.6,chestR:.25*b,waistR:.19*b,armR:.072*Math.sqrt(b),foreR:.062*Math.sqrt(b),legR:.095*Math.sqrt(b),shinR:.072*Math.sqrt(b),headR:.17*race.head,shoulderX:.27*b+.02,hipX:.105*b,upperArm:.32,foreArm:.3}
}

const cyl=(rt:number,rb:number,h:number,seg=7)=>new THREE.CylinderGeometry(rt,rb,h,seg)
function part(geo:THREE.BufferGeometry,material:THREE.Material,parent:THREE.Object3D,x=0,y=0,z=0,body?:THREE.Object3D[]){
 const m=new THREE.Mesh(geo,material);m.position.set(x,y,z);m.castShadow=true;m.receiveShadow=true;parent.add(m);body?.push(m);return m
}
function joint(parent:THREE.Object3D,x:number,y:number,z:number){const g=new THREE.Group();g.position.set(x,y,z);parent.add(g);return g}

/** Builds a jointed low-poly body. Joints are plain groups so animation is just rotations. */
export function buildRig(raceId:string):Rig{
 const race=RACES[raceId]||RACES.human;const d=dimsFor(race);const body:THREE.Object3D[]=[]
 const skin=mat(race.skin,{rough:.75});const skin2=mat(race.skin2||race.skin,{rough:.8});const hair=mat(race.hair,{rough:.9})
 const panda=race.features.includes('panda');const limb=panda?skin2:skin
 const root=new THREE.Group();root.scale.setScalar(race.height)
 const hips=joint(root,0,d.leg,0)
 part(new THREE.BoxGeometry(d.waistR*2.1,.16,d.waistR*1.4),skin,hips,0,.02,0,body)
 const spine=joint(hips,0,.06,0);spine.rotation.x=race.hunch
 const torsoMesh=part(cyl(d.chestR,d.waistR,d.torso,8),skin,spine,0,d.torso/2,0,body);torsoMesh.scale.z=.72
 if(race.skin2&&!panda){const belly=part(cyl(d.chestR*.8,d.waistR*.8,d.torso*.7,8),skin2,spine,0,d.torso*.42,d.waistR*.22,body);belly.scale.z=.6}
 const chest=joint(spine,0,d.torso,0)
 const neck=joint(chest,0,.02,0);part(cyl(.07*d.bulk,.08*d.bulk,.1,6),skin,neck,0,.04,0,body)
 const head=joint(neck,0,.08+d.headR*.9,0);head.rotation.x=-race.hunch*.8
 buildHead(head,race,d,{skin,skin2,hair},body)
 const back=joint(chest,0,-.05,-d.chestR*.72)
 const arm=(side:1|-1)=>{
  const shoulder=joint(chest,side*d.shoulderX,-.07,0);shoulder.rotation.z=side*.12
  part(new THREE.IcosahedronGeometry(d.armR*1.25,0),panda?skin2:skin,shoulder,0,0,0,body)
  part(cyl(d.armR,d.armR*.85,d.upperArm),limb,shoulder,0,-d.upperArm/2,0,body)
  const elbow=joint(shoulder,0,-d.upperArm,0)
  part(cyl(d.foreR,d.foreR*.85,d.foreArm),limb,elbow,0,-d.foreArm/2,0,body)
  const hand=joint(elbow,0,-d.foreArm-.03,0)
  part(new THREE.IcosahedronGeometry(.062*Math.sqrt(d.bulk),0),limb,hand,0,-.02,0,body)
  return {shoulder,elbow,hand}
 }
 const L=arm(-1),R=arm(1)
 const hooves=race.features.includes('hooves')
 const leg=(side:1|-1)=>{
  const hip=joint(hips,side*d.hipX,-.02,0)
  part(cyl(d.legR,d.legR*.8,d.leg/2),limb,hip,0,-d.leg/4,0,body)
  const knee=joint(hip,0,-d.leg/2,0)
  part(cyl(d.shinR,d.shinR*.75,d.leg/2),limb,knee,0,-d.leg/4,0,body)
  const foot=joint(knee,0,-d.leg/2,0)
  if(hooves)part(cyl(d.shinR*.85,d.shinR*1.05,.08,6),mat('#2b2420',{rough:.6}),foot,0,.04,.01,body)
  else part(new THREE.BoxGeometry(.11*Math.sqrt(d.bulk),.07,.22),limb,foot,0,.035,.05,body)
  return {hip,knee,foot}
 }
 const LL=leg(-1),RL=leg(1)
 if(race.features.includes('tail')){
  const tail=new THREE.Group();tail.position.set(0,.02,-d.waistR*.9);hips.add(tail);tail.rotation.x=.9
  const thick=raceId==='draenei'?.05:.025
  part(cyl(thick*.5,thick,.45,6),raceId==='draenei'?skin:hair,tail,0,-.22,0,body)
  if(raceId!=='draenei')part(new THREE.IcosahedronGeometry(.05,0),hair,tail,0,-.46,0,body)
  tail.userData.sway=1
 }
 const joints={root,hips,spine,chest,neck,head,back,shoulderL:L.shoulder,shoulderR:R.shoulder,elbowL:L.elbow,elbowR:R.elbow,handL:L.hand,handR:R.hand,hipL:LL.hip,hipR:RL.hip,kneeL:LL.knee,kneeR:RL.knee,footL:LL.foot,footR:RL.foot}
 return {root,joints,dims:d,race,body,hooves}
}

function buildHead(head:THREE.Group,race:RaceShape,d:Dims,m:{skin:THREE.Material;skin2:THREE.Material;hair:THREE.Material},body:THREE.Object3D[]){
 const r=d.headR;const f=race.features
 const skull=part(new THREE.IcosahedronGeometry(r,1),m.skin,head,0,0,0,body);skull.scale.set(.95,1.05,1)
 const eyeMat=race.eyeGlow?mat(race.eye,{emissive:race.eye,glow:2.2}):mat(race.eye,{rough:.4})
 const eyeZ=f.includes('wolf')||f.includes('bull')?r*.78:r*.88
 for(const s of [-1,1]){
  const eye=part(new THREE.BoxGeometry(r*.26,r*.12,r*.08),eyeMat,head,s*r*.38,r*.12,eyeZ,body)
  if(race.eyeGlow){const halo=new THREE.Mesh(new THREE.PlaneGeometry(r*.6,r*.35),glow(race.eye,.35));halo.position.copy(eye.position);halo.position.z+=.01;head.add(halo)}
 }
 const hairOn=(geo:THREE.BufferGeometry,x:number,y:number,z:number,sx=1,sy=1,sz=1)=>{const h=part(geo,m.hair,head,x,y,z,body);h.scale.set(sx,sy,sz);return h}
 if(f.includes('hair'))hairOn(new THREE.IcosahedronGeometry(r*1.02,1),0,r*.12,-r*.12,1,.9,1.02)
 if(f.includes('bigHair'))for(const [x,y,z,s] of [[0,.55,-.1,.75],[-.55,.3,-.2,.6],[.55,.3,-.2,.6],[0,.25,-.55,.7]])hairOn(new THREE.IcosahedronGeometry(r*s,0),x*r,y*r+r*.2,z*r)
 if(f.includes('ponytail'))hairOn(new THREE.CylinderGeometry(r*.12,r*.2,r*1.6,5),0,-r*.6,-r*.95).rotation.x=.35
 if(f.includes('mohawk'))for(let i=0;i<5;i++)hairOn(new THREE.BoxGeometry(r*.14,r*(.5-Math.abs(i-2)*.08),r*.3),0,r*1.02,r*(.5-i*.32)).rotation.x=-.2+i*.1
 if(f.includes('topknot')){hairOn(new THREE.IcosahedronGeometry(r*.32,0),0,r*.95,-r*.35);hairOn(new THREE.IcosahedronGeometry(r*.85,1),0,r*.22,-r*.18,1,.7,1)}
 if(f.includes('beard')){const beard=hairOn(new THREE.ConeGeometry(r*.75,r*1.5,6),0,-r*.75,r*.55);beard.rotation.x=Math.PI+.25;hairOn(new THREE.BoxGeometry(r*.9,r*.18,r*.3),0,-r*.18,r*.82)}
 if(f.includes('longEars'))for(const s of [-1,1]){const ear=part(new THREE.ConeGeometry(r*.14,r*1.25,4),m.skin,head,s*r*.95,r*.25,-r*.1,body);ear.rotation.set(-.6,0,-s*1.1)}
 if(f.includes('bigEars'))for(const s of [-1,1]){const ear=part(new THREE.ConeGeometry(r*.32,r*1.1,4),m.skin,head,s*r*1.25,r*.1,0,body);ear.rotation.set(0,0,-s*1.45);ear.scale.z=.35}
 if(f.includes('bigNose')){const nose=part(new THREE.ConeGeometry(r*.13,r*.75,5),m.skin,head,0,-r*.05,r*1.15,body);nose.rotation.x=Math.PI/2+.25}
 if(f.includes('tusks')||f.includes('bigTusks')){const big=f.includes('bigTusks');for(const s of [-1,1]){const t=part(new THREE.ConeGeometry(r*.07,r*(big?.9:.45),5),mat('#d6cba8',{rough:.6}),head,s*r*.32,-r*(big?.15:.38),r*.85,body);t.rotation.set(-.3,0,s*(big?.5:.15))}}
 if(f.includes('horns'))for(const s of [-1,1]){const horn=part(new THREE.TorusGeometry(r*.55,r*.1,5,8,Math.PI*.8),mat('#2d2a33',{rough:.5}),head,s*r*.45,r*.55,-r*.25,body);horn.rotation.set(0,s*Math.PI/2,Math.PI*.15)}
 if(f.includes('tendrils'))for(const s of [-1,1]){const t=part(new THREE.CylinderGeometry(r*.03,r*.07,r*.8,4),m.skin,head,s*r*.28,-r*.85,r*.55,body);t.rotation.x=.25}
 if(f.includes('jaw'))part(new THREE.BoxGeometry(r*.6,r*.18,r*.25),mat('#2a2622'),head,0,-r*.42,r*.78,body)
 if(f.includes('wolf')){
  const snout=part(new THREE.BoxGeometry(r*.62,r*.5,r*.95),m.skin2,head,0,-r*.18,r*.95,body);snout.rotation.x=.12
  part(new THREE.BoxGeometry(r*.24,r*.16,r*.16),mat('#151515'),head,0,-r*.02,r*1.42,body)
  for(const s of [-1,1]){const ear=part(new THREE.ConeGeometry(r*.24,r*.65,4),m.skin,head,s*r*.55,r*.95,-r*.1,body);ear.rotation.z=-s*.25}
 }
 if(f.includes('bull')){
  const muzzle=part(new THREE.BoxGeometry(r*.95,r*.62,r*.7),m.skin2,head,0,-r*.3,r*.88,body);muzzle.rotation.x=.08
  for(const s of [-1,1])part(new THREE.BoxGeometry(r*.12,r*.1,r*.05),mat('#1a1414'),head,s*r*.2,-r*.2,r*1.24,body)
  hairOn(new THREE.IcosahedronGeometry(r*.6,0),0,r*.75,-r*.1,1.3,.5,1)
 }
 if(f.includes('bullHorns'))for(const s of [-1,1]){const horn=part(new THREE.TorusGeometry(r*.6,r*.12,5,8,Math.PI*.6),mat('#e9dfc4',{rough:.55}),head,s*r*.95,r*.45,0,body);horn.rotation.set(Math.PI/2,0,s>0?-.3:Math.PI+.3)}
 if(f.includes('panda')){
  for(const s of [-1,1]){part(new THREE.IcosahedronGeometry(r*.32,0),m.skin2,head,s*r*.72,r*.82,-r*.05,body);const patch=part(new THREE.BoxGeometry(r*.42,r*.3,r*.1),m.skin2,head,s*r*.38,r*.1,r*.84,body);patch.rotation.z=s*.35}
  part(new THREE.BoxGeometry(r*.5,r*.35,r*.4),m.skin,head,0,-r*.32,r*.85,body)
  part(new THREE.BoxGeometry(r*.2,r*.12,r*.08),m.skin2,head,0,-r*.18,r*1.06,body)
 }
}
