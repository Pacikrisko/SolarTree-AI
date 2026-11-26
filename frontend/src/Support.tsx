import {useEffect,useRef,useState,type FormEvent} from 'react'
import {Headphones, Mail, MessageCircle, ShieldCheck} from 'lucide-react'
import {request} from './api'
import {getLanguage} from './language'
import type {Tree} from './types'
import './support.css'

const t=(bg:string,en:string)=>getLanguage()==='en'?en:bg
export function warrantyText(date?:string|null){
  if(!date) return t('Гаранция · няма потвърден срок','Warranty · term unconfirmed')
  const active=date>=new Date().toISOString().slice(0,10)
  return (active?t('В гаранция до ','Under warranty until '):t('Гаранцията е изтекла на ','Warranty expired on '))+new Date(date+'T12:00:00').toLocaleDateString(getLanguage()==='en'?'en-GB':'bg-BG')
}
const categories=()=>({account:t('Профил и достъп','Account access'),connection:t('Свързване и Wi-Fi','Connectivity and Wi-Fi'),performance:t('Измервания и работа','Readings and performance'),warranty:t('Гаранция и сервиз','Warranty and repair'),other:t('Друго','Other')})
type Ticket={id:number;subject:string;category:keyof ReturnType<typeof categories>;channel:string;model:string|null;serial:string|null;warranty:string|null;customer:string;agent:string|null;closed:boolean}
type Desk={agent:boolean;online:boolean;tickets:Ticket[]}
type Stats={power_w:number|null;water_pct:number|null;oxygen_flow_lph:number|null;battery_pct:number|null;time:string|null}
type Thread=Ticket & {viewer_agent:boolean;stats:Stats|null;messages:{id:number;agent:boolean;body:string;time:string}[]}
const state=(r:Ticket)=>r.closed?t('Приключено','Closed'):r.agent?t('Агент · ','Agent · ')+r.agent:t('Очаква агент','Waiting for agent')
const post=(path:string,data?:unknown)=>request(path,{method:'POST',body:data?JSON.stringify(data):undefined})
const chatUrl=(id:number)=>location.pathname+'?support-session='+id
function popup(url:string){return window.open(url,'_blank','popup,width=560,height=740,resizable=yes,scrollbars=yes')}
function Conversation({id,live}:{id:number;live:boolean}){
  const [row,setRow]=useState<Thread|null>(null),[note,setNote]=useState(''),[draft,write]=useState(''),[busy,setBusy]=useState(false),[ended,end]=useState(false),[tick,reload]=useState(0)
  const bottom=useRef<HTMLDivElement>(null)
  useEffect(()=>{
    if(ended)return
    let active=true,timer=0,lastPulse=0
    async function poll(){
      try{
        const item=await request<Thread>('/support/'+id)
        if(live&&item.channel!=='chat')throw Error(t('Невалидна сесия','Invalid session'))
        if(live&&!item.closed&&(!item.viewer_agent||item.agent)&&Date.now()-lastPulse>12000){
          await post('/support/'+id+'/pulse');lastPulse=Date.now()
        }
        if(active){setRow(item);setNote('');if(item.closed&&live)end(true)}
      }catch(e){if(active){setRow(null);setNote((e as Error).message)}}
      finally{if(active)timer=window.setTimeout(poll,live?2000:5000)}
    }
    void poll()
    return ()=>{active=false;clearTimeout(timer)}
  },[id,live,tick,ended])
  useEffect(()=>{bottom.current?.scrollIntoView({block:'nearest'})},[row?.messages.length])
  async function action(name:'accept'|'reply'|'close'){
    if(busy)return
    setBusy(true)
    try{
      await post('/support/'+id+'/'+name,name==='reply'?{body:draft.trim()}:undefined)
      if(name==='reply')write('')
      if(name==='close'&&live){end(true);setRow(null)}
      else reload(v=>v+1)
    }catch(e){setNote((e as Error).message)}finally{setBusy(false)}
  }
  if(ended)return <div role="status"><ShieldCheck/><h3>{t('Сесията приключи','Session ended')}</h3><p>{t('Достъпът на агента до дървото е прекратен.','Agent access to this tree has ended.')}</p></div>
  return <>{note&&<p role="alert">{note}</p>}{!row?!note&&<p>{t('Свързване…','Connecting…')}</p>:<>
    <small>#{id} · {categories()[row.category]}</small><h2>{row.subject}</h2><p className="desk-status">{state(row)}</p>
    {row.serial&&<p>{row.model} · {row.serial}<br/>{warrantyText(row.warranty)}</p>}
    {row.stats&&<section><h3>{t('Показатели за сесията','Session readings')}</h3><div className="desk-readings">{([['power_w',t('Мощност','Power'),'W'],['oxygen_flow_lph','O₂','L/h'],['water_pct',t('Вода','Water'),'%'],['battery_pct',t('Батерия','Battery'),'%']] as const).map(([k,label,unit])=><div key={k}><small>{label}</small><strong>{row.stats![k]??'—'} {unit}</strong></div>)}</div>{row.stats.time&&<small>{new Date(row.stats.time).toLocaleString()}</small>}</section>}
    <div className="desk-log" role="log">{row.messages.map(m=><article key={m.id} className={m.agent===row.viewer_agent?'own':''}><strong>{m.agent?row.agent:row.customer}</strong> <small>{new Date(m.time).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}</small><p>{m.body}</p></article>)}<div ref={bottom}/></div>
    {!row.closed&&<>{live&&!row.agent?row.viewer_agent?<button className="btn btn-primary" disabled={busy} onClick={()=>action('accept')}>{t('Приеми сесията','Accept session')}</button>:<p role="status">{t('Заявката е изпратена. Остави прозореца отворен, докато агент приеме.','Request sent. Keep this window open until an agent accepts.')}</p>:<form className="modal-form" onSubmit={e=>{e.preventDefault();void action('reply')}}><label>{t('Съобщение','Message')}<textarea value={draft} onChange={e=>write(e.target.value)} maxLength={4000} required/></label><button className="btn btn-primary" disabled={busy||!draft.trim()}>{t('Изпрати','Send')}</button></form>}
    {(!row.viewer_agent||row.agent)&&<button className="btn btn-quiet" disabled={busy} onClick={()=>action('close')}>{t('Приключи разговора','End conversation')}</button>}</>}
  </>}</>
}
export function LiveChat({id}:{id:number}){
  return <main className="desk-window"><div className="desk-heading"><Headphones/><h1>{t('Чат с агент','Live support')}</h1></div><section className="panel"><Conversation id={id} live/></section></main>
}
export default function Support({trees}:{trees:Tree[]}){
  const [desk,setDesk]=useState<Desk|null>(null),[id,select]=useState<number|null>(null),[channel,choose]=useState('ticket'),[treeId,setTree]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false),[revision,refresh]=useState(0),[blocked,setBlocked]=useState<number|null>(null)
  useEffect(()=>{
    let active=true,timer=0,lastPulse=0
    async function poll(){
      try{const data=await request<Desk>('/support')
        if(active){setDesk(data);if(data.agent&&Date.now()-lastPulse>15000){await post('/support/presence');lastPulse=Date.now()}}
      }catch(e){if(active)setError((e as Error).message)}
      finally{if(active)timer=window.setTimeout(poll,4000)}
    }
    void poll();return ()=>{active=false;clearTimeout(timer)}
  },[revision])
  async function submit(e:FormEvent<HTMLFormElement>){
    e.preventDefault();if(busy)return
    const form=e.currentTarget,data=Object.fromEntries(new FormData(form)),win=channel==='chat'?popup('about:blank'):null
    setBusy(true);setError('')
    try{const r=await request<{id:number}>('/support',{method:'POST',body:JSON.stringify({...data,channel,tree_id:treeId?Number(treeId):null})})
      if(channel==='chat'){if(win)win.location.replace(chatUrl(r.id));else setBlocked(r.id)}else select(r.id)
      form.reset();setTree('');refresh(v=>v+1)
    }catch(e){win?.close();setError((e as Error).message)}finally{setBusy(false)}
  }
  const tree=trees.find(r=>String(r.id)===treeId)
  return <main className="page-body support-desk"><header className="desk-heading"><Headphones/><div><h2>{desk?.agent?t('Агентска конзола','Agent workspace'):t('Център за поддръжка','Support center')}</h2>{desk&&<small>{desk.agent?t('Получаваш заявки, докато конзолата е отворена.','You receive requests while this desk is open.'):desk.online?t('Има агент онлайн','Agent online'):t('В момента няма агент онлайн','No agents currently online')}</small>}</div></header>
    {error&&<p role="alert">{error}</p>}{blocked&&<a className="btn btn-primary" href={chatUrl(blocked)} target="_blank" rel="noreferrer">{t('Отвори прозореца за чат','Open chat window')}</a>}
    <div className="support-columns"><aside className="panel"><h3>{desk?.agent?t('Входящи случаи','Incoming cases'):t('Моите запитвания','My requests')}</h3>
      {!desk?.agent&&<button className="btn btn-primary" onClick={()=>select(null)}>{t('Ново запитване','New request')}</button>}
      {desk?.tickets.map(r=><button key={r.id} className="btn btn-outline support-case" onClick={()=>{if(r.channel==='chat'&&!r.closed){if(!popup(chatUrl(r.id)))setBlocked(r.id)}else select(r.id)}}>#{r.id} · {r.subject}<small>{r.channel==='chat'?t('Чат','Chat'):t('Запитване','Ticket')} · {state(r)}</small></button>)}
      {desk&&!desk.tickets.length&&<p>{t('Няма запитвания.','No requests yet.')}</p>}</aside>
    <section className="panel">{!desk?<p>{t('Зареждане…','Loading…')}</p>:id?<Conversation key={id} id={id} live={false}/>:desk.agent?<p>{t('Избери входяща заявка, за да видиш описанието и да приемеш разговора.','Select a request to read the description and accept the chat.')}</p>:<form className="modal-form" onSubmit={submit}>
      <div className="desk-channels">{(['ticket','chat'] as const).map(k=><button key={k} type="button" aria-pressed={channel===k} onClick={()=>choose(k)}>{k==='chat'?<MessageCircle/>:<Mail/>}{k==='chat'?t('Чат с агент','Live chat'):t('Писмено запитване','Written request')}</button>)}</div>
      {channel==='chat'&&<p>{t('Чатът се отваря в отделен прозорец. Агентът вижда показателите на избраното дърво само през активната сесия.','Chat opens in a separate window. The agent can view the selected tree’s readings during the active session.')}</p>}
      <label>{t('За кое устройство е запитването?','Which device do you need help with?')}<select value={treeId} onChange={e=>setTree(e.target.value)}><option value="">{t('Общо запитване','General inquiry')}</option>{trees.map(r=><option key={r.id} value={r.id}>{r.name} · {r.code}</option>)}</select></label>
      {tree&&<small className="warranty-label">{warrantyText(tree.warranty_until)}</small>}
      <label>{t('Категория','Category')}<select name="category">{Object.entries(categories()).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label>
      <label>{t('Тема','Subject')}<input required name="subject" minLength={2} maxLength={140}/></label><label>{t('Опиши проблема','Describe the issue')}<textarea required name="body" maxLength={4000}/></label>
      <button disabled={busy} className="btn btn-primary">{channel==='chat'?t('Поискай връзка с агент','Request live chat'):t('Изпрати запитване','Submit request')}</button></form>}</section></div></main>
}
