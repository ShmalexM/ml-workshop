import * as THREE from 'three'
import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js'
import {RenderPass} from 'three/addons/postprocessing/RenderPass.js'
import {UnrealBloomPass} from 'three/addons/postprocessing/UnrealBloomPass.js'
import {OutputPass} from 'three/addons/postprocessing/OutputPass.js'
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js'

export function createRenderer(canvas:HTMLCanvasElement,opts:{alpha?:boolean;shadows?:boolean;preserve?:boolean}={}){
 const renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:opts.alpha??false,preserveDrawingBuffer:opts.preserve??false,powerPreference:'high-performance'})
 renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2))
 renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.05
 renderer.outputColorSpace=THREE.SRGBColorSpace
 if(opts.shadows){renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFShadowMap}
 return renderer
}

const envCache=new WeakMap<THREE.WebGLRenderer,THREE.Texture>()
/** Soft studio reflections so metal reads as metal without any texture files. */
export function environment(renderer:THREE.WebGLRenderer){
 let tex=envCache.get(renderer)
 if(!tex){const pmrem=new THREE.PMREMGenerator(renderer);tex=pmrem.fromScene(new RoomEnvironment(),.04).texture;pmrem.dispose();envCache.set(renderer,tex)}
 return tex
}

export function createComposer(renderer:THREE.WebGLRenderer,scene:THREE.Scene,camera:THREE.Camera,bloom={strength:.85,radius:.55,threshold:.82}){
 const size=renderer.getSize(new THREE.Vector2())
 const composer=new EffectComposer(renderer)
 composer.addPass(new RenderPass(scene,camera))
 const pass=new UnrealBloomPass(size,bloom.strength,bloom.radius,bloom.threshold);composer.addPass(pass)
 composer.addPass(new OutputPass())
 return {composer,bloom:pass}
}

export function reducedMotion(){return typeof matchMedia==='function'&&matchMedia('(prefers-reduced-motion: reduce)').matches}

export function webglAvailable(){
 try{const c=document.createElement('canvas');return !!(c.getContext('webgl2')||c.getContext('webgl'))}catch{return false}
}
