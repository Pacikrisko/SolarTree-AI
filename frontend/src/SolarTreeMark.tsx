export default function SolarTreeMark({size=28}:{size?:number}){
  return <svg width={size} height={size} viewBox="0 0 48 48" fill="none" role="img" aria-label="SolarTree" xmlns="http://www.w3.org/2000/svg">
    <path d="M24 42V18M24 28 12 20M24 24l12-9" stroke="currentColor" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round"/>
    <rect x="6" y="9" width="19" height="10" rx="2" transform="rotate(24 6 9)" fill="currentColor" fillOpacity=".9"/>
    <path d="m11 11 6 10M18 13l5 9" stroke="var(--surface,#142122)" strokeWidth=".9"/>
    <rect x="27" y="8" width="16" height="9" rx="1.8" transform="rotate(-23 27 8)" fill="currentColor" fillOpacity=".85"/>
    <circle cx="24" cy="13" r="3.4" fill="currentColor"/>
    <path d="M13 44h22" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"/>
  </svg>
}
