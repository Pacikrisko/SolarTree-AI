import {useEffect,useRef} from 'react'

export function usePullRefresh(page:string){
  const ref=useRef<HTMLDivElement>(null)
  useEffect(()=>{
    const el=ref.current
    if(!el||!matchMedia('(pointer: coarse)').matches)return
    let start:Touch|null=null,ready=false
    function reset(){start=null;ready=false;el?.removeAttribute('data-pull')}
    function begin(e:TouchEvent){
      reset()
      if(!el||el.scrollTop>0||e.touches.length!==1)return
      const target=e.target as Element
      if(target.closest('input,textarea,select,button,a,svg,[role=log]'))return
      for(let n=target;n&&n!==el;n=n.parentElement!)if(n.scrollHeight>n.clientHeight+1&&/auto|scroll/.test(getComputedStyle(n).overflowY))return
      start=e.touches[0]
    }
    function move(e:TouchEvent){
      if(!el||!start)return
      const dy=e.touches[0].clientY-start.clientY
      if(e.touches.length!==1||dy<0||Math.abs(e.touches[0].clientX-start.clientX)>dy||el.scrollTop>0){reset();return}
      if(dy>12&&e.cancelable)e.preventDefault()
      ready=dy>=90
      if(dy>20)el.dataset.pull=ready?'↻':'↓'
    }
    function end(){const reload=ready;reset();if(reload)location.reload()}
    el.addEventListener('touchstart',begin,{passive:true});el.addEventListener('touchmove',move,{passive:false})
    el.addEventListener('touchend',end);el.addEventListener('touchcancel',reset)
    return ()=>{el.removeEventListener('touchstart',begin);el.removeEventListener('touchmove',move);el.removeEventListener('touchend',end);el.removeEventListener('touchcancel',reset)}
  },[page,ref.current])
  return ref
}
