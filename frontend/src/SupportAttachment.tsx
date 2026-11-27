import {useEffect,useRef,useState} from 'react'
import {FileText, FileSpreadsheet, FileArchive, File, Image as ImageIcon, Download, Paperclip, X} from 'lucide-react'
import {getLanguage} from './language'
import './support-attachments.css'

const label=(bg:string,en:string)=>getLanguage()==='en'?en:bg

function fileIcon(ext:string){
  if(['jpg','jpeg','png','webp','avif','gif','bmp'].includes(ext))return ImageIcon
  if(['xls','xlsx','csv','ods'].includes(ext))return FileSpreadsheet
  if(['zip','rar','7z','gz'].includes(ext))return FileArchive
  return ['pdf','txt','doc','docx'].includes(ext)?FileText:File
}

export function InquiryAttachment(){
  const [names,setNames]=useState<string[]>([])
  const input=useRef<HTMLInputElement>(null)
  useEffect(()=>{
    const form=input.current?.form
    const reset=()=>setNames([])
    form?.addEventListener('reset',reset)
    return ()=>form?.removeEventListener('reset',reset)
  },[])
  return <div><label className="inquiry-upload"><Paperclip size={20}/><span><strong>{label('Избери файлове или снимки','Choose files or photos')}</strong><small>{label('До 5 MB общо','Up to 5 MB total')}</small></span><input type="file" multiple name="file" ref={input} onChange={ev=>setNames(Array.from(ev.target.files??[],f=>f.name))}/></label>
    {names.map((name,i)=>{
      const ext=name.split('.').pop()?.toLowerCase()||''
      const Icon=fileIcon(ext)
      return <div className="selected-support-file" key={i}><Icon size={20}/><span>{name}</span></div>
    })}</div>

}

async function fileBlob(ticket:number,message:number,signal?:AbortSignal){
  const res=await fetch('/api/support/'+ticket+'/files/'+message,{signal,headers:{Authorization:'Bearer '+localStorage.getItem('solartree_token')}})
  if(!res.ok)throw Error(label('Файлът е недостъпен.','File unavailable.'))
  return res.blob()
}

export function AttachmentCard({ticket,message,name}:{ticket:number;message:number;name:string}){
  const ext=name.includes('.')?name.split('.').pop()!.toLowerCase():''
  const mime:Record<string,string>={jpg:'image/jpeg',jpeg:'image/jpeg',png:'image/png',gif:'image/gif',webp:'image/webp',avif:'image/avif',bmp:'image/bmp'}
  const type=Object.hasOwn(mime,ext)?mime[ext]:null
  const [src,setSrc]=useState(''),[error,setError]=useState('')
  const dialog=useRef<HTMLDialogElement>(null)
  useEffect(()=>{
    if(!type)return
    const controller=new AbortController()
    let url=''
    fileBlob(ticket,message,controller.signal).then(blob=>{
      if(controller.signal.aborted)return
      url=URL.createObjectURL(blob.slice(0,blob.size,type))
      setSrc(url)
    }).catch(()=>{})
    return ()=>{controller.abort();if(url)URL.revokeObjectURL(url)}
  },[ticket,message,type])
  async function save(){
    try{
      setError('')
      const url=src||URL.createObjectURL(await fileBlob(ticket,message))
      const link=document.createElement('a');link.href=url;link.download=name;link.click()
      if(!src)setTimeout(()=>URL.revokeObjectURL(url),30000)
    }catch(e){setError((e as Error).message)}
  }
  const sheet=['xls','xlsx','csv','ods'].includes(ext),archive=['zip','rar','7z','gz'].includes(ext)
  const Icon=fileIcon(ext)
  return <div className="support-attachment">
    {src&&<button className="attachment-preview" onClick={()=>dialog.current?.showModal()} aria-label={label('Отвори снимката','Open image')+' '+name}><img alt={name} src={src} onError={()=>setSrc('')}/></button>}
    <button className="attachment-document" onClick={save} aria-label={label('Изтегли','Download')+' '+name}><span data-kind={ext==='pdf'?'pdf':sheet?'sheet':archive?'archive':'file'}><Icon size={23}/></span><strong>{name}<small>{ext.toUpperCase().slice(0,10)||label('Файл','File')}</small></strong><Download size={16}/></button>
    {error&&<small role="alert">{error}</small>}
    {src&&<dialog ref={dialog} className="attachment-dialog" aria-label={name} onClick={ev=>{if(ev.target===dialog.current)dialog.current.close()}}><header><strong>{name}</strong><button autoFocus onClick={()=>dialog.current?.close()} aria-label={label('Затвори','Close')}><X/></button></header><img src={src} alt={name}/></dialog>}
  </div>
}

