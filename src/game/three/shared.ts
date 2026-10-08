import * as THREE from 'three'

// A renderer adds a 'dispose' listener to every material, texture and geometry it draws, and
// renderer.dispose() leaves those listeners in place. Objects that outlive the renderer (the
// material cache, the shared textures and three.js's own lighting lookup texture) then keep
// the whole closed renderer, its WebGL context and its buffers in memory. Each armory or
// battle that was opened and closed used to stay in memory this way.
type Listener=(event:any)=>void
type Added={target:WeakRef<object>;listener:Listener}
let collecting:Added[]|null=null

const proto=THREE.EventDispatcher.prototype as unknown as {addEventListener:(this:object,type:string,listener:Listener)=>void}
const add=proto.addEventListener
proto.addEventListener=function(type,listener){
 if(collecting&&type==='dispose')collecting.push({target:new WeakRef(this),listener})
 add.call(this,type,listener)
}

/** Records the dispose listeners the renderer adds while it renders, and removes them in renderer.dispose(). */
export function releaseListenersOnDispose(renderer:THREE.WebGLRenderer){
 let added:Added[]=[];let prune=256
 const render=renderer.render.bind(renderer)
 renderer.render=(scene,camera)=>{
  const previous=collecting;collecting=added
  try{render(scene,camera)}finally{collecting=previous}
  // Objects that were collected since need no removal, so a long-lived renderer keeps a short list.
  if(added.length>prune){added=added.filter(entry=>entry.target.deref());prune=Math.max(256,added.length*2)}
 }
 const dispose=renderer.dispose.bind(renderer)
 renderer.dispose=()=>{
  for(const entry of added)(entry.target.deref() as THREE.EventDispatcher<any>|undefined)?.removeEventListener('dispose',entry.listener)
  added=[];dispose()
 }
 return renderer
}
