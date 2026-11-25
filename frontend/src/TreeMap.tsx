import {useRef,useState} from 'react'
import type {FormEvent,MouseEvent} from 'react'
import {MapPin} from 'lucide-react'
import type {Tree} from './types'
import {getLanguage} from './language'
import {api} from './api'
import './tree-map.css'

// Natural Earth 1:50m Bulgaria boundary in a local equirectangular projection.
const outline='M565.4,317.6 L552.6,315.3 L548.2,316.0 L545.4,319.2 L539.5,318.5 L532.1,318.6 L524.5,322.2 L520.3,323.7 L514.6,320.4 L504.1,310.4 L497.7,303.4 L493.0,301.7 L488.2,303.7 L471.1,306.1 L467.1,310.2 L459.2,314.6 L451.2,316.8 L439.8,318.3 L433.8,318.1 L430.5,320.3 L427.7,326.8 L425.8,333.2 L424.1,335.8 L409.9,339.0 L406.8,342.7 L405.9,346.3 L406.2,349.9 L394.9,346.4 L386.1,348.7 L384.0,351.5 L382.2,355.4 L383.2,359.7 L386.5,363.8 L389.5,374.8 L390.6,385.9 L388.7,392.2 L382.2,396.7 L368.8,401.7 L355.8,399.3 L350.0,401.3 L340.4,401.9 L331.5,403.2 L317.9,407.8 L305.6,410.4 L294.5,401.2 L281.4,394.9 L267.6,391.1 L262.8,393.9 L260.7,396.0 L249.2,387.8 L244.0,384.9 L241.5,381.8 L236.7,370.9 L233.9,370.5 L224.4,374.6 L215.2,374.4 L209.7,373.7 L193.3,374.1 L191.1,381.6 L189.1,382.7 L185.5,383.7 L176.8,383.2 L165.7,388.7 L153.7,392.1 L144.4,392.2 L134.7,390.6 L129.0,391.7 L116.5,392.3 L108.7,400.4 L96.4,399.9 L86.1,398.6 L87.4,396.0 L89.4,364.1 L94.5,349.8 L94.3,346.9 L93.2,344.7 L88.7,342.4 L85.5,334.7 L78.7,314.4 L74.8,310.3 L64.1,306.0 L54.8,300.2 L46.8,292.5 L32.3,273.4 L39.7,271.5 L41.9,267.6 L49.2,257.2 L50.0,252.0 L49.3,249.1 L44.4,244.1 L41.0,233.1 L43.5,222.8 L43.8,217.5 L41.3,212.3 L43.9,205.8 L49.1,202.2 L52.5,201.2 L66.4,200.5 L75.2,187.4 L80.5,183.3 L86.0,175.9 L88.6,173.2 L91.0,167.4 L91.8,161.5 L80.8,153.3 L77.1,147.1 L72.2,140.3 L65.5,135.5 L52.1,127.4 L46.9,119.2 L44.6,108.5 L41.0,100.4 L37.1,95.1 L36.4,90.9 L34.7,85.6 L34.4,75.3 L37.5,61.5 L39.6,56.6 L44.1,55.3 L56.2,48.0 L56.7,38.6 L58.9,32.8 L62.7,29.4 L66.3,27.2 L72.9,32.6 L88.9,41.3 L96.7,47.6 L96.3,51.6 L92.6,55.4 L85.7,59.2 L81.6,64.3 L80.5,70.5 L81.6,74.9 L86.4,78.8 L115.1,73.7 L144.2,76.3 L183.4,84.9 L209.3,87.9 L228.5,83.9 L264.0,91.1 L297.0,97.8 L328.7,99.7 L346.5,94.5 L359.0,87.4 L369.7,74.2 L396.3,56.7 L422.0,46.9 L455.7,38.9 L478.2,36.2 L481.3,38.9 L510.0,55.0 L522.7,55.0 L533.1,57.9 L536.8,62.1 L539.4,63.2 L553.1,59.2 L559.2,68.0 L568.7,80.3 L584.9,86.7 L599.3,90.3 L603.8,90.8 L619.0,90.6 L616.8,121.4 L607.8,135.8 L594.0,131.0 L576.6,135.0 L567.3,151.3 L562.1,156.1 L557.3,161.8 L554.3,183.0 L553.6,217.6 L546.9,221.9 L540.8,223.2 L515.6,253.7 L530.1,262.3 L536.6,268.8 L547.2,287.0 L562.4,307.5 L565.4,317.6 Z'
const project=(lng:number,lat:number)=>[(lng-22)*94,(44.45-lat)*128]
const inView=(t:Tree)=>t.lat!=null && t.lng!=null && t.lat>=41.05 && t.lat<=44.45 && t.lng>=22 && t.lng<=29.02

