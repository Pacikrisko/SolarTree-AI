import {LanguageButton,useLanguage} from './LanguageButton'
import {tr,getLanguage,locale} from './language'
import {useCallback,useEffect,useMemo,useRef,useState, type FormEvent, type ReactNode} from 'react'
import {Area,AreaChart,CartesianGrid,Line,LineChart,ResponsiveContainer,Tooltip,XAxis,YAxis} from 'recharts'
import {Activity,ArrowLeft,ArrowRight,ArrowUpRight,Bell,BrainCircuit,Check,CheckCircle2,ChevronRight,CircleAlert,Clock3,Database,Droplets,Filter,Gauge,Info,Leaf,LockKeyhole,LogOut,MapPin,MessageCircle,Plus,RefreshCw,Search,Send,ScanLine,Settings2,Shield,ShieldCheck,SlidersHorizontal,Sparkles,Sun,Moon,Wifi,TreePine,TrendingUp,UserRound,Waves,Wrench,X,Zap, type LucideIcon} from 'lucide-react'
import {latestMetric,latestTime} from './telemetry'
import AuthScreen from './AuthScreen'
import DeviceMedia from './DeviceMedia'
import DeviceThumbnail from './DeviceThumbnail'
import SolarTreeMark from './SolarTreeMark'
import PhonePairing from './PhonePairing'
import ConnectionGuide from './ConnectionGuide'
import ResourcePlanner from './ResourcePlanner'
import PairQrScanner from './PairQrScanner'
import {api,hasAuthToken,setAuthToken,syncAuthToken} from './api'
import type {Alert,ChatMessage,Forecast,Health,Page,Reading,Service,TokenPayload,Tree,User,OxygenHistory,PairResult,ChatExchange} from './types'
import './styles.css'

