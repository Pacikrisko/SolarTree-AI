import {useSyncExternalStore} from 'react'
import type {Page} from './types'

const pages:Record<Page,true> = {
  overview:true, trees:true, detail:true, insights:true, assistant:true,
  service:true, settings:true, profile:true, admin:true,
}
function subscribe(update:()=>void){
  window.addEventListener('hashchange',update)
  window.addEventListener('popstate',update)
  window.addEventListener('solartree-navigation',update)
  return ()=>{
    window.removeEventListener('hashchange',update)
    window.removeEventListener('popstate',update)
    window.removeEventListener('solartree-navigation',update)
  }
}
export function parseWorkspaceRoute(hash:string){
  const match=/^#\/([a-z]+)(?:\/([1-9]\d*))?$/.exec(hash)
  const page:Page=match && Object.prototype.hasOwnProperty.call(pages,match[1]) ? match[1] as Page : 'overview'
  const id=Number(match?.[2])
  return {page,treeId:Number.isSafeInteger(id)&&id>0?id:null}
}
export function useWorkspaceRoute(){
  return parseWorkspaceRoute(useSyncExternalStore(subscribe,()=>window.location.hash))
}
export function goToSection(page:Page,id:number|null,replace=false){
  const url=new URL(window.location.href)
  url.hash='/'+page+(id===null?'':'/'+id)
  if(url.href===window.location.href)return
  if(replace) window.history.replaceState(null,'',url)
  else window.history.pushState(null,'',url)
  window.dispatchEvent(new Event('solartree-navigation'))
}
