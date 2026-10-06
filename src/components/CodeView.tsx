// Line-numbered code and line diff adapted from beautiful-ui CodeBlock (github.com/slev12397/beautiful-ui), MIT License, Copyright (c) 2026 Shane Levine.
import {useMemo} from 'react'
import {highlightCode,tagHighlighter,tags as t} from '@lezer/highlight'
import {pythonLanguage} from '@codemirror/lang-python'
import './codeView.css'

type Token={text:string;cls:string}
type Row={kind:'same'|'add'|'del';tokens:Token[];old?:number;cur?:number}

// The same Python parser the editor uses; JavaScript stays plain text.
const highlighter=tagHighlighter([
 {tag:t.keyword,class:'hl-keyword'},
 {tag:[t.string,t.escape],class:'hl-string'},
 {tag:[t.number,t.bool,t.null],class:'hl-number'},
 {tag:t.comment,class:'hl-comment'},
 {tag:[t.function(t.variableName),t.function(t.propertyName)],class:'hl-function'},
 {tag:t.className,class:'hl-type'},
])

const clean=(code:string)=>code.replace(/\r\n?/g,'\n').replace(/\s+$/,'')

function highlightLines(code:string,python:boolean):Token[][]{
 if(!python)return code.split('\n').map(text=>[{text,cls:''}])
 const lines:Token[][]=[[]]
 highlightCode(code,pythonLanguage.parser.parse(code),highlighter,(text,cls)=>{lines[lines.length-1].push({text,cls})},()=>{lines.push([])})
 return lines
}

/** Longest common subsequence over lines; trailing spaces do not count as a change. */
function lineDiff(before:Token[][],after:Token[][]):Row[]{
 const key=(line:Token[])=>line.map(token=>token.text).join('').trimEnd()
 const a=before.map(key),b=after.map(key),n=a.length,m=b.length
 const lcs=Array.from({length:n+1},()=>new Array<number>(m+1).fill(0))
 for(let i=n-1;i>=0;i--)for(let j=m-1;j>=0;j--)lcs[i][j]=a[i]===b[j]?lcs[i+1][j+1]+1:Math.max(lcs[i+1][j],lcs[i][j+1])
 const rows:Row[]=[];let i=0,j=0
 while(i<n||j<m){
  if(i<n&&j<m&&a[i]===b[j]){rows.push({kind:'same',tokens:after[j],old:i+1,cur:j+1});i++;j++}
  else if(i<n&&(j===m||lcs[i+1][j]>=lcs[i][j+1])){rows.push({kind:'del',tokens:before[i],old:i+1});i++}
  else{rows.push({kind:'add',tokens:after[j],cur:j+1});j++}
 }
 return rows
}

const Text=({tokens}:{tokens:Token[]})=><span className="code-text">{tokens.map((token,i)=><span key={i} className={token.cls||undefined}>{token.text}</span>)}</span>

export function CodeLines({code,python,label}:{code:string;python:boolean;label:string}){
 const lines=useMemo(()=>highlightLines(clean(code),python),[code,python])
 return <pre className="code-view" aria-label={label}><code>{lines.map((tokens,i)=><span key={i} className="code-row"><span className="code-num" aria-hidden="true">{i+1}</span><Text tokens={tokens}/></span>)}</code></pre>
}

/** Unified diff from the learner's code to the solution, marked with − and + as well as color. */
export function CodeDiff({mine,solution,python}:{mine:string;solution:string;python:boolean}){
 const rows=useMemo(()=>lineDiff(highlightLines(clean(mine),python),highlightLines(clean(solution),python)),[mine,solution,python])
 const removed=rows.filter(r=>r.kind==='del').length,added=rows.filter(r=>r.kind==='add').length
 return <>
  <div className="diff-legend">{added+removed===0?'Your code matches the solution':<><span><b className="diff-del">−</b>Only in your code ({removed})</span><span><b className="diff-add">+</b>Only in the solution ({added})</span></>}</div>
  <pre className="code-view diff-view" aria-label="Your code compared with the solution"><code>{rows.map((row,i)=><span key={i} className={'code-row '+row.kind}><span className="code-num" aria-hidden="true">{row.old??''}</span><span className="code-num" aria-hidden="true">{row.cur??''}</span><span className="diff-mark">{row.kind==='add'?'+':row.kind==='del'?'−':' '}</span><Text tokens={row.tokens}/></span>)}</code></pre>
 </>
}
