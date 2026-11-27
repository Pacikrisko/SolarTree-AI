import {tr} from './language'
import { useEffect, useRef, useState } from 'react'
import { Camera, CameraOff, ImagePlus, ScanLine } from 'lucide-react'

import jsQR from 'jsqr'

function decode(canvas:HTMLCanvasElement, source:CanvasImageSource, width:number, height:number){
  const scale=Math.min(1,1600/Math.max(width,height))
  canvas.width=Math.max(1,Math.round(width*scale))
  canvas.height=Math.max(1,Math.round(height*scale))
  const ctx=canvas.getContext('2d',{willReadFrequently:true})
  if(!ctx)throw new Error('Canvas unavailable')
  ctx.drawImage(source,0,0,canvas.width,canvas.height)
  const pixels=ctx.getImageData(0,0,canvas.width,canvas.height)
  return jsQR(pixels.data,pixels.width,pixels.height)?.data
}

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
  if(!/^[A-Za-z0-9-]{3,40}$/.test(code)||claim_token.length<12||claim_token.length>200)throw new Error(tr("QR кодът не е за сдвояване със Solix."))
  return {code:code.toUpperCase(),claim_token}
}

export default function PairQrScanner({onRead}:{onRead:(code:string,claim_token:string)=>void}){
  const video=useRef<HTMLVideoElement|null>(null)
  const stream=useRef<MediaStream|null>(null)
  const timer=useRef<number|undefined>(undefined)
  const generation=useRef(0)
  const [active,setActive]=useState(false)
  const [error,setError]=useState('')
  function release(){
    generation.current++
    window.clearTimeout(timer.current)
    stream.current?.getTracks().forEach(track=>track.stop())
    stream.current=null
    if(video.current)video.current.srcObject=null
  }
  function stop(){release();setActive(false)}
  useEffect(()=>{
    window.addEventListener('pagehide',stop)
    return ()=>{window.removeEventListener('pagehide',stop);release()}
  },[])
  function handleScan(raw:string){
    try{
      const found=readPairingCode(raw)
      stop()
      setError('')
      onRead(found.code,found.claim_token)
      return true
    }catch(e){setError((e as Error).message);return false}
  }
  async function start(){
    release()
    const session=generation.current
    setError('')
    if(!navigator.mediaDevices?.getUserMedia){setError(tr("Камерата е достъпна само през localhost или защитена HTTPS връзка."));return}
    setActive(true)
    try{
      const media=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'}},audio:false})
      const preview=video.current
      if(session!==generation.current||!preview){media.getTracks().forEach(track=>track.stop());return}
      stream.current=media
      preview.srcObject=media
      await preview.play()
      const canvas=document.createElement('canvas')
      function tick(){
        if(session!==generation.current)return
        if(preview && preview.readyState>=2 && preview.videoWidth && preview.videoHeight){
          const raw=decode(canvas,preview,preview.videoWidth,preview.videoHeight)
          if(raw && handleScan(raw))return
        }
        timer.current=window.setTimeout(tick,150)
      }
      tick()
    }catch{
      if(session!==generation.current)return
      stop()
      setError(tr("Не може да се отвори камерата. Разреши достъпа или използвай ръчно въвеждане."))
    }
  }
  async function fromImage(file:File|undefined){
    if(!file)return
    stop()
    const session=generation.current
    const url=URL.createObjectURL(file)
    try{
      const image=new Image()
      image.src=url
      await image.decode()
      if(session!==generation.current)return
      const raw=decode(document.createElement('canvas'),image,image.naturalWidth,image.naturalHeight)
      if(raw)handleScan(raw)
      else setError(tr("Не е намерен QR код в изображението."))
    }catch{if(session===generation.current)setError(tr("Неуспешно разчитане на изображението."))}
    finally{URL.revokeObjectURL(url)}
  }
  return <div className="pair-scanner">
    <div className="pair-scan-heading"><ScanLine size={18}/><strong>{tr("Сдвояване с QR код")}</strong></div>
    <p>{tr("Сканирай регистрационния QR код, предоставен с устройството. Системата разпознава модела автоматично.")}</p>
    <video ref={video} muted playsInline className={`pair-video ${active?'active':''}`}/>
    <div className="pair-scan-actions">
      <button type="button" className="btn btn-primary" onClick={active?stop:start}>{active?<><CameraOff size={16}/> {tr("Спри камерата")}</>:<><Camera size={16}/> {tr("Сканирай с камера")}</>}</button>
      <label className="btn btn-quiet pair-file"><ImagePlus size={16}/> {tr("QR от снимка")}<input aria-label={tr("Снимка на QR код")} type="file" accept="image/*" onChange={e=>{void fromImage(e.target.files?.[0]);e.target.value=''}}/></label>
    </div>
    {error&&<div role="alert" className="pair-scan-error">{tr(error)}</div>}
  </div>
}
