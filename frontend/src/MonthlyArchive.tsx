import {lazy,Suspense,useEffect,useRef,useState} from 'react'
import {CalendarDays,ChevronLeft,ChevronRight} from 'lucide-react'
import {request} from './api'
import {locale} from './language'
import type {Forecast,OxygenHistory} from './types'
import './archive.css'

const Power=lazy(()=>import('./Charts').then(m=>({default:m.ForecastChart})))
const Oxygen=lazy(()=>import('./Charts').then(m=>({default:m.OxygenChart})))
type Day={date:string;energy_kwh:number;oxygen_l:number}
type Props={treeId?:number;kind:'power'|'oxygen';forecast?:Forecast|null;oxygen?:OxygenHistory|null}
function dateKey(date:Date){
  return [date.getFullYear(),String(date.getMonth()+1).padStart(2,'0'),String(date.getDate()).padStart(2,'0')].join('-')
}

// Distribute the archive's daily totals across hourly intervals with a daylight peak.
function hourly(day:Day){
  const weights=Array.from({length:24},(_,h)=>.008+Math.max(0,Math.sin((h-6)*Math.PI/12)))
  const sum=weights.reduce((a,b)=>a+b,0)
  let liters=0
  return weights.map((w,h)=>{
    const flow=day.oxygen_l*w/sum
    liters+=flow
    return {time:day.date+'T'+String(h).padStart(2,'0')+':00:00',power_w:day.energy_kwh*1000*w/sum,
      cumulative_l:liters,oxygen_flow_lph:flow,basis:'estimated',source:'simulation'}
  })
}
export default function MonthlyArchive({treeId,kind,forecast,oxygen}:Props){
  const lang=locale(),en=lang.startsWith('en'),power=kind==='power'
  const [open,setOpen]=useState(false),[day,select]=useState<Day|null>(null)
  const [month,setMonth]=useState(''),[months,setMonths]=useState<string[]>([]),[days,setDays]=useState<Day[]>([])
  const [error,setError]=useState(''),[retry,setRetry]=useState(0)
  const root=useRef<HTMLDivElement>(null),trigger=useRef<HTMLButtonElement>(null)
  useEffect(()=>{
    if(!open||!treeId)return
    let active=true
    setError('');setDays([])
    request<{month:string;months:string[];days:Day[]}>('/trees/'+treeId+'/monthly-archive'+(month?'?month='+month:''))
      .then(r=>{if(active){setMonths(r.months);setDays(r.days)}}).catch(e=>{if(active)setError(e.message)})
    return ()=>{active=false}
  },[open,month,treeId,retry])
  useEffect(()=>{
    if(!open)return
    const outside=(e:PointerEvent)=>{if(!root.current?.contains(e.target as Node))setOpen(false)}
    const escape=(e:KeyboardEvent)=>{if(e.key==='Escape'){setOpen(false);trigger.current?.focus()}}
    document.addEventListener('pointerdown',outside);document.addEventListener('keydown',escape)
    return ()=>{document.removeEventListener('pointerdown',outside);document.removeEventListener('keydown',escape)}
  },[open])
  const current=month||months[0],index=months.indexOf(current)
  const first=new Date((current||'2000-01')+'-01T12:00:00'),offset=(first.getDay()+6)%7
  const title=power?(day?(en?'Power':'Мощност'):(en?'Power forecast':'Прогноза за мощност')):(en?'Oxygen production':'Производство на кислород')
  const rows=day?hourly(day):[]
  function pick(value:Day|null){select(value);setOpen(false);trigger.current?.focus()}
  return <section className="panel archive-chart"><header><h3>{title}</h3><div ref={root} className="archive-picker">
    <button type="button" ref={trigger} className="btn btn-outline" disabled={!treeId} aria-expanded={open} aria-label={(en?'Calendar · ':'Календар · ')+title} onClick={()=>setOpen(!open)}><CalendarDays size={16}/>{day?new Date(day.date+'T12:00:00').toLocaleDateString(lang):en?'History':'История'}</button>
    {open&&<div className="archive-pop" role="dialog" aria-label={en?'Choose a date':'Избери дата'}>
      {current&&<div className="archive-month"><strong>{first.toLocaleDateString(lang,{month:'long',year:'numeric'})}</strong>
      <button aria-label={en?'Previous month':'Предходен месец'} disabled={index+1>=months.length} onClick={()=>setMonth(months[index+1])}><ChevronLeft size={16}/></button>
      <button aria-label={en?'Next month':'Следващ месец'} disabled={index<=0} onClick={()=>setMonth(months[index-1])}><ChevronRight size={16}/></button></div>}
      {error?<button onClick={()=>setRetry(r=>r+1)}>{en?'Retry':'Опитай отново'}</button>:days.length?<div className="archive-days">
        {Array.from({length:7},(_,i)=><small key={i}>{new Date(2024,0,1+i).toLocaleDateString(lang,{weekday:'short'})}</small>)}
        {Array.from({length:42},(_,i)=>{const number=i-offset+1,value=days[number-1],date=new Date(first.getFullYear(),first.getMonth(),number)
          return <button key={i} disabled={!value} aria-label={dateKey(date)} aria-pressed={!!value&&day?.date===value.date} onClick={()=>pick(value)}>{date.getDate()}</button>})}
      </div>:<p role="status">{en?'Loading…':'Зареждане…'}</p>}
      <button className="archive-reset" onClick={()=>pick(null)}>{en?'Current data':'Текущи данни'}</button>
    </div>}</div></header>
    {day&&<small>{en?'Illustrative hourly estimates':'Примерни почасови стойности'}{power?' · '+day.energy_kwh.toLocaleString(lang)+' kWh':''}</small>}
    <Suspense fallback={<div className="chart-box" aria-busy="true"/>}>{power?<Power forecast={day?{points:rows,mae_w:null,trained_samples:0,model:'archive'}:forecast??null} historical={!!day}/>:<Oxygen history={day?{tree_id:treeId!,points:rows,total_l:day.oxygen_l,current_flow_lph:rows[23].oxygen_flow_lph,basis:'estimated',note:''}:oxygen??null}/>}</Suspense>
  </section>
}
