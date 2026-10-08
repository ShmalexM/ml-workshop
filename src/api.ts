import type { BookImportResult } from './libraryTypes'

/** Shown when this browser has no valid session token. */
export const connectMessage = 'Open Engineering Workshop from its shortcut or start command to connect this browser.'
const tokenKey = 'engineering-workshop-session'
export const unreachable = 'Cannot reach the local server. Start Engineering Workshop again, then reload this page.'

// The launcher opens http://127.0.0.1:<port>/#session=<token>, optionally followed by &<page route>.
// Keep the token, then remove it from the address bar and from this history entry.
function takeTokenFromAddress(): string {
  const match = location.hash.match(/^#session=([A-Za-z0-9_-]{32,128})(?:&(.*))?$/)
  if (!match) return ''
  history.replaceState(history.state, '', location.pathname + location.search + (match[2] ? '#' + match[2] : ''))
  try { localStorage.setItem(tokenKey, match[1]) } catch { /* storage unavailable: keep the token for this tab only */ }
  return match[1]
}
let tabToken = takeTokenFromAddress()
// An open tab or the Mac window can get a new address with a token. Store it and load the page again.
addEventListener('hashchange', () => { const next = takeTokenFromAddress(); if (next) { tabToken = next; location.reload() } })
// Read storage on every request, so a token that another tab received is used here too.
function currentToken() {
  try { return localStorage.getItem(tokenKey) || tabToken } catch { return tabToken }
}

let connected = Boolean(currentToken())
const listeners = new Set<(connected: boolean) => void>()
function setConnected(value: boolean) {
  if (connected === value) return
  connected = value
  listeners.forEach(listener => listener(value))
}
/** Calls listener now and whenever this browser gains or loses a valid session. Returns an unsubscribe function. */
export function onSessionChange(listener: (connected: boolean) => void) {
  listeners.add(listener); listener(connected)
  return () => { listeners.delete(listener) }
}
addEventListener('storage', event => { if (event.key === tokenKey && event.newValue) setConnected(true) })

const isExpired = (status: number, data: {code?: string} | null) => status === 403 && data?.code === 'session-expired'

/** fetch with the session token. Throws connectMessage when the server does not accept the token. */
export async function authorized(url: string, init: RequestInit): Promise<Response> {
  let sent = ''
  for (let attempt = 0; attempt < 2; attempt++) {
    const token = currentToken()
    // Retry only when another tab stored a different token after the first attempt.
    if (!token || token === sent) break
    sent = token
    let response: Response
    try { response = await fetch(url, {...init, headers: {...init.headers as Record<string, string>, 'X-Workshop-Token': token}}) }
    catch { throw new Error(unreachable) }
    if (response.status !== 403 || !isExpired(response.status, await response.clone().json().catch(() => null))) { setConnected(true); return response }
  }
  setConnected(false)
  throw new Error(connectMessage)
}

type Options={keepalive?:boolean}
export async function api<T>(path:string, body?:unknown, options:Options={}):Promise<T> {
  // keepalive lets a write finish while the page is closing or reloading.
  const response=await authorized('/api'+path,{method:body===undefined?'GET':'POST',headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),keepalive:options.keepalive})
  const data=await response.json()
  if(!response.ok)throw new Error(data.error||'The local server could not complete this request.')
  return data
}

/** Download a file from the local server. The request carries the token, so it is saved from a blob: URL. */
export async function downloadFile(url: string, filename: string) {
  const response = await authorized(url, {cache: 'no-store'})
  if (!response.ok) throw new Error((await response.json().catch(() => null))?.error || 'Could not download this file.')
  const link = document.createElement('a')
  link.href = URL.createObjectURL(await response.blob())
  link.download = filename
  document.body.append(link); link.click(); link.remove()
  // Some browsers read the blob after click() returns.
  setTimeout(() => URL.revokeObjectURL(link.href), 60_000)
}

/** Stream the file to the local server without base64 copies or a JSON body limit. */
export async function importBook(file: File, bookId: string, onProgress: (percent: number) => void): Promise<BookImportResult> {
  const upload = (token: string) => new Promise<{status: number; data: BookImportResult & {error?: string; code?: string}}>((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    const query = new URLSearchParams({filename: file.name})
    if (bookId) query.set('book', bookId)
    xhr.open('POST', '/api/library/import?' + query)
    xhr.setRequestHeader('Content-Type', 'application/octet-stream')
    xhr.setRequestHeader('X-Workshop-Token', token)
    xhr.responseType = 'json'
    xhr.timeout = 180_000
    xhr.upload.onprogress = event => { if (event.lengthComputable) onProgress(Math.round(event.loaded / event.total * 100)) }
    xhr.upload.onload = () => onProgress(100)
    xhr.onload = () => resolve({status: xhr.status, data: xhr.response || {error: 'The server returned an unreadable response. Reload Books to check whether the import finished.'}})
    xhr.onerror = () => reject(new Error('Cannot reach the local server. Restart Workshop, then choose the file again.'))
    xhr.ontimeout = () => reject(new Error('The import timed out. Reload Books to check whether it finished, then retry if needed.'))
    xhr.send(file)
  })
  let sent = currentToken()
  if (!sent) { setConnected(false); throw new Error(connectMessage) }
  let result = await upload(sent)
  // Another tab may have stored a newer token. Retry once with it.
  if (isExpired(result.status, result.data) && currentToken() !== sent) {
    sent = currentToken(); onProgress(0); result = await upload(sent)
  }
  if (isExpired(result.status, result.data)) { setConnected(false); throw new Error(connectMessage) }
  setConnected(true)
  if (result.status < 200 || result.status >= 300) throw new Error(result.data.error || 'Could not import this book. Choose the file again to retry.')
  return result.data
}
/** Delete the app's stored copy of a book. Notes and reading position stay on the server. */
export function removeBook(bookId: string) { return api<{ok: boolean}>('/library/remove', {bookId}) }
/** True when the server answers /api/health within 5 seconds. */
export async function serverReachable(){
  try{return (await fetch('/api/health',{cache:'no-store',signal:AbortSignal.timeout(5000)})).ok}catch{return false}
}
