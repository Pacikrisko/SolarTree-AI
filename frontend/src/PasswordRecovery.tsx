import {useState,type FormEvent} from 'react'
import {useLanguage,LanguageButton} from './LanguageButton'
import {getLanguage} from './language'
import {setAuthToken} from './api'

export default function PasswordRecovery({hash}:{hash:string}){
  useLanguage()
  const en=getLanguage()==='en'
  const t=(bg:string,english:string)=>en?english:bg
  const reset=hash.startsWith('#/reset-password/')
  const [email,setEmail]=useState(''),[password,setPassword]=useState(''),[again,setAgain]=useState('')
  const [busy,setBusy]=useState(false),[done,setDone]=useState(false),[error,setError]=useState('')
  async function submit(e:FormEvent){
    e.preventDefault()
    if(busy)return
    setError('')
    if(reset&&password!==again){setError(t('Паролите не съвпадат.','Passwords do not match.'));return}
    setBusy(true)
    try{
      const body=reset?{token:hash.slice('#/reset-password/'.length),password}:{email:email.trim(),language:en?'en':'bg'}
      const r=await fetch('/api/auth/'+(reset?'reset-password':'forgot-password'),{
        method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)
      })
      if(!r.ok){
        const invalid=reset&&(r.status===400||r.status===422)
        setError(invalid?t('Връзката е изтекла или вече е използвана. Заяви нова.','This link has expired or has been used. Request another.')
          :t('Услугата е временно недостъпна. Опитай по-късно.','The service is temporarily unavailable. Try again later.'))
        return
      }
      setPassword('');setAgain('');setDone(true)
      if(reset)setAuthToken('')
    }catch{setError(t('Няма връзка със сървъра.','Could not reach the server.'))}
    finally{setBusy(false)}
  }
  return <main className="signin stellar-entry">
    <div className="entry-top"><div className="entry-top-inner"><strong>SolarTree AI</strong><LanguageButton/></div></div>
    <header className="entry-heading" style={{textAlign:'center'}}><h1>{reset?t('Нова парола','New password'):t('Забравена парола','Forgot password')}</h1></header>
    <section className="signin-panel" style={{width:'min(440px,calc(100% - 32px))',margin:'0 auto',padding:24}}>
    {done?<p role="status">{reset?t('Паролата е сменена. Влез с новата парола.','Password changed. Sign in with your new password.'):t('Ако имаш профил с парола на този адрес, ще получиш връзка по имейл. Тя е валидна 30 минути.','If this address has a password account, you will receive a link by email. It expires in 30 minutes.')}</p>
      :<form className="signin-form" onSubmit={submit}>
      {reset?<>
        <label className="signin-field">{t('Нова парола (поне 8 символа)','New password (at least 8 characters)')}<span className="signin-input"><input required type="password" autoComplete="new-password" minLength={8} maxLength={128} value={password} onChange={e=>setPassword(e.target.value)}/></span></label>
        <label className="signin-field">{t('Повтори паролата','Confirm password')}<span className="signin-input"><input required type="password" autoComplete="new-password" minLength={8} maxLength={128} value={again} onChange={e=>setAgain(e.target.value)}/></span></label>
      </>
        :<label className="signin-field">{t('Имейл на профила','Account email')}<span className="signin-input"><input required type="email" autoComplete="email" maxLength={200} value={email} onChange={e=>setEmail(e.target.value)}/></span></label>}
      {error&&<p className="signin-error" role="alert">{error}</p>}
      <button type="submit" className="btn btn-primary" disabled={busy}>{busy?'…':reset?t('Запази паролата','Save password'):t('Изпрати връзка','Send reset link')}</button>
      {reset&&error&&<a href="#/forgot-password">{t('Заяви нова връзка','Request a new link')}</a>}
    </form>}
    <p className="signin-switch"><a href="#/overview">{t('Към входа','Back to sign in')}</a></p>
    </section>
  </main>
}
