import {useEffect,useState} from 'react'
import {Smartphone,RefreshCcw,Copy,CheckCircle2,ShieldCheck} from 'lucide-react'
import {api} from './api'
import type {PairSessionStart} from './types'
export default function PhonePairing({onAdded}:{onAdded:(treeId:number)=>Promise<void>}){
  const [session,setSession]=useState<PairSessionStart|null>(null)
  const [busy,setBusy]=useState(false)
  const [error,setError]=useState('')
  const [showLink,setShowLink]=useState(false)
  const [copied,setCopied]=useState(false)
  const [status,setStatus]=useState('pending')
  async function copyLink(){
    if(!session?.url)return
    try{await navigator.clipboard.writeText(session.url);setCopied(true)}catch{setShowLink(true)}
  }
  async function start(){setBusy(true);setError('');try{const s=await api.startPairSession();setSession(s);setStatus('pending');setShowLink(false);setCopied(false)}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
  useEffect(()=>{if(!session||status!=='pending')return
    let running=true
    let checking=false
    const interval=window.setInterval(async()=>{
      if(checking)return
      checking=true
      try{const result=await api.pairSessionStatus(session.id)
        if(!running)return
        setError('')
        if(result.status==='completed'&&result.tree_id){setStatus('completed');window.clearInterval(interval);await onAdded(result.tree_id)}
        else if(result.status!=='pending'){setStatus(result.status);window.clearInterval(interval)}
      }catch(e){if(running)setError((e as Error).message)}finally{checking=false}
    },1400)
    return()=>{running=false;window.clearInterval(interval)}
  },[session,status,onAdded])
  return <section className="phone-pair">
    <div className="phone-pair-title"><Smartphone size={21}/><div><strong>Сканирай с телефон</strong><small>Отвори скенер само с камера. Дървото се появява автоматично тук.</small></div></div>
    {!session?<button className="btn btn-primary full" type="button" onClick={start} disabled={busy}>{busy?'Подготовка…':'Създай линк за телефона'}</button>:
    session.needs_https?<div className="phone-setup"><ShieldCheck size={20}/><div><strong>Необходим е защитен адрес</strong><p>За камерата на телефона настрой <code>PUBLIC_SCANNER_URL</code> в <code>backend/.env</code> към HTTPS адреса на скенера. След това рестартирай сървъра и натисни „Нов линк“.</p></div><button type="button" onClick={start} disabled={busy} className="btn btn-outline"><RefreshCcw size={14}/> Нов линк</button></div>:
    <div className="phone-pair-ready">
      {session.qr_data_uri&&<img src={session.qr_data_uri} alt="Временен QR код за отваряне на скенер на телефон" className="session-qr"/>}
      <div className="phone-pair-instructions"><strong>{status==='pending'?'Очаквам сканиране…':status==='completed'?'Устройството е добавено':'Сесията е изтекла'}</strong>
        <p>1. Сканирай този код от екрана с телефона.</p><p>2. Отвори камерата и насочи към QR етикета върху дървото.</p><p>3. То се добавя към твоя профил без повторно влизане.</p>
        <div className="phone-pair-buttons"><button type="button" className="btn btn-outline btn-small" onClick={copyLink}><Copy size={14}/> {copied?'Копирано':'Копирай линка'}</button><button type="button" className="btn btn-quiet btn-small" disabled={busy} onClick={start}><RefreshCcw size={14}/> Нов линк</button></div>
        {showLink&&<label>Копирай линка ръчно<input readOnly value={session.url||''} onFocus={e=>e.target.select()}/></label>}
      </div>
    </div>}
    {status==='completed'&&<p className="pairing-complete"><CheckCircle2 size={16}/> Успешно сдвояване</p>}
    {error&&<p className="pair-scan-error">{error}</p>}
  </section>
}
