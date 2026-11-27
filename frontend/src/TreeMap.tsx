import {useRef,useState} from 'react'
import type {FormEvent,MouseEvent} from 'react'
import {MapPin} from 'lucide-react'
import type {Tree} from './types'
import {getLanguage} from './language'
import {api} from './api'
import './tree-map.css'

// Administrative boundaries: SimpleMaps Bulgaria, via Europe-Elects/bulgaria.
import provinces from './bg-regions.json'
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
      {provinces.map((d,i)=><path key={i} d={d} className="tree-map-land province"/>)}
      <g transform={`translate(${project(23.3219,42.6977).join(" ")})`} className="sofia-label"><circle r="2.8"/><text x="7" y="5">{en?"Sofia":"София"}</text></g>
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
