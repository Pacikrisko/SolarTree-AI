import {tr,locale} from './language'
import {useEffect,useState} from 'react'
import {Droplets, Gauge, Waves, CircleHelp, Clock3, Zap} from 'lucide-react'
import {api} from './api'
import type {ResourceEstimate,Tree} from './types'

const fmt=(n:number,d=1)=>new Intl.NumberFormat(locale(),{maximumFractionDigits:d}).format(n)
function duration(h:number|null){
  if(h===null)return '—'
  if(h===0)return tr("0 мин")
  const minutes=Math.round(h*60)
  if(minutes===0)return tr("< 1 мин")
  const days=Math.floor(minutes/1440), hours=Math.floor((minutes%1440)/60), mins=minutes%60
  return [days?`${days} ${locale()==='en-GB'?'d':'дн.'}`:'',hours?`${hours} ${locale()==='en-GB'?'h':'ч'}`:'',mins?`${mins} ${locale()==='en-GB'?'min':'мин'}`:''].filter(Boolean).join(' ')
}

/** Advisory estimate; input pressures are not sent to the hydrogen equipment. */
export default function ResourcePlanner({tree}:{tree:Tree}){
  const [customFill,setFill]=useState<number|null>(null)
  const [customPressure,setPressure]=useState<string|null>(null)
  const [customLoad,setLoad]=useState<number|null>(null)
  const simulated=tree.simulation
  const water=tree.latest_sensors?.water_pct ?? (tree.latest?.source==='device'||simulated ? tree.latest?.water_pct : null)
  const fill=customFill ?? water ?? 100
  const pressure=customPressure ?? String(simulated?.hydrogen_pressure_bar_g ?? '')
  const load=customLoad ?? simulated?.fuel_cell_load_kw ?? tree.model.fuel_cell_kw ?? 1
  const [efficiency,setEfficiency]=useState(50)
  const [result,setResult]=useState<ResourceEstimate|null>(null)
  const [error,setError]=useState('')
  useEffect(()=>{
    let cancelled=false
    const timeout=window.setTimeout(()=>{
      const pressureNum=pressure.trim()===''?null:Number(pressure)
      if(pressureNum!==null&&(!Number.isFinite(pressureNum)||pressureNum<0||pressureNum>500)){
        setError(tr("Въведи налягане между 0 и 500 bar."));setResult(null);return
      }
      api.resources(tree.id,fill,pressureNum,load,efficiency/100)
        .then(x=>{if(!cancelled){setResult(x);setError('')}})
        .catch(e=>{if(!cancelled){setError((e as Error).message);setResult(null)}})
    },180)
    return()=>{cancelled=true;window.clearTimeout(timeout)}
  },[tree.id,fill,pressure,load,efficiency])
  const sensorWater=tree.latest_sensors?.water_pct!=null || tree.latest?.source==='device'
  return <section className="panel resource-planner" aria-label={tr("Резервоари и изчислено време на работа")}>
    <div className="resource-head"><div><span className="eyebrow">{tr("URBAN 2K · РЕСУРСИ")}</span><h3>{tr("Резервоари и оставащо време")}</h3><p>{tr("Разчет по проектните параметри; не управлява физически клапани или налягане.")}</p></div><span className="resource-engine"><Zap size={16}/> {tr("Електролизер")} {fmt(tree.model.electrolyzer_kw??2)} kW</span></div>
    {simulated && <p className="info-box">{tr("Симулирани ниво на водата, налягане и товар. Ръчните промени важат само за този разчет.")}</p>}
    <div className="resource-grid">
      <article className="resource-card water"><div className="resource-card-top"><span className="resource-icon"><Droplets size={20}/></span><div><small>{tr("Резервоар за електролиза")}</small><strong>{fmt(tree.model.water_tank_l??10,0)} {tr("L вода")}</strong></div></div>
        <div className="resource-label"><span>{tr("Ниво на запълване")}</span><strong>{fmt(fill,0)}%</strong></div>
        <input type="range" min={0} max={100} step={1} value={fill} onChange={e=>setFill(Number(e.target.value))} aria-label={tr("Процент вода")}/>
        <div className="resource-stats"><div><span>{tr("Налична вода")}</span><strong>{result?fmt(result.water_available_l,2):'—'} L</strong></div><div><span>{tr("Разход при")} {fmt(tree.model.oxygen_nominal_lph??250,0)} Nl/h O₂</span><strong>{result?fmt(result.water_consumption_lph,3):'—'} L/h</strong></div></div>
        <div className="resource-time"><Clock3 size={19}/><div><small>{tr("При непрекъсната електролиза")}</small><strong>{duration(result?.water_runtime_hours??null)}</strong></div></div>
        <p className="resource-note">{simulated?tr("Началното ниво следва симулацията."):sensorWater?tr("Изходното ниво е взето от устройството; може да се коригира само за изчислението."):tr("Изходно ниво: пълен 10-литров резервоар. Премести плъзгача за друга ситуация.")}</p>
      </article>
      <article className="resource-card hydrogen"><div className="resource-card-top"><span className="resource-icon"><Waves size={20}/></span><div><small>{tr("Съд за водород към горивната клетка")}</small><strong>{fmt(tree.model.hydrogen_tank_l??20,0)} {tr("L вътрешен обем")}</strong></div></div>
        <div className="resource-fields"><label>{tr("Налягане в съда (bar, манометрично)")}
          <input type="number" min={0} max={500} step="any" inputMode="decimal" placeholder={tr("Въведи измереното налягане")} value={pressure} onChange={e=>setPressure(e.target.value)}/></label>
          <label>{tr("Натоварване на горивната клетка (kW)")}
          <input type="number" min={0} max={tree.model.fuel_cell_kw??1} step="any" value={load} onChange={e=>setLoad(Math.min(tree.model.fuel_cell_kw??1,Math.max(0,Number(e.target.value))))}/></label></div>
        <label className="resource-efficiency">{tr("Приета ефективност:")} <strong>{efficiency}%</strong><input type="range" min={30} max={65} step={5} value={efficiency} onChange={e=>setEfficiency(Number(e.target.value))}/></label>
        <div className="resource-stats"><div><span>{tr("Използваем H₂ (норм. литри)")}</span><strong>{result?.hydrogen_usable_normal_l==null?'—':`${fmt(result.hydrogen_usable_normal_l,1)} Nl`}</strong></div><div><span>{tr("Разход при това натоварване")}</span><strong>{result?`${fmt(result.fuel_cell_hydrogen_consumption_nlph,0)} Nl/h`:'—'}</strong></div></div>
        <div className="resource-time"><Clock3 size={19}/><div><small>{tr("При")} {fmt(load)} {tr("kW консумация")}</small><strong>{pressure===''?tr("Въведи налягане"):load===0?tr("Без консумация"):duration(result?.hydrogen_runtime_hours??null)}</strong></div></div>
        <p className="resource-note"><CircleHelp size={14}/> {tr("Без налягане не може да се изчисли запасът от газ. Изчислението приема идеален газ при 20°C и спад до 0 bar(g); реално използваемото количество зависи от оборудването.")}</p>
      </article>
    </div>
    <div className="resource-footer"><Gauge size={16}/><span>{tr("Прогноза, не измерване. Необходим е одобрен съд под налягане, регулатор, подходящи датчици и независими защити. Изчисленията не доказват безопасност или реален капацитет.")}</span></div>
    {error&&<p className="resource-error" role="alert">{tr(error)}</p>}
  </section>
}
