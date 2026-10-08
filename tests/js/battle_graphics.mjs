// Checks how src/game/graphics.ts keeps the Battle graphics setting. Node loads the TypeScript file by removing
// its types. Each case loads a fresh copy of the module, as a page reload would. Run by tests/test_three_helpers.py.
import assert from 'node:assert/strict'

let copy = 0
const load = () => import(new URL(`../../src/game/graphics.ts?copy=${++copy}`, import.meta.url).href)
const KEY = 'ml-workshop-battle-graphics'

function storage(entries = {}, {broken = false} = {}) {
  const map = new Map(Object.entries(entries))
  globalThis.localStorage = {
    getItem: key => { if (broken) throw new Error('blocked'); return map.has(key) ? map.get(key) : null },
    setItem: (key, value) => { if (broken) throw new Error('blocked'); map.set(key, String(value)) },
  }
  return map
}

// Standard by default.
storage()
let graphics = await load()
assert.equal(graphics.readBattleGraphics(), 'standard')
assert.equal(graphics.LIGHT_PIXEL_RATIO, 1.5)

// Light is saved and read back after a reload.
const saved = storage()
graphics = await load()
graphics.saveBattleGraphics('light')
assert.equal(saved.get(KEY), 'light')
assert.equal(graphics.readBattleGraphics(), 'light')
assert.equal((await load()).readBattleGraphics(), 'light')
graphics.saveBattleGraphics('standard')
assert.equal(saved.get(KEY), 'standard')
assert.equal((await load()).readBattleGraphics(), 'standard')

// An unknown stored value reads as Standard.
for (const value of ['', 'LIGHT', 'low', '{}']) {
  storage({[KEY]: value})
  assert.equal((await load()).readBattleGraphics(), 'standard', value)
}

// Without storage, the choice still applies on this page, and nothing throws.
storage({}, {broken: true})
graphics = await load()
assert.equal(graphics.readBattleGraphics(), 'standard')
graphics.saveBattleGraphics('light')
assert.equal(graphics.readBattleGraphics(), 'light')
assert.equal((await load()).readBattleGraphics(), 'standard')

console.log('battle graphics ok')
