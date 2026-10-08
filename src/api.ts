import type { BookImportResult } from './libraryTypes'

let token = ''
let renewal:Promise<void>|null = null
type Options={keepalive?:boolean}
async function request(path:string, body?:unknown, options:Options={}):Promise<[Response,any]> {
  let response:Response
  // keepalive lets a write finish while the page is closing or reloading.
  try{response=await fetch('/api'+path,{method:body===undefined?'GET':'POST',headers:body===undefined?{}:{'Content-Type':'application/json','X-Workshop-Token':token},body:body===undefined?undefined:JSON.stringify(body),keepalive:options.keepalive})}
  catch{throw new Error('Cannot reach the local server. Start Engineering Workshop again, then reload this page.')}
  return [response,await response.json()]
}
export async function api<T>(path:string, body?:unknown, options?:Options):Promise<T> {
  let [response,data]=await request(path,body,options)
  // A restarted server rejects the old session token. Get the new token once, then retry this write once.
  if(response.status===403&&data.code==='session-expired'){await renewToken();[response,data]=await request(path,body,options)}
  if(!response.ok)throw new Error(data.error||'The local server could not complete this request.')
  return data
}
export async function bootstrap(){const data=await api<{token:string}>('/bootstrap');token=data.token}
// Writes that fail together share one token request.
function renewToken(){return renewal??=bootstrap().finally(()=>{renewal=null})}

/** Stream the file to the local server without base64 copies or a JSON body limit. */
export async function importBook(file: File, bookId: string, onProgress: (percent: number) => void): Promise<BookImportResult> {
  const upload = () => new Promise<{status: number; data: BookImportResult & {error?: string; code?: string}}>((resolve, reject) => {
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
  let result = await upload()
  if (result.status === 403 && result.data.code === 'session-expired') {
    await renewToken(); onProgress(0); result = await upload()
  }
  if (result.status < 200 || result.status >= 300) throw new Error(result.data.error || 'Could not import this book. Choose the file again to retry.')
  return result.data
}
/** Delete the app's stored copy of a book. Notes and reading position stay on the server. */
export function removeBook(bookId: string) { return api<{ok: boolean}>('/library/remove', {bookId}) }
/** True when the server answers /api/health within 5 seconds. */
export async function serverReachable(){
  try{return (await fetch('/api/health',{cache:'no-store',signal:AbortSignal.timeout(5000)})).ok}catch{return false}
}
