// Checks for the game's three.js helpers that need no browser. Run by tests/test_three_helpers.py.
import assert from 'node:assert/strict'
import * as THREE from 'three'
import {releaseListenersOnDispose} from '../../src/game/three/shared.ts'

// A stand-in renderer: like three's WebGLRenderer, render() adds one 'dispose' listener per object it draws.
function fakeRenderer(){
 const seen=new Set()
 const renderer={disposed:false,render(objects){for(const o of objects)if(!seen.has(o)){seen.add(o);o.addEventListener('dispose',()=>{})}},dispose(){this.disposed=true}}
 return releaseListenersOnDispose(renderer)
}
const listeners=o=>o._listeners?.dispose?.length??0

const sharedMaterial=new THREE.MeshStandardMaterial(),sharedTexture=new THREE.DataTexture(new Uint8Array(4),1,1)
const a=fakeRenderer(),b=fakeRenderer()
a.render([sharedMaterial,sharedTexture]);b.render([sharedMaterial])
assert.equal(listeners(sharedMaterial),2)
assert.equal(listeners(sharedTexture),1)

// Disposing one renderer removes only its own listeners.
a.dispose()
assert.equal(a.disposed,true)
assert.equal(listeners(sharedMaterial),1)
assert.equal(listeners(sharedTexture),0)

// Listeners added outside a render call belong to nobody and stay.
const own=()=>{};sharedMaterial.addEventListener('dispose',own)
b.dispose()
assert.deepEqual(sharedMaterial._listeners.dispose,[own])

// Other event types are left alone, and a later renderer starts with a clean list.
const c=fakeRenderer();const geometry=new THREE.BufferGeometry()
c.render([geometry]);geometry.addEventListener('other',()=>{})
c.dispose()
assert.equal(listeners(geometry),0)
assert.equal(geometry._listeners.other.length,1)
c.dispose()

console.log('three helpers ok')
