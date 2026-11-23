import {tr} from './language'
import {useEffect,useState} from 'react'
import {ImageOff} from 'lucide-react'
import type {Tree} from './types'
import {api} from './api'
import SolarTreeMark from './SolarTreeMark'

export default function DeviceMedia({tree,compact=false}:{tree:Tree|null;compact?:boolean;onChanged?:()=>Promise<void>}){
  const [url,setUrl]=useState<string|null>(null)
  const [error,setError]=useState(false)
  useEffect(()=>{
    let active=true,objectUrl:string|null=null
    setUrl(null);setError(false)
    if(!tree?.id||!tree.media_kind)return
    api.loadTreeMedia(tree.id).then(blob=>{
      objectUrl=URL.createObjectURL(blob)
      if(active)setUrl(objectUrl)
      else URL.revokeObjectURL(objectUrl)
    }).catch(()=>{if(active)setError(true)})
    return()=>{active=false;if(objectUrl)URL.revokeObjectURL(objectUrl)}
  },[tree?.id,tree?.media_kind])
  return <div className={`device-media ${compact?'device-media-compact':''} official-device-media`}>
    {tree?.media_kind && url ? tree.media_kind==='video' ?
      <video className="device-media-content" playsInline muted loop autoPlay controls={!compact} preload="metadata" src={url}/>
      :<img className="device-media-content" alt={`${tr("Официално изображение на")} ${tree.model.name}`} src={url}/>
      :<div className="device-media-placeholder"><div className="media-placeholder-halo"><SolarTreeMark size={68}/></div><strong>{tree?.model?.name||'SolarTree'}</strong><span>{error?tr("Изображението не може да се зареди."):tr("Официално изображение на модела")}</span><ImageOff size={16} opacity={.4}/></div>}
    {tree?.media_kind&&<div className="official-media-caption">{tree.model.name}</div>}
  </div>
}
