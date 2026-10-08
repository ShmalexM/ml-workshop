// The Markdown subset of assistant answers, parsed into plain data. Markdown.tsx renders the data as React
// elements, so text is never parsed as HTML. Every step reads the text from left to right without
// backtracking, so a hostile or broken answer cannot freeze the tab. This file has no imports, so
// tests/markdown_check.mjs can load it in Node.

export type Inline={t:'text';v:string}|{t:'code';v:string}|{t:'strong'|'em';c:Inline[]}|{t:'link';text:string;href:string;host:string}|{t:'br'}
export type Block={kind:'p'|'h'|'quote';text:string}|{kind:'pre'|'plain';text:string}|{kind:'code';lang:string;text:string;open:boolean}|{kind:'ul'|'ol';items:string[];start:number}|{kind:'hr'}

/** Lines longer than this are shown as plain text, without Markdown. */
export const LONG_LINE=2000

/** Remove a model's <think> section. While it is still open, say so instead of showing it. */
export function withoutThinking(text:string):{text:string;thinking:boolean}{
 const start=text.trimStart()
 if(!start.startsWith('<think>'))return {text,thinking:false}
 const end=start.indexOf('</think>')
 return end<0?{text:'',thinking:true}:{text:start.slice(end+8).trimStart(),thinking:false}
}

const space=(char:string|undefined)=>char===' '||char==='\t'
const fence=/^[ \t]{0,3}(`{3,}|~{3,})[ \t]*([\w+#.-]*)/
const headingStart=/^[ \t]{0,3}#{1,6}[ \t]+/
const bulletStart=/^[ \t]{0,3}[-*+][ \t]+/
const numberStart=/^[ \t]{0,3}(\d{1,4})[.)][ \t]+/
const quoteStart=/^[ \t]{0,3}>[ \t]?/
const listItem=(line:string,ordered:boolean)=>{const m=(ordered?numberStart:bulletStart).exec(line);return m?line.slice(m[0].length):null}

/** Heading text without trailing spaces and a closing run of #. */
function headingText(raw:string){
 let end=raw.length
 while(end>0&&space(raw[end-1]))end--
 let hashes=end
 while(hashes>0&&raw[hashes-1]==='#')hashes--
 if(hashes<end&&(hashes===0||space(raw[hashes-1]))){end=hashes;while(end>0&&space(raw[end-1]))end--}
 return raw.slice(0,end)
}

function isRule(line:string){
 if(!/^[ \t]{0,3}[-*_]/.test(line))return false
 const marks=line.replace(/[ \t]/g,'')
 return marks.length>=3&&(/^-+$/.test(marks)||/^\*+$/.test(marks)||/^_+$/.test(marks))
}

function isTableRow(line:string){const t=line.trim();return t.length>=2&&t[0]==='|'&&t[t.length-1]==='|'}

export function parseBlocks(source:string):Block[]{
 const lines=source.replace(/\r\n?/g,'\n').split('\n');const blocks:Block[]=[];let paragraph:string[]=[]
 const endParagraph=()=>{if(paragraph.length){blocks.push({kind:'p',text:paragraph.join('\n')});paragraph=[]}}
 for(let i=0;i<lines.length;i++){
  const line=lines[i]
  if(line.length>LONG_LINE){endParagraph();blocks.push({kind:'plain',text:line});continue}
  const open=fence.exec(line)
  if(open){
   endParagraph();const marker=open[1][0].repeat(open[1].length);const body:string[]=[];let closed=false
   for(i++;i<lines.length;i++){const t=lines[i].trim();if(t.startsWith(marker)&&t.replace(/[`~]/g,'')===''){closed=true;break}body.push(lines[i])}
   blocks.push({kind:'code',lang:open[2],text:body.join('\n'),open:!closed});continue
  }
  if(!line.trim()){endParagraph();continue}
  const heading=headingStart.exec(line)
  if(heading){endParagraph();blocks.push({kind:'h',text:headingText(line.slice(heading[0].length))});continue}
  if(isRule(line)){endParagraph();blocks.push({kind:'hr'});continue}
  if(quoteStart.test(line)){
   endParagraph();const quote:string[]=[]
   for(;i<lines.length&&lines[i].length<=LONG_LINE&&quoteStart.test(lines[i]);i++)quote.push(lines[i].replace(quoteStart,''))
   i--;blocks.push({kind:'quote',text:quote.join('\n')});continue
  }
  if(isTableRow(line)){
   endParagraph();const rows:string[]=[]
   for(;i<lines.length&&lines[i].length<=LONG_LINE&&isTableRow(lines[i]);i++)rows.push(lines[i].trim())
   i--;blocks.push({kind:'pre',text:rows.join('\n')});continue
  }
  const bullet=listItem(line,false);const numbered=bullet===null?numberStart.exec(line):null
  if((bullet!==null||numbered)&&!paragraph.length){
   const ordered=bullet===null;const items:string[]=[];const start=numbered?Number(numbered[1]):1
   for(;i<lines.length&&lines[i].length<=LONG_LINE;i++){
    const item=listItem(lines[i],ordered)
    if(item!==null){items.push(item);continue}
    // An indented line continues the item above it.
    if(lines[i].trim()&&/^[ \t]{2,}/.test(lines[i])&&!fence.test(lines[i])){items[items.length-1]+='\n'+lines[i].trim();continue}
    break
   }
   i--;blocks.push({kind:ordered?'ol':'ul',items,start});continue
  }
  paragraph.push(line)
 }
 endParagraph()
 return blocks
}

