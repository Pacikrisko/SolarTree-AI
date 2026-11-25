import {TreePine, type LucideIcon} from 'lucide-react'
import type {ReactNode} from 'react'

export default function Empty({icon:Icon=TreePine,title,desc,action}:{icon?:LucideIcon;title:string;desc:string;action?:ReactNode}){return <div className="empty-state"><div className="empty-icon"><Icon size={26}/></div><h3>{title}</h3><p>{desc}</p>{action}</div>}
