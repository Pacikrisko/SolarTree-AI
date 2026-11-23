import {useEffect,useRef,useState} from 'react'
import {api} from './api'
import type {ChatMessage} from './types'

export function useLocalAi(){
  const [state,setState]=useState<'off'|'loading'|'ready'|'error'>('off')
  const [status,setStatus]=useState('')
  const worker=useRef<Worker|null>(null)
  const pending=useRef<{resolve:(value:string)=>void;reject:(reason:Error)=>void}|null>(null)
  function stop(){
    worker.current?.terminate()
    worker.current=null
    pending.current?.reject(new Error('Локалният AI е спрян.'))
    pending.current=null
  }
  useEffect(()=>stop,[])
  function disable(){stop();setState('off');setStatus('')}
  function enable(){
    stop()
    if(!('gpu' in navigator)){
      setState('error');setStatus('Браузърът не предоставя WebGPU. Опитай с актуален Chrome или Edge с включено графично ускорение.');return
    }
    setState('loading');setStatus('Подготовка на модела…')
    const fail=(reason:string)=>{
      stop();setState('error');setStatus('Моделът не успя да се зареди или изпълни. Провери връзката и поддръжката на WebGPU. '+reason)
    }
    try{
      const w=new Worker(new URL('./localAi.worker.ts',import.meta.url),{type:'module'})
      worker.current=w
      w.onerror=e=>{if(worker.current===w)fail(e.message)}
      w.onmessage=({data})=>{
        if(worker.current!==w)return
        if(data.type==='progress')setStatus(data.text)
        if(data.type==='ready'){setState('ready');setStatus('Локалният AI е готов.')}
        if(data.type==='answer'){pending.current?.resolve(data.text);pending.current=null}
        if(data.type==='error'){
          if(!pending.current){fail(data.text);return}
          pending.current.reject(new Error('Неуспешен локален отговор. Опитай с по-кратък въпрос или избери едно дърво. '+data.text));pending.current=null
        }
      }
      w.postMessage({type:'init'})
    }catch(err){fail(String(err))}
  }
  async function ask(question:string,id:number|null,history:ChatMessage[]){
    const w=worker.current
    if(!w||state!=='ready'||pending.current)throw new Error('Моделът е зает или още се зарежда.')
    const devices=id===null?await api.trees():[await api.tree(id)]
    const context=await Promise.all(devices.map(async tree=>{
      const [services,oxygen,forecast]=await Promise.all([api.maintenanceFor(tree.id),api.oxygen(tree.id),api.forecast(tree.id)])
      return {name:tree.name,code:tree.code,location:tree.location,model:tree.model,connection:tree.connection,
        latest:tree.latest,sensors:tree.latest_sensors,simulation:tree.simulation,alerts:tree.open_alerts,
        maintenance:services.map(s=>({label:s.label,due:s.due_at})),
        oxygen:{total_l:oxygen.total_l,basis:oxygen.basis,from:oxygen.points[0]?.time,to:oxygen.points.at(-1)?.time},
        forecast:forecast.points}
    }))
    if(worker.current!==w)throw new Error('Локалната сесия е прекратена.')
    return new Promise<string>((resolve,reject)=>{
      pending.current={resolve,reject}
      w.postMessage({type:'ask',context,question,history:history.slice(-4).map(({role,content})=>({role,content:content.slice(0,400)}))})
    })
  }
  return {state,status,enable,disable,ask}
}