export default function TreeMap({trees,onOpen,onSaved}:{trees:Tree[];onOpen:(id:number)=>void;onSaved:()=>Promise<void>}){
  const en=getLanguage()==='en'
  const [id,choose]=useState<number|null>(null),[editing,edit]=useState(false)
  const [lat,setLat]=useState(''),[lng,setLng]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState('')
  const svg=useRef<SVGSVGElement>(null)
  const pins=trees.filter(inView)
  const current=trees.find(t=>t.id===id)??pins[0]??trees[0]
  function select(i:number){choose(i);edit(false);setError('')}
  function place(e:MouseEvent<SVGSVGElement>){
    const el=svg.current,matrix=el?.getScreenCTM()
    if(!editing||busy||!el||!matrix)return
    const pt=new DOMPoint(e.clientX,e.clientY).matrixTransform(matrix.inverse())
    setLat((44.45-pt.y/128).toFixed(5));setLng((22+pt.x/94).toFixed(5))
  }
  async function save(ev:FormEvent){
    ev.preventDefault()
    if(!current||busy)return
    setBusy(true);setError('')
    try{await api.setCoordinates(current.id,Number(lat),Number(lng));await onSaved();edit(false)}
    catch(err){setError(err instanceof Error?err.message:String(err))}
    finally{setBusy(false)}
  }
  return <section className="panel tree-map" aria-label={en?'Tree locations':'Местоположение на дърветата'}>
    <div className="tree-map-art"><svg viewBox="0 0 660 435" ref={svg} onClick={place} style={{cursor:editing?'crosshair':undefined}} aria-label={en?'Map of Bulgaria':'Карта на България'}>
      <path d={outline} className="tree-map-land"/>
      {pins.map(tree=>{const [x,y]=project(tree.lng!,tree.lat!);return <g key={tree.id} transform={`translate(${x} ${y})`} className="tree-map-pin" role="button" tabIndex={editing?-1:0} aria-label={tree.name} onKeyDown={event=>{if(!editing&&(event.key==='Enter'||event.key===' ')){event.preventDefault();select(tree.id)}}} data-selected={tree.id===current?.id} onClick={()=>{if(!editing)select(tree.id)}}>
        <title>{tree.name} · {tree.location}</title><circle cy="-10" r="19" fill="transparent"/><path d="M0 0 C-2 -4 -10 -10 -10 -17 A10 10 0 1 1 10 -17 C10 -10 2 -4 0 0Z"/><circle cy="-17" r="3" fill="white"/>
      </g>})}
      {editing&&lat&&lng&&<circle cx={project(Number(lng),Number(lat))[0]} cy={project(Number(lng),Number(lat))[1]} r="6" fill="none" stroke="currentColor" strokeWidth="2"/>}
    </svg></div>
    <div className="tree-map-info"><h3><MapPin size={18}/> {en?'Trees in Bulgaria':'Дървета в България'}</h3>
    {current?<><label>{en?'Device':'Устройство'}<select value={current.id} disabled={busy} onChange={ev=>select(Number(ev.target.value))}>{trees.map(t=><option key={t.id} value={t.id}>{t.name} · {t.code}</option>)}</select></label>
    <p>{current.location}</p><small>{current.lat==null||current.lng==null?(en?'No coordinates yet':'Все още няма координати'):!inView(current)?(en?'Outside this map':'Извън обхвата на картата'):`${current.lat.toFixed(4)}°, ${current.lng.toFixed(4)}°`}</small>
    {editing?<form onSubmit={save}><small>{en?'Click the map or enter coordinates.':'Посочи точка върху картата или въведи координати.'}</small>
    <label>{en?'Latitude':'Ширина'}<input type="number" step="any" min="-90" max="90" required value={lat} onChange={e=>setLat(e.target.value)}/></label>
    <label>{en?'Longitude':'Дължина'}<input type="number" step="any" min="-180" max="180" required value={lng} onChange={e=>setLng(e.target.value)}/></label>
    {error&&<p role="alert">{error}</p>}<button className="btn btn-primary" disabled={busy}>{en?'Save':'Запази'}</button><button type="button" className="btn btn-outline" disabled={busy} onClick={()=>edit(false)}>{en?'Cancel':'Отказ'}</button></form>:
    <div><button className="btn btn-primary" onClick={()=>onOpen(current.id)}>{en?'Open tree':'Отвори дървото'}</button><button className="btn btn-outline" onClick={()=>{choose(current.id);setLat(current.lat?.toString()??'');setLng(current.lng?.toString()??'');edit(true)}}>{en?'Place pin':'Постави пин'}</button></div>}</>:<p>{en?'Add a tree to place its pin.':'Добави дърво, за да поставиш неговия пин.'}</p>}</div>
  </section>
}
