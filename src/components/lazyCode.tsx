import {Suspense,type ComponentProps} from 'react'
import {preloadable} from '../preloadable'
import type {EditorPrefs} from '../types'
// In the main stylesheet, so the plain fallback below has the same layout as the highlighted view.
import './codeView.css'

// The editor and the highlighted code views use CodeMirror, about 470 kB of script. They load on their own,
// when the Learn page opens, so the other pages never download it.
const Editor=preloadable(()=>import('./CodeEditor'))
const loadView=()=>import('./CodeView')
const Lines=preloadable(()=>loadView().then(module=>({default:module.CodeLines})))
const Diff=preloadable(()=>loadView().then(module=>({default:module.CodeDiff})))

/** Starts loading the editor and code views. The Learn page calls it, so they are ready before a stage needs them. */
export function preloadCode(){Editor.preload();Lines.preload();Diff.preload()}

type EditorProps={code:string;onCode:(s:string)=>void;onRun:(mode:'run'|'check')=>void;busy:boolean;js:boolean;prefs:EditorPrefs;label:string}
/** Until CodeMirror has loaded, an empty box of the same size holds its place. */
export function CodeEditor(props:EditorProps){
 return <Suspense fallback={<div className={props.prefs.dark?'cm-theme':'cm-theme-light'}/>}><Editor {...props}/></Suspense>
}

/** Until the highlighter has loaded, the lines show without colors. */
export function CodeLines(props:ComponentProps<typeof Lines>){
 const lines=props.code.replace(/\r\n?/g,'\n').replace(/\s+$/,'').split('\n')
 const plain=<pre className="code-view" aria-label={props.label}><code>{lines.map((text,i)=><span key={i} className="code-row"><span className="code-num" aria-hidden="true">{i+1}</span><span className="code-text">{text}</span></span>)}</code></pre>
 return <Suspense fallback={plain}><Lines {...props}/></Suspense>
}

export function CodeDiff(props:ComponentProps<typeof Diff>){
 return <Suspense fallback={<pre className="code-view diff-view" aria-busy="true"/>}><Diff {...props}/></Suspense>
}
