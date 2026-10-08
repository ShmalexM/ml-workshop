import {useState,type ReactNode} from 'react'
import {Check,Copy} from 'lucide-react'

// A small Markdown subset rendered as React elements. Text is never parsed as HTML, so raw HTML in an answer
// stays visible as text. Images are dropped (their alt text stays), and only http and https links work.

type Block={kind:'p'|'h'|'quote'|'pre';text:string}|{kind:'code';lang:string;text:string;open:boolean}|{kind:'ul'|'ol';items:string[];start:number}|{kind:'hr'}

const fence=/^\s{0,3}(```+|~~~+)\s*([\w+#.-]*)/
const bullet=/^\s{0,3}[-*+]\s+(.*)$/
const numbered=/^\s{0,3}(\d{1,4})[.)]\s+(.*)$/

export function parseBlocks(source:string):Block[]{
 const lines=source.replace(/\r\n?/g,'\n').split('\n');const blocks:Block[]=[];let paragraph:string[]=[]
 const endParagraph=()=>{if(paragraph.length){blocks.push({kind:'p',text:paragraph.join('\n')});paragraph=[]}}
 for(let i=0;i<lines.length;i++){
  const line=lines[i];const open=line.match(fence)
  if(open){
   endParagraph();const marker=open[1];const body:string[]=[];let closed=false
   for(i++;i<lines.length;i++){if(lines[i].trim().startsWith(marker[0].repeat(marker.length))&&lines[i].trim().replace(/[`~]/g,'')===''){closed=true;break}body.push(lines[i])}
   blocks.push({kind:'code',lang:open[2],text:body.join('\n'),open:!closed});continue
  }
  if(!line.trim()){endParagraph();continue}
  const heading=line.match(/^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$/)
  if(heading){endParagraph();blocks.push({kind:'h',text:heading[1]});continue}
  if(/^\s{0,3}([-*_])(\s*\1){2,}\s*$/.test(line)){endParagraph();blocks.push({kind:'hr'});continue}
  if(/^\s{0,3}>/.test(line)){
   endParagraph();const quote:string[]=[]
   for(;i<lines.length&&/^\s{0,3}>/.test(lines[i]);i++)quote.push(lines[i].replace(/^\s{0,3}>\s?/,''))
   i--;blocks.push({kind:'quote',text:quote.join('\n')});continue
  }
  if(/^\s*\|.*\|\s*$/.test(line)){
   endParagraph();const rows:string[]=[]
   for(;i<lines.length&&/^\s*\|.*\|\s*$/.test(lines[i]);i++)rows.push(lines[i].trim())
   i--;blocks.push({kind:'pre',text:rows.join('\n')});continue
  }
  const listMatch=line.match(bullet)||line.match(numbered)
  if(listMatch&&!paragraph.length){
   const ordered=!line.match(bullet);const items:string[]=[];const start=ordered?Number(listMatch[1]):1
   for(;i<lines.length;i++){
    const item=ordered?lines[i].match(numbered):lines[i].match(bullet)
    if(item){items.push(ordered?item[2]:item[1]);continue}
    // An indented line continues the item above it.
    if(lines[i].trim()&&/^\s{2,}/.test(lines[i])&&!lines[i].match(fence)){items[items.length-1]+='\n'+lines[i].trim();continue}
    break
   }
   i--;blocks.push({kind:ordered?'ol':'ul',items,start});continue
  }
  paragraph.push(line)
 }
 endParagraph()
 return blocks
}

function safeLink(url:string):URL|null{try{const parsed=new URL(url);return parsed.protocol==='https:'||parsed.protocol==='http:'?parsed:null}catch{return null}}

/** Inline code, bold, italics and links. Everything else is plain text. */
export function inline(text:string,key='i'):ReactNode[]{
 const out:ReactNode[]=[];let rest=text;let n=0
 // Underscores are left alone, so Python names such as __init__ and snake_case stay as written.
 const pattern=/`([^`\n]+)`|\*\*([^*\n]+)\*\*|\*([^*\s][^*\n]*)\*|!\[([^\]\n]*)\]\(([^)\s]*)[^)]*\)|\[([^\]\n]+)\]\(([^)\s]+)[^)]*\)/
 while(rest){
  const m=rest.match(pattern)
  if(!m||m.index===undefined){out.push(rest);break}
  if(m.index>0)out.push(rest.slice(0,m.index))
  const k=`${key}-${n++}`
  if(m[1]!==undefined)out.push(<code key={k}>{m[1]}</code>)
  else if(m[2]!==undefined)out.push(<strong key={k}>{inline(m[2],k)}</strong>)
  else if(m[3]!==undefined)out.push(<em key={k}>{inline(m[3],k)}</em>)
  else if(m[4]!==undefined)out.push(m[4])
  else{
   const url=safeLink(m[7])
   out.push(url?<a key={k} href={url.href} target="_blank" rel="noreferrer noopener">{m[6]}<span className="md-host"> ({url.host})</span></a>:m[6])
  }
  rest=rest.slice(m.index+m[0].length)
 }
 return out
}

function lines(text:string,key:string){return text.split('\n').flatMap((line,i)=>i?[<br key={key+'b'+i}/>,...inline(line,key+i)]:inline(line,key+i))}

function CodeBlock({lang,text}:{lang:string;text:string}){
 const [copied,setCopied]=useState(false)
 async function copy(){try{await navigator.clipboard.writeText(text);setCopied(true);setTimeout(()=>setCopied(false),1500)}catch{setCopied(false)}}
 return <div className="md-code"><div className="md-code-bar"><span>{lang||'code'}</span><button type="button" onClick={copy} aria-label={copied?'Copied':'Copy code'}>{copied?<Check size={13}/>:<Copy size={13}/>}{copied?'Copied':'Copy'}</button></div><pre><code>{text}</code></pre></div>
}

/** Remove a model's <think> section. While it is still open, say so instead of showing it. */
export function withoutThinking(text:string){
 const stripped=text.replace(/^\s*<think>[\s\S]*?<\/think>\s*/,'')
 return /^\s*<think>/.test(stripped)?{text:'',thinking:true}:{text:stripped,thinking:false}
}

export default function Markdown({text}:{text:string}){
 const {text:shown,thinking}=withoutThinking(text)
 if(thinking)return <p className="assistant-thinking">Thinking…</p>
 return <div className="md">{parseBlocks(shown).map((block,i)=>{
  const key='b'+i
  switch(block.kind){
   case 'code':return <CodeBlock key={key} lang={block.lang} text={block.text}/>
   case 'h':return <p key={key} className="md-heading">{inline(block.text,key)}</p>
   case 'quote':return <blockquote key={key}>{lines(block.text,key)}</blockquote>
   case 'pre':return <pre key={key} className="md-table">{block.text}</pre>
   case 'hr':return <hr key={key}/>
   case 'ul':return <ul key={key}>{block.items.map((item,j)=><li key={j}>{lines(item,key+'-'+j)}</li>)}</ul>
   case 'ol':return <ol key={key} start={block.start}>{block.items.map((item,j)=><li key={j}>{lines(item,key+'-'+j)}</li>)}</ol>
   default:return <p key={key}>{lines(block.text,key)}</p>
  }
 })}</div>
}
