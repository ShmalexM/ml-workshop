import * as THREE from 'three'

type MatOpts={metal?:number;rough?:number;emissive?:string;glow?:number;flat?:boolean;map?:THREE.Texture;side?:THREE.Side;transparent?:boolean;opacity?:number}
const cache=new Map<string,THREE.Material>()
// Every material from mat() and glow(). Many meshes use each one, so nothing may change them after they are made.
const shared=new WeakSet<THREE.Material>()
/** True for a material from mat() or glow(). The tests check that no code changes one. */
export const isShared=(m:THREE.Material)=>shared.has(m)

/** Cached flat-shaded standard material: the low-poly look comes from flat normals, not textures. */
export function mat(color:string,o:MatOpts={}):THREE.MeshStandardMaterial{
 const key=['s',color,o.metal??0,o.rough??.8,o.emissive??'',o.glow??0,o.flat??true,o.map?.uuid??'',o.side??0,o.opacity??1].join('|')
 let m=cache.get(key) as THREE.MeshStandardMaterial|undefined
 if(!m){
  m=new THREE.MeshStandardMaterial({color,metalness:o.metal??0,roughness:o.rough??.8,flatShading:o.flat??true,map:o.map??null,side:o.side??THREE.FrontSide,transparent:o.transparent||(o.opacity??1)<1,opacity:o.opacity??1})
  if(o.emissive){m.emissive=new THREE.Color(o.emissive);m.emissiveIntensity=o.glow??1}
  cache.set(key,m);shared.add(m)
 }
 return m
}

/** Additive, unlit material for halos, beams and rune light. Bloom picks these up. */
export function glow(color:string,opacity=.8,side:THREE.Side=THREE.FrontSide){
 const key=['g',color,opacity,side].join('|');let m=cache.get(key) as THREE.MeshBasicMaterial|undefined
 if(!m){m=ownGlow(color,opacity,side);cache.set(key,m);shared.add(m)}
 return m
}

/** The same material as glow(), but new and owned by one mesh, which may fade or recolor it. Dispose it with the mesh. */
export function ownGlow(color:string,opacity=.8,side:THREE.Side=THREE.FrontSide){
 return new THREE.MeshBasicMaterial({color,transparent:true,opacity,blending:THREE.AdditiveBlending,depthWrite:false,side})
}

let mailTexture:THREE.CanvasTexture|null=null
/** Interlocking ring pattern so mail reads differently from plate at a glance. */
export function mailMap(){
 if(mailTexture)return mailTexture
 const c=document.createElement('canvas');c.width=c.height=64;const g=c.getContext('2d')!
 g.fillStyle='#d8d8d8';g.fillRect(0,0,64,64);g.strokeStyle='#5a5a5a';g.lineWidth=2.2
 for(let y=0;y<5;y++)for(let x=0;x<5;x++){g.beginPath();g.arc(x*16+(y%2)*8,y*16,7,0,Math.PI*2);g.stroke()}
 mailTexture=new THREE.CanvasTexture(c);mailTexture.wrapS=mailTexture.wrapT=THREE.RepeatWrapping;mailTexture.repeat.set(3,3);mailTexture.colorSpace=THREE.SRGBColorSpace
 return mailTexture
}

let softDot:THREE.CanvasTexture|null=null
/** Radial falloff sprite for particles and glow cards. */
export function dotTexture(){
 if(softDot)return softDot
 const c=document.createElement('canvas');c.width=c.height=64;const g=c.getContext('2d')!
 const r=g.createRadialGradient(32,32,0,32,32,32);r.addColorStop(0,'rgba(255,255,255,1)');r.addColorStop(.25,'rgba(255,255,255,.75)');r.addColorStop(1,'rgba(255,255,255,0)')
 g.fillStyle=r;g.fillRect(0,0,64,64);softDot=new THREE.CanvasTexture(c);return softDot
}

/** Disposes geometries of a subtree. Materials are shared through the cache and stay alive. */
export function disposeTree(root:THREE.Object3D){root.traverse(o=>{const m=o as THREE.Mesh;if(m.geometry)m.geometry.dispose()})}
