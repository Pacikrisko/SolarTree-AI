import { english } from './translations'

export type Language='bg'|'en'
const key='solartree_language'
export function getLanguage():Language { return localStorage.getItem(key)==='en'?'en':'bg' }
export function locale() { return getLanguage()==='en'?'en-GB':'bg-BG' }
export function tr(text:string) { return getLanguage()==='en'?(english[text]??text):text }
export function setLanguage(language:Language) {
  localStorage.setItem(key,language)
  document.documentElement.lang=language
  window.dispatchEvent(new Event('solartree-language'))
}
export function subscribeLanguage(notify:()=>void) {
  const onStorage=(event:StorageEvent)=>{
    if(event.key===key||event.key===null){
      document.documentElement.lang=getLanguage()
      notify()
    }
  }
  window.addEventListener('solartree-language',notify)
  window.addEventListener('storage',onStorage)
  return ()=>{
    window.removeEventListener('solartree-language',notify)
    window.removeEventListener('storage',onStorage)
  }
}
