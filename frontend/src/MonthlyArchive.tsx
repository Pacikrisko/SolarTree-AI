import {useEffect,useState} from 'react'
import {CalendarDays} from 'lucide-react'
import {request} from './api'
import {getLanguage} from './language'

type Day={date:string;oxygen_l:number;energy_kwh:number}
type Archive=Day & {month:string;months:string[];days:Day[];peak_oxygen_day:string}

export default function MonthlyArchive({treeId}:{treeId:number}){
  const en=getLanguage()==='en', locale=en?'en-GB':'bg-BG'
  const [open,setOpen]=useState(false),[month,setMonth]=useState('')
  const [data,setData]=useState<Archive|null>(null),[error,setError]=useState(''),[retry,setRetry]=useState(0)
  const [metric,setMetric]=useState<'oxygen_l'|'energy_kwh'>('oxygen_l')
  useEffect(()=>{
    if(!open)return
    let active=true
    setData(null);setError('')
    request<Archive>('/trees/'+treeId+'/monthly-archive'+(month?'?month='+month:''))
      .then(value=>{if(active)setData(value)}).catch(e=>{if(active)setError(e.message)})
    return ()=>{active=false}
  },[open,month,treeId,retry])
  const fmt=(n:number)=>n.toLocaleString(locale,{maximumFractionDigits:2})
  const monthName=(m:string)=>new Date(m+'-15T12:00:00').toLocaleDateString(locale,{month:'long',year:'numeric'})
  const unit=metric==='oxygen_l'?'L':'kWh'
  const max=data?Math.max(...data.days.map(d=>d[metric]),0.001):1
  return <section className="panel" style={{padding:'1rem',marginBottom:'1rem'}}>
    <button className="btn btn-outline" aria-expanded={open} onClick={()=>setOpen(!open)}><CalendarDays size={18}/>{en?'Analysis history':'История на анализите'}</button>
    {open&&<div>{error?<p role="alert">{error} <button onClick={()=>setRetry(v=>v+1)}>{en?'Retry':'Опитай отново'}</button></p>:!data?<p role="status">{en?'Loading…':'Зареждане…'}</p>:<>
      <p><label>{en?'Month':'Месец'} <select value={data.month} onChange={e=>setMonth(e.target.value)}>{data.months.map(m=><option key={m} value={m}>{monthName(m)}</option>)}</select></label></p>
      <h3>{monthName(data.month)}</h3><small>{en?'Illustrative monthly estimates':'Примерни изчислени данни за месеца'}</small>
      <p>{en?'Oxygen':'Кислород'} <strong>{fmt(data.oxygen_l)} L</strong> · {en?'Energy':'Енергия'} <strong>{fmt(data.energy_kwh)} kWh</strong></p>
      <label>{en?'Daily chart':'Диаграма по дни'} <select value={metric} onChange={e=>setMetric(e.target.value as typeof metric)}><option value="oxygen_l">O₂ (L)</option><option value="energy_kwh">{en?'Energy':'Енергия'} (kWh)</option></select></label>
      <div style={{display:'flex',alignItems:'end',height:128,gap:2,marginTop:14,borderBottom:'1px solid currentColor'}}>{data.days.map(d=><div key={d.date} title={d.date+' · '+fmt(d[metric])+' '+unit} style={{flex:1,height:(100*d[metric]/max)+'%',background:'var(--app-accent)',borderRadius:'3px 3px 0 0'}}/>)}</div>
      <small style={{display:'flex',justifyContent:'space-between'}}><span>01</span><span>15</span><span>{data.days.length}</span></small>
      <details><summary>{en?'Daily values':'Стойности по дни'}</summary><table><thead><tr><th>{en?'Day':'Ден'}</th><th>O₂ (L)</th><th>kWh</th></tr></thead><tbody>{data.days.map(d=><tr key={d.date}><td>{d.date}</td><td>{fmt(d.oxygen_l)}</td><td>{fmt(d.energy_kwh)}</td></tr>)}</tbody></table></details>
    </>}</div>}
  </section>
}
