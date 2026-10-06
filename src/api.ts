let token = ''
let renewal:Promise<void>|null = null
async function request(path:string, body?:unknown):Promise<[Response,any]> {
  let response:Response
  try{response=await fetch('/api'+path,{method:body===undefined?'GET':'POST',headers:body===undefined?{}:{'Content-Type':'application/json','X-Workshop-Token':token},body:body===undefined?undefined:JSON.stringify(body)})}
  catch{throw new Error('Cannot reach the local server. Start Engineering Workshop again, then reload this page.')}
  return [response,await response.json()]
}
export async function api<T>(path:string, body?:unknown):Promise<T> {
  let [response,data]=await request(path,body)
  // A restarted server rejects the old session token. Get the new token once, then retry this write once.
  if(response.status===403&&data.code==='session-expired'){await renewToken();[response,data]=await request(path,body)}
  if(!response.ok)throw new Error(data.error||'The local server could not complete this request.')
  return data
}
export async function bootstrap(){const data=await api<{token:string}>('/bootstrap');token=data.token}
// Writes that fail together share one token request.
function renewToken(){return renewal??=bootstrap().finally(()=>{renewal=null})}
/** True when the server answers /api/health within 5 seconds. */
export async function serverReachable(){
  try{return (await fetch('/api/health',{cache:'no-store',signal:AbortSignal.timeout(5000)})).ok}catch{return false}
}
