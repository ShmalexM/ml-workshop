import type {Course,LearningStage,Lesson,RunResult} from '../types'

// Page context that can go with a question. Each chip is shown above the input and can be turned off.
// Never included: the reference solution, the check code (the browser never has it) and the prediction's answer.

export type ChipId='lesson'|'example'|'code'|'run'|'hints'|'notes'|'page'
export type Chip={id:ChipId;label:string;text:string;truncated:boolean;on:boolean}
// result is the last run of the learner's code; exampleResult the last run of the worked example.
export type LessonContext={kind:'lesson';lesson:Lesson;course:Course;stage:LearningStage;code:string;notes:string;result:RunResult|null;exampleResult?:RunResult|null}
export type PageContext={kind:'page';name:string}
export type AssistantContext=LessonContext|PageContext

/** Characters per chip. The server checks the same limits. */
export const caps:Record<ChipId,number>={lesson:4096,example:3072,code:12288,run:6144,hints:1536,notes:3072,page:200}
const stageNames:Record<LearningStage,string>={understand:'Understand',example:'See an example',practice:'Try it yourself'}

/** Cut text to the cap and mark the cut. keep says which part matters: the start, the end, or both ends. */
export function cut(text:string,cap:number,keep:'start'|'end'|'both'='start'):{text:string;truncated:boolean}{
 if(text.length<=cap)return {text,truncated:false}
 const mark=(n:number)=>`\n[… ${n} characters cut …]\n`
 if(keep==='end'){const tail=text.slice(text.length-cap);return {text:mark(text.length-cap).trimStart()+tail,truncated:true}}
 if(keep==='both'){const head=Math.floor(cap*2/3),tail=cap-head;return {text:text.slice(0,head)+mark(text.length-cap)+text.slice(text.length-tail),truncated:true}}
 return {text:text.slice(0,cap)+mark(text.length-cap).trimEnd(),truncated:true}
}

function lessonText(c:LessonContext){
 const {lesson,course}=c
 return [`Lesson: ${lesson.title}`,`Path: ${course.title}`,`Stage: ${stageNames[c.stage]}`,`Language: ${lesson.language==='javascript'?'JavaScript':course.id==='cuda'?'Python with the Numba CUDA simulator':'Python'}`,
  '',`Idea: ${lesson.concept}`,'',lesson.explanation,'','Tasks:',...lesson.tasks.map(t=>`- ${t}`),'','Checks that Check answer runs:',...lesson.checkLabels.map(t=>`- ${t}`)].join('\n')
}
function exampleText(lesson:Lesson){
 const g=lesson.example
 // The answer index and the feedback are left out: they give away the prediction.
 return ['Worked example:','```',g.code.trimEnd(),'```','',...g.steps.map((s,i)=>`${i+1}. ${s}`),'',`Prediction question: ${g.question}`,...g.choices.map((choice,i)=>`${String.fromCharCode(65+i)}. ${choice}`)].join('\n')
}
function runText(result:RunResult,example:boolean){
 const lines:string[]=[]
 if(result.error){
  lines.push(example?'The worked example ended with an error when it ran.':'The last run ended with an error.')
  if(result.summary)lines.push(`Error: ${result.summary}`)
  if(result.explanation)lines.push(`Plain-language note: ${result.explanation}`)
  lines.push('Traceback:',cut(result.error,3500,'end').text)
 }else if(result.checks.length){
  const failed=result.checks.filter(c=>!c.passed)
  lines.push(`Check answer: ${result.checks.length-failed.length} of ${result.checks.length} checks passed.`)
  for(const c of failed){
   lines.push(`Failed: ${c.label}`)
   if(c.call)lines.push(`  Call: ${c.call}`)
   if(c.got!==undefined)lines.push(`  Expected: ${c.expected}`,`  Got: ${c.got}`)
   else if(c.detail)lines.push(`  Detail: ${c.detail}`)
   if(c.explanation)lines.push(`  Note: ${c.explanation}`)
  }
 }else lines.push(example?'The worked example ran without an error.':'The last run finished without an error.')
 if(result.stdout)lines.push('Output:',cut(result.stdout,2000,'end').text)
 return lines.join('\n')
}

/** Build the chips for a page. overrides holds the learner's on/off choices for this conversation. */
export function buildChips(context:AssistantContext,hints:number,overrides:Record<string,boolean>):Chip[]{
 const chips:Omit<Chip,'on'>[]=[];const defaults:Partial<Record<ChipId,boolean>>={}
 const add=(id:ChipId,label:string,raw:string,on:boolean,keep:'start'|'end'|'both'='start')=>{const {text,truncated}=cut(raw,caps[id],keep);chips.push({id,label,text,truncated});defaults[id]=on}
 if(context.kind==='page'){add('page','Page name',`Page: ${context.name}`,true);return chips.map(c=>({...c,on:overrides[c.id]??defaults[c.id]!}))}
 const {lesson,stage}=context
 add('lesson','Lesson and stage',lessonText(context),true)
 add('example','Worked example',exampleText(lesson),stage==='example')
 add('code','Your code',context.code,stage==='practice','both')
 // On the example stage the run chip holds the worked example's run, on the practice stage the learner's run.
 const example=stage==='example'
 const result=example?context.exampleResult??null:context.result
 if(result)add('run',(example?'Example run':'Last run')+(result.error?': error':result.checks.some(c=>!c.passed)?': failed checks':''),runText(result,example),stage!=='understand','end')
 if(hints>0)add('hints',`Hints opened (${hints})`,lesson.hints.slice(0,hints).map((h,i)=>`${i+1}. ${h}`).join('\n'),true)
 if(context.notes.trim())add('notes','Your notes',context.notes,false)
 return chips.map(c=>({...c,on:overrides[c.id]??defaults[c.id]!}))
}
