import {useEffect,useMemo,useState} from 'react'
import {Area,AreaChart,CartesianGrid,Line,LineChart,ResponsiveContainer,Tooltip,XAxis,YAxis} from 'recharts'
import {Activity,Waves,TrendingUp} from 'lucide-react'
import {locale,tr} from './language'
import {formatNum,formatTime} from './format'
import Empty from './Empty'
import type {Reading,Forecast,OxygenHistory} from './types'

function useChartMotion() {
  const [enabled, setEnabled] = useState(() => !window.matchMedia('(prefers-reduced-motion: reduce)').matches)
  useEffect(() => {
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)')
    const update = () => setEnabled(!preference.matches)
    update()
    preference.addEventListener('change', update)
    return () => preference.removeEventListener('change', update)
  }, [])
  return enabled
}
export function TelemetryChart({readings,small=false}:{readings:Reading[];small?:boolean}){
  const animate = useChartMotion()
  const currentSource=readings.at(-1)?.source
  const language = locale()
  const rows=useMemo(()=>readings.filter(r=>r.source===currentSource).slice(small?-48:-100).map(r=>({at:formatTime(r.time),w:r.power_w})),[readings,small,currentSource,language])
  if(!rows.length)return <Empty icon={Activity} title={tr("Няма измервания")} desc={tr("Показателите ще се появят след свързване на устройството или въвеждане на сценарий.")}/>
  return <div className={`chart-box ${small?'chart-small':''}`}>{currentSource==='device'&&<span className="chart-source-badge">{tr("Измерени данни")}</span>}<ResponsiveContainer width="100%" height="100%"><AreaChart data={rows} margin={{top:14,right:6,left:-24,bottom:0}}><defs><linearGradient id="powerGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--chart-power)" stopOpacity={.25}/><stop offset="96%" stopColor="var(--chart-power)" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="var(--app-edge)" vertical={false} strokeDasharray="3 6"/><XAxis dataKey="at" stroke="var(--app-sub)" tick={{fill:'var(--app-sub)',fontSize:11}} tickLine={false} axisLine={false} minTickGap={38}/><YAxis stroke="var(--app-sub)" tick={{fill:'var(--app-sub)',fontSize:11}} tickLine={false} axisLine={false} tickFormatter={v=>`${v}`}/><Tooltip contentStyle={{background:'var(--app-surface)',border:'1px solid var(--app-edge)',borderRadius:12,color:'var(--app-text)',fontSize:12}} labelStyle={{color:'var(--app-sub)'}} formatter={(value)=>[`${formatNum(Number(value))} W`,tr("Мощност")]}/><Area isAnimationActive={animate} animationDuration={500} type="monotone" dataKey="w" stroke="var(--chart-power)" strokeWidth={2.4} fill="url(#powerGradient)" dot={false} activeDot={{r:4,stroke:'var(--chart-power)',fill:'var(--app-surface)'}}/></AreaChart></ResponsiveContainer></div>
}
export function OxygenChart({history}:{history:OxygenHistory|null}){
  const animate = useChartMotion()
  const rows=history?.points||[]
  if(!rows.length)return <Empty icon={Waves} title={tr("Все още няма данни за кислород")} desc={tr("Свържи датчик за кислороден дебит или зареди данни от симулацията.")}/>
  return <div className="oxygen-chart-wrap"><div className="oxygen-highlights"><div><small>{tr("За периода")}</small><strong>{formatNum(history?.total_l||0,1)} <span>L O₂</span></strong></div><div><small>{tr("Последен дебит")}</small><strong>{formatNum(history?.current_flow_lph||0,1)} <span>L/h</span></strong></div><span className="oxygen-source">{history?.basis==='measured'?tr("От датчик"):history?.basis==='simulation'?tr("Изчислени стойности"):history?.basis==='estimated'?tr("Изчислени стойности"):tr("Няма източник")}</span></div><div className="chart-box"><ResponsiveContainer width="100%" height="100%"><AreaChart data={rows.map(r=>({at:formatTime(r.time),liters:r.cumulative_l}))} margin={{top:14,right:9,left:-18,bottom:0}}><defs><linearGradient id="oxygenGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--chart-oxygen)" stopOpacity={.28}/><stop offset="95%" stopColor="var(--chart-oxygen)" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="var(--app-edge)" vertical={false} strokeDasharray="3 6"/><XAxis dataKey="at" tick={{fill:'var(--app-sub)',fontSize:11}} minTickGap={35} tickLine={false} axisLine={false}/><YAxis tick={{fill:'var(--app-sub)',fontSize:11}} tickLine={false} axisLine={false}/><Tooltip contentStyle={{background:'var(--app-surface)',border:'1px solid var(--app-edge)',borderRadius:12,color:'var(--app-text)'}} formatter={v=>[`${formatNum(Number(v),1)} L`,tr("Произведен кислород")]}/><Area isAnimationActive={animate} animationDuration={500} type="monotone" dataKey="liters" stroke="var(--chart-oxygen)" strokeWidth={2.5} dot={false} fill="url(#oxygenGradient)"/></AreaChart></ResponsiveContainer></div></div>
}
export function ForecastChart({forecast,historical=false}:{forecast:Forecast|null;historical?:boolean}){
  const animate = useChartMotion()
  if(!forecast||!forecast.points?.length)return <Empty icon={TrendingUp} title={tr("Все още няма прогноза")} desc={tr("Необходими са повече записи от избраното дърво.")}/>
  return <div className="chart-box"><ResponsiveContainer width="100%" height="100%"><LineChart data={forecast.points.map(x=>({at:formatTime(x.time),w:x.power_w}))} margin={{top:18,right:10,left:-23,bottom:0}}><CartesianGrid stroke="var(--app-edge)" vertical={false} strokeDasharray="3 6"/><XAxis ticks={forecast.points.filter(point=>new Date(point.time).getHours()%2===0).map(point=>formatTime(point.time))} interval="preserveStartEnd" minTickGap={12} dataKey="at" stroke="var(--app-sub)" tick={{fill:'var(--app-sub)',fontSize:11}} tickLine={false} axisLine={false}/><YAxis tick={{fill:'var(--app-sub)',fontSize:11}} tickLine={false} axisLine={false} stroke="var(--app-sub)"/><Tooltip contentStyle={{background:'var(--app-surface)',border:'1px solid var(--app-edge)',borderRadius:12,color:'var(--app-text)'}} formatter={v=>[`${formatNum(Number(v))} W`,historical?tr("Мощност"):tr("Прогноза")]}/><Line isAnimationActive={animate} animationDuration={500} dataKey="w" type="monotone" stroke="var(--chart-power)" strokeWidth={3} dot={{fill:'var(--chart-power)',r:4}} activeDot={{r:5}}/></LineChart></ResponsiveContainer></div>
}
