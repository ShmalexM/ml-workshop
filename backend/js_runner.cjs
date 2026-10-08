// Trusted learner JavaScript. A fresh Node process runs each exercise.
const fs = require('node:fs');
const vm = require('node:vm');
const {inspect,isDeepStrictEqual} = require('node:util');
const LEARNER_FILE='exercise.js';
const MISMATCH='The result did not match this requirement. Try a hint or inspect your output.';
const RETURNED_UNDEFINED='Your function returned undefined. `console.log` shows a value but does not return it. Use `return`.';
const IS_UNDEFINED='This value is undefined. Set it to the value that the task asks for.';
const request=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const result={error:null,summary:null,checks:[],passed:false};
// Values a simple check compared, so a failure can show them.
let values={};
const context=vm.createContext({console,require,process,Buffer,setTimeout,clearTimeout});
// Checks receive their helpers as parameters, so learner code that declares equal cannot change them.
const HELPERS='__workshopCheckHelpers';
Object.defineProperty(context,HELPERS,{value:Object.freeze({
  equal:(a,b)=>{values={got:a,expected:b};return isDeepStrictEqual(JSON.parse(JSON.stringify(a)),JSON.parse(JSON.stringify(b)))},
  value:(key,value)=>{values[key]=value;return value}})});
const withHelpers=code=>`((equal,_workshopValue)=>(${code}))(${HELPERS}.equal,${HELPERS}.value)`;

const shown=value=>{const text=inspect(value,{depth:4,breakLength:Infinity});return text.length>200?text.slice(0,199)+'…':text};
// Keep the message and the learner's frames; drop runner and Node internals, which include install paths.
const learnerStack=e=>typeof e?.stack==='string'?e.stack.split('\n').filter(l=>!/^\s+at /.test(l)||l.includes(LEARNER_FILE)).join('\n'):String(e);
const errorLine=e=>{const line=typeof e?.stack==='string'&&e.stack.match(/exercise\.js:(\d+)/);return (line?`Line ${line[1]}: `:'')+String(e).split('\n')[0]};

// Characters outside brackets and strings; everything nested becomes a space. Null when unsure.
function topLevel(source){
  if(/[`/]/.test(source))return null;
  let depth=0,quote=null,out='';
  for(let i=0;i<source.length;i++){
    const ch=source[i];
    if(quote){if(ch==='\\'){out+='  ';i++}else{if(ch===quote)quote=null;out+=' '}continue}
    if(ch==='"'||ch==="'"){quote=ch;out+=' ';continue}
    if('([{'.includes(ch)){out+=depth++===0?ch:' ';continue}
    if(')]}'.includes(ch)){if(--depth<0)return null;out+=depth===0?ch:' ';continue}
    out+=depth===0?ch:' ';
  }
  return depth===0&&!quote?out:null;
}

// A check that is one `a === b` or one `equal(a, b)`: return its call text and the code to run.
function comparison(expr){
  const source=expr.trim(),top=topLevel(source);
  if(!top||source.startsWith('{'))return null;
  if(/^equal\(\s*\)$/.test(top)){
    const inner=source.slice(6,-1),commas=[...(topLevel(inner)||'')].flatMap((ch,i)=>ch===','?[i]:[]);
    return commas.length===1?{call:inner.slice(0,commas[0]).trim(),code:source}:null;
  }
  const at=top.indexOf('===');
  if(at<0||/[=&|?,^;!<>]/.test(top.slice(0,at)+top.slice(at+3)))return null;
  const left=source.slice(0,at),right=source.slice(at+3);
  try{new vm.Script(source)}catch{return null}
  return {call:left.trim(),code:`_workshopValue("got",(${left}))===_workshopValue("expected",(${right}))`};
}

function compared(plan){
  if(!plan||!('got' in values)||!('expected' in values))return {};
  const fields={call:plan.call.slice(0,200),expected:shown(values.expected),got:shown(values.got)};
  fields.detail=`Got ${fields.got}, expected ${fields.expected}.`;
  // Return advice fits a function call only, such as counter(s, a); not counter(s, a).count or a variable.
  if(values.got===undefined&&values.expected!==undefined)fields.explanation=/^[\w$.\s]+\(\s*\)$/.test(topLevel(plan.call)||'')?RETURNED_UNDEFINED:IS_UNDEFINED;
  return fields;
}

try {
  vm.runInContext(request.code,context,{filename:LEARNER_FILE,timeout:40000});
  for(const check of request.checks) {
    const plan=comparison(check.expr);
    let passed=false,detail='',fields={};
    values={};
    try { passed=Boolean(vm.runInContext(withHelpers(plan?plan.code:check.expr),context,{timeout:5000})); if(!passed){detail=MISMATCH;fields=compared(plan)} }
    catch(e){detail=errorLine(e).slice(0,1200);if(values.got===undefined)fields=compared(plan)}
    result.checks.push({label:check.label,passed,detail,...fields});
  }
  result.passed=result.checks.length>0&&result.checks.every(c=>c.passed);
} catch(e){result.error=learnerStack(e).slice(-6000);result.summary=errorLine(e).slice(0,600)}
const pending=process.argv[3]+'.tmp';
fs.writeFileSync(pending,JSON.stringify(result));
fs.renameSync(pending,process.argv[3]);
// Keep the Windows tree root alive until the parent cleans up with taskkill /T.
if(process.platform==='win32')setInterval(()=>{},60000);
