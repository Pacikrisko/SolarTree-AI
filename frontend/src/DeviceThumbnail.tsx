import {useEffect,useState} from 'react'
import type {Tree} from './types'
import {api} from './api'
import SolarTreeMark from './SolarTreeMark'

function OfficialThumbnail({tree}:{tree:Tree}){
  const [url,setUrl]=useState<string|null>(null)
  useEffect(()=>{let active=true,u:string|null=null;setUrl(null)
    if(tree.media_kind)api.loadTreeMedia(tree.id).then(b=>{u=URL.createObjectURL(b);if(active)setUrl(u);else URL.revokeObjectURL(u)}).catch(()=>{})
    return()=>{active=false;if(u)URL.revokeObjectURL(u)}
  },[tree.id,tree.media_kind])
  return <div className="official-tree-thumb">{url ? tree.media_kind==='video' ?<video src={url} muted loop playsInline autoPlay/>:<img src={url} alt={tree.model.name}/> :<SolarTreeMark size={88}/>}</div>
}

const cardArt: Record<string,string> = {
  'IVAN-TREE-0001':'prototype',
  'URBAN-TREE-0001':'urban-straight',
  'URBAN-TREE-0002':'urban-curved',
}

export default function DeviceThumbnail({tree}:{tree:Tree}){
  const art=cardArt[tree.code]
  if(!art)return <OfficialThumbnail tree={tree}/>
  return <div className="official-tree-thumb">
    <img src={'/tree-cards/'+art+'.png'} alt={tree.model.name} style={{objectFit:'contain',padding:'6px',boxSizing:'border-box',background:'transparent'}}/>
  </div>
}
