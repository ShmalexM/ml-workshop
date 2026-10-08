import {memo,useMemo,useState,type ReactNode} from 'react'
import {Check,Copy} from 'lucide-react'
import {parseBlocks,parseInline,withoutThinking,type Block,type Inline} from './markdownParser'

// Renders the parsed answer (markdownParser.ts) as React elements. Text is never parsed as HTML, so raw HTML in an
// answer stays visible as text. Images are dropped (their alt text stays), and only http and https links work.

type Shown=Exclude<Block,{kind:'p'|'h'|'quote'|'ul'|'ol'}>|{kind:'p'|'h'|'quote';inline:Inline[]}|{kind:'ul'|'ol';items:Inline[][];start:number}

function inline(tokens:Inline[],key:string):ReactNode[]{
 return tokens.map((token,i)=>{
  const k=`${key}-${i}`
  switch(token.t){
   case 'text':return token.v
   case 'br':return <br key={k}/>
   case 'code':return <code key={k}>{token.v}</code>
   case 'strong':return <strong key={k}>{inline(token.c,k)}</strong>
   case 'em':return <em key={k}>{inline(token.c,k)}</em>
   default:return <a key={k} href={token.href} target="_blank" rel="noreferrer noopener">{token.text}<span className="md-host"> ({token.host})</span></a>
  }
 })
}

function CodeBlock({lang,text}:{lang:string;text:string}){
 const [copied,setCopied]=useState(false)
 async function copy(){try{await navigator.clipboard.writeText(text);setCopied(true);setTimeout(()=>setCopied(false),1500)}catch{setCopied(false)}}
 return <div className="md-code"><div className="md-code-bar"><span>{lang||'code'}</span><button type="button" onClick={copy} aria-label={copied?'Copied':'Copy code'}>{copied?<Check size={13}/>:<Copy size={13}/>}{copied?'Copied':'Copy'}</button></div>
  <pre><code>{text}</code></pre></div>
}

function prepare(block:Block):Shown{
 switch(block.kind){
  case 'p':case 'h':case 'quote':return {kind:block.kind,inline:parseInline(block.text)}
  case 'ul':case 'ol':return {kind:block.kind,start:block.start,items:block.items.map(parseInline)}
  default:return block
 }
}

function Markdown({text}:{text:string}){
 // Parsed once per text. A message that did not change keeps its blocks.
 const blocks=useMemo(()=>{const {text:shown,thinking}=withoutThinking(text);return thinking?null:parseBlocks(shown).map(prepare)},[text])
 if(!blocks)return <p className="assistant-thinking">Thinking…</p>
 return <div className="md">{blocks.map((block,i)=>{
  const key='b'+i
  switch(block.kind){
   case 'code':return <CodeBlock key={key} lang={block.lang} text={block.text}/>
   case 'h':return <p key={key} className="md-heading">{inline(block.inline,key)}</p>
   case 'quote':return <blockquote key={key}>{inline(block.inline,key)}</blockquote>
   case 'pre':return <pre key={key} className="md-table">{block.text}</pre>
   case 'plain':return <p key={key} className="md-plain">{block.text}</p>
   case 'hr':return <hr key={key}/>
   case 'ul':return <ul key={key}>{block.items.map((item,j)=><li key={j}>{inline(item,key+'-'+j)}</li>)}</ul>
   case 'ol':return <ol key={key} start={block.start}>{block.items.map((item,j)=><li key={j}>{inline(item,key+'-'+j)}</li>)}</ol>
   default:return <p key={key}>{inline(block.inline,key)}</p>
  }
 })}</div>
}

export default memo(Markdown)
