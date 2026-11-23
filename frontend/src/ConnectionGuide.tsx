import { PlugZap, ShieldCheck, X, Radio } from 'lucide-react'
import type { Tree } from './types'

export default function ConnectionGuide({tree,onClose}:{tree:Tree;onClose:()=>void}){
  const steps=[
    {title:'Свържи контролера',body:'Raspberry Pi Pico 2 W трябва да е включен към същата локална мрежа или към защитен сървър, достъпен през интернет. Само QR регистрацията не включва телеметрия.'},
    {title:'Прочети реални сензори',body:'Фърмуерът трябва да събира наличните измервания (например температура и влажност от BME280). Мощност, водно ниво и кислороден дебит изискват съответните физически измервания.'},
    {title:'Изпрати към FastAPI',body:'Фърмуерът отправя HTTPS или локална HTTP заявка към API адреса и удостоверява устройството с неговия отделен X-Device-Key. Ключът не се поставя в публичния QR етикет.'},
    {title:'Провери връзката',body:'След успешно подаване на данни статусът е „Свързано“. За Pico сензорите връзката се счита активна, ако е имало измерване през последните 5 минути.'},
  ]
  return <div className="modal-backdrop" onMouseDown={e=>{if(e.target===e.currentTarget)onClose()}}><div className="modal connect-modal" role="dialog" aria-modal="true" aria-label="Свързване на реално устройство">
    <div className="modal-heading"><div><span className="eyebrow">РЕАЛНА ТЕЛЕМЕТРИЯ</span><h2>Свържи {tree.name}</h2></div><button className="icon-btn" onClick={onClose} aria-label="Затвори"><X size={18}/></button></div>
    <div className="connect-status"><span className={`connection-mark ${tree.connection}`}><Radio size={20}/></span><div><strong>{tree.connection==='live'?'Получават се данни от устройството':'Все още няма активна връзка'}</strong><small>Устройство {tree.code}</small></div></div>
    <div className="connect-steps">{steps.map((step,index)=><div key={index} className="connect-step"><span>{index+1}</span><div><h3>{step.title}</h3><p>{step.body}</p></div></div>)}</div>
    <div className="connect-api"><span><PlugZap size={16}/> Адрес за подаване на данни</span><code>POST /api/device/{tree.code}/sensors</code><small>Само налични датчици: docs/PICO_REAL_CONNECTION_v06.md. За пълни измервания: /reading</small></div>
    <div className="connection-safety"><ShieldCheck size={18}/> Функцията записва измервания и не изпраща команди към електролизера или защитите му.</div>
    <button className="btn btn-primary full" onClick={onClose}>Разбрах</button>
  </div></div>
}
