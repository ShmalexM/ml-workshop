import {useMemo,useRef} from 'react'
import CodeMirror,{keymap,Prec} from '@uiw/react-codemirror'
import {python} from '@codemirror/lang-python'
import {oneDark} from '@codemirror/theme-one-dark'
import type {EditorPrefs} from '../types'

/** The exercise editor. Workspace loads it through lazyCode.tsx, so pages without an editor do not load CodeMirror. */
export default function CodeEditor({code,onCode,onRun,busy,js,prefs,label}:{code:string;onCode:(s:string)=>void;onRun:(mode:'run'|'check')=>void;busy:boolean;js:boolean;prefs:EditorPrefs;label:string}){
 const run=useRef(onRun);run.current=onRun;const idle=useRef(!busy);idle.current=!busy
 // In the editor, the shortcut must come before CodeMirror's own Mod-Enter, which inserts a blank line.
 const extensions=useMemo(()=>{const shortcut=(mode:'run'|'check')=>()=>{if(idle.current)run.current(mode);return true};return [...(js?[]:[python()]),Prec.highest(keymap.of([{key:'Mod-Enter',run:shortcut('run')},{key:'Shift-Mod-Enter',run:shortcut('check')}]))]},[js])
 return <CodeMirror value={code} height="100%" extensions={extensions} theme={prefs.dark?oneDark:'light'} onChange={onCode} editable={!busy} basicSetup={{lineNumbers:true,foldGutter:false,highlightActiveLine:true,autocompletion:prefs.suggestions}} aria-label={label}/>
}
