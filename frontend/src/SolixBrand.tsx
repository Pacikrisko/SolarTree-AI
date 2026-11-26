import {getLanguage} from './language'

export default function SolixBrand({onHome}:{onHome?:()=>void}){
  return <a className="solix-brand" href="/#/overview"
    aria-label={getLanguage()==='en'?'Solix home':'Solix — начало'}
    onClick={event=>{
      if(!onHome||event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return
      event.preventDefault()
      onHome()
    }}>
    <img className="solix-symbol" src="/solix.svg" alt="" width={44} height={44}/>
    <span>Solix</span>
  </a>
}
