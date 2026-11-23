import {tr} from './language'
import {LanguageButton} from './LanguageButton'
import {useState, type FormEvent} from 'react'
import {ArrowRight, CircleAlert, Eye, EyeOff, LoaderCircle, LockKeyhole, Mail, UserRound} from 'lucide-react'
import SolarTreeMark from './SolarTreeMark'
import {api} from './api'
import type {TokenPayload} from './types'
import './auth.css'

export default function AuthScreen({onSuccess}: {onSuccess: (payload: TokenPayload) => void}) {
  const [registering, setRegistering] = useState(false)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [visible, setVisible] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  function switchMode() {
    setRegistering(!registering)
    setError('')
    setPassword('')
    setVisible(false)
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (busy) return
    setBusy(true)
    setError('')
    try {
      const result = registering
        ? await api.register(name.trim(), email.trim(), password)
        : await api.login(email.trim(), password)
      onSuccess(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : tr("Възникна грешка. Опитай отново."))
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="signin">
      <div className="signin-card">
        <figure className="signin-poster">
          <img className="signin-art" src="/solar-concept.jpg" alt="" width="1000" height="1000" />
          <div className="signin-brand" aria-label="SolarTree AI">
            <span className="signin-mark" aria-hidden="true"><SolarTreeMark size={28} /></span>
            <span>SolarTree <b>AI</b></span>
          </div>
          <figcaption>
            <span>{tr("Концептуална визуализация")}</span>
            <strong>{tr("Соларно дърво")}</strong>
          </figcaption>
        </figure>
        <section className="signin-panel" aria-labelledby="signin-title">
          <div className="signin-content">
            <LanguageButton/>
            <header key={registering ? "register" : "login"}>
              <h1 id="signin-title">{registering ? tr("Създай профил") : tr("Вход в профила")}</h1>
              <p>{registering ? tr("С един профил можеш да добавяш и следиш своите соларни дървета.") : tr("Влез, за да следиш устройствата и измерванията си.")}</p>
            </header>
            <form onSubmit={submit} className="signin-form" aria-busy={busy}>
              {registering && (
                <div className="signin-field">
                  <label htmlFor="signin-name">{tr("Име и фамилия")}</label>
                  <div className="signin-input">
                    <UserRound size={18} aria-hidden="true" />
                    <input id="signin-name" name="name" autoComplete="name" required minLength={2} maxLength={100} value={name} onChange={e => setName(e.target.value)} />
                  </div>
                </div>
              )}
              <div className="signin-field">
                <label htmlFor="signin-email">{tr("Имейл адрес")}</label>
                <div className="signin-input">
                  <Mail size={18} aria-hidden="true" />
                  <input id="signin-email" name="email" type="email" autoComplete="username" autoCapitalize="none" spellCheck={false} placeholder="name@example.com" required value={email} onChange={e => setEmail(e.target.value)} />
                </div>
              </div>
              <div className="signin-field">
                <label htmlFor="signin-password">{tr("Парола")}</label>
                <div className="signin-input">
                  <LockKeyhole size={18} aria-hidden="true" />
                  <input id="signin-password" name="password" type={visible ? 'text' : 'password'} autoComplete={registering ? 'new-password' : 'current-password'} placeholder={registering ? tr("Въведи нова парола") : tr("Въведи паролата си")} required minLength={registering ? 8 : 1} value={password} onChange={e => setPassword(e.target.value)} />
                  <button type="button" className="signin-reveal" aria-label={visible ? tr("Скрий паролата") : tr("Покажи паролата")} onClick={() => setVisible(!visible)}>
                    {visible ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
                {registering && <small>{tr("Използвай поне 8 символа.")}</small>}
              </div>
              {error && <p className="signin-error" role="alert"><CircleAlert size={17} aria-hidden="true" />{tr(error)}</p>}
              <button className="signin-submit" type="submit" disabled={busy}>
                {busy ? tr("Свързване…") : registering ? tr("Създай профил") : tr("Влез в приложението")}
                {busy ? <LoaderCircle size={18} aria-hidden="true" /> : <ArrowRight size={18} aria-hidden="true" />}
              </button>
            </form>
            <p className="signin-switch">
              {registering ? tr("Вече имаш профил?") : tr("Нямаш профил?")}
              <button type="button" disabled={busy} onClick={switchMode}>{registering ? tr("Вход") : tr("Регистрация")}</button>
            </p>
          </div>
        </section>
      </div>
    </main>
  )
}
