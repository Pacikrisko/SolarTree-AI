import {useEffect, useRef, useState} from 'react'
import {api} from './api'
import {getLanguage,tr} from './language'

type GoogleID={
  initialize:(config:{client_id:string; callback:(result:{credential?:string})=>void; auto_select:boolean})=>void
  renderButton:(element:HTMLElement, options:{
    type:'standard'; theme:'outline'|'filled_black'; size:'large'; text:'continue_with'
    shape:'pill'; logo_alignment:'center'; width:string; locale:string
  })=>void
}
declare global { interface Window { google?:{accounts?:{id?:GoogleID}} } }

let sdk:Promise<GoogleID>|null=null
let configuredClient=''
let receive:((credential:string)=>void)|null=null
function loadSDK():Promise<GoogleID>{
  const ready=window.google?.accounts?.id
  if(ready)return Promise.resolve(ready)
  if(sdk)return sdk
  sdk=new Promise<GoogleID>((resolve,reject)=>{
    const script=document.createElement('script')
    script.src='https://accounts.google.com/gsi/client'
    script.async=true
    const fail=()=>{window.clearTimeout(timeout);script.remove();sdk=null;reject(new Error('Google не се зареди.'))}
    const timeout=window.setTimeout(fail,15000)
    script.onerror=fail
    script.onload=()=>{
      window.clearTimeout(timeout)
      const id=window.google?.accounts?.id
      if(id)resolve(id);else fail()
    }
    document.head.appendChild(script)
  })
  return sdk
}

export default function GoogleSignIn({onCredential, disabled}: {
  onCredential: (credential: string) => void
  disabled: boolean
}) {
  const target = useRef<HTMLDivElement>(null)
  const callback = useRef(onCredential)
  callback.current = onCredential
  const [state, setState] = useState<'loading' | 'ready' | 'disabled' | 'error'>('loading')
  const [attempt, setAttempt] = useState(0)
  const language = getLanguage()

  useEffect(() => {
    let active = true
    let observer: ResizeObserver | undefined
    const element = target.current
    const listener = (credential: string) => { if (active) callback.current(credential) }
    setState('loading')

    api.googleConfig().then(async config => {
      if (!active || !element) return
      if (!config.client_id) { setState('disabled'); return }
      const id = await loadSDK()
      if (!active) return
      if (configuredClient !== config.client_id) {
        id.initialize({
          client_id: config.client_id,
          auto_select: false,
          callback: result => { if (result.credential) receive?.(result.credential) }
        })
        configuredClient = config.client_id
      }
      receive = listener
      let lastWidth = 0
      observer = new ResizeObserver(([entry]) => {
        if (!active) return
        const width = Math.min(400, Math.floor(entry.contentRect.width))
        if (width <= 0 || width === lastWidth) return
        lastWidth = width
        element.replaceChildren()
        id.renderButton(element, {
          type: 'standard',
          theme: document.documentElement.dataset.theme === 'dark' ? 'filled_black' : 'outline',
          size: 'large',
          text: 'continue_with',
          shape: 'pill',
          logo_alignment: 'center',
          width: String(width),
          locale: language
        })
      })
      observer.observe(element)
      setState('ready')
    }).catch(() => { if (active) setState('error') })

    return () => {
      active = false
      observer?.disconnect()
      if (receive === listener) receive = null
      element?.replaceChildren()
    }
  }, [language, attempt])

  return (
    <div className="google-signin" hidden={state === 'disabled' || state === 'loading'} inert={disabled}>
      <div className="google-signin-widget" ref={target} hidden={state === 'error'} />
      {state === 'ready' && <div className="google-signin-divider">{tr('или')}</div>}
      {state === 'error' && (
        <div role="status">{tr('Google не се зареди.')} <button type="button" onClick={() => setAttempt(n => n + 1)}>{tr('Опитай отново')}</button></div>
      )}
    </div>
  )
}
