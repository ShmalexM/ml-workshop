import {useRef,type KeyboardEvent} from 'react'
const MIN=28,MAX=62
export const DEFAULT_READER_WIDTH=40
export function clampReaderWidth(value:number){return Number.isFinite(value)&&value>0?Math.min(MAX,Math.max(MIN,Math.round(value))):DEFAULT_READER_WIDTH}
/** The line between the lesson text and the editor. Drag it, or focus it and use the arrow keys, to change the lesson text's share of the width. */
export default function PanelDivider({value,onChange}:{value:number;onChange:(value:number,done:boolean)=>void}){
 const line=useRef<HTMLDivElement>(null);const dragging=useRef(false)
 const at=(x:number)=>{const box=line.current?.parentElement?.getBoundingClientRect();return box?clampReaderWidth((x-box.left)/box.width*100):value}
 function key(e:KeyboardEvent){const next=e.key==='ArrowLeft'?value-2:e.key==='ArrowRight'?value+2:e.key==='Home'?MIN:e.key==='End'?MAX:null;if(next===null)return;e.preventDefault();onChange(clampReaderWidth(next),true)}
 return <div ref={line} className="panel-divider" role="separator" tabIndex={0} aria-orientation="vertical" aria-label="Width of the lesson text" aria-valuemin={MIN} aria-valuemax={MAX} aria-valuenow={value} aria-valuetext={`${value}%`} title="Drag to resize. Double-click to reset."
  onPointerDown={e=>{dragging.current=true;e.currentTarget.setPointerCapture(e.pointerId);e.preventDefault()}}
  onPointerMove={e=>{if(dragging.current)onChange(at(e.clientX),false)}}
  onPointerUp={e=>{if(!dragging.current)return;dragging.current=false;onChange(at(e.clientX),true)}}
  onPointerCancel={()=>{dragging.current=false}}
  onDoubleClick={()=>onChange(DEFAULT_READER_WIDTH,true)} onKeyDown={key}/>
}
