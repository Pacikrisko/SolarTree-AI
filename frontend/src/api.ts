import type {Alert, ChatMessage, Forecast, Health, Reading, Service, TokenPayload, Tree, TreeConfig, User, PairResult, OxygenHistory, PairSessionStart, PairSessionStatus, ResourceEstimate} from './types'
let token = localStorage.getItem('solartree_token') || ''
export function setAuthToken(value:string) {
  token=value
  if (value) localStorage.setItem('solartree_token',value)
  else localStorage.removeItem('solartree_token')
}
async function request<T>(path:string, options:RequestInit={}):Promise<T> {
  const headers:Record<string,string>={'Content-Type':'application/json'}
  if(token) headers.Authorization=`Bearer ${token}`
  const response=await fetch(`/api${path}`,{...options,headers:{...headers,...(options.headers as Record<string,string>||{})}})
  if(!response.ok){
    let message=`Грешка ${response.status}`
    try {const json=await response.json(); if(typeof json.detail==='string')message=json.detail} catch { /* fallback */ }
    throw new Error(message)
  }
  return response.json() as Promise<T>
}
export const api={
  health:()=>request<Health>('/health'),
  login:(email:string,password:string)=>request<TokenPayload>('/auth/login',{method:'POST',body:JSON.stringify({email,password})}),
  register:(name:string,email:string,password:string)=>request<TokenPayload>('/auth/register',{method:'POST',body:JSON.stringify({name,email,password})}),
  me:()=>request<User>('/auth/me'),
  updateProfile:(name:string)=>request<User>('/auth/me',{method:'PATCH',body:JSON.stringify({name})}),
  changePassword:(current_password:string,new_password:string)=>request<{ok:boolean}>('/auth/change-password',{method:'POST',body:JSON.stringify({current_password,new_password})}),
  trees:()=>request<Tree[]>('/trees'),
  tree:(id:number)=>request<Tree>(`/trees/${id}`),
  treeConfig:(id:number)=>request<TreeConfig>(`/trees/${id}/config`),
  resources:(id:number,waterFill:number,pressure:number|null,load:number,efficiency:number)=>{
    const params=new URLSearchParams({water_fill_pct:String(waterFill),fuel_cell_load_kw:String(load),efficiency:String(efficiency)})
    if(pressure!==null)params.set('pressure_bar_g',String(pressure))
    return request<ResourceEstimate>(`/trees/${id}/resources?${params.toString()}`)
  },
  readings:(id:number)=>request<Reading[]>(`/trees/${id}/readings?limit=144`),
  oxygen:(id:number)=>request<OxygenHistory>(`/trees/${id}/oxygen?limit=240`),
  forecast:(id:number)=>request<Forecast>(`/trees/${id}/forecast`),
  alerts:()=>request<Alert[]>('/alerts'),
  maintenance:()=>request<Service[]>('/maintenance'),
  maintenanceFor:(id:number)=>request<Service[]>(`/trees/${id}/maintenance`),
  serviceSchedule:(treeId:number,component:string,interval_days:number)=>request<{ok:boolean}>(`/trees/${treeId}/maintenance/${component}`,{method:'PUT',body:JSON.stringify({interval_days})}),
  serviceDone:(treeId:number,component:string)=>request<{ok:boolean}>(`/trees/${treeId}/maintenance/${component}/complete`,{method:'POST'}),
  ack:(id:number)=>request<{ok:boolean}>(`/alerts/${id}/ack`,{method:'POST'}),
  simulate:(id:number,mode:'normal'|'anomaly')=>request<unknown>(`/trees/${id}/simulate`,{method:'POST',body:JSON.stringify({mode})}),
  startPairSession:()=>request<PairSessionStart>('/pair-sessions',{method:'POST'}),
  pairSessionStatus:(id:number)=>request<PairSessionStatus>(`/pair-sessions/${id}`),
  pairResolve:(code:string,claim_token:string)=>request<PairResult>('/pair/resolve',{method:'POST',body:JSON.stringify({code,claim_token})}),
  removeTree:(id:number)=>request<{ok:boolean}>(`/trees/${id}`,{method:'DELETE'}),
  createTree:(data:{name:string;code:string;claim_token:string;location:string;lat:number|null;lng:number|null})=>request<Tree>('/trees',{method:'POST',body:JSON.stringify(data)}),

  loadTreeMedia:async(id:number):Promise<Blob>=>{
    const response=await fetch(`/api/trees/${id}/media`,{headers:token?{Authorization:`Bearer ${token}`}:{}})
    if(!response.ok)throw new Error('Неуспешно зареждане на медийния файл.')
    return response.blob()
  },
  chat:(message:string,tree_id:number|null,history:ChatMessage[])=>request<{reply:string;mode:'llm';model:string}>('/chat',{method:'POST',body:JSON.stringify({message,tree_id,history:history.slice(-8)})}),
}
