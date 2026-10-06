import * as THREE from 'three'
import {dotTexture} from './materials'
import type {FxSpec} from './gear'

const VERT=`attribute float size;attribute float alpha;attribute vec3 tint;varying float vAlpha;varying vec3 vTint;uniform float scale;
void main(){vAlpha=alpha;vTint=tint;vec4 mv=modelViewMatrix*vec4(position,1.0);gl_PointSize=size*scale/max(.1,-mv.z);gl_Position=projectionMatrix*mv;}`
const FRAG=`uniform sampler2D map;varying float vAlpha;varying vec3 vTint;
void main(){vec4 t=texture2D(map,gl_PointCoord);gl_FragColor=vec4(vTint*1.6,t.a*vAlpha);if(gl_FragColor.a<.01)discard;}`

export type Burst={count:number;color:string;speed:number;size:number;life:number;gravity?:number;spread?:number;up?:number}

/** One additive point cloud per scene; everything glowy that moves goes through here. */
export class Particles{
 readonly points:THREE.Points
 private max:number;private n=0
 private pos:Float32Array;private vel:Float32Array;private tint:Float32Array;private size:Float32Array;private alpha:Float32Array;private life:Float32Array;private total:Float32Array;private grav:Float32Array;private base:Float32Array
 private geo=new THREE.BufferGeometry()
 constructor(max=1500){
  this.max=max;this.pos=new Float32Array(max*3);this.vel=new Float32Array(max*3);this.tint=new Float32Array(max*3)
  this.size=new Float32Array(max);this.alpha=new Float32Array(max);this.life=new Float32Array(max);this.total=new Float32Array(max);this.grav=new Float32Array(max);this.base=new Float32Array(max)
  this.geo.setAttribute('position',new THREE.BufferAttribute(this.pos,3).setUsage(THREE.DynamicDrawUsage))
  this.geo.setAttribute('tint',new THREE.BufferAttribute(this.tint,3).setUsage(THREE.DynamicDrawUsage))
  this.geo.setAttribute('size',new THREE.BufferAttribute(this.size,1).setUsage(THREE.DynamicDrawUsage))
  this.geo.setAttribute('alpha',new THREE.BufferAttribute(this.alpha,1).setUsage(THREE.DynamicDrawUsage))
  const material=new THREE.ShaderMaterial({uniforms:{map:{value:dotTexture()},scale:{value:600}},vertexShader:VERT,fragmentShader:FRAG,transparent:true,depthWrite:false,blending:THREE.AdditiveBlending})
  this.points=new THREE.Points(this.geo,material);this.points.frustumCulled=false;this.geo.setDrawRange(0,0)
 }
 setScale(viewportHeight:number){(this.points.material as THREE.ShaderMaterial).uniforms.scale.value=viewportHeight*.9}
 spawn(p:THREE.Vector3,v:THREE.Vector3,color:THREE.Color,size:number,life:number,gravity=0){
  if(this.n>=this.max)return;const i=this.n++
  this.pos.set([p.x,p.y,p.z],i*3);this.vel.set([v.x,v.y,v.z],i*3);this.tint.set([color.r,color.g,color.b],i*3)
  this.base[i]=size;this.size[i]=size;this.alpha[i]=1;this.life[i]=life;this.total[i]=life;this.grav[i]=gravity
 }
 burst(at:THREE.Vector3,b:Burst){
  const c=new THREE.Color(b.color);const v=new THREE.Vector3()
  for(let i=0;i<b.count;i++){
   const a=Math.random()*Math.PI*2,e=(Math.random()-.3)*(b.spread??1.2)
   v.set(Math.cos(a)*Math.cos(e),Math.sin(e)+(b.up??0),Math.sin(a)*Math.cos(e)).multiplyScalar(b.speed*(.4+Math.random()*.6))
   this.spawn(at,v,c,b.size*(.6+Math.random()*.6),b.life*(.6+Math.random()*.6),b.gravity??0)
  }
 }
 update(dt:number){
  let i=0
  while(i<this.n){
   this.life[i]-=dt
   if(this.life[i]<=0){this.n--;this.copy(this.n,i);continue}
   const k=i*3;this.vel[k+1]-=this.grav[i]*dt
   this.pos[k]+=this.vel[k]*dt;this.pos[k+1]+=this.vel[k+1]*dt;this.pos[k+2]+=this.vel[k+2]*dt
   const t=this.life[i]/this.total[i];this.alpha[i]=Math.min(1,t*2.2)*Math.min(1,(1-t)*8+.2);this.size[i]=this.base[i]*(.5+t*.5)
   i++
  }
  this.geo.setDrawRange(0,this.n)
  for(const name of ['position','tint','size','alpha'])(this.geo.getAttribute(name) as THREE.BufferAttribute).needsUpdate=true
 }
 private copy(from:number,to:number){
  this.pos.copyWithin(to*3,from*3,from*3+3);this.vel.copyWithin(to*3,from*3,from*3+3);this.tint.copyWithin(to*3,from*3,from*3+3)
  this.size[to]=this.size[from];this.alpha[to]=this.alpha[from];this.life[to]=this.life[from];this.total[to]=this.total[from];this.grav[to]=this.grav[from];this.base[to]=this.base[from]
 }
 clear(){this.n=0;this.geo.setDrawRange(0,0)}
 dispose(){this.geo.dispose();(this.points.material as THREE.Material).dispose()}
}

const tmp=new THREE.Vector3(),vel=new THREE.Vector3()
/** Continuous emitter pinned to a gear piece (legendary auras, epic embers). */
export class Emitter{
 private acc=0;private color:THREE.Color
 constructor(readonly target:THREE.Object3D,readonly spec:FxSpec){this.color=new THREE.Color(spec.color)}
 update(dt:number,particles:Particles,intensity=1){
  this.acc+=dt*this.spec.rate*intensity
  while(this.acc>=1){
   this.acc--;this.target.getWorldPosition(tmp);const s=this.spec.spread
   tmp.x+=(Math.random()-.5)*s*2;tmp.y+=(Math.random()-.5)*s*2;tmp.z+=(Math.random()-.5)*s*2
   const k=this.spec.kind
   if(k==='embers')vel.set((Math.random()-.5)*.15,.35+Math.random()*.35,(Math.random()-.5)*.15)
   else if(k==='sparks')vel.set((Math.random()-.5)*1.4,(Math.random()-.2)*1.2,(Math.random()-.5)*1.4)
   else if(k==='snow')vel.set((Math.random()-.5)*.1,-.18-Math.random()*.12,(Math.random()-.5)*.1)
   else if(k==='shards')vel.set((Math.random()-.5)*.5,(Math.random()-.3)*.5,(Math.random()-.5)*.5)
   else vel.set((Math.random()-.5)*.2,.08+Math.random()*.12,(Math.random()-.5)*.2)
   const life=k==='sparks'?.35:k==='embers'?1.1:1.7;const size=k==='sparks'?.05:k==='shards'?.075:.07
   particles.spawn(tmp,vel,this.color,size,life*(.7+Math.random()*.6),k==='sparks'?1.5:0)
  }
 }
}
