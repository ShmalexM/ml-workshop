let token = ''
export async function api<T>(path:string, body?:unknown):Promise<T> {
  const response=await fetch('/api'+path,{method:body===undefined?'GET':'POST',headers:body===undefined?{}:{'Content-Type':'application/json','X-Workshop-Token':token},body:body===undefined?undefined:JSON.stringify(body)})
  const data=await response.json()
  if(!response.ok)throw new Error(data.error||'The local server could not complete this request.')
  return data
}
export async function bootstrap(){const data=await api<{token:string}>('/bootstrap');token=data.token}
