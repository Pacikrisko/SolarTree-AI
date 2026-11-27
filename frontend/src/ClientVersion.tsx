import {useEffect,useState,type ReactNode} from 'react'
import {getLanguage} from './language'

function launcher(){
  const params=new URLSearchParams(location.search)
  const platform=params.get('solixClient')
  if(platform==='windows'||platform==='android') {
    const client={platform,build:Number(params.get('build'))||0}
    sessionStorage.setItem('solix.launcher',JSON.stringify(client))
    return client
  }
  return JSON.parse(sessionStorage.getItem('solix.launcher')||'null') as {platform:string;build:number}|null
}

export default function ClientVersion({children}:{children:ReactNode}){
  const [client]=useState(launcher)
  const [update,setUpdate]=useState('')
  useEffect(()=>{
    if(!client)return
    let active=true
    async function check(){
      try {
        const res=await fetch('/client-version.json',{cache:'no-store'})
        if(!res.ok)return
        const current=await res.json()
        if(active&&client&&client.build<current.minimumBuild)setUpdate(current.downloads[client.platform])
      }catch{/* Retry when the app regains focus or the connection returns. */}
    }
    void check()
    const interval=setInterval(check,60000)
    window.addEventListener('focus',check)
    window.addEventListener('online',check)
    return ()=>{active=false;clearInterval(interval);window.removeEventListener('focus',check);window.removeEventListener('online',check)}
  },[client])
  if(!update)return <>{children}</>
  const en=getLanguage()==='en'
  return <main className="signin"><section className="panel" style={{margin:'auto',maxWidth:'28rem',padding:'clamp(1.5rem,5vw,2.5rem)',display:'grid',gap:'1.25rem',justifyItems:'start',lineHeight:1.55}}><h1>{en?'Update Solix':'Актуализирай Solix'}</h1><p>{en?'Install the current version, then reopen Solix to continue.':'Инсталирай актуалната версия и отвори Solix отново, за да продължиш.'}</p><a className="btn btn-primary" href={update}>{en?'Update':'Актуализирай'}</a></section></main>
}

