// Checks how src/api.ts takes a session token from the address. Node loads the TypeScript file by removing its
// types. Each case loads a fresh copy of the module with its own fake browser: address, storage and server.
// tests/test_local_security.py runs this file.
import assert from 'node:assert/strict'

const GOOD = 'G'.repeat(43), NEW = 'N'.repeat(43), JUNK = 'A'.repeat(43)
let copy = 0

/** A fake browser. server(token) gives the status of GET /api/session for that token, or throws when unreachable. */
function browser({hash = '', stored = '', server}) {
  const storage = new Map(stored ? [['engineering-workshop-session', stored]] : [])
  const page = {listeners: {}, reloads: 0, sent: []}
  globalThis.location = {hash, pathname: '/', search: '', reload: () => { page.reloads++ }}
  globalThis.history = {state: null, replaceState: (state, title, url) => { globalThis.location.hash = url.includes('#') ? url.slice(url.indexOf('#')) : '' }}
  globalThis.localStorage = {getItem: key => storage.get(key) ?? null, setItem: (key, value) => { storage.set(key, value) }}
  globalThis.addEventListener = (type, listener) => { (page.listeners[type] ||= []).push(listener) }
  globalThis.fetch = async (url, init = {}) => {
    const token = init.headers?.['X-Workshop-Token'] || ''
    const status = url === '/api/session' ? server(token) : token === GOOD || token === NEW ? 200 : 403
    if (url !== '/api/session') page.sent.push(token)
    const body = status === 403 ? {error: 'expired', code: 'session-expired'} : {ok: true}
    return {status, ok: status === 200, json: async () => body, clone() { return this }}
  }
  page.stored = () => storage.get('engineering-workshop-session') || ''
  return page
}

async function load() {
  return import(new URL(`../../src/api.ts?copy=${++copy}`, import.meta.url).href)
}

const accepts = (...tokens) => token => tokens.includes(token) ? 200 : 403
const checks = []
const check = (name, run) => checks.push([name, run])

check('a refused token from the address keeps the stored token', async () => {
  const page = browser({hash: '#session=' + JUNK + '&learn/python-1', stored: GOOD, server: accepts(GOOD)})
  const api = await load()
  await api.api('/state')
  assert.equal(page.stored(), GOOD)
  assert.deepEqual(page.sent, [GOOD])
  assert.equal(location.hash, '#learn/python-1')
})

check('an accepted token from the address replaces the stored token', async () => {
  const page = browser({hash: '#session=' + NEW, stored: GOOD, server: accepts(GOOD, NEW)})
  const api = await load()
  await api.api('/state')
  assert.equal(page.stored(), NEW)
  assert.deepEqual(page.sent, [NEW])
  assert.equal(location.hash, '')
})

check('a token that cannot be checked is used in this tab only', async () => {
  const page = browser({hash: '#session=' + NEW, stored: GOOD, server: () => { throw new TypeError('offline') }})
  const api = await load()
  await api.api('/state')
  assert.equal(page.stored(), GOOD)
  assert.deepEqual(page.sent, [NEW])
})

check('a new address in an open tab reloads only for an accepted token', async () => {
  const page = browser({stored: GOOD, server: accepts(GOOD, NEW)})
  const api = await load()
  location.hash = '#session=' + JUNK
  page.listeners.hashchange.forEach(listener => listener())
  await api.api('/state')
  assert.equal(page.reloads, 0)
  assert.equal(page.stored(), GOOD)
  location.hash = '#session=' + NEW
  page.listeners.hashchange.forEach(listener => listener())
  await api.api('/state')
  assert.equal(page.reloads, 1)
  assert.equal(page.stored(), NEW)
})

let failed = 0
for (const [name, run] of checks) {
  try { await run(); console.log('ok', name) } catch (error) { failed++; console.log('FAIL', name, '\n', error) }
}
if (failed) process.exit(1)
console.log(`${checks.length} session checks passed`)
