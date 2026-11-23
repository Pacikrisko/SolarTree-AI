import {tr} from './language'
import { useEffect, useRef, useState } from 'react'
import { Camera, CameraOff, ImagePlus, ScanLine } from 'lucide-react'

type QRDetector={detect:(source:HTMLVideoElement|ImageBitmap)=>Promise<Array<{rawValue:string}>>}
type BarcodeDetectorClass=new (settings:{formats:string[]})=>QRDetector

export function readPairingCode(raw:string):{code:string;claim_token:string}{
  const value=raw.trim()
  let code='', claim_token=''
  if(value.startsWith('STREE1|')){
    const parts=value.split('|')
    if(parts.length===3){code=parts[1];claim_token=parts[2]}
  }else{
    try{
      const url=new URL(value)
      if(url.protocol==='solartree:' || (url.protocol==='https:' && url.pathname.endsWith('/pair'))){
        code=url.searchParams.get('device')||''
        claim_token=url.searchParams.get('claim')||''
      }
    }catch{ /* Unrecognized QR content */ }
  }
  if(!/^[A-Za-z0-9-]{3,40}$/.test(code)||claim_token.length<12||claim_token.length>200)throw new Error(tr("QR кодът не е за сдвояване със SolarTree."))
  return {code:code.toUpperCase(),claim_token}
}

export default function PairQrScanner({onRead}:{onRead:(code:string,claim_token:string)=>void}){
  const video=useRef<HTMLVideoElement|null>(null)
  const stream=useRef<MediaStream|null>(null)
  const frame=useRef<number|null>(null)
  const [active,setActive]=useState(false)
  const [error,setError]=useState('')
  const [available]=useState(()=>!!((window as unknown as {BarcodeDetector?:BarcodeDetectorClass}).BarcodeDetector))
  function stop(){
    if(frame.current!==null){cancelAnimationFrame(frame.current);frame.current=null}
    stream.current?.getTracks().forEach(t=>t.stop());stream.current=null
    if(video.current)video.current.srcObject=null
    setActive(false)
  }
  useEffect(()=>()=>{if(frame.current!==null)cancelAnimationFrame(frame.current);stream.current?.getTracks().forEach(t=>t.stop())},[])
  function handleScan(raw:string):boolean{
    try {const found=readPairingCode(raw);stop();setError('');onRead(found.code,found.claim_token);return true}
    catch(e){setError((e as Error).message);return false}
  }
  async function start(){
    setError('')
    if(!available){setError(tr("Този браузър не поддържа QR сканиране. Използвай Chrome/Edge или въведи кода ръчно."));return}
    if(!navigator.mediaDevices?.getUserMedia){setError(tr("Камерата е достъпна само през localhost или защитена HTTPS връзка."));return}
    try{
      const media=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'}},audio:false})
      stream.current=media
      if(!video.current){media.getTracks().forEach(t=>t.stop());return}
      video.current.srcObject=media
      await video.current.play()
      setActive(true)
      const Detect=(window as unknown as {BarcodeDetector:BarcodeDetectorClass}).BarcodeDetector
      const detector=new Detect({formats:['qr_code']})
      let busy=false
      const tick=async()=>{
        if(!stream.current)return
        if(!busy && video.current?.readyState===4){
          busy=true
          try{const codes=await detector.detect(video.current)
            if(codes[0]?.rawValue && handleScan(codes[0].rawValue)){busy=false;return}
          }catch{ /* camera frame may be unavailable during initialization */ }
          busy=false
        }
        frame.current=requestAnimationFrame(tick)
      }
      frame.current=requestAnimationFrame(tick)
    }catch{setError(tr("Не може да се отвори камерата. Разреши достъпа или използвай ръчно въвеждане."));stop()}
  }
  async function fromImage(file:File|undefined){
    if(!file)return
    if(!available){setError(tr("Браузърът не поддържа разчитане на QR изображения."));return}
    let bitmap:ImageBitmap|null=null
    try{
      bitmap=await createImageBitmap(file)
      const Detect=(window as unknown as {BarcodeDetector:BarcodeDetectorClass}).BarcodeDetector
      const codes=await new Detect({formats:['qr_code']}).detect(bitmap)
      if(!codes.length){setError(tr("Не е намерен QR код в изображението."));return}
      handleScan(codes[0].rawValue)
    }catch{setError(tr("Неуспешно разчитане на изображението."))}finally{bitmap?.close()}
  }
  return <div className="pair-scanner">
    <div className="pair-scan-heading"><ScanLine size={18}/><strong>{tr("Сдвояване с QR код")}</strong></div>
    <p>{tr("Сканирай регистрационния QR код, предоставен с устройството. Системата разпознава модела автоматично.")}</p>
    <video ref={video} muted playsInline className={`pair-video ${active?'active':''}`}/>
    <div className="pair-scan-actions">
      <button type="button" className="btn btn-outline" onClick={active?stop:start}>{active?<><CameraOff size={16}/> {tr("Спри камерата")}</>:<><Camera size={16}/> {tr("Сканирай с камера")}</>}</button>
      <label className="btn btn-quiet pair-file"><ImagePlus size={16}/> {tr("QR от снимка")}<input aria-label={tr("Снимка на QR код")} type="file" accept="image/*" onChange={e=>{void fromImage(e.target.files?.[0]);e.target.value=''}}/></label>
    </div>
    {error&&<div role="alert" className="pair-scan-error">{tr(error)}</div>}
  </div>
}
