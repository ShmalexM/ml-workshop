// Checks that the game never changes a material from the cache in src/game/three/materials.ts. Many meshes share
// each one, so a change made for one mesh shows on all of them. Builds every gear look and runs a fight for each
// class with the real battle engine, bundled for Node the way scripts/game_balance_sim.mjs does it.
// Run by tests/test_three_helpers.py.
import assert from 'node:assert/strict'
import path from 'node:path'
import {fileURLToPath} from 'node:url'
import * as esbuild from 'esbuild'

const root = fileURLToPath(new URL('../../', import.meta.url))
const stub = path.join(root, 'scripts', 'game-sim', 'scene-stub.ts')
// No WebGL in Node: the renderer comes from the simulation's stub.
const noRenderer = {name: 'no-renderer', setup(build) {
  build.onResolve({filter: /(^|\/)scene$/}, args => args.importer.includes(`${path.sep}src${path.sep}game${path.sep}`) ? {path: stub} : undefined)
}}
const entry = `import './scripts/game-sim/stubs'
export * as THREE from 'three'
export {clock, runDue, simulatedTimeout, canvas, overlay} from './scripts/game-sim/stubs'
export {gearParts, weaponModel} from './src/game/three/gear'
export {dimsFor, RACES} from './src/game/three/rig'
export {isShared, glow, ownGlow} from './src/game/three/materials'
export {appearanceOf} from './src/game/three/hero'
export {heroStats} from './src/game/stats'
export {BattleEngine} from './src/game/battle/engine'
export {KITS} from './src/game/battle/kits'`
const built = await esbuild.build({stdin: {contents: entry, resolveDir: root, loader: 'ts'}, bundle: true, platform: 'node', format: 'esm', write: false, plugins: [noRenderer], logLevel: 'warning'})
const game = await import('data:text/javascript;base64,' + Buffer.from(built.outputFiles[0].text).toString('base64'))
const {THREE} = game

// Record every shared material as each mesh is added to a parent, then compare at the end.
const state = m => JSON.stringify([m.side, m.opacity, m.transparent, m.visible, m.depthWrite, m.blending, m.color?.getHex(), m.emissive?.getHex(), m.emissiveIntensity, m.map?.uuid])
const seen = new Map()
const add = THREE.Object3D.prototype.add
THREE.Object3D.prototype.add = function (...objects) {
  for (const object of objects) for (const material of [object.material ?? []].flat())
    if (game.isShared(material) && !seen.has(material)) seen.set(material, {before: state(material), mesh: object.type})
  return add.apply(this, objects)
}
function unchanged(what) {
  const changed = [...seen].filter(([material, {before}]) => state(material) !== before)
  assert.deepEqual(changed.map(([material, {before, mesh}]) => `${mesh}: ${before} -> ${state(material)}`), [], `${what} changed a shared material`)
}

// ownGlow() matches glow() but is a new material each time.
const shared = game.glow('#ff8000', .9, THREE.DoubleSide), own = game.ownGlow('#ff8000', .9, THREE.DoubleSide)
assert.notEqual(own, shared)
assert.notEqual(game.ownGlow('#ff8000', .9, THREE.DoubleSide), own)
assert.equal(game.isShared(shared), true)
assert.equal(game.isShared(own), false)
for (const key of ['side', 'opacity', 'transparent', 'blending', 'depthWrite']) assert.equal(own[key], shared[key], key)
assert.equal(own.color.getHex(), shared.color.getHex())
own.opacity = .1
assert.equal(shared.opacity, .9)

// Every gear look, as the armory and the battle build them.
const dims = game.dimsFor(game.RACES.human)
const rarities = ['basic', 'common', 'rare', 'epic', 'legendary']
let seed = 1000
for (const slot of ['head', 'shoulders', 'chest', 'hands', 'legs', 'feet'])
  for (const base of ['cloth', 'leather', 'mail', 'plate'])
    for (const rarity of rarities)
      for (let i = 0; i < 3; i++) {
        const parts = game.gearParts({slot, base, rarity, seed: seed++ * 7919, effect: rarity === 'legendary' ? 'inferno' : null, twoHand: false}, dims)
        const holder = new THREE.Group()
        for (const part of parts) holder.add(part.object)
      }
for (const rarity of rarities) for (const part of game.gearParts({slot: 'back', base: 'cloak', rarity, seed: seed++ * 7919, effect: null, twoHand: false}, dims)) new THREE.Group().add(part.object)
for (const base of ['sword', 'greatsword', 'dagger', 'axe', 'greataxe', 'mace', 'warhammer', 'polearm', 'staff', 'wand', 'fist', 'warglaive', 'bow', 'crossbow', 'gun', 'shield', 'tome', 'orb'])
  for (const rarity of rarities) new THREE.Group().add(game.weaponModel({slot: 'mainhand', base, rarity, seed: seed++ * 7919, effect: null, twoHand: false}))
unchanged('Building gear')

// A cloth chest's skirt is double-sided, and the cloth it shares with the rest of the chest stays one-sided.
const chest = game.gearParts({slot: 'chest', base: 'cloth', rarity: 'rare', seed: 4242, effect: null, twoHand: false}, dims)
const meshes = [];chest[0].object.traverse(o => { if (o.isMesh) meshes.push(o) })
const skirt = meshes.find(m => m.geometry.parameters?.openEnded && m.geometry.parameters.height > .3)
assert.ok(skirt, 'no skirt in a cloth chest')
assert.equal(skirt.material.side, THREE.DoubleSide)
assert.equal(meshes[0].material.side, THREE.FrontSide)
assert.notEqual(meshes[0].material, skirt.material)

// A fight for every class: abilities make rings that fade out, among other effects.
const cloth = Object.fromEntries(['head', 'shoulders', 'chest', 'hands', 'legs', 'feet'].map((slot, i) => [slot, {slot, base: 'cloth', rarity: 'epic', seed: 77 + i, effect: null, twoHand: false}]))
for (const cls of Object.keys(game.KITS)) {
  const stats = {...game.heroStats({}, 60), maxHp: 1e9}
  game.clock.now = 0;game.clock.queue = []
  const realTimeout = globalThis.setTimeout;globalThis.setTimeout = game.simulatedTimeout
  const engine = new game.BattleEngine(game.canvas(), game.overlay, {appearance: game.appearanceOf('human', cls, 'melee', cloth), classColor: '#ffd65a', stats, name: 'Test', stage: 3, stageName: 'Stage', bossName: 'Boss', bossHp: 1e9, bossRemaining: 1e9, seed: 7919}, {hud() {}, banner() {}, end() {}})
  try {
    engine.setAuto(true)
    for (let step = 0; step < 40 * 60; step++) {
      game.clock.now += 1 / 60;game.runDue()
      if (step % 90 === 0) for (const key of ['Q', 'W', 'E', 'R']) engine.cast(key, true)
      engine.update(1 / 60)
    }
    // A ring in the hero ring's own color, while the hero ring is in the scene.
    engine.ringFx(engine.heroPos, 3, '#ffd65a', .5)
    for (let step = 0; step < 60; step++) engine.update(1 / 60)
  } finally {
    engine.dispose();globalThis.setTimeout = realTimeout
  }
  unchanged(`A ${cls} fight`)
}

console.log('shared materials ok')
