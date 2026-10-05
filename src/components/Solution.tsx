import {useEffect,useRef} from 'react'
import {CheckCircle2,X} from 'lucide-react'
import type {Lesson} from '../types'
export default function Solution({lesson,code,onClose,onLoad}:{lesson:Lesson;code:string;onClose:()=>void;onLoad:()=>void}){
 const dialog=useRef<HTMLDialogElement>(null)
 useEffect(()=>{dialog.current?.showModal()},[])
 return <dialog ref={dialog} className="solution-dialog" aria-label="Worked solution" onCancel={onClose} onClick={e=>{if(e.target===e.currentTarget)onClose()}}><div className="dialog-header"><h2>Solution</h2><button className="icon-button" aria-label="Close solution" onClick={onClose}><X size={20}/></button></div><h3>{lesson.title}</h3><p className="answer-explanation">{lesson.explanation}</p><pre>{code}</pre><div className="answer-checks"><h3>Checks this solution passes</h3><ul>{lesson.checkLabels.map(label=><li key={label}>{label}</li>)}</ul></div><p className="answer-load-note">Load into editor replaces your code. Only viewing the solution changes nothing.</p><div className="button-row"><button className="secondary-button" onClick={onClose}>Back to lesson</button><button className="primary-button" onClick={onLoad}><CheckCircle2 size={16}/>Load into editor</button></div></dialog>
}
