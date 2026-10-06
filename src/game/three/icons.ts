import * as THREE from 'three'
import {createRenderer,environment} from './scene'
import {buildRig} from './rig'
import {gearParts,weaponModel} from './gear'
import {disposeTree} from './materials'
import {RARITY_COLOR} from '../rarity'
import type {GearLook} from '../types'

const SIZE=160
let renderer:THREE.WebGLRenderer|null=null
const cache=new Map<string,string>()
const waiting=new Map<string,((url:string)=>void)[]>()
const queue:GearLook[]=[]
let pumping=false
// A message channel instead of requestAnimationFrame: icons keep rendering even when the page is not painting.
const channel=typeof MessageChannel==='undefined'?null:new MessageChannel()
if(channel)channel.port1.onmessage=()=>pump()
const schedule=()=>{if(channel)channel.port2.postMessage(null);else setTimeout(pump,0)}

export const iconKey=(l:GearLook)=>[l.slot,l.base,l.rarity,l.seed,l.effect??''].join(':')
export function cachedIcon(look:GearLook){return cache.get(iconKey(look))}

/** Renders an item's 3D model to a PNG once, then serves it from memory. */
export function itemIcon(look:GearLook):Promise<string>{
 const key=iconKey(look);const hit=cache.get(key);if(hit)return Promise.resolve(hit)
 return new Promise(resolve=>{const list=waiting.get(key);if(list){list.push(resolve);return}waiting.set(key,[resolve]);queue.push(look);if(!pumping){pumping=true;schedule()}})
}

function pump(){
 const start=performance.now()
 while(queue.length&&performance.now()-start<16){const look=queue.shift()!;const key=iconKey(look);let url=''
  try{url=render(look)}catch(error){console.warn("Item icon failed to render",key,error);url=""}
  // Keep failures out of the cache so the icon is tried again next time.
  if(url)cache.set(key,url);for(const done of waiting.get(key)||[])done(url);waiting.delete(key)}
 if(queue.length)schedule();else pumping=false
}

function render(look:GearLook){
 // The browser can take the context back when too many are open; start a new renderer then.
 if(renderer?.getContext().isContextLost()){renderer.dispose();renderer=null}
 if(!renderer){const canvas=document.createElement('canvas');canvas.width=canvas.height=SIZE;renderer=createRenderer(canvas,{alpha:true,preserve:true});renderer.setPixelRatio(1);renderer.setSize(SIZE,SIZE,false)}
 const scene=new THREE.Scene();scene.environment=environment(renderer);scene.environmentIntensity=.45
 const glowColor=RARITY_COLOR[look.rarity].glow
 scene.add(new THREE.HemisphereLight('#ffffff','#30303a',.65))
 const key=new THREE.DirectionalLight('#fff4e6',1.6);key.position.set(-2,3,4);scene.add(key)
 const rim=new THREE.DirectionalLight(glowColor,look.rarity==='basic'?.5:.85);rim.position.set(3,1,-3);scene.add(rim)
 const holder=new THREE.Group();scene.add(holder)
 const weapon=look.slot==='mainhand'||look.slot==='offhand'
 let rigRoot:THREE.Object3D|null=null
 if(weapon){
  const obj=weaponModel(look);holder.add(obj)
  const upright=['staff','polearm','bow','greatsword','greataxe','warhammer','sword','axe','mace','dagger','wand','warglaive','fist']
  if(upright.includes(look.base))obj.rotation.z=-Math.PI/4
  if(look.base==='gun'||look.base==='crossbow')obj.rotation.set(0,Math.PI/2.4,-.35)
  if(look.base==='shield'||look.base==='tome')obj.rotation.y=-.35
 }else{
  const rig=buildRig('human');rigRoot=rig.root;holder.add(rig.root)
  for(const b of rig.body)b.visible=false
  const parts=gearParts(look,rig.dims)
  for(const p of parts){rig.joints[p.joint].add(p.object);if(p.side==='L'&&look.slot!=='legs')p.object.visible=false}
  rig.joints.shoulderR.rotation.z=.12
  holder.rotation.y=look.slot==='back'?Math.PI+.5:look.slot==='shoulders'?-.5:-.45
 }
 holder.updateMatrixWorld(true)
 const box=new THREE.Box3()
 holder.traverseVisible(o=>{const m=o as THREE.Mesh;if(m.isMesh&&(m.material as THREE.Material).blending!==THREE.AdditiveBlending)box.expandByObject(m)})
 if(box.isEmpty())holder.traverseVisible(o=>{if((o as THREE.Mesh).isMesh)box.expandByObject(o)})
 const center=box.getCenter(new THREE.Vector3());const size=box.getSize(new THREE.Vector3())
 holder.position.sub(center)
 const radius=Math.max(size.x,size.y,size.z)*.62
 const camera=new THREE.PerspectiveCamera(28,1,.01,50)
 const dir=new THREE.Vector3(.25,.32,1).normalize()
 camera.position.copy(dir.multiplyScalar(radius/Math.tan(THREE.MathUtils.degToRad(14))*1.02));camera.lookAt(0,0,0)
 renderer.setClearColor(0x000000,0);renderer.clear()
 renderer.render(scene,camera)
 const url=renderer.domElement.toDataURL('image/png')
 disposeTree(holder);if(rigRoot)disposeTree(rigRoot)
 return url
}
