import {useEffect,useState,type FormEvent} from 'react'
import {request} from './api'
import {getLanguage} from './language'
import type {Tree} from './types'

type Ticket={id:number;subject:string;category:string;channel:string;model:string|null;serial:string|null;warranty:string|null;customer:string;agent:string|null;closed:boolean}
type Desk={agent:boolean;tickets:Ticket[]}
type Thread=Ticket & {messages:{id:number;agent:boolean;body:string;time:string}[]}

export default function Support({trees}:{trees:Tree[]}){
  const en=getLanguage()==='en'
  const t=(bg:string,eng:string)=>en?eng:bg
  const categories:Record<string,string>={account:t('Профил и достъп','Account and access'),connection:t('Свързване и Wi-Fi','Connectivity and Wi-Fi'),performance:t('Измервания и работа','Readings and performance'),warranty:t('Гаранция и сервиз','Warranty and repair'),other:t('Друго','Other')}
  const [desk,setDesk]=useState<Desk|null>(null),[id,select]=useState<number|null>(null)
  const [thread,setThread]=useState<Thread|null>(null),[revision,refresh]=useState(0)
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[network,setNetwork]=useState('')
  useEffect(()=>{
    let active=true,timer:number
    async function poll(){
      try{
        const [list,detail]=await Promise.all([request<Desk>('/support'),id?request<Thread>('/support/'+id):Promise.resolve(null)])
        if(active){setDesk(list);setThread(detail);setNetwork('')}
      }catch(e){if(active)setNetwork((e as Error).message)}
      finally{if(active)timer=window.setTimeout(poll,id?3000:6000)}
    }
    void poll()
    return ()=>{active=false;window.clearTimeout(timer)}
  },[id,revision])
  async function submit(event:FormEvent<HTMLFormElement>,action:'new'|'reply'|'close'){
    event.preventDefault()
    if(busy)return
    const form=event.currentTarget,fields=new FormData(form)
    setBusy(true);setError('')
    try{
      if(action==='new'){
        const data=Object.fromEntries(fields)
        const row=await request<{id:number}>('/support',{method:'POST',body:JSON.stringify({...data,tree_id:data.tree_id?Number(data.tree_id):null})})
        select(row.id)
      }else{
        await request('/support/'+id+'/'+action,{method:'POST',body:JSON.stringify({body:fields.get('body')})})
      }
      form.reset();refresh(v=>v+1)
    }catch(e){setError((e as Error).message)}finally{setBusy(false)}
  }
  const status=(r:Ticket)=>r.closed?t('Приключено','Closed'):r.agent?t('Агент','Agent')+' · '+r.agent:t('Очаква агент','Waiting for an agent')
  const current=thread?.id===id?thread:null
  return <div className="page-body support-desk"><h2>{desk?.agent?t('Работно място на агента','Agent workspace'):t('Център за поддръжка','Support center')}</h2>
    {(error||network)&&<p role="alert">{error||network}</p>}
    <div className="support-columns"><aside className="panel"><h3>{desk?.agent?t('Входящи случаи','Incoming cases'):t('Моите запитвания','My requests')}</h3>
      {!desk?.agent&&<button className="btn btn-primary" onClick={()=>select(null)}>{t('Ново запитване','New request')}</button>}
      {desk?.tickets.map(r=><button key={r.id} className="btn btn-outline support-case" aria-pressed={id===r.id} onClick={()=>select(r.id)}>#{r.id} · {r.subject}<small>{status(r)}</small></button>)}
      {desk&&!desk.tickets.length&&<p>{t('Все още няма запитвания.','No requests yet.')}</p>}</aside>
    <section className="panel">{!desk||id&&!current?<p>{t('Зареждане…','Loading…')}</p>:current?<div key={current.id}>
      <small>#{current.id} · {categories[current.category]} · {current.channel==='chat'?t('Чат на живо','Live chat'):t('Запитване','Request')}</small><h3>{current.subject}</h3>
      <p>{current.customer} · {status(current)}</p><p>{current.model?current.model+' · '+current.serial:t('Общо запитване','General inquiry')}</p>
      {current.serial&&<p>{current.warranty?(current.warranty>=new Date().toISOString().slice(0,10)?t('В гаранция до ','Under warranty until '):t('Гаранцията е изтекла на ','Warranty expired on '))+current.warranty:t('Гаранция · срокът не е потвърден','Warranty · term unconfirmed')}</p>}
      <div className="support-log" role="log">{current.messages.map(m=><article key={m.id}><strong>{m.agent?current.agent:current.customer}</strong> <small>{new Date(m.time).toLocaleString(en?'en-GB':'bg-BG')}</small><p>{m.body}</p></article>)}</div>
      {!current.closed&&<><form className="modal-form" onSubmit={ev=>submit(ev,'reply')}><label>{t('Отговор','Reply')}<textarea required maxLength={4000} name="body"/></label><button disabled={busy} className="btn btn-primary">{t('Изпрати','Send')}</button></form><form onSubmit={ev=>submit(ev,'close')}><button disabled={busy} className="btn btn-quiet">{t('Приключи случая','Close case')}</button></form></>}
    </div>:desk.agent?<p>{t('Избери случай от входящите запитвания.','Select an incoming case.')}</p>:<form className="modal-form" onSubmit={ev=>submit(ev,'new')}>
      <label>{t('Как искаш да се свържеш с нас?','How would you like to contact us?')}<select name="channel"><option value="ticket">{t('Писмено запитване','Written request')}</option><option value="chat">{t('Чат на живо с агент','Live agent chat')}</option></select></label>
      <label>{t('Устройство','Device')}<select name="tree_id"><option value="">{t('Общо запитване','General inquiry')}</option>{trees.map(tree=><option key={tree.id} value={tree.id}>{tree.name} · {tree.code}</option>)}</select></label>
      <label>{t('Категория','Category')}<select name="category">{Object.entries(categories).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label>
      <label>{t('Тема','Subject')}<input required name="subject" minLength={2} maxLength={140}/></label><label>{t('Опиши проблема','Describe the issue')}<textarea required name="body" maxLength={4000}/></label>
      <button disabled={busy} className="btn btn-primary">{t('Свържи се с екипа','Contact the team')}</button></form>}</section></div></div>
}
