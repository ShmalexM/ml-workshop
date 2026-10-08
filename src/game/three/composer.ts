import * as THREE from 'three'
import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js'
import {RenderPass} from 'three/addons/postprocessing/RenderPass.js'
import {UnrealBloomPass} from 'three/addons/postprocessing/UnrealBloomPass.js'
import {OutputPass} from 'three/addons/postprocessing/OutputPass.js'

// Only battles use post-processing, so it lives apart from scene.ts and loads with the battle code, not the armory.
export function createComposer(renderer:THREE.WebGLRenderer,scene:THREE.Scene,camera:THREE.Camera,bloom={strength:.22,radius:.4,threshold:1.4}){
 const size=renderer.getSize(new THREE.Vector2())
 const composer=new EffectComposer(renderer)
 composer.addPass(new RenderPass(scene,camera))
 const pass=new UnrealBloomPass(size,bloom.strength,bloom.radius,bloom.threshold);composer.addPass(pass)
 composer.addPass(new OutputPass())
 return {composer,bloom:pass}
}