/** Only http and https links work. */
export function safeLink(url:string):URL|null{
 try{const parsed=new URL(url);return parsed.protocol==='https:'||parsed.protocol==='http:'?parsed:null}catch{return null}
}

/** The next index of char at or after `from`. Callers ask with growing `from`, so the text is searched once. */
function finder(text:string,char:string){
 let at=-2
 return (from:number)=>{if(at===-1||at>=from)return at;at=text.indexOf(char,from);return at}
}

/** Inline code, bold, italics and links in one line. Images keep their alt text. Underscores are left alone,
 * so Python names such as __init__ and snake_case stay as written. */
function parseLine(text:string):Inline[]{
 if(text.length>LONG_LINE)return [{t:'text',v:text}]
 const out:Inline[]=[];const tick=finder(text,'`'),star=finder(text,'*'),close=finder(text,']'),paren=finder(text,')')
 let plain=0,i=0
 const emit=(token:Inline,end:number)=>{if(i>plain)out.push({t:'text',v:text.slice(plain,i)});out.push(token);plain=i=end}
 // [label](target): the index after the closing ), with the label and the target, or null.
 const bracket=(at:number,empty:boolean)=>{
  if(!empty&&text[at+1]===']')return null
  const end=close(at+1)
  if(end<0||text[end+1]!=='(')return null
  const last=paren(end+2)
  if(last<0)return null
  const inside=text.slice(end+2,last);const target=inside.split(/\s/,1)[0]
  if(!empty&&!target)return null
  return {label:text.slice(at+1,end),target,next:last+1}
 }
 while(i<text.length){
  const char=text[i]
  if(char==='`'&&text[i+1]!=='`'&&i+1<text.length){
   const end=tick(i+2)
   if(end>0){emit({t:'code',v:text.slice(i+1,end)},end+1);continue}
  }else if(char==='*'){
   if(text[i+1]==='*'&&text[i+2]!=='*'&&i+2<text.length){
    const end=star(i+3)
    if(end>0&&text[end+1]==='*'){emit({t:'strong',c:parseLine(text.slice(i+2,end))},end+2);continue}
   }
   const next=text[i+1]
   if(next!==undefined&&next!=='*'&&!/\s/.test(next)){
    const end=star(i+2)
    if(end>0){emit({t:'em',c:parseLine(text.slice(i+1,end))},end+1);continue}
   }
  }else if(char==='!'&&text[i+1]==='['){
   const image=bracket(i+1,true)
   if(image){emit({t:'text',v:image.label},image.next);continue}
  }else if(char==='['){
   const link=bracket(i,false)
   if(link){
    const url=safeLink(link.target);const label=link.label
    emit(url?{t:'link',text:label,href:url.href,host:url.host}:{t:'text',v:label},link.next);continue
   }
  }
  i++
 }
 if(plain<text.length)out.push({t:'text',v:text.slice(plain)})
 return out
}

/** Inline Markdown for text that may have several lines. Lines are joined with breaks. */
export function parseInline(text:string):Inline[]{
 return text.split('\n').flatMap((line,i)=>i?[{t:'br'} as Inline,...parseLine(line)]:parseLine(line))
}
