import {useEffect,useState} from 'react'
import {api,type AdminDevice,type SimulatorKeys} from './api'
import {getLanguage,locale} from './language'

export default function AdminPanel(){
  const en=getLanguage()==='en'
  const [offset,setOffset]=useState(0),[revision,setRevision]=useState(0)
  const [rows,setRows]=useState<AdminDevice[]>([]),[more,setMore]=useState(false)
  const [keys,setKeys]=useState<SimulatorKeys|null>(null),[creating,setCreating]=useState(false)
  const [loading,setLoading]=useState(true),[error,setError]=useState('')
  useEffect(()=>{
    let live=true
    setLoading(true);setError('')
    api.adminDevices(offset).then(result=>{
      if(live){setRows(result.devices);setMore(result.has_more)}
    }).catch(err=>{if(live){setRows([]);setMore(false);setError(String(err.message))}})
      .finally(()=>{if(live)setLoading(false)})
    return ()=>{live=false}
  },[offset,revision])
  async function create(){
    setCreating(true);setError('')
    try{setKeys(await api.createSimulator());setOffset(0);setRevision(v=>v+1)}
    catch(err){setError(err instanceof Error?err.message:String(err))}
    finally{setCreating(false)}
  }
  const labels={active:en?'Activated':'Активирано',free:en?'Available':'Свободно',reserved:en?'Reserved':'Запазено за акаунт'}
  return <div className="page-body">
    <button className="btn btn-primary" onClick={create} disabled={creating||!!keys}>{en?'Create Solix Arc 2K simulator':'Създай симулиран Solix Arc 2K'}</button>
    {error&&<p role="alert">{error}</p>}
    {keys&&<section className="panel" style={{padding:'1rem',overflowWrap:'anywhere'}}>
      <h2>{keys.code}</h2>
      <p>{en?'Save the keys before closing. They are displayed once.':'Запази ключовете преди затваряне. Показват се еднократно.'}</p>
      <img width="180" height="180" src={keys.qr} alt={en?'Pairing QR code':'QR код за добавяне'}/>
      <p>{en?'Pairing key':'Ключ за добавяне'} <code>{keys.claim}</code></p>
      <p>{en?'Telemetry key':'Ключ за телеметрия'} <code>{keys.telemetry}</code></p>
      <a className="btn btn-outline" href={keys.qr} download={keys.code+'.png'}>{en?'Save QR':'Запази QR'}</a>
      <a className="btn btn-outline" download={keys.code+'.json'} href={'data:application/json;charset=utf-8,'+encodeURIComponent(JSON.stringify({code:keys.code,claim_token:keys.claim,telemetry_key:keys.telemetry},null,2))}>{en?'Save keys':'Запази ключовете'}</a>
      <button className="btn btn-outline" onClick={()=>setKeys(null)}>{en?'Close':'Затвори'}</button>
    </section>}
    <section className="panel" style={{padding:'1rem',overflowX:'auto'}}>
      <h2>{en?'Registered trees':'Регистрирани дървета'}</h2>
      <button className="btn btn-outline" onClick={()=>setRevision(v=>v+1)} disabled={loading}>{en?'Refresh':'Обнови'}</button>
      {loading?<p role="status">{en?'Loading…':'Зареждане…'}</p>:<table style={{width:'100%',textAlign:'left',borderSpacing:8}}>
        <thead><tr>{(en?['Serial number','Model','Status','Latest sensor sample']:['Сериен номер','Модел','Статус','Последна сензорна проба']).map(col=><th key={col}>{col}</th>)}</tr></thead>
        <tbody>{rows.map(row=><tr key={row.code}><td>{row.code}</td><td>{row.model}</td><td>{labels[row.status]}</td><td>{row.sample_time?new Date(row.sample_time).toLocaleString(locale()):'—'}</td></tr>)}</tbody>
      </table>}
      {offset>0&&<button className="btn btn-outline" disabled={loading} onClick={()=>setOffset(offset-50)}>{en?'Previous':'Назад'}</button>}
      {more&&<button className="btn btn-outline" disabled={loading} onClick={()=>setOffset(offset+50)}>{en?'Next':'Напред'}</button>}
    </section>
  </div>
}
