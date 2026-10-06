import * as THREE from 'three'
import {buildRig,type Rig} from './rig'
import {gearParts,underclothes} from './gear'
import {Emitter,type Particles} from './fx'
import {disposeTree} from './materials'
import type {GearLook,Role,Slot} from '../types'

export type Appearance={race:string;cls:string;role:Role;gear:Partial<Record<Slot,GearLook>>}
export type Action='attack'|'cast'|'shoot'|'hit'|'death'|'spin'

const SLOTS:Slot[]=['head','shoulders','back','chest','hands','legs','feet','mainhand','offhand']
type Anim={o:THREE.Object3D;base:THREE.Vector3;scale:THREE.Vector3;phase:number}

/** A posable hero: the outer `object` is positioned and faced by callers, the rig inside is animated here. */
export class HeroModel{
 readonly object=new THREE.Group()
 readonly rig:Rig
 readonly emitters:Emitter[]=[]
 private anims:Anim[]=[]
 private cloaks:THREE.Object3D[]=[]
 private action:Action|null=null;private actionT=0;private actionDur=0
 private phase=0;speed=0;dead=false
 readonly role:Role;readonly ranged:boolean
 constructor(readonly look:Appearance){
  this.rig=buildRig(look.race);this.object.add(this.rig.root);this.role=look.role;this.ranged=look.role!=='melee'
  const parts=look.gear.legs||look.gear.chest?.base==='cloth'?[]:underclothes(this.rig.dims)
  for(const slot of SLOTS){const g=look.gear[slot];if(g)parts.push(...gearParts(g,this.rig.dims))}
  for(const p of parts)this.rig.joints[p.joint].add(p.object)
  this.rig.root.traverse(o=>{
   const u=o.userData
   if(u.fx)this.emitters.push(new Emitter(o,u.fx))
   if(u.cloak&&o.parent)this.cloaks.push(o.parent)
   if(u.spin||u.float||u.orbit||u.pulse||u.flicker)this.anims.push({o,base:o.position.clone(),scale:o.scale.clone(),phase:Math.random()*6})
   const m=o as THREE.Mesh;if(m.isMesh){m.castShadow=true}
  })
 }
 get height(){return 1.9*this.rig.race.height}
 play(action:Action,duration=action==='attack'?.38:action==='hit'?.22:action==='death'?.7:.42){
  if(this.dead&&action!=='death')return
  if(action==='hit'&&this.action&&this.action!=='hit')return
  this.action=action;this.actionT=0;this.actionDur=duration;if(action==='death')this.dead=true
 }
 stopSpin(){if(this.action==='spin')this.action=null}
 revive(){this.dead=false;this.action=null;this.rig.root.rotation.set(0,0,0);this.rig.root.position.y=0}
 update(dt:number,time:number,particles?:Particles,fxIntensity=1){
  const j=this.rig.joints;const s=Math.min(1,this.speed)
  this.phase+=dt*(4+8*s)
  const sw=Math.sin(this.phase)
  // Base pose: breathing idle blended with a run cycle.
  j.hips.position.y=this.rig.dims.leg+Math.abs(sw)*.035*s+Math.sin(time*1.7)*.006*(1-s)
  j.hipL.rotation.x=-sw*.75*s;j.hipR.rotation.x=sw*.75*s
  j.kneeL.rotation.x=Math.max(0,-Math.cos(this.phase))*1.1*s;j.kneeR.rotation.x=Math.max(0,Math.cos(this.phase))*1.1*s
  j.chest.rotation.x=Math.sin(time*1.7)*.025*(1-s)+.12*s;j.spine.rotation.y=sw*.12*s
  j.shoulderL.rotation.set(sw*.6*s,0,-.12-Math.sin(time*1.7)*.02)
  j.shoulderR.rotation.set(-sw*.6*s-(this.ranged?0:.25),0,.12+Math.sin(time*1.7)*.02)
  j.elbowL.rotation.x=-.25-.35*s;j.elbowR.rotation.x=-.45-.35*s
  j.head.rotation.y=Math.sin(time*.6)*.12*(1-s)
  this.rig.root.rotation.y=0
  if(this.action&&!(this.dead&&this.action==='death'&&this.actionT>=this.actionDur)){
   this.actionT+=dt;const p=Math.min(1,this.actionT/this.actionDur)
   const ease=(a:number,b:number)=>{const t=Math.min(1,Math.max(0,(p-a)/(b-a)));return t*t*(3-2*t)}
   switch(this.action){
    case 'attack':{const up=ease(0,.35),down=ease(.35,.6),back=ease(.6,1);const x=-.25-2.5*up+2.3*down+(-.05)*back
     j.shoulderR.rotation.x=x;j.shoulderR.rotation.z=.12+.5*up-.4*down;j.elbowR.rotation.x=-.45-.6*up+.6*down;j.spine.rotation.y=-.35*up+.6*down-.25*back;break}
    case 'cast':{const r=ease(0,.4)-ease(.75,1);j.shoulderL.rotation.x=-1.45*r;j.shoulderR.rotation.x=-1.45*r;j.shoulderL.rotation.z=-.12-.25*r;j.shoulderR.rotation.z=.12+.25*r;j.elbowL.rotation.x=-.25*r;j.elbowR.rotation.x=-.25*r;break}
    case 'shoot':{const r=ease(0,.3)-ease(.8,1);const draw=ease(.1,.7);j.shoulderL.rotation.x=-1.5*r;j.shoulderR.rotation.x=-1.45*r;j.elbowR.rotation.x=-.3-1.7*draw*r;j.spine.rotation.y=.4*r;break}
    case 'hit':{const r=Math.sin(p*Math.PI);j.spine.rotation.x=-.3*r;j.head.rotation.x=-.2*r;break}
    case 'spin':{this.rig.root.rotation.y=time*15;j.shoulderL.rotation.z=-1.3;j.shoulderR.rotation.z=1.3;j.shoulderR.rotation.x=-.3;break}
    case 'death':{const f=ease(0,1);this.rig.root.rotation.x=-1.45*f;this.rig.root.position.y=.12*f;j.shoulderL.rotation.z=-.8*f;j.shoulderR.rotation.z=.8*f;break}
   }
   if(p>=1&&this.action!=='death'&&this.action!=='spin')this.action=null
  }
  for(const c of this.cloaks)c.rotation.x=.12+.55*s+Math.sin(time*2.2)*.03
  for(const a of this.anims){
   const u=a.o.userData
   if(u.spin)a.o.rotation.z+=dt*u.spin
   if(u.float)a.o.position.y=a.base.y+Math.sin(time*2+a.phase)*.025
   if(u.orbit){const o=u.orbit;const ang=time*o.speed+o.phase;a.o.position.set(Math.cos(ang)*o.r,o.y+Math.sin(ang*1.7)*.03,Math.sin(ang)*o.r);a.o.rotation.y+=dt*3}
   if(u.pulse)a.o.scale.setScalar(1+Math.sin(time*4+a.phase)*.14)
   if(u.flicker)a.o.scale.set(a.scale.x*(1+Math.sin(time*11+a.phase)*.08),a.scale.y*(1+Math.sin(time*17+a.phase)*.18),a.scale.z)
  }
  if(particles&&!this.dead)for(const e of this.emitters)e.update(dt,particles,fxIntensity)
 }
 dispose(){this.object.removeFromParent();disposeTree(this.object)}
}

export function appearanceOf(race:string,cls:string,role:Role,items:Partial<Record<Slot,{slot:Slot;base:string;rarity:GearLook['rarity'];seed:number;effect:{id:string}|null;twoHand:boolean}>>):Appearance{
 const gear:Partial<Record<Slot,GearLook>>={}
 for(const [slot,item] of Object.entries(items))if(item)gear[slot as Slot]={slot:item.slot,base:item.base,rarity:item.rarity,seed:item.seed,effect:item.effect?.id??null,twoHand:item.twoHand}
 return {race,cls,role,gear}
}
