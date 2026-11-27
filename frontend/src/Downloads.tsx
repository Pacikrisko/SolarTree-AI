import {useState} from 'react'
import {Download, Monitor, Smartphone} from 'lucide-react'
import {getLanguage} from './language'
import './downloads.css'

export default function Downloads(){
  const [guide,setGuide]=useState(false)
  if(window.matchMedia('(display-mode: standalone)').matches||(navigator as Navigator & {standalone?:boolean}).standalone||sessionStorage.getItem('solix.launcher'))return null
  const en=getLanguage()==='en'
  const base='https://github.com/Pacikrisko/SolarTree-AI/releases/latest/download/'
  return <footer className="download-banner">
    <div className="download-identity"><img src="/solix.svg" width="52" height="52" alt=""/><div>
      <h2>{en?'Get the Solix app':'Изтегли приложението Solix'}</h2>
      <p>{en?'Your trees on your computer or phone.':'Твоите дървета на компютъра или телефона.'}</p>
    </div></div>
    <div className="download-actions">{([[Monitor,'Windows','Solix-Setup.exe'],[Smartphone,'Android','Solix.apk']] as const).map(([Icon,name,file])=>{
      const Device=Icon
      return <a key={String(name)} href={base+file}><Device size={19}/>{String(name)}<Download size={15}/></a>
    })}<a href="/Solix.mobileconfig" onClick={()=>setGuide(true)}><Smartphone size={19}/>iPhone<Download size={15}/></a></div>
    {guide&&<p className="iphone-guide">{en?'Open Settings → Profile Downloaded → Install to add the Solix icon.':'Отвори Настройки → Изтеглен профил → Инсталиране, за да добавиш иконата на Solix.'}</p>}
  </footer>
}
