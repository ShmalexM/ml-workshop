let token = ''
export async function api<T>(path:string, body?:unknown):Promise<T> {
  let response:Response
  try{response=await fetch('/api'+path,{method:body===undefined?'GET':'POST',headers:body===undefined?{}:{'Content-Type':'application/json','X-Workshop-Token':token},body:body===undefined?undefined:JSON.stringify(body)})}
  catch{throw new Error('Cannot reach the local server. Start Engineering Workshop again, then reload this page.')}
  const data=await response.json()
  if(!response.ok)throw new Error(data.error||'The local server could not complete this request.')
  return data
}
export async function bootstrap(){const data=await api<{token:string}>('/bootstrap');token=data.token}
