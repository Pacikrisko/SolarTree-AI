import {useSyncExternalStore} from 'react'
import {Languages} from 'lucide-react'
import {getLanguage,setLanguage,subscribeLanguage} from './language'

export const useLanguage=()=>useSyncExternalStore(subscribeLanguage,getLanguage)
export function LanguageButton(){
  const language=useLanguage()
  const next=language==='bg'?'en':'bg'
  const label=next==='en'?'Switch to English':'Премини на български'
  return <button type="button" className="language-switch" aria-label={label} title={label} lang={next} onClick={()=>setLanguage(next)}>
    <Languages size={16} aria-hidden="true"/>{next==='en'?'EN':'БГ'}
  </button>
}