const formatNum=(n:number,d=0)=>new Intl.NumberFormat(locale(),{maximumFractionDigits:d,minimumFractionDigits:d}).format(n)
function metricText(tree:Tree|null,field:Parameters<typeof latestMetric>[1],unit:string,decimals=0) {
  const value=latestMetric(tree,field)
  return value===null?'—':formatNum(value,decimals)+unit
}
const formatWhen=(iso:string)=>new Date(iso).toLocaleDateString(locale(),{day:'2-digit',month:'short',year:'numeric'})
const formatTime=(iso:string)=>new Date(iso).toLocaleTimeString(locale(),{hour:'2-digit',minute:'2-digit'})
const relativeDay=(s:Service)=>s.status==='overdue'?(getLanguage()==='en'?`${Math.abs(s.days_left)} days overdue`:`${Math.abs(s.days_left)} дни просрочено`):s.days_left===0?tr("Днес"):(getLanguage()==='en'?`In ${s.days_left} days`:`След ${s.days_left} дни`)
function serviceColor(status:Service['status']){return status==='overdue'?'danger':status==='soon'?'amber':'good'}
function initial(name:string){return name.trim().slice(0,1).toUpperCase()||'S'}
function Logo({small=false}:{small?:boolean}){return <div className={`brand ${small?'brand-small':''}`}><div className="brand-symbol"><Leaf size={24} strokeWidth={2.5}/><span/></div>{!small&&<div className="brand-copy"><strong>SolarTree<span> AI</span></strong><small>INTELLIGENT ECOSYSTEM</small></div>}</div>}
function IconButton({icon:Icon,title,onClick,badge,active=false}:{icon:LucideIcon;title:string;onClick:()=>void;badge?:boolean;active?:boolean}){return <button className={`icon-btn ${active?'active':''}`} type="button" aria-label={title} title={title} onClick={onClick}><Icon size={19}/>{badge&&<i className="mini-dot"/>}</button>}
function StatePill({tree}:{tree:Tree}){const live=tree.connection==='live';return <span className={`state-pill ${live?'live':tree.connection==='model'?'virtual':'offline'}`}><i/>{live?tr("Свързано"):tree.connection==='model'?tr("Симулация"):tr("Няма връзка")}</span>}
function SectionHeading({eyebrow,title,action}:{eyebrow?:string;title:string;action?:ReactNode}){return <div className="section-heading"><div>{eyebrow&&<span className="eyebrow">{eyebrow}</span>}<h2>{title}</h2></div>{action}</div>}
function Panel({children,className='' }:{children:ReactNode;className?:string}){return <div className={`panel ${className}`}>{children}</div>}
function Empty({icon:Icon=TreePine,title,desc,action}:{icon?:LucideIcon;title:string;desc:string;action?:ReactNode}){return <div className="empty-state"><div className="empty-icon"><Icon size={26}/></div><h3>{title}</h3><p>{desc}</p>{action}</div>}
function ErrorText({message}:{message:string}){return <div className="error-note"><CircleAlert size={16}/>{tr(message)}</div>}
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
function TelemetryChart({readings,small=false}:{readings:Reading[];small?:boolean}){
  const animate = useChartMotion()
  const currentSource=readings.at(-1)?.source
  const rows=useMemo(()=>readings.filter(r=>r.source===currentSource).map(r=>({at:formatTime(r.time),w:r.power_w,time:r.time})).slice(-Math.max(24,small?48:100)),[readings,small,currentSource])
  if(!rows.length)return <Empty icon={Activity} title={tr("Няма измервания")} desc={tr("Показателите ще се появят след свързване на устройството или въвеждане на сценарий.")}/>
  return <div className={`chart-box ${small?'chart-small':''}`}><span className="chart-source-badge">{currentSource==='device'?tr("Измерени данни"):tr("Симулация")}</span><ResponsiveContainer width="100%" height="100%"><AreaChart data={rows} margin={{top:14,right:6,left:-24,bottom:0}}><defs><linearGradient id="powerGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--chart-power)" stopOpacity={.25}/><stop offset="96%" stopColor="var(--chart-power)" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="#273236" vertical={false} strokeDasharray="3 6"/><XAxis dataKey="at" stroke="#627477" tick={{fill:'#758687',fontSize:11}} tickLine={false} axisLine={false} minTickGap={38}/><YAxis stroke="#627477" tick={{fill:'#758687',fontSize:11}} tickLine={false} axisLine={false} tickFormatter={v=>`${v}`}/><Tooltip contentStyle={{background:'#1b2628',border:'1px solid #34413f',borderRadius:12,color:'#eaf5eb',fontSize:12}} labelStyle={{color:'#a7b6af'}} formatter={(value)=>[`${formatNum(Number(value))} W`,tr("Мощност")]}/><Area isAnimationActive={animate} animationDuration={500} type="monotone" dataKey="w" stroke="var(--chart-power)" strokeWidth={2.4} fill="url(#powerGradient)" dot={false} activeDot={{r:4,stroke:'var(--chart-power)',fill:'#23352c'}}/></AreaChart></ResponsiveContainer></div>
}
function OxygenChart({history}:{history:OxygenHistory|null}){
  const animate = useChartMotion()
  const rows=history?.points||[]
  if(!rows.length)return <Empty icon={Waves} title={tr("Все още няма данни за кислород")} desc={tr("Свържи датчик за кислороден дебит или зареди данни от симулацията.")}/>
  return <div className="oxygen-chart-wrap"><div className="oxygen-highlights"><div><small>{tr("За периода")}</small><strong>{formatNum(history?.total_l||0,1)} <span>L O₂</span></strong></div><div><small>{tr("Последен дебит")}</small><strong>{formatNum(history?.current_flow_lph||0,1)} <span>L/h</span></strong></div><span className="oxygen-source">{history?.basis==='measured'?tr("От датчик"):history?.basis==='simulation'?tr("Симулирани стойности"):history?.basis==='estimated'?tr("Изчислени стойности"):tr("Няма източник")}</span></div><div className="chart-box"><ResponsiveContainer width="100%" height="100%"><AreaChart data={rows.map(r=>({at:formatTime(r.time),liters:r.cumulative_l}))} margin={{top:14,right:9,left:-18,bottom:0}}><defs><linearGradient id="oxygenGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--chart-oxygen)" stopOpacity={.28}/><stop offset="95%" stopColor="var(--chart-oxygen)" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="#273236" vertical={false} strokeDasharray="3 6"/><XAxis dataKey="at" tick={{fill:'#758687',fontSize:11}} minTickGap={35} tickLine={false} axisLine={false}/><YAxis tick={{fill:'#758687',fontSize:11}} tickLine={false} axisLine={false}/><Tooltip contentStyle={{background:'#1b2628',border:'1px solid #34413f',borderRadius:12,color:'#eaf5eb'}} formatter={v=>[`${formatNum(Number(v),1)} L`,tr("Натрупан кислород")]}/><Area isAnimationActive={animate} animationDuration={500} type="monotone" dataKey="liters" stroke="var(--chart-oxygen)" strokeWidth={2.5} dot={false} fill="url(#oxygenGradient)"/></AreaChart></ResponsiveContainer></div></div>
}
function ForecastChart({forecast}:{forecast:Forecast|null}){
  const animate = useChartMotion()
  if(!forecast||!forecast.points?.length)return <Empty icon={TrendingUp} title={tr("Все още няма прогноза")} desc={tr("Необходими са повече записи от избраното дърво.")}/>
  return <div className="chart-box"><ResponsiveContainer width="100%" height="100%"><LineChart data={forecast.points.map(x=>({at:formatTime(x.time),w:x.power_w}))} margin={{top:18,right:10,left:-23,bottom:0}}><CartesianGrid stroke="#273236" vertical={false} strokeDasharray="3 6"/><XAxis dataKey="at" stroke="#758687" tick={{fill:'#758687',fontSize:11}} tickLine={false} axisLine={false}/><YAxis tick={{fill:'#758687',fontSize:11}} tickLine={false} axisLine={false} stroke="#758687"/><Tooltip contentStyle={{background:'#1b2628',border:'1px solid #34413f',borderRadius:12,color:'#eaf5eb'}} formatter={v=>[`${formatNum(Number(v))} W`,tr("Прогноза")]}/><Line isAnimationActive={animate} animationDuration={500} dataKey="w" type="monotone" stroke="var(--chart-power)" strokeWidth={3} dot={{fill:'var(--chart-power)',r:4}} activeDot={{r:5}}/></LineChart></ResponsiveContainer></div>
}
function NewTreeModal({onClose,onSave,onPhoneAdded}:{onClose:()=>void;onSave:(value:{name:string;code:string;claim_token:string;location:string;lat:number|null;lng:number|null})=>Promise<void>;onPhoneAdded:(treeId:number)=>Promise<void>}){
  const [name,setName]=useState(''),[code,setCode]=useState(''),[token,setToken]=useState(''),[location,setLocation]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[resolved,setResolved]=useState<PairResult|null>(null)
  async function resolve(c=code,t=token){setBusy(true);setError('');setResolved(null);try{const r=await api.pairResolve(c,t);setCode(r.code);setToken(t);setResolved(r)}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
  async function submit(e:FormEvent){e.preventDefault();setBusy(true);setError('');try{if(!resolved)throw new Error(tr("Първо разпознай устройството."));await onSave({name,code:resolved.code,claim_token:token,location,lat:null,lng:null})}catch(err){setError((err as Error).message)}finally{setBusy(false)}}
  return <div className="modal-backdrop" onMouseDown={e=>{if(e.target===e.currentTarget)onClose()}}><div className="modal pairing-modal"><div className="modal-heading"><div><span className="eyebrow">{tr("СВЪРЗВАНЕ НА УСТРОЙСТВО")}</span><h2>{tr("Добавяне на дърво")}</h2></div><IconButton title={tr("Затвори")} icon={X} onClick={onClose}/></div>
    <PhonePairing onAdded={onPhoneAdded}/>
    <div className="pair-divider">{tr("или сканирай директно с компютъра")}</div>
    <PairQrScanner onRead={(c,t)=>{setCode(c);setToken(t);void resolve(c,t)}}/>
    <div className="pair-divider">{tr("или въведи регистрационните данни")}</div>
    <form className="modal-form" onSubmit={submit}><label>{tr("Сериен номер")}<input required minLength={3} maxLength={40} value={code} onChange={e=>{setCode(e.target.value.toUpperCase());setResolved(null)}} placeholder={tr("Напр. ST-M6-1001")}/></label><label>{tr("Еднократен код за сдвояване")}<input required minLength={12} maxLength={200} value={token} onChange={e=>{setToken(e.target.value);setResolved(null)}} placeholder={tr("Код от устройството или QR етикета")}/></label>
      <button type="button" className="btn btn-outline full" disabled={busy||!code||!token} onClick={()=>resolve()}><ScanLine size={16}/> {busy?tr("Проверка…"):tr("Разпознай модела")}</button>
      {resolved&&<div className="paired-model"><CheckCircle2 size={21}/><div><strong>{resolved.model.name}</strong><small>{resolved.code} · {resolved.model.panel_count} {tr("панела")} · {resolved.kind==='municipal'?tr("Общинско"):tr("Частно")} {tr("дърво")}</small></div></div>}
      {resolved&&<><label>{tr("Име на дървото")}<input required minLength={2} maxLength={120} value={name} onChange={e=>setName(e.target.value)} placeholder={tr("Напр. Соларно дърво у дома")}/></label><label>{tr("Местоположение")}<input required minLength={3} maxLength={150} value={location} onChange={e=>setLocation(e.target.value)} placeholder={tr("Град или обект")}/></label></>}
      {error&&<ErrorText message={error}/>}
      <div className="modal-actions"><button className="btn btn-quiet" type="button" onClick={onClose}>{tr("Отказ")}</button><button className="btn btn-primary" disabled={busy||!resolved} type="submit">{busy?tr("Добавяне…"):tr("Добави устройство")}<ArrowRight size={16}/></button></div>
    </form></div></div>
}

function ServiceActionModal({item,mode,onClose,onSave}:{item:Service;mode:'complete'|'schedule';onClose:()=>void;onSave:(days:number)=>Promise<void>}){
  const [days,setDays]=useState(item.interval_days),[busy,setBusy]=useState(false),[error,setError]=useState('')
  async function submit(e:FormEvent){e.preventDefault();setBusy(true);setError('');try{await onSave(days)}catch(err){setError((err as Error).message)}finally{setBusy(false)}}
  return <div className="modal-backdrop" onMouseDown={e=>{if(e.target===e.currentTarget)onClose()}}><div className="modal"><div className="modal-heading"><div><span className="eyebrow">{tr("СЕРВИЗЕН ЦЕНТЪР")}</span><h2>{mode==='complete'?tr("Потвърждение за обслужване"):tr("Сервизен интервал")}</h2></div><IconButton icon={X} title={tr("Затвори")} onClick={onClose}/></div><p><strong>{tr(item.label)}</strong> · {item.tree_name}</p><form className="modal-form" onSubmit={submit}>{mode==='schedule'?<><label>{tr("Интервал между обслужванията (дни)")}<input required type="number" min={1} max={3650} value={days} onChange={e=>setDays(Number(e.target.value))}/></label><div className="calendar-note"><Info size={16}/> {tr("Интервалът трябва да съответства на сервизната документация на действителното оборудване.")}</div></>:<div className="calendar-note"><CheckCircle2 size={18}/> {tr("Потвърждавам, че компонентът действително е обслужен. Системата ще запише днешната дата и ще изчисли следващия срок.")}</div>}{error&&<ErrorText message={error}/>}<div className="modal-actions"><button className="btn btn-quiet" type="button" onClick={onClose}>{tr("Отказ")}</button><button className="btn btn-primary" type="submit" disabled={busy}>{busy?tr("Запис…"):mode==='schedule'?tr("Запази интервала"):tr("Потвърди обслужването")}<Check size={16}/></button></div></form></div></div>
}
function ProfilePage({user,onSave,onPassword,onLogout,onSettings}:{user:User;onSave:(name:string)=>Promise<void>;onPassword:(oldPassword:string,newPassword:string)=>Promise<void>;onLogout:()=>void;onSettings:()=>void}){
  const [name,setName]=useState(user.name),[current,setCurrent]=useState(''),[next,setNext]=useState(''),[busy,setBusy]=useState(false),[notice,setNotice]=useState(''),[error,setError]=useState('')
  useEffect(()=>{setName(user.name)},[user.name])
  async function changeName(e:FormEvent){e.preventDefault();setBusy(true);setError('');setNotice('');try{await onSave(name);setNotice(tr("Промените са запазени."))}catch(x){setError((x as Error).message)}finally{setBusy(false)}}
  async function changePassword(e:FormEvent){e.preventDefault();setBusy(true);setError('');setNotice('');try{await onPassword(current,next);setCurrent('');setNext('');setNotice(tr("Паролата е променена успешно."))}catch(x){setError((x as Error).message)}finally{setBusy(false)}}
  return <div className="page-body profile-page"><SectionHeading eyebrow={tr("МОЯТ АКАУНТ")} title={tr("Личен профил")}/><div className="profile-header-card"><span className="profile-big-avatar">{initial(user.name)}</span><div><h2>{user.name}</h2><p>{user.email}</p><span className="profile-access-tag"><ShieldCheck size={14}/>{user.role==='municipality'?tr("Общински служител"):tr("Частен собственик")}</span></div></div><div className="profile-grid"><Panel className="profile-box"><div className="profile-box-title"><UserRound size={19}/><h3>{tr("Лични данни")}</h3></div><form onSubmit={changeName} className="modal-form"><label>{tr("Име и фамилия")}<input value={name} onChange={e=>setName(e.target.value)} minLength={2} maxLength={100} required/></label><label>{tr("Имейл адрес")}<input value={user.email} disabled type="email"/></label><small className="profile-hint">{tr("Имейлът и ролята се управляват от системата.")}</small><button className="btn btn-primary" disabled={busy||name.trim()===user.name} type="submit">{tr("Запази промените")} <Check size={16}/></button></form></Panel><Panel className="profile-box"><div className="profile-box-title"><LockKeyhole size={19}/><h3>{tr("Сигурност")}</h3></div><form onSubmit={changePassword} className="modal-form"><label>{tr("Настояща парола")}<input type="password" autoComplete="current-password" value={current} onChange={e=>setCurrent(e.target.value)} required/></label><label>{tr("Нова парола")}<input type="password" autoComplete="new-password" minLength={8} required value={next} onChange={e=>setNext(e.target.value)}/></label><button type="submit" className="btn btn-outline" disabled={busy||!current||next.length<8}>{tr("Промени паролата")}</button></form></Panel></div>{error&&<ErrorText message={error}/>} {notice&&<div className="profile-success"><CheckCircle2 size={17}/>{notice}</div>}<button className="btn btn-outline" onClick={onSettings}><Settings2 size={16}/> {tr("Настройки на приложението")}</button><button className="profile-logout" onClick={onLogout}><LogOut size={17}/> {tr("Излез от профила")}</button></div>
}
const getNavItems=():{key:Page;icon:LucideIcon;label:string}[]=>[{key:'overview',icon:Gauge,label:tr("Преглед")},{key:'trees',icon:TreePine,label:tr("Моите дървета")},{key:'insights',icon:Activity,label:tr("Анализи")},{key:'assistant',icon:MessageCircle,label:tr("AI асистент")},{key:'service',icon:Wrench,label:tr("Сервиз")}]
const getPageNames=():Record<Page,string>=>({overview:tr("Преглед"),trees:tr("Моите дървета"),detail:tr("Детайли"),insights:tr("Анализи"),assistant:tr("AI асистент"),service:tr("Сервиз"),settings:tr("Настройки"),profile:tr("Профил")})

export default function App(){
  const [session,setSession]=useState(0)
  const endSession=useCallback(()=>{ setAuthToken(''); setSession(previous=>previous+1) },[])
  useEffect(()=>{
    window.addEventListener('solartree-session-ended',endSession)
    const onStorage=(event:StorageEvent)=>{
      if(event.storageArea===localStorage && (event.key==='solartree_token'||event.key===null) && syncAuthToken()){
        setSession(previous=>previous+1)
      }
    }
    window.addEventListener('storage',onStorage)
    return ()=>{
      window.removeEventListener('solartree-session-ended',endSession)
      window.removeEventListener('storage',onStorage)
    }
  },[endSession])
  return <Workspace key={session} logout={endSession}/>
}

function Workspace({logout}:{logout:()=>void}){
  useLanguage()
  const navItems=getNavItems(),pageNames=getPageNames()
  const [bootError,setBootError]=useState(false)
  const [bootAttempt,setBootAttempt]=useState(0)
  const [historyError,setHistoryError]=useState('')

  const [user,setUser]=useState<User|null>(null),[ready,setReady]=useState(false),[trees,setTrees]=useState<Tree[]>([]),[alerts,setAlerts]=useState<Alert[]>([]),[services,setServices]=useState<Service[]>([]),[health,setHealth]=useState<Health|null>(null)
  const [page,setPage]=useState<Page>('overview'),[selectedId,setSelectedId]=useState<number|null>(null),[readings,setReadings]=useState<Reading[]>([]),[forecast,setForecast]=useState<Forecast|null>(null),[oxygen,setOxygen]=useState<OxygenHistory|null>(null)
  const [modal,setModal]=useState(false),[connectGuide,setConnectGuide]=useState(false),[notifOpen,setNotifOpen]=useState(false),[search,setSearch]=useState(''),[toast,setToast]=useState(''),[refreshIndex,setRefreshIndex]=useState(0),[busyAction,setBusyAction]=useState(false),[serviceAction,setServiceAction]=useState<{item:Service;mode:'complete'|'schedule'}|null>(null)
  const [theme,setTheme]=useState<'dark'|'light'>(()=>localStorage.getItem('solartree_theme')==='dark'?'dark':'light')
  useEffect(()=>{document.documentElement.dataset.theme=theme;localStorage.setItem('solartree_theme',theme)},[theme])
  const selected=trees.find(t=>t.id===selectedId)||trees[0]||null
  const message=(msg:string)=>{setToast(msg);window.setTimeout(()=>setToast(''),4200)}
  const [accountStatus,setAccountStatus]=useState<'loading'|'ready'|'error'>('loading')
  const refreshVersion=useRef(0)
  const refresh=useCallback(async()=>{
    const version=++refreshVersion.current
    const [ts,as,ss,h]=await Promise.all([api.trees(),api.alerts(),api.maintenance(),api.health()]).catch(error=>{
      if(version===refreshVersion.current)setAccountStatus('error')
      throw error
    })
    if(version!==refreshVersion.current)return
    setAccountStatus('ready');setTrees(ts);setAlerts(as);setServices(ss);setHealth(h)
    setSelectedId(prev=>prev&&ts.some(t=>t.id===prev)?prev:ts[0]?.id??null)
    setRefreshIndex(x=>x+1)
  },[])
  useEffect(()=>{
    let active=true
    if(!hasAuthToken()){setReady(true);return}
    setBootError(false)
    api.me().then(me=>{if(active){setUser(me);setReady(true)}})
      .catch(()=>{if(active){if(hasAuthToken())setBootError(true);else setReady(true)}})
    return ()=>{active=false}
  },[bootAttempt])
  useEffect(()=>{if(user)refresh().catch(err=>message((err as Error).message))},[user,refresh])
  useEffect(()=>{if(!user)return;const timer=window.setInterval(()=>refresh().catch(()=>{}),60000);return()=>window.clearInterval(timer)},[user,refresh])
  useEffect(()=>{setReadings([]);setForecast(null);setOxygen(null);setHistoryError('')},[selectedId])
  useEffect(()=>{
    let active=true
    if(!selectedId){setReadings([]);setForecast(null);setOxygen(null);return}
    Promise.allSettled([api.readings(selectedId),api.forecast(selectedId),api.oxygen(selectedId)])
      .then(([r,f,o])=>{
        if(!active)return
        const missing:string[]=[]
        if(r.status==='fulfilled')setReadings(r.value);else missing.push(tr("измерванията"))
        if(f.status==='fulfilled')setForecast(f.value);else missing.push(tr("прогнозата"))
        if(o.status==='fulfilled')setOxygen(o.value);else missing.push(tr("историята за кислорода"))
        setHistoryError(missing.length?tr("Неуспешно обновяване на") + ' '+missing.join(', ')+'.':'')
      })
    return ()=>{active=false}
  },[selectedId,refreshIndex])
  const pendingAlerts=alerts.filter(a=>!a.acknowledged)
  const pendingService=services.filter(s=>s.status!=='ok')
  const attention=pendingAlerts.length+pendingService.length
  const powerLevels=trees.map(t=>latestMetric(t,'power_w')).filter((v):v is number=>v!=null)
  const totalPower=powerLevels.reduce((sum,v)=>sum+v,0)
  const updatedAt=latestTime(selected)
  const waterLevels=trees.map(t=>latestMetric(t,'water_pct')).filter((v):v is number=>v!=null)
  const avgWater=waterLevels.length?waterLevels.reduce((sum,v)=>sum+v,0)/waterLevels.length:null
  const includesSimulation=trees.some(t=>t.latest?.source==='simulation')
  const detailsService=services.filter(s=>s.tree_id===selected?.id)
  const filtered=trees.filter(t=>`${t.name} ${t.code} ${t.location}`.toLowerCase().includes(search.toLowerCase()))
  async function removeTree(tree:Tree){
    if(!window.confirm(getLanguage()==='en'?`Remove “${tree.name}” (${tree.code}) from your account? The code will remain reserved for this account.`:`Да премахна ли „${tree.name}“ (${tree.code}) от твоя профил? Кодът остава запазен за този акаунт.`))return
    setBusyAction(true)
    try{
      await api.removeTree(tree.id)
      refreshVersion.current++
      setTrees(items=>items.filter(item=>item.id!==tree.id))
      setServices(items=>items.filter(item=>item.tree_id!==tree.id))
      setAlerts(items=>items.filter(item=>item.tree_id!==tree.id))
      setSelectedId(trees.find(item=>item.id!==tree.id)?.id??null)
      setPage('trees')
      message(tr("Дървото е премахнато."))
    }catch(err){message((err as Error).message)}
    finally{setBusyAction(false)}
  }
  const openTree=(id:number)=>{setSelectedId(id);setPage('detail')}
  const onAuth=(payload:TokenPayload)=>{setAuthToken(payload.access_token);setUser(payload.user);setPage('overview')}
  const action=async(run:()=>Promise<unknown>,success:string)=>{setBusyAction(true);try{await run();await refresh();message(success)}catch(err){message((err as Error).message)}finally{setBusyAction(false)}}
  const saveServiceAction=async(days:number)=>{if(!serviceAction)return;const {item,mode}=serviceAction;if(mode==='schedule')await api.serviceSchedule(item.tree_id,item.component,days);else await api.serviceDone(item.tree_id,item.component);await refresh();setServiceAction(null);message(mode==='schedule'?tr("Сервизният интервал е обновен."):tr("Обслужването е записано."))}
  const create=async(value:{name:string;code:string;claim_token:string;location:string;lat:number|null;lng:number|null})=>{const tree=await api.createTree(value);await refresh();setSelectedId(tree.id);setPage('detail');setModal(false);message(tr("Дървото е добавено."))}
  const phoneAdded=useCallback(async(treeId:number)=>{await refresh();setSelectedId(treeId);setPage('detail');setModal(false);message(tr("Устройството е добавено чрез телефона."))},[refresh])
  const nav=(p:Page)=>{setPage(p);setNotifOpen(false)}
  const saveProfile=async(name:string)=>{const updated=await api.updateProfile(name);setUser(updated)}
  const changePassword=async(current:string,next:string)=>{await api.changePassword(current,next)}
  if(bootError)return <div className="boot"><p role="alert">{tr("Връзката със сървъра прекъсна.")}</p><button className="btn btn-primary" onClick={()=>setBootAttempt(n=>n+1)}>{tr("Опитай отново")}</button><button className="btn btn-outline" onClick={logout}>{tr("Към входа")}</button></div>
  if(!ready)return <div className="boot"><div className="boot-logo"><Leaf size={32}/></div><span>SolarTree AI</span></div>
  if(!user)return <AuthScreen onSuccess={onAuth}/>
  return <div className="app-shell">
    <aside className="sidebar"><div className="side-brand"><Logo/></div>
      <div className="sidebar-workspace"><span className="workspace-dot"/><strong>{user.role==='municipality'?tr("Общинска мрежа"):tr("Моето пространство")}</strong></div>
      <nav className="side-nav" aria-label={tr("Основна навигация")}>{navItems.map(({key,icon:Icon,label})=><button key={key} title={label} className={page===key||(page==='detail'&&key==='trees')?'selected':''} onClick={()=>nav(key)}><Icon size={19}/><span>{key==='trees'&&user.role==='municipality'?tr("Общински дървета"):label}</span>{key==='service'&&attention>0&&<i className="side-count">{attention}</i>}</button>)}</nav>
      <div className="sidebar-spacer"/>
      <div className="side-nav side-bottom"><button className={page==='settings'?'selected':''} onClick={()=>nav('settings')}><Settings2 size={19}/><span>{tr("Настройки")}</span></button></div>
      <div className="side-profile"><button className="profile-launch" title={tr("Отвори профила")} onClick={()=>nav('profile')}><span className="avatar">{initial(user.name)}</span><span className="side-profile-name"><strong>{user.name}</strong><span>{user.role==='municipality'?tr("Общински администратор"):tr("Частен собственик")}</span></span></button><button title={tr("Изход")} onClick={logout}><LogOut size={17}/></button></div>
    </aside>
    <main className="main-area"><header className="topbar"><div className="top-heading"><span className="breadcrumb">SolarTree <ChevronRight size={13}/> {page==='detail'?tr("Дървета"):pageNames[page]}</span><h1>{page==='detail'?selected?.name||tr("Дърво"):pageNames[page]}</h1></div><div className="top-actions"><LanguageButton/><button className="theme-switch" type="button" onClick={()=>setTheme(v=>v==='dark'?'light':'dark')} aria-label={theme==='dark'?tr("Светла тема"):tr("Тъмна тема")} title={theme==='dark'?tr("Светла тема"):tr("Тъмна тема")}>{theme==='dark'?<Sun size={17}/>:<Moon size={17}/>}<span>{theme==='dark'?tr("Светла"):tr("Тъмна")}</span></button><div className="system-state">{accountStatus==='ready'&&<span className="pulse-dot"/>} {accountStatus==='ready'?tr("Сървърът е активен"):accountStatus==='loading'?tr("Свързване…"):tr("Проблем с обновяването")}</div><IconButton icon={RefreshCw} title={tr("Обнови данните")} onClick={()=>refresh().catch(e=>message((e as Error).message))}/><div className="notifications-wrap"><IconButton icon={Bell} title={tr("Известия")} badge={attention>0} active={notifOpen} onClick={()=>setNotifOpen(v=>!v)}/>{notifOpen&&<div className="notification-pop"><div className="popover-head"><strong>{tr("Известия")}</strong><span>{attention} {tr("активни")}</span></div>{attention===0?<div className="notification-empty"><CheckCircle2 size={20}/> {tr("Няма нови известия")}</div>:<div className="notif-list">{pendingService.slice(0,4).map(s=><button key={`s${s.id}`} onClick={()=>{setSelectedId(s.tree_id);nav('service')}}><span className="notif-icon amber"><Wrench size={17}/></span><span><strong>{tr(s.label)}</strong><small>{s.tree_name} · {relativeDay(s)}</small></span><ChevronRight size={15}/></button>)}{pendingAlerts.slice(0,4).map(a=><button key={`a${a.id}`} onClick={()=>{setSelectedId(a.tree_id);nav('service')}}><span className="notif-icon danger"><CircleAlert size={17}/></span><span><strong>{tr("Необичайни показания")}</strong><small>{a.tree_name}</small></span><ChevronRight size={15}/></button>)}</div>}<button className="popover-footer" onClick={()=>nav('service')}>{tr("Отвори сервизния център")} <ArrowRight size={14}/></button></div>}</div><button type="button" title={tr("Отвори моя профил")} aria-label={tr("Отвори моя профил")} className="top-avatar profile-avatar-button" onClick={()=>nav('profile')}>{initial(user.name)}</button></div></header>
    <div className="main-scroll">
    {accountStatus==='error'&&<div role="alert" className="info-box">{tr("Данните на профила не се обновиха.")} <button className="btn btn-outline btn-small" onClick={()=>refresh().catch(()=>{})}>{tr("Опитай отново")}</button></div>}
    {refreshIndex===0&&accountStatus==='loading'&&<div role="status" className="info-box">{tr("Зареждане на данните…")}</div>}
    {historyError&&['overview','insights','detail'].includes(page)&&<div role="status" className="info-box">{historyError} <button className="btn btn-outline btn-small" onClick={()=>setRefreshIndex(i=>i+1)}>{tr("Опитай отново")}</button></div>}
    {refreshIndex>0&&page==='overview'&&<div className="page-body dashboard"><div className="welcome-row"><div><span className="eyebrow"><span className="accent-tick"/> {new Intl.DateTimeFormat(locale(), {weekday:'long', day:'numeric', month:'long'}).format(new Date())}</span><h2>{tr("Добре дошъл,")} {user.name.split(' ')[0]}<span className="welcome-dot">.</span></h2><p>{trees.length ? tr("Мощност, вода и сервизни сигнали за твоите соларни дървета.") : tr("Добави първото си соларно дърво, за да проследиш неговите измервания.")}</p></div><button className="btn btn-outline" onClick={()=>setModal(true)}><Plus size={17}/> {tr("Добави дърво")}</button></div>
      <div className="stat-grid"><StatCard icon={TreePine} label={tr("Соларни дървета")} value={String(trees.length).padStart(2,'0')} sub={user.role==='municipality'?tr("В общинската мрежа"):tr("В личния ти профил")} accent="green"/><StatCard icon={Zap} label={tr("Соларна мощност")} value={powerLevels.length?`${formatNum(totalPower/1000,2)} kW`:'—'} sub={includesSimulation?tr("Включва симулирана мощност"):tr("Общо от последните записи")} accent="blue"/><StatCard icon={Droplets} label={tr("Ниво на резервоарите")} value={avgWater===null?'—':`${formatNum(avgWater)}%`} sub={includesSimulation?tr("Включва симулирано ниво"):tr("Средно от наличните нива")} accent="purple"/><StatCard icon={Bell} label={tr("За внимание")} value={String(attention).padStart(2,'0')} sub={tr("Сервизни задачи и сигнали")} accent="orange"/></div>
      {trees.length>0&&<div className="context-selector">
        <label htmlFor="overview-tree">{tr("Избрано устройство")}</label>
        <select id="overview-tree" value={selected?.id??''} onChange={e=>setSelectedId(Number(e.target.value))}>
          {trees.map(tree=><option key={tree.id} value={tree.id}>{tree.name} · {tree.code}</option>)}
        </select>
      </div>}
      <div className="dashboard-main"><Panel key={selected?.id ?? "empty"} className="featured-panel"><div className="featured-top"><div><span className="eyebrow">{tr("ИЗБРАНО УСТРОЙСТВО")}</span><h3>{selected?.name||tr("Няма избрано дърво")}</h3><span className="device-subtitle">{selected?.code||'—'} {selected?' · '+selected.location:''}</span></div>{selected&&<StatePill tree={selected}/>}</div><DeviceMedia tree={selected} compact onChanged={refresh}/><div className="featured-bottom"><div className="featured-reading"><span>{tr("МОЩНОСТ")}</span><strong>{metricText(selected,'power_w',' W')}</strong></div><div className="featured-reading"><span>{tr("КИСЛОРОД")}</span><strong>{metricText(selected,'oxygen_flow_lph',' L/h',1)}</strong></div><div className="featured-reading"><span>{tr("ВОДЕН РЕЗЕРВОАР")}</span><strong>{metricText(selected,'water_pct','%')}</strong></div><button className="featured-open" aria-label={tr("Отвори избраното дърво")} disabled={!selected} onClick={()=>selected&&openTree(selected.id)}><ArrowUpRight size={19}/></button></div></Panel><div className="right-stack"><Panel className="trend-panel"><div className="panel-top"><div><span className="eyebrow">{tr("МОНИТОРИНГ")}</span><h3>{tr("Производителност")}</h3></div><span className="chart-unit">{tr("W / история")}</span></div><TelemetryChart readings={readings} small/></Panel><Panel className="attention-panel"><div className="panel-top"><div><span className="eyebrow">{tr("СЕРВИЗНИ СЪБИТИЯ")}</span><h3>{tr("Изисква внимание")}</h3></div><button className="text-link" onClick={()=>nav('service')}>{tr("Всички")} <ArrowRight size={15}/></button></div>{attention===0?<div className="all-clear"><CheckCircle2 size={19}/> {tr("Всички устройства са без активни сигнали")}</div>:<div className="attention-list">{pendingService.slice(0,2).map(s=><button key={s.id} onClick={()=>{setSelectedId(s.tree_id);nav('service')}}><span className="attention-icon"><Wrench size={17}/></span><span><strong>{s.component==='water_filter'?tr("Смяна на филтър"):tr("Изсушаващ модул")}</strong><small>{s.tree_name} · {relativeDay(s)}</small></span><ChevronRight size={15}/></button>)}{pendingAlerts.slice(0,1).map(a=><button key={a.id} onClick={()=>nav('service')}><span className="attention-icon"><CircleAlert size={17}/></span><span><strong>{tr("Необичайни показания")}</strong><small>{a.tree_name}</small></span><ChevronRight size={15}/></button>)}</div>}</Panel></div></div>
      <Panel className="devices-panel"><div className="panel-top"><div><span className="eyebrow">{tr("УСТРОЙСТВА")}</span><h3>{user.role==='municipality'?tr("Общинска мрежа"):tr("Моите соларни дървета")}</h3></div><button className="text-link" onClick={()=>nav('trees')}>{tr("Виж всички")} <ArrowRight size={16}/></button></div>{!trees.length?<Empty title={tr("Добави първото си дърво")} desc={tr("Регистрирай устройство, за да започнеш мониторинг.")} action={<button className="btn btn-primary" onClick={()=>setModal(true)}><Plus size={16}/> {tr("Добави дърво")}</button>}/>:<div className="devices-rows">{trees.slice(0,4).map(t=><button className="device-row" key={t.id} onClick={()=>openTree(t.id)}><span className="tree-icon"><SolarTreeMark size={27}/></span><span className="device-row-main"><strong>{t.name}</strong><small>{t.code} · {t.location}</small></span><span className="device-row-power">{metricText(t,'power_w',' W')}</span><StatePill tree={t}/><ChevronRight className="row-chevron" size={18}/></button>)}</div>}</Panel>
    </div>}
    {refreshIndex>0&&page==='trees'&&<div className="page-body"><SectionHeading eyebrow={tr("ТВОЯТА МРЕЖА")} title={user.role==='municipality'?tr("Общински соларни дървета"):tr("Моите соларни дървета")} action={<div className="tree-header-actions"><button className="btn btn-primary" onClick={()=>setModal(true)}><Plus size={17}/> {tr("Ново дърво")}</button></div>}/><div className="filter-line"><div className="search-box"><Search size={18}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder={tr("Търси по име, код или местоположение")}/></div><div className="list-count"><SlidersHorizontal size={16}/> {filtered.length} {tr("устройства")}</div></div>{!filtered.length?<Panel><Empty icon={TreePine} title={trees.length?tr("Няма резултати"):tr("Все още няма дървета")} desc={trees.length?tr("Промени търсенето."):tr("Добави първото си устройство, за да започнеш.")} action={<button className="btn btn-outline" onClick={()=>{setSearch('');if(!trees.length)setModal(true)}}>{trees.length?tr("Изчисти търсенето"):tr("Добави дърво")}</button>}/></Panel>:<div className="tree-grid">{filtered.map(t=><button className="tree-card" key={t.id} onClick={()=>openTree(t.id)}><div className="tree-card-upper"><span className="tree-card-icon"><SolarTreeMark size={30}/></span><StatePill tree={t}/></div><DeviceThumbnail tree={t}/><div className="tree-card-name"><span>{t.code}</span><h3>{t.name}</h3><p><MapPin size={13}/>{t.location}</p></div><div className="tree-card-bottom"><span><small>{tr("Мощност")}</small><strong>{metricText(t,'power_w',' W')}</strong></span><span><small>{t.model.code==='ST-URBAN-2KW'?tr("Вода / H₂ съд"):tr("Резервоар")}</small><strong>{t.model.code==='ST-URBAN-2KW'?'10 L / 20 L':metricText(t,'water_pct','%')}</strong></span><span className="tree-card-arrow"><ArrowUpRight size={20}/></span></div></button>)}</div>}</div>}
    {page==='detail'&&<div className="page-body detail-page">{!selected?<Empty title={tr("Няма избрано дърво")} desc={tr("Добави или избери устройство от списъка.")}/>:<><div className="detail-actions"><button className="back-link" onClick={()=>nav('trees')}><ArrowLeft size={16}/> {tr("Всички дървета")}</button><div className="detail-actions-right"><StatePill tree={selected}/><button type="button" disabled={busyAction} className="btn btn-subtle-warning" onClick={()=>removeTree(selected)}>{tr("Премахни дървото")}</button>{!selected.simulation&&<button className="btn btn-outline" onClick={()=>setConnectGuide(true)}><Wifi size={16}/> {tr("Свържи устройство")}</button>}<button className="btn btn-outline" onClick={()=>nav('assistant')}><Sparkles size={16}/> {tr("Попитай AI")}</button></div></div><div className="detail-grid"><Panel className="model-panel"><div className="model-panel-top"><div><span className="eyebrow">{tr("СНИМКА ИЛИ ВИДЕО")}</span><h3>{selected.name}</h3><span className="muted-small">{selected.code} · {selected.model.panel_count} {tr("панела · Каталожна конфигурация")}</span></div><span className="outline-badge model-identified"><CheckCircle2 size={13}/> {selected.model.name}</span></div>{selected.model.electrolyzer_kw&&<div className="industrial-specs"><span>{tr("Електролизер")} <strong>{selected.model.electrolyzer_kw} kW</strong></span><span>{tr("O₂ (проектно)")} <strong>{selected.model.oxygen_nominal_lph} L/h</strong></span><span>{tr("Горивна клетка")} <strong>{selected.model.fuel_cell_kw} kW</strong></span>{selected.model.water_tank_l&&<span>{tr("Вода")} <strong>{selected.model.water_tank_l} L</strong></span>}{selected.model.hydrogen_tank_l&&<span>{tr("H₂ съд")} <strong>{selected.model.hydrogen_tank_l} L</strong></span>}</div>}<DeviceMedia tree={selected}/></Panel><div className="detail-side"><Panel className="detail-status"><span className="eyebrow">{tr("ТЕКУЩИ ДАННИ")}</span><div className="detail-power"><Zap size={24}/><strong>{metricText(selected,'power_w','')}</strong><span>W</span></div><span className="muted-small">{tr("Последно обновяване:")} {updatedAt?`${formatWhen(updatedAt)}, ${formatTime(updatedAt)}`:tr("няма записи")}</span><div className="detail-separator"/><div className="telemetry-mini"><div><Sun size={17}/><span>{tr("Температура")}</span><strong>{metricText(selected,'temperature_c','°C',1)}</strong></div><div><Droplets size={17}/><span>{tr("Влажност")}</span><strong>{metricText(selected,'humidity_pct','%',1)}</strong></div><div><Waves size={17}/><span>{tr("Ниво на водата")}</span><strong>{metricText(selected,'water_pct','%',1)}</strong></div><div><Activity size={17}/><span>{selected.simulation||selected.latest_sensors?.mq8_adc_raw!=null?tr("MQ-8 (суров ADC)"):tr("MQ-8 (отн. единици)")}</span><strong>{selected.simulation ? formatNum(selected.simulation.mq8_adc_raw) : selected.latest_sensors?.mq8_adc_raw!=null?selected.latest_sensors.mq8_adc_raw:selected.latest?formatNum(selected.latest.h2_sensor_value,2):'—'}</strong></div></div></Panel><Panel className="detail-service"><div className="panel-top"><div><span className="eyebrow">{tr("ПОДДРЪЖКА")}</span><h3>{tr("Сервизно състояние")}</h3></div><Wrench size={19}/></div>{detailsService.map(s=><div className="detail-service-row" key={s.id}><span className={`service-indicator ${serviceColor(s.status)}`}/><div><strong>{s.component==='water_filter'?tr("Воден филтър"):tr("Изсушаващ модул")}</strong><small>{s.status==='ok'?tr("Следваща смяна:") + ' ': tr("Срок:") + ' '}{formatWhen(s.due_at)}</small></div><span className={s.status==='ok'?'ok-text':'warn-text'}>{relativeDay(s)}</span></div>)}<button className="text-link" onClick={()=>nav('service')}>{tr("Сервизни детайли")} <ArrowRight size={15}/></button></Panel></div></div><div className="detail-bottom"><Panel className="detail-history"><div className="panel-top"><div><span className="eyebrow">{tr("ИСТОРИЯ")}</span><h3>{tr("Енергийна активност")}</h3></div><span className="chart-unit">{tr("W / 15 мин.")}</span></div><TelemetryChart readings={readings}/></Panel>{selected.simulation ? <Panel className="scenarios-panel">
      <span className="eyebrow">{tr("АВТОМАТИЧНА СИМУЛАЦИЯ")}</span><h3>{tr("Работа на Urban 2K")}</h3>
      <p>{tr("Стойностите се обновяват всяка минута. Панелите захранват електролизера през деня. Горивната клетка черпи от запаса на водород и през нощта.")}</p>
      <div className="model-metric"><span>{tr("Електролизер")}</span><strong>{formatNum(selected.latest?.electrolyzer_power_w??0)} W</strong></div>
      <div className="model-metric"><span>{tr("Производство на H₂")}</span><strong>{formatNum(selected.simulation.hydrogen_flow_nlph,1)} Nl/h</strong></div>
      <div className="model-metric"><span>{tr("Горивна клетка")}</span><strong>{formatNum(selected.simulation.fuel_cell_load_kw*1000)} W</strong></div>
      <div className="model-metric"><span>{tr("Налягане в съда")}</span><strong>{formatNum(selected.simulation.hydrogen_pressure_bar_g,1)} bar(g)</strong></div>
    </Panel> : <Panel className="scenarios-panel"><span className="eyebrow">{tr("АНАЛИЗ И ТЕСТОВЕ")}</span><h3>{tr("Сценарии и анализ")}</h3><p>{tr("Изследвай различни състояния, без да изпращаш команди към физическото устройство.")}</p><div className="scenario-callout"><Info size={17}/> {tr("Сценариите записват само виртуални измервания.")}</div><button disabled={busyAction||!health?.simulation_enabled} className="btn btn-outline full" onClick={()=>action(()=>api.simulate(selected.id,'normal'),tr("Добавено е виртуално измерване."))}><Activity size={16}/> {tr("Нормален сценарий")}</button><button disabled={busyAction||!health?.simulation_enabled} className="btn btn-subtle-warning full" onClick={()=>action(()=>api.simulate(selected.id,'anomaly'),tr("Генериран е сценарий с отклонение."))}><CircleAlert size={16}/> {tr("Сценарий с отклонение")}</button><span className="source-indicator">{tr("Източник на последния запис:")} {selected.latest?.source==='device'?tr("устройство"):selected.latest?.source==='simulation'?tr("виртуален модел"):tr("няма")}</span></Panel>}</div>{selected.model.code==='ST-URBAN-2KW'&&<ResourcePlanner key={selected.id} tree={selected}/>}<Panel className="oxygen-detail-panel"><div className="panel-top"><div><span className="eyebrow">{tr("КИСЛОРОД")}</span><h3>{tr("Произведен кислород")}</h3></div><span className="chart-unit">{tr("L · за наличния период")}</span></div><OxygenChart history={oxygen}/><p className="oxygen-footnote">{(oxygen?.note&&tr(oxygen.note))||tr("Данните ще се появят след свързване на измерването.")}</p></Panel></>}</div>}
    {page==='insights'&&<div className="page-body"><SectionHeading eyebrow="INTELLIGENCE ENGINE" title={tr("Анализи и прогнози")}/><div className="context-selector"><span><TreePine size={17}/> {tr("Избрано устройство")}</span><select aria-label={tr("Избрано устройство")} value={selected?.id??''} onChange={e=>setSelectedId(Number(e.target.value))}>{trees.map(t=><option key={t.id} value={t.id}>{t.name} · {t.code}</option>)}</select></div><div className="insight-banner"><div><span className="eyebrow">{tr("ПРОГНОЗЕН МОДЕЛ")}</span><h3>{tr("От данните към решенията.")}</h3><p>{tr("Моделът анализира историята на измерванията и изчислява ориентировъчната електрическа мощност за следващите интервали.")}</p></div><div className="insight-visual"><BrainCircuit size={82} strokeWidth={1.1}/></div></div><div className="insight-grid"><Panel><div className="panel-top"><div><span className="eyebrow">{tr("МАШИННО ОБУЧЕНИЕ")}</span><h3>{tr("Прогноза за мощност")}</h3></div><span className="outline-badge">{tr("6 интервала")}</span></div><ForecastChart forecast={forecast}/></Panel><Panel className="insight-model-info"><span className="eyebrow">{tr("МОДЕЛ И ТОЧНОСТ")}</span><h3>{(forecast?.model&&tr(forecast.model))||tr("Няма данни")}</h3><div className="model-metric"><span>{tr("Обучаващи записи")}</span><strong>{forecast?.trained_samples??'—'}</strong></div><div className="model-metric"><span>{tr("Средна абсолютна грешка (MAE)")}</span><strong>{forecast?.mae_w==null?'—':`${formatNum(forecast.mae_w,1)} W`}</strong></div><div className="model-metric"><span>{tr("Източник на данните")}</span><strong>{selected?.latest?.source==='device'?tr("Устройство"):selected?.latest?.source==='simulation'?tr("Виртуален модел"):tr("Няма данни")}</strong></div><div className="info-box"><Info size={16}/> {tr("Прогнозата е експериментален анализ, не измерване и не команда за управление.")}</div></Panel></div><Panel className="oxygen-insight-panel"><div className="panel-top"><div><span className="eyebrow">O₂ ANALYTICS</span><h3>{tr("Производство на кислород")}</h3></div><Waves size={21}/></div><OxygenChart history={oxygen}/></Panel><Panel className="insight-bottom"><div className="insight-icon"><ShieldCheck size={24}/></div><div><h3>{tr("Откриване на необичайни показания")}</h3><p>{tr("Модулът сравнява новите измервания с историческите данни. При значимо отклонение се създава известие за проверка. Аварийните защити на реалното устройство са независими.")}</p></div><button className="btn btn-outline" onClick={()=>nav('service')}>{tr("Виж събитията")} <ArrowRight size={15}/></button></Panel></div>}
    {page==='assistant'&&<AssistantPage key={user.id+'-'+trees.map(t=>t.id).join(',')} health={health} trees={trees} selected={selected} onSelect={setSelectedId}/>}
    {page==='service'&&<div className="page-body"><SectionHeading eyebrow="SERVICE CENTER" title={tr("Поддръжка и известия")}/><div className="service-summary"><div className="service-kpi"><div className="service-kpi-icon"><Wrench size={20}/></div><div><span>{tr("За обслужване")}</span><strong>{pendingService.length}</strong></div></div><div className="service-kpi"><div className="service-kpi-icon amber"><Clock3 size={20}/></div><div><span>{tr("Предстоящи смени")}</span><strong>{services.filter(s=>s.status==='soon').length}</strong></div></div><div className="service-kpi"><div className="service-kpi-icon red"><Bell size={20}/></div><div><span>{tr("Активни сигнали")}</span><strong>{pendingAlerts.length}</strong></div></div></div><div className="service-sections"><Panel><div className="panel-top"><div><span className="eyebrow">{tr("ПРЕВАНТИВНА ПОДДРЪЖКА")}</span><h3>{tr("Сервизен график")}</h3></div><span className="chart-unit">{tr("Изчислено по календар")}</span></div>{!services.length?<Empty icon={Wrench} title={tr("Няма сервизни записи")} desc={tr("При добавяне на устройство ще се създаде сервизен график.")}/>:<div className="service-list">{[...services].sort((a,b)=>a.days_left-b.days_left).map(s=><div className="service-item" key={s.id}><span className={`service-item-icon ${serviceColor(s.status)}`}>{s.component==='water_filter'?<Filter size={20}/>:<Droplets size={20}/>}</span><div className="service-item-info"><strong>{tr(s.label)}</strong><small>{s.tree_name} · {formatWhen(s.due_at)}</small><span className={`service-state ${serviceColor(s.status)}`}>{s.status==='overdue'?tr("Просрочен"):s.status==='soon'?tr("Предстои"):tr("По график")} · {relativeDay(s)}</span></div><div className="service-item-actions"><button className="icon-btn" title={tr("Промени сервизен интервал")} disabled={busyAction} onClick={()=>setServiceAction({item:s,mode:'schedule'})}><Settings2 size={15}/></button><button className="btn btn-outline btn-small" disabled={busyAction} onClick={()=>setServiceAction({item:s,mode:'complete'})}><Check size={15}/> {tr("Обслужено")}</button></div></div>)}</div>}<div className="calendar-note"><Info size={16}/> {tr("Сроковете са приблизителни и се основават на зададени интервали, а не на измерено износване. Коригирай ги според спецификацията на производителя.")}</div></Panel><Panel className="alerts-panel"><div className="panel-top"><div><span className="eyebrow">{tr("СЪБИТИЯ")}</span><h3>{tr("Сигнали и история")}</h3></div><span className="outline-badge">{alerts.length}</span></div>{!alerts.length?<div className="all-clear large"><CheckCircle2 size={24}/> {tr("Няма регистрирани отклонения")}</div>:<div className="alerts-list">{alerts.map(a=><div className="alert-item" key={a.id}><span className={`alert-glyph ${a.acknowledged?'resolved':''}`}><CircleAlert size={19}/></span><div><strong>{tr(a.message)}</strong><small>{a.tree_name} · {formatWhen(a.time)} · {formatTime(a.time)}</small></div>{a.acknowledged?<span className="tag-done"><Check size={13}/> {tr("Разгледан")}</span>:<button className="btn btn-outline btn-small" disabled={busyAction} onClick={()=>action(()=>api.ack(a.id),tr("Сигналът е отбелязан като разгледан."))}>{tr("Разгледано")}</button>}</div>)}</div>}</Panel></div></div>}
    {page==='profile'&&<ProfilePage user={user} onSave={saveProfile} onPassword={changePassword} onLogout={logout} onSettings={()=>nav('settings')}/>}
    {page==='settings'&&<div className="page-body"><SectionHeading eyebrow="PREFERENCES & INTEGRATIONS" title={tr("Настройки")}/><div className="settings-grid"><Panel className="settings-block"><div className="settings-icon"><UserRound size={22}/></div><h3>{tr("Профил и достъп")}</h3><p>{tr("Идентичност и права за текущото работно пространство.")}</p><button className="btn btn-outline" onClick={()=>nav('profile')}>{tr("Редактирай профила")} <ArrowRight size={15}/></button><div className="setting-line"><span>{tr("Потребител")}</span><strong>{user.name}</strong></div><div className="setting-line"><span>{tr("Имейл")}</span><strong>{user.email}</strong></div><div className="setting-line"><span>{tr("Роля")}</span><strong>{user.role==='municipality'?tr("Общински служител"):tr("Собственик")}</strong></div></Panel><Panel className="settings-block"><div className="settings-icon"><BrainCircuit size={22}/></div><h3>{tr("AI интеграция")}</h3><p>{tr("Свободен разговор чрез езиков модел. API ключът се съхранява само на сървъра.")}</p><div className="setting-line"><span>{tr("Състояние")}</span><span className={`integration-state ${health?.real_llm?'connected':'disconnected'}`}><i/>{health?.real_llm?tr("Конфигурирано"):tr("Очаква настройка")}</span></div><div className="setting-line"><span>{tr("Настройка")}</span><strong>{health?.ai_provider==='openai'?'OpenAI':'Cloudflare Workers AI'}</strong></div><button className="btn btn-outline" onClick={()=>nav('assistant')}>{tr("Към асистента")} <ArrowRight size={15}/></button></Panel><Panel className="settings-block"><div className="settings-icon"><Database size={22}/></div><h3>{tr("Източници на данни")}</h3><p>{tr("Приложението съхранява измерванията в локалната база данни.")}</p><div className="setting-line"><span>{tr("Свързани устройства")}</span><strong>{trees.filter(t=>t.connection==='live').length}</strong></div><div className="setting-line"><span>{tr("Дървета с тестови данни")}</span><strong>{trees.filter(t=>t.connection==='model').length}</strong></div><div className="setting-line"><span>{tr("Версия")}</span><strong>{health?.version||'0.5.0'}</strong></div></Panel><Panel className="settings-block"><div className="settings-icon"><Shield size={22}/></div><h3>{tr("Управление на безопасността")}</h3><p>{tr("Платформата показва данни и препоръки. Не управлява защитните вериги на електролизера или газовата система.")}</p><div className="setting-line"><span>{tr("Достъп")}</span><strong>{tr("Сървърно ограничен по роли")}</strong></div><div className="setting-line"><span>{tr("Управление на газова система")}</span><strong>{tr("Неактивно")}</strong></div></Panel></div></div>}
    </div></main>
    <div className="mobile-nav">{navItems.map(({key,icon:Icon,label})=><button key={key} className={page===key||(page==='detail'&&key==='trees')?'active':''} onClick={()=>nav(key)}><Icon size={21}/><span>{key==='trees'?tr("Дървета"):key==='assistant'?'AI':label}</span></button>)}</div>
    {connectGuide&&selected&&<ConnectionGuide tree={selected} onClose={()=>setConnectGuide(false)}/>}
    {serviceAction&&<ServiceActionModal item={serviceAction.item} mode={serviceAction.mode} onClose={()=>setServiceAction(null)} onSave={saveServiceAction}/>}
    {modal&&<NewTreeModal onClose={()=>setModal(false)} onSave={create} onPhoneAdded={phoneAdded}/>}{toast&&<div className="toast"><Info size={17}/>{toast}<button onClick={()=>setToast('')} aria-label={tr("Затвори")}><X size={15}/></button></div>}
  </div>
}
function StatCard({icon:Icon,label,value,sub,accent}:{icon:LucideIcon;label:string;value:string;sub:string;accent:string}){return <div className={`stat-card stat-${accent}`}><div className="stat-top"><span>{label}</span><span className={`stat-icon ${accent}`}><Icon size={19}/></span></div><strong>{value}</strong><div className="stat-sub"><span className={`stat-spark ${accent}`}/>{sub}</div></div>}
function requestId(){
  const bytes=crypto.getRandomValues(new Uint8Array(16))
  bytes[6]=(bytes[6]&15)|64
  bytes[8]=(bytes[8]&63)|128
  const hex=Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('')
  return [hex.slice(0,8),hex.slice(8,12),hex.slice(12,16),hex.slice(16,20),hex.slice(20)].join('-')
}
function AssistantPage({health,trees,selected,onSelect}:{health:Health|null;trees:Tree[];selected:Tree|null;onSelect:(id:number)=>void}){
  const [wholeAccount,setWholeAccount]=useState(true)
  const scopeId=wholeAccount?null:selected?.id??null
  function changeScope(value:string){
    setWholeAccount(!value)
    if(value)onSelect(Number(value))
  }
  return <Conversation key={scopeId??'account'} {...{health,trees,selected,scopeId,wholeAccount,changeScope}}/>
}

function Conversation({health,trees,selected,scopeId,wholeAccount,changeScope}:{
  health:Health|null;trees:Tree[];selected:Tree|null;scopeId:number|null;wholeAccount:boolean;changeScope:(value:string)=>void
}){
  const [text,setText]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState('')
  const [exchanges,setExchanges]=useState<ChatExchange[]>([])
  const [hasMore,setHasMore]=useState(false),[loading,setLoading]=useState(true),[loadError,setLoadError]=useState(false)
  const [attempt,setAttempt]=useState(0),[loadingOlder,setLoadingOlder]=useState(false)
  const [pending,setPending]=useState('')
  const canChat=health?.real_llm
  const endRef=useRef<HTMLDivElement>(null)
  const sending=useRef(false)
  const retry=useRef<{message:string;report?:string;language:string;id:string}|null>(null)
  const chat:ChatMessage[]=exchanges.flatMap(row=>[{role:'user',content:row.question},{role:'assistant',content:row.reply}])
  if(pending)chat.push({role:'user',content:pending})
  useEffect(()=>{
    let active=true
    setLoading(true);setLoadError(false)
    api.chatHistory(scopeId).then(page=>{
      if(active){setExchanges(page.exchanges);setHasMore(page.has_more)}
    }).catch(()=>{if(active)setLoadError(true)}).finally(()=>{if(active)setLoading(false)})
    return ()=>{active=false}
  },[scopeId,attempt])
  useEffect(()=>{endRef.current?.scrollIntoView({block:'nearest'})},[exchanges.at(-1)?.id,pending])
  async function older(){
    if(loadingOlder||!exchanges.length)return
    setLoadingOlder(true);setError('')
    try{
      const page=await api.chatHistory(scopeId,exchanges[0].id)
      setExchanges(rows=>[...page.exchanges.filter(row=>!rows.some(old=>old.id===row.id)),...rows])
      setHasMore(page.has_more)
    }catch(err){setError((err as Error).message)}finally{setLoadingOlder(false)}
  }
  const send=async(value?:string,report?:'overview'|'energy'|'maintenance')=>{
    const q=(value??text).trim()
    if(!q||sending.current||loading||loadError||(!report&&!canChat))return
    const language=getLanguage()
    const previous=retry.current
    const id=previous?.message===q&&previous.report===report&&previous.language===language?previous.id:requestId()
    retry.current={message:q,report,language,id}
    sending.current=true;setPending(q);setBusy(true);setError('')
    try{
      const saved=await api.chat(q,scopeId,id,language,report)
      setExchanges(rows=>rows.some(row=>row.id===saved.id)?rows:[...rows,saved])
      if(!report)setText('')
      retry.current=null
      window.dispatchEvent(new CustomEvent('solartree-chat-saved',{detail:scopeId}))
    }catch(err){setError((err as Error).message)}
    finally{sending.current=false;setBusy(false);setPending('')}
  }
  useEffect(()=>{
    const sync=(event:Event)=>{
      if(!sending.current&&(event as CustomEvent).detail===scopeId)setAttempt(n=>n+1)
    }
    window.addEventListener('solartree-chat-saved',sync)
    return ()=>window.removeEventListener('solartree-chat-saved',sync)
  },[scopeId])
  return <div className="page-body assistant-page"><div className="assistant-layout"><Panel className="conversation-panel"><div className="chat-head"><div className="chat-identity"><span className="assistant-avatar"><Sparkles size={23}/></span><div><h3>SolarTree Intelligence</h3><small>{health?.ai_provider==='cloudflare'?'Cloudflare Workers AI':health?.real_llm?tr("Свободен разговор с AI"):tr("Справки от данните в профила")}</small></div></div></div>
    <div className="prompt-chips">{([['overview',tr("Състояние")],['energy',tr("Мощност, вода и кислород")],['maintenance',tr("Сервизни срокове")]] as const).map(([kind,label])=><button key={kind} disabled={busy||loading||loadError} onClick={()=>send(label,kind)}>{label}</button>)}</div>
    <div className="chat-stream">
      {hasMore&&<button className="btn btn-quiet btn-small" disabled={loadingOlder} onClick={older}>{tr("По-стари съобщения")}</button>}
      {loading?<p role="status">{tr("Зареждане на историята…")}</p>:loadError?<div role="alert">{tr("Историята не се зареди.")} <button className="btn btn-outline" onClick={()=>setAttempt(n=>n+1)}>{tr("Опитай отново")}</button></div>:chat.length===0?<div className="chat-intro"><div className="chat-intro-icon"><BrainCircuit size={39} strokeWidth={1.4}/></div><span className="eyebrow">SOLARTREE AI</span><h2>{tr("Как мога да помогна?")}</h2><p>{canChat?tr("Избери справка или задай въпрос за дърветата в профила си."):tr("Избери справка за дърветата в профила си.")}</p></div>:<div className="chat-bubbles">{chat.map((msg,i)=><div key={i} className={`chat-bubble ${msg.role}`}><span className="chat-bubble-avatar">{msg.role==='assistant'?<Sparkles size={15}/>:<UserRound size={15}/>}</span><div style={{whiteSpace:'pre-wrap'}}>{msg.content}</div></div>)}{busy&&<div className="chat-bubble assistant"><span className="chat-bubble-avatar"><Sparkles size={15}/></span><div className="typing"><i/><i/><i/></div></div>}<div ref={endRef}/></div>}</div>{error&&<div className="chat-error"><ErrorText message={error}/></div>}<div className="chat-input-area"><div className="chat-input-box"><textarea aria-label={tr("Съобщение до AI асистента")} value={text} disabled={!canChat||loading||loadError||busy} rows={2} maxLength={1600} placeholder={canChat?tr("Напиши съобщение…"):tr("Облачният чат е недостъпен")} onChange={e=>setText(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}}}/><button type="button" aria-label={tr("Изпрати")} disabled={!canChat||busy||!text.trim()} onClick={()=>send()}><Send size={18}/></button></div><small>{tr("AI предоставя информация и препоръки. Не управлява физически защитни системи.")}</small></div></Panel><div className="assistant-context"><Panel className="context-card"><span className="eyebrow">{tr("КОНТЕКСТ НА РАЗГОВОРА")}</span><h3>{tr("Обхват")}</h3><select aria-label={tr("Обхват на разговора")} value={scopeId??''} onChange={e=>changeScope(e.target.value)}><option value="">{tr("Всички мои дървета")}</option>{trees.map(t=><option value={t.id} key={t.id}>{t.name}</option>)}</select>{wholeAccount?<p>{tr("Дървета в профила:")} {trees.length}</p>:<><div className="context-device"><div className="context-tree-icon"><TreePine size={28}/></div><h4>{selected?.name||tr("Няма дърво")}</h4><span>{selected?.code||'—'}</span></div><div className="context-metric"><span>{tr("Мощност")}</span><strong>{metricText(selected,'power_w',' W')}</strong></div><div className="context-metric"><span>{tr("Вода")}</span><strong>{metricText(selected,'water_pct','%')}</strong></div><div className="context-metric"><span>{tr("Източник")}</span><strong>{selected?.latest?.source==='simulation'&&latestTime(selected)===selected.latest.time?tr("Симулация"):latestTime(selected)?tr("Устройство"):tr("Няма измерване")}</strong></div></>}</Panel><Panel className="context-privacy"><ShieldCheck size={22}/><h3>{tr("Твоите данни остават твои")}</h3><p>{tr("При разговор облачният AI получава въпроса, последните съобщения и данни за избраните дървета. Справките се изготвят на сървъра на SolarTree.")}</p></Panel></div></div></div>
}
