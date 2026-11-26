import {useEffect,useRef,useState,type FormEvent} from 'react'
import {Headphones, Mail, MessageCircle, Send, ShieldCheck} from 'lucide-react'
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
function WarrantyRemaining({date}:{date:string}){
  const today=new Date(),end=new Date(date+'T23:59:59')
  if(end<today)return null
  let months=(end.getFullYear()-today.getFullYear())*12+end.getMonth()-today.getMonth()
  if(end.getDate()<today.getDate())months--
  const years=Math.floor(months/12),rest=months%12
  const label=[years?years+t(' г.',' yr'):null,rest?rest+t(' мес.',' mo'):null].filter(Boolean).join(' ')
  return <small>{t('Остават ','Remaining: ')}{label||t('под месец','under one month')}</small>
}
const categories=()=>({account:t('Профил и достъп','Account access'),connection:t('Свързване и Wi-Fi','Connectivity and Wi-Fi'),performance:t('Измервания и работа','Readings and performance'),warranty:t('Гаранция и сервиз','Warranty and repair'),other:t('Друго','Other')})
type Ticket={id:number;subject:string;category:keyof ReturnType<typeof categories>;channel:string;model:string|null;serial:string|null;warranty:string|null;customer:string;agent:string|null;closed:boolean}
type Desk={agent:boolean;online:boolean;tickets:Ticket[]}
type Stats={power_w:number|null;water_pct:number|null;oxygen_flow_lph:number|null;battery_pct:number|null;time:string|null}
type Score={average:number|null;count:number}
type Thread=Ticket & {remaining:number|null;rating:Score|null;typing:boolean;agent_photo:string|null;customer_photo:string|null;viewer_agent:boolean;stats:Stats|null;messages:{id:number;agent:boolean;body:string;time:string}[]}
const state=(r:Ticket)=>r.closed?t('Приключено','Closed'):r.agent?t('Агент · ','Agent · ')+r.agent:t('Очаква агент','Waiting for agent')
const post=(path:string,data?:unknown)=>request(path,{method:'POST',body:data?JSON.stringify(data):undefined})
const chatUrl=(id:number)=>location.pathname+'?support-session='+id
function popup(url:string){return window.open(url,'_blank','popup,width=560,height=740,resizable=yes,scrollbars=yes')}
const timeoutNotice=()=>t('Когато е твой ред, имаш 5 минути да изпратиш съобщение. Докато чакаш агента, времето не тече.','When it’s your turn, send a message within 5 minutes. There is no time limit while you wait for the agent.')
function ScoreBadge({score}:{score:Score}){
  return <small className="agent-score">★ {score.average===null?t('Без оценки','No ratings'):score.average.toLocaleString(getLanguage()==='en'?'en-GB':'bg-BG',{minimumFractionDigits:1})+' / 5 ('+score.count+')'}</small>
}
export function ProfileRating(){
  const [score,setScore]=useState<Score|null>(null)
  useEffect(()=>{let active=true;request<Score|null>('/profile/support-rating').then(s=>{if(active)setScore(s)}).catch(()=>{});return ()=>{active=false}},[])
  return score&&<p>{t('Агентски рейтинг','Agent rating')} <ScoreBadge score={score}/></p>
}
function SessionRating({id}:{id:number}){
  const [available,show]=useState(false),[stars,setStars]=useState<number|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('')
  useEffect(()=>{let active=true;request<{stars:number|null}>('/support/'+id+'/rating').then(r=>{if(active){setStars(r.stars);show(true)}}).catch(()=>{});return ()=>{active=false}},[id])
  async function submit(value:number){
    setBusy(true);setError('')
    try{await request('/support/'+id+'/rating',{method:'PUT',body:JSON.stringify({stars:value})});setStars(value)}
    catch(e){setError((e as Error).message)}finally{setBusy(false)}
  }
  if(!available)return null
  return <section><h3>{t('Как оценяваш разговора?','How was your conversation?')}</h3><div className="chat-stars">{[1,2,3,4,5].map(n=><button key={n} type="button" disabled={busy} aria-pressed={stars===n} aria-label={n+' / 5'} onClick={()=>submit(n)}>{n<=(stars??0)?'★':'☆'}</button>)}</div><small role="status">{error||(stars?t('Благодарим за оценката!','Thank you for your rating!'):'')}</small></section>
}
function Conversation({id,live,onDelete}:{id:number;live:boolean;onDelete?:()=>void}){
  const [row,setRow]=useState<Thread|null>(null),[note,setNote]=useState(''),[draft,write]=useState(''),[busy,setBusy]=useState(false),[ended,end]=useState(false),[tick,reload]=useState(0)
  const log=useRef<HTMLDivElement>(null),lastTyping=useRef(0),lastMessage=useRef<number|null>(null)
  const audio=useRef<AudioContext|null>(null)
  function unlock(){
    if(!live||!window.AudioContext)return
    try{audio.current??=new AudioContext();if(audio.current.state==='suspended')void audio.current.resume().catch(()=>{})}catch{/* Audio is optional. */}
  }
  function chime(){
    const ctx=audio.current
    if(!ctx||ctx.state!=='running')return
    const tone=ctx.createOscillator(),volume=ctx.createGain(),now=ctx.currentTime
    tone.frequency.setValueAtTime(680,now);tone.frequency.exponentialRampToValueAtTime(860,now+.09)
    volume.gain.setValueAtTime(.001,now);volume.gain.exponentialRampToValueAtTime(.045,now+.018)
    volume.gain.exponentialRampToValueAtTime(.001,now+.17)
    tone.connect(volume);volume.connect(ctx.destination);tone.start(now);tone.stop(now+.18)
  }
  useEffect(()=>{
    window.addEventListener('pointerdown',unlock);window.addEventListener('keydown',unlock)
    return ()=>{window.removeEventListener('pointerdown',unlock);window.removeEventListener('keydown',unlock);void audio.current?.close();audio.current=null}
  },[live])
  function typing(value:string){
    write(value)
    if(live&&row?.agent&&value.trim()&&Date.now()-lastTyping.current>1800){
      lastTyping.current=Date.now();void post('/support/'+id+'/typing').catch(()=>{})
    }
  }
  async function remove(){
    if(!window.confirm(t('Да изтрия ли запитването и съобщенията му?','Delete this inquiry and its messages?')))return
    setBusy(true)
    try{await request('/support/'+id,{method:'DELETE'});onDelete?.()}catch(e){setNote((e as Error).message)}finally{setBusy(false)}
  }
  useEffect(()=>{
    if(ended)return
    let active=true,timer=0
    async function poll(){
      try{
        const item=await request<Thread>('/support/'+id)
        if(live&&item.channel!=='chat')throw Error(t('Невалидна сесия','Invalid session'))
        if(active&&live){
          const latest=item.messages[item.messages.length-1]
          if(latest&&lastMessage.current!==null&&latest.id>lastMessage.current&&latest.agent!==item.viewer_agent)chime()
          lastMessage.current=latest?.id??0
        }
        if(active){setRow(item);setNote('');if(item.closed&&live)end(true)}
      }catch(e){
        if(active){
          const message=(e as Error).message
          setRow(null)
          if(live&&message==='Сесията не е достъпна.')end(true)
          else setNote(message)
        }
      }
      finally{if(active)timer=window.setTimeout(poll,live?2000:5000)}
    }
    void poll()
    return ()=>{active=false;clearTimeout(timer)}
  },[id,live,tick,ended])
  useEffect(()=>{if(log.current)log.current.scrollTop=log.current.scrollHeight},[row?.messages.length])
  async function action(name:'accept'|'reply'|'close'){
    if(busy)return
    setBusy(true)
    try{
      await post('/support/'+id+'/'+name,name==='reply'?{body:draft.trim()}:undefined)
      if(name==='reply'){if(live)setRow(r=>r&&!r.viewer_agent?{...r,remaining:null}:r);write('');if(live)chime()}
      if(name==='close'&&live){end(true);setRow(null)}
      else reload(v=>v+1)
    }catch(e){setNote((e as Error).message)}finally{setBusy(false)}
  }
  if(ended)return <div role="status"><ShieldCheck/><h3>{t('Сесията приключи','Session ended')}</h3><p>{t('Достъпът на агента до дървото е прекратен.','Agent access to this tree has ended.')}</p><SessionRating id={id}/></div>
  return <>{note&&<p role="alert">{note}</p>}{!row?!note&&<p>{t('Свързване…','Connecting…')}</p>:<>
    <header className="desk-context"><small>#{id} · {categories()[row.category]}</small><h2>{row.subject}</h2><p className="desk-status">{state(row)} {live&&row.rating&&<ScoreBadge score={row.rating}/>}</p>{live&&!row.viewer_agent&&<small>{timeoutNotice()}</small>}
    {row.serial&&<p>{row.model} · {row.serial}<br/><span className="desk-warranty">{row.warranty&&row.warranty>=new Date().toISOString().slice(0,10)&&<ShieldCheck size={16}/>} {warrantyText(row.warranty)}{row.warranty&&<WarrantyRemaining date={row.warranty}/>}</span></p>}
    {row.stats&&<section><h3>{t('Показатели за сесията','Session readings')}</h3><div className="desk-readings">{([['power_w',t('Мощност','Power'),'W'],['oxygen_flow_lph','O₂','L/h'],['water_pct',t('Вода','Water'),'%'],['battery_pct',t('Батерия','Battery'),'%']] as const).map(([k,label,unit])=><div key={k}><small>{label}</small><strong>{row.stats![k]??'—'} {unit}</strong></div>)}</div>{row.stats.time&&<small>{new Date(row.stats.time).toLocaleString()}</small>}</section>}
    </header><div className="desk-log" ref={log} role="log">{row.messages.map(m=><article key={m.id} className={m.agent===row.viewer_agent?'own':''}><span className="desk-author">{(m.agent?row.agent_photo:row.customer_photo)&&<img alt="" src={(m.agent?row.agent_photo:row.customer_photo)!}/>}<strong>{m.agent?row.agent:row.customer}</strong></span> <small>{new Date(m.time).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}</small><p>{m.body}</p></article>)}</div>
    <footer className="desk-composer">{live&&!row.viewer_agent&&row.remaining!==null&&row.remaining<=60&&<small role="alert" className="idle-warning">{t("Остава под минута. Изпрати съобщение, за да продължиш.","Less than a minute left. Send a message to keep chatting.")}</small>}{live&&row.typing&&<small className="desk-typing" role="status">{row.viewer_agent?row.customer:row.agent} {t("пише","is typing")} <i/><i/><i/></small>}{!row.closed&&<>{live&&!row.agent?row.viewer_agent?<button className="btn btn-primary" disabled={busy} onClick={()=>action('accept')}>{t('Приеми сесията','Accept session')}</button>:<p role="status">{t('Заявката е изпратена. Остави прозореца отворен, докато агент приеме.','Request sent. Keep this window open until an agent accepts.')}</p>:<form className="modal-form" onSubmit={e=>{e.preventDefault();void action('reply')}}><label>{!live&&t('Съобщение','Message')}<textarea aria-label={t('Съобщение','Message')} placeholder={t('Напиши съобщение…','Write a message…')} onKeyDown={e=>{
      if(live&&e.key==='Enter'&&!e.shiftKey&&!e.nativeEvent.isComposing){
        e.preventDefault()
        if(!e.repeat&&!busy&&draft.trim())e.currentTarget.form?.requestSubmit()
      }
    }} value={draft} onChange={e=>typing(e.target.value)} maxLength={4000} required/></label><button className="btn btn-primary" disabled={busy||!draft.trim()} aria-label={t('Изпрати','Send')} title={t('Изпрати','Send')}>{live?<Send size={18}/>:t('Изпрати','Send')}</button></form>}
    {(!row.viewer_agent||row.agent)&&<button className="btn btn-quiet" disabled={busy} onClick={()=>action('close')}>{t('Приключи разговора','End conversation')}</button>}</>}
    {onDelete&&row.channel==="ticket"&&!row.viewer_agent&&<button type="button" className="btn btn-quiet" disabled={busy} onClick={remove}>{t("Изтрий запитването","Delete inquiry")}</button>}</footer>
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
    setBusy(true);setError('');setBlocked(null)
    try{const r=await request<{id:number}>('/support',{method:'POST',body:JSON.stringify({...data,channel,tree_id:treeId?Number(treeId):null})})
      if(channel==='chat'){if(win)win.location.replace(chatUrl(r.id));else setBlocked(r.id)}else select(r.id)
      form.reset();setTree('');refresh(v=>v+1)
    }catch(e){win?.close();setError((e as Error).message)}finally{setBusy(false)}
  }
  const [showArchive,setShowArchive]=useState(false),[archive,setArchive]=useState<{id:number;category:Ticket['category'];accepted:string|null}[]>([])
  useEffect(()=>{
    if(!showArchive||!desk?.agent)return
    let active=true
    void request<typeof archive>('/support/archive').then(rows=>{if(active)setArchive(rows)}).catch(e=>{if(active)setError(e.message)})
    return ()=>{active=false}
  },[showArchive,desk])
  const [formVersion,resetForm]=useState(0)
  function startNew(kind:string){
    select(null);choose(kind);setTree('');setBlocked(null);setError('');resetForm(v=>v+1)
  }
  const inbox=desk?.tickets.filter(ticket=>desk.agent||ticket.channel!=='chat')??[]
  const tree=trees.find(r=>String(r.id)===treeId)
  return <main className="page-body support-desk"><header className="desk-heading"><Headphones/><div><h2>{desk?.agent?t('Агентска конзола','Agent workspace'):t('Център за поддръжка','Support center')}</h2>{desk&&<small>{desk.agent?t('Получаваш заявки, докато конзолата е отворена.','You receive requests while this desk is open.'):desk.online?t('Има агент онлайн','Agent online'):t('В момента няма агент онлайн','No agents currently online')}</small>}</div></header>
    {error&&<p role="alert">{error}</p>}{blocked&&<a className="btn btn-primary" href={chatUrl(blocked)} target="_blank" rel="noreferrer">{t('Отвори прозореца за чат','Open chat window')}</a>}
    <div className="support-columns"><aside className="panel"><h3>{desk?.agent?t('Входящи случаи','Incoming cases'):t('Моите запитвания','My requests')}</h3>
      {desk?.agent&&<button className="btn btn-outline" aria-pressed={showArchive} onClick={()=>{setShowArchive(!showArchive);select(null)}}>{showArchive?t("Към входящите","Back to inbox"):t("История на живите сесии","Live session history")}</button>}{!desk?.agent&&<button className="btn btn-primary" onClick={()=>startNew('ticket')}>{t('Ново запитване','New request')}</button>}{desk&&!desk.agent&&<button className="btn btn-outline" onClick={()=>startNew('chat')}>{t('Нов чат с агент','New agent chat')}</button>}
      {inbox.map(r=><button key={r.id} className="btn btn-outline support-case" onClick={()=>{setShowArchive(false);if(r.channel==='chat'&&!r.closed){if(!popup(chatUrl(r.id)))setBlocked(r.id)}else select(r.id)}}>#{r.id} · {r.subject}<small>{r.channel==='chat'?t('Чат','Chat'):t('Запитване','Ticket')} · {state(r)}</small></button>)}
      {desk&&!inbox.length&&<p>{t('Няма запитвания.','No requests yet.')}</p>}</aside>
    <section className="panel">{!desk?<p>{t('Зареждане…','Loading…')}</p>:showArchive?<><h3>{t('История на живите сесии','Live session history')}</h3>{!archive.length&&<p>{t('Няма приключени сесии.','No completed sessions.')}</p>}{archive.map(r=><p key={r.id}>#{r.id} · {categories()[r.category]} · {r.accepted?new Date(r.accepted).toLocaleString():t('Приключена сесия','Closed session')}</p>)}</>:id?<Conversation key={id} id={id} live={false} onDelete={()=>{select(null);refresh(v=>v+1)}}/>:desk.agent?<p>{t('Избери входяща заявка, за да видиш описанието и да приемеш разговора.','Select a request to read the description and accept the chat.')}</p>:<form key={formVersion} className="modal-form" onSubmit={submit}>
      <div className="desk-channels">{(['ticket','chat'] as const).map(k=><button key={k} type="button" aria-pressed={channel===k} onClick={()=>startNew(k)}>{k==='chat'?<MessageCircle/>:<Mail/>}{k==='chat'?t('Чат с агент','Live chat'):t('Писмено запитване','Written request')}</button>)}</div>
      {channel==='chat'&&!desk.online&&<p>{t('Можеш да изчакаш агент тук или да оставиш писмено запитване за по-късно.','Wait for an agent or leave a written request for later.')}</p>}
      {channel==='chat'&&<p>{t('Чатът се отваря в отделен прозорец. Агентът вижда показателите на избраното дърво само през активната сесия.','Chat opens in a separate window. The agent can view the selected tree’s readings during the active session.')}</p>}
      <label>{t('За кое устройство е запитването?','Which device do you need help with?')}<select value={treeId} onChange={e=>setTree(e.target.value)}><option value="">{t('Общо запитване','General inquiry')}</option>{trees.map(r=><option key={r.id} value={r.id}>{r.name} · {r.code}</option>)}</select></label>
      {tree&&<small className="warranty-label">{warrantyText(tree.warranty_until)}</small>}
      <label>{t('Категория','Category')}<select name="category">{Object.entries(categories()).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label>
      <label>{t('Тема','Subject')}<input required name="subject" minLength={2} maxLength={140}/></label><label>{t('Опиши проблема','Describe the issue')}<textarea required name="body" maxLength={4000}/></label>
      <button disabled={busy} className="btn btn-primary">{channel==='chat'?t('Поискай връзка с агент','Request live chat'):t('Изпрати запитване','Submit request')}</button></form>}</section></div></main>
}

