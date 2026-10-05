import {useEffect,useRef} from 'react'
import {CheckCircle2,X} from 'lucide-react'
export default function Solution({code,onClose,onLoad}:{code:string;onClose:()=>void;onLoad:()=>void}){
 const dialog=useRef<HTMLDialogElement>(null)
 useEffect(()=>{dialog.current?.showModal()},[])
 return <dialog ref={dialog} className="solution-dialog" aria-label="Worked solution" onCancel={onClose} onClick={e=>{if(e.target===e.currentTarget)onClose()}}><div className="dialog-header"><h2>A worked solution</h2><button className="icon-button" aria-label="Close solution" onClick={onClose}><X size={20}/></button></div><p>Read it, explain why it works, then try writing it from memory.</p><pre>{code}</pre><div className="button-row"><button className="secondary-button" onClick={onClose}>Back to my code</button><button className="primary-button" onClick={onLoad}><CheckCircle2 size={16}/>Load into editor</button></div></dialog>
}
