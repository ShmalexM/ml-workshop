import {useLayoutEffect,useRef,useState} from 'react'
import {Archive,ArrowLeft,ArrowRight,Check,ChevronDown,CircleCheck,Clock,Copy,ExternalLink,FileCode2,FolderGit2,Search} from 'lucide-react'
import type {Course,Lesson,State} from '../types'
import type {Platform,Portfolio,Project,ProjectState,ProjectTask,TaskProgress,Verify} from '../portfolioTypes'
import {formatMinutes,runCheck} from '../projectChecks'
import './projects.css'

type Props={data:Portfolio;courses:Course[];lessons:Lesson[];state:State;selected:string;initialFilter:string;gameEnabled?:boolean;onSelectProject:(id:string)=>void;onLesson:(id:string)=>void;onChange:(id:string,value:ProjectState)=>void;saveStatus:string}

const platformNames:Record<Platform,string>={macos:'macOS',linux:'Linux',windows:'Windows'}
const platformKey='ml-workshop-setup-platform'
const emptyState:ProjectState={notes:'',reviewed:[],updatedAt:0,tasks:{}}

function platformNote(project:Project){
 return project.platforms.includes('windows')?'':project.platforms.map(p=>platformNames[p]).join(' or ')+' only'
}
// Requirements that rule a project out for some learners are shown on the card.
function cardBadges(project:Project){
 return [platformNote(project),project.prerequisites.tools.some(t=>/^Docker/.test(t))?'Needs Docker':''].filter(Boolean)
}
function taskCounts(project:Project,saved?:ProjectState){
 return {done:project.tasks.filter((_,i)=>saved?.reviewed.includes(i)).length,checked:project.tasks.filter(t=>saved?.tasks?.[t.id]?.verifiedAt).length}
}
function savedPlatform():'unix'|'windows'{
 try{const saved=localStorage.getItem(platformKey);if(saved==='unix'||saved==='windows')return saved}catch{/* storage may be blocked */}
 return /Windows/.test(navigator.userAgent)?'windows':'unix'
}

async function copyText(text:string){
 try{await navigator.clipboard.writeText(text);return}catch{/* fall back below */}
 const area=document.createElement('textarea')
 area.value=text;area.setAttribute('readonly','');area.style.position='fixed';area.style.opacity='0'
 document.body.appendChild(area);area.select()
 try{document.execCommand('copy')}finally{area.remove()}
}
function CopyButton({text,label='Copy',name}:{text:string;label?:string;name?:string}){
 const [copied,setCopied]=useState(false)
 return <button type="button" className="copy-button" aria-label={name} onClick={()=>void copyText(text).then(()=>{setCopied(true);setTimeout(()=>setCopied(false),1500)})}>{copied?<Check size={13}/>:<Copy size={13}/>}{label&&(copied?'Copied':label)}</button>
}
function Commands({commands,title}:{commands:string[];title:string}){
 return <div className="command-block"><div className="command-toolbar"><span>{title}</span><CopyButton text={commands.join('\n')} label={commands.length>1?'Copy all':'Copy'}/></div><ol>{commands.map((command,i)=><li key={i}><code>{command}</code>{commands.length>1&&<CopyButton text={command} label="" name={`Copy command ${i+1}`}/>}</li>)}</ol></div>
}
function PasteCheck({verify,id,passedAt,onPass}:{verify:Verify;id:string;passedAt?:number;onPass?:()=>void}){
 const [text,setText]=useState('')
 if(!verify.check)return null
 const check=verify.check
 const outcome=text.trim()?runCheck(check,text):undefined
 return <div className="paste-check"><label htmlFor={id}>Paste your output <small>optional</small></label><p className="paste-hint">{verify.paste?verify.paste+' ':''}The text is checked in this browser. It is not saved or sent.</p><textarea id={id} value={text} rows={4} spellCheck={false} autoComplete="off" onChange={e=>{setText(e.target.value);if(onPass&&runCheck(check,e.target.value))onPass()}}/>{outcome!==undefined&&<p role="status" className={outcome?'paste-pass':'paste-fail'}>{outcome===null?'This browser cannot run this check.':outcome?onPass?'Matches the expected output. Check recorded.':'Matches the expected output.':'Does not match the expected output yet.'}</p>}{passedAt&&outcome===undefined&&<p className="paste-recorded"><CircleCheck size={14}/>Check passed on {new Date(passedAt).toLocaleDateString(undefined,{dateStyle:'medium'})}</p>}</div>
}
function LessonChip({id,lessons,state,onLesson}:{id:string;lessons:Lesson[];state:State;onLesson:(id:string)=>void}){
 const lesson=lessons.find(l=>l.id===id);const done=!!state.completed[id]
 return <button type="button" className={'prereq-chip'+(done?' done':'')} onClick={()=>onLesson(id)} title={done?'Lesson finished':'Open lesson'}>{done&&<Check size={12}/>}{lesson?.title||id}</button>
}

function TaskCard({task,index,stretch,open,done,progress,lessons,state,onToggle,onDone,onProgress,onLesson}:{task:ProjectTask;index:number;stretch?:boolean;open:boolean;done:boolean;progress?:TaskProgress;lessons:Lesson[];state:State;onToggle:()=>void;onDone:(done:boolean)=>void;onProgress:(patch:TaskProgress)=>void;onLesson:(id:string)=>void}){
 const id='task-'+task.id;const [first,last]=task.source.lines
 return <article className={'task-card'+(open?' open':'')+(done?' done':'')}>
  <div className="task-header">
   {stretch?<span className="task-stretch-mark" aria-hidden="true">+</span>:<input type="checkbox" checked={done} aria-label={`Task ${index+1} done`} onChange={e=>onDone(e.target.checked)}/>}
   <button type="button" className="task-toggle" aria-expanded={open} aria-controls={open?id:undefined} onClick={onToggle}><span className="task-meta"><small>{stretch?'Stretch task · optional':`Task ${index+1}`} · {task.minutes} min</small>{progress?.verifiedAt&&<span className="task-checked"><CircleCheck size={13}/>Check passed</span>}</span><strong>{task.title}</strong><ChevronDown size={18} className="task-chevron"/></button>
  </div>
  {open&&<div className="task-body" id={id}>
   <p>{task.do}</p>
   <a className="source-link" href={task.source.url} target="_blank" rel="noreferrer"><FileCode2 size={14}/>{task.source.path}:{first}{last!==first?`–${last}`:''}<ExternalLink size={12}/></a>
   <h4>Change</h4><p>{task.change}</p>
   {task.starter&&<details className="starter-file"><summary>Starter file: {task.starter.path}</summary><div className="command-block"><div className="command-toolbar"><span>{task.starter.path}</span><CopyButton text={task.starter.text}/></div><pre>{task.starter.text}</pre></div></details>}
   <h4>Check</h4>
   <Commands commands={task.verify.commands} title="Run from the repository folder"/>
   <p className="expect"><strong>Expected</strong>{task.verify.expect}</p>
   <PasteCheck verify={task.verify} id={id+'-paste'} passedAt={progress?.verifiedAt} onPass={()=>{if(!progress?.verifiedAt)onProgress({verifiedAt:Date.now()})}}/>
   <label className="task-notes-label" htmlFor={id+'-notes'}>Notes for this task</label>
   <textarea id={id+'-notes'} className="task-notes" value={progress?.notes||''} maxLength={5000} placeholder="What you changed and what you saw" onChange={e=>onProgress({notes:e.target.value})}/>
   {task.lessons.length>0&&<div className="prereq-row"><span>Lessons</span>{task.lessons.map(l=><LessonChip key={l} id={l} lessons={lessons} state={state} onLesson={onLesson}/>)}</div>}
  </div>}
 </article>
}

function HandsOnProject({project,data,progress,lessons,state,gameEnabled,saveStatus,update,onLesson,onSelectProject}:{project:Project;data:Portfolio;progress:ProjectState;lessons:Lesson[];state:State;gameEnabled?:boolean;saveStatus:string;update:(patch:Partial<ProjectState>)=>void;onLesson:(id:string)=>void;onSelectProject:(id:string)=>void}){
 const tasks=progress.tasks||{}
 const started=progress.reviewed.length>0||Object.keys(tasks).length>0||!!progress.notes
 // Setup and the first run are collapsed once the learner has started; one task is open at a time.
 const [setupOpen,setSetupOpen]=useState(!started);const [runOpen,setRunOpen]=useState(!started)
 const [openTask,setOpenTask]=useState(()=>project.tasks.find((_,i)=>!progress.reviewed.includes(i))?.id||'')
 const [platform,setPlatform]=useState(savedPlatform)
 const choose=(next:'unix'|'windows')=>{setPlatform(next);try{localStorage.setItem(platformKey,next)}catch{/* not remembered */}}
 const updateTask=(id:string,patch:TaskProgress)=>{
  const next:Record<string,TaskProgress>={...tasks};const entry={...next[id],...patch}
  if(!entry.notes)delete entry.notes;if(!entry.verifiedAt)delete entry.verifiedAt
  if(Object.keys(entry).length)next[id]=entry;else delete next[id]
  update({tasks:next})
 }
 const {done,checked}=taskCounts(project,progress)
 const commands=platform==='windows'?project.setup.windows:project.setup.unix
 const note=platformNote(project)
 const pre=project.prerequisites
 return <>
  <p className="project-goal">{project.goal}</p>
  <p className="project-time"><Clock size={15}/>≈ {formatMinutes(project.minutes.setup+project.minutes.tasks)}: setup {formatMinutes(project.minutes.setup)}, {project.tasks.length} tasks {formatMinutes(project.minutes.tasks)}.{project.stretch&&` Stretch task: ${formatMinutes(project.minutes.stretch)} more.`}</p>
  {(pre.lessons.length>0||pre.projects.length>0||pre.tools.length>0)&&<section className="prereq-block" aria-label="Before you start"><h2>Before you start</h2>
   {pre.lessons.length>0&&<div className="prereq-row"><span>Lessons</span>{pre.lessons.map(l=><LessonChip key={l} id={l} lessons={lessons} state={state} onLesson={onLesson}/>)}</div>}
   {pre.projects.length>0&&<div className="prereq-row"><span>Projects</span>{pre.projects.map(id=>{const other=data.projects.find(p=>p.id===id);const finished=!!other&&other.tasks.length>0&&taskCounts(other,data.projectState[id]).done===other.tasks.length;return <button type="button" key={id} className={'prereq-chip'+(finished?' done':'')} onClick={()=>onSelectProject(id)}>{finished&&<Check size={12}/>}{other?.title||id}</button>})}</div>}
   {pre.tools.length>0&&<div className="prereq-row"><span>Tools</span>{pre.tools.map(t=><span key={t} className="tool-chip">{t}</span>)}</div>}
  </section>}
  <section className="hands-on-grid"><div>
   <details className="project-section" open={setupOpen} onToggle={e=>setSetupOpen(e.currentTarget.open)}><summary><span>Set up</span><small>{formatMinutes(project.minutes.setup)}{note&&` · ${note}`}</small><ChevronDown size={18}/></summary>
    <div className="platform-toggle" role="group" aria-label="Operating system"><button type="button" aria-pressed={platform==='unix'} onClick={()=>choose('unix')}>macOS / Linux</button><button type="button" aria-pressed={platform==='windows'} onClick={()=>choose('windows')}>Windows</button></div>
    {commands.length?<Commands commands={commands} title={platform==='windows'?'PowerShell':'Terminal'}/>:<p className="platform-missing">This project does not run on Windows. Use a Mac or a Linux computer.</p>}
   </details>
   {project.run&&<details className="project-section" open={runOpen} onToggle={e=>setRunOpen(e.currentTarget.open)}><summary><span>Run it</span><small>before you change anything</small><ChevronDown size={18}/></summary>
    <Commands commands={project.run.commands} title="Run from the repository folder"/>
    <p className="expect"><strong>Expected</strong>{project.run.expect}</p>
    <PasteCheck verify={project.run} id={project.id+'-run-paste'}/>
   </details>}
   <div className="task-list-heading"><h2>Tasks</h2><span>{done}/{project.tasks.length} done · {checked} checked</span></div>
   <p className="task-list-note">Tick a task when you have made the change and run its check. Notes and ticks are saved on this computer.</p>
   <div className="task-list">{project.tasks.map((task,i)=><TaskCard key={task.id} task={task} index={i} open={openTask===task.id} done={progress.reviewed.includes(i)} progress={tasks[task.id]} lessons={lessons} state={state} onLesson={onLesson}
     onToggle={()=>setOpenTask(openTask===task.id?'':task.id)}
     onDone={value=>{update({reviewed:value?[...progress.reviewed.filter(n=>n!==i),i]:progress.reviewed.filter(n=>n!==i)});if(value)setOpenTask(project.tasks.find((_,j)=>j>i&&!progress.reviewed.includes(j))?.id||'')}}
     onProgress={patch=>updateTask(task.id,patch)}/>)}
   </div>
   {project.stretch&&<div className="task-list stretch-list"><TaskCard task={project.stretch} index={project.tasks.length} stretch open={openTask===project.stretch.id} done={false} progress={tasks[project.stretch.id]} lessons={lessons} state={state} onLesson={onLesson} onToggle={()=>setOpenTask(openTask===project.stretch!.id?'':project.stretch!.id)} onDone={()=>{}} onProgress={patch=>updateTask(project.stretch!.id,patch)}/></div>}
   {project.troubleshooting.length>0&&<details className="project-section troubleshooting"><summary><span>Troubleshooting</span><small>{project.troubleshooting.length} known problems</small><ChevronDown size={18}/></summary><dl>{project.troubleshooting.map((item,i)=><div key={i}><dt>{item.problem}</dt><dd>{item.fix}</dd></div>)}</dl></details>}
   <div className="project-deliverable"><strong>What to produce</strong><p>{project.deliverable}</p></div>
   <label className="project-notes-label" htmlFor="project-notes">Project notes</label>
   <textarea id="project-notes" className="project-notes" value={progress.notes} maxLength={30000} placeholder="Commands that worked, outputs, what you would change next" onChange={e=>update({notes:e.target.value})}/>
   <p className="project-save" role="status">{saveStatus} · {done}/{project.tasks.length} tasks done</p>
  </div>
  <aside className="project-evidence"><FolderGit2 size={24}/><h3>Pinned source</h3>
   {project.pin&&<a className="pin-link" href={`${project.repoUrl}/tree/${project.pin.ref}`} target="_blank" rel="noreferrer">Commit {project.pin.ref.slice(0,7)} · {project.pin.label}<ExternalLink size={14}/></a>}
   {project.entryPoint.url&&<a className="source-entry" href={project.entryPoint.url} target="_blank" rel="noreferrer">{project.entryPoint.label}<ExternalLink size={14}/></a>}
   {project.why&&<><h4>Why this repository</h4><p>{project.why}</p></>}
   <h4>Before you begin</h4><p>{project.requirements}</p>
   <h4>How this was checked</h4><p>{project.evidence}</p>
   {gameEnabled&&<><h4>Hero chest</h4><p>Tick all {project.tasks.length} tasks to earn a chest. If every task with a check has a passing check before you open it, the chest is one tier better. The stretch task does not count.</p></>}
   {project.repoUrl&&<a href={project.repoUrl} target="_blank" rel="noreferrer">Open GitHub repository<ExternalLink size={14}/></a>}
   <p className="evidence-note">This is a link to an independent upstream project. The workshop does not install or run it for you.</p>
  </aside></section>
 </>
}

function RetiredProjects({data}:{data:Portfolio}){
 const known=new Set(data.projects.map(p=>p.id))
 const old=Object.entries(data.projectState).filter(([id,s])=>!known.has(id)&&(s.notes||s.reviewed.length>0))
 if(!old.length)return null
 return <details className="retired-projects"><summary><Archive size={16}/>Retired projects ({old.length})</summary><p>These projects left the catalog. Your notes are kept here, read-only. Copy anything you still need.</p>{old.map(([id,s])=>{const info=data.retired?.find(r=>r.id===id);return <article key={id}><h3>{info?.title||id}</h3><small>Retired project{info?` · ${Math.min(s.reviewed.length,info.steps)}/${info.steps} steps done`:''}</small>{s.notes?<pre>{s.notes}</pre>:<p>No notes.</p>}</article>})}</details>
}

export default function Projects({data,courses,lessons,state,selected,initialFilter,gameEnabled,onSelectProject,onLesson,onChange,saveStatus}:Props){
 const container=useRef<HTMLElement>(null)
 useLayoutEffect(()=>{container.current?.scrollTo(0,0);if(window.matchMedia('(max-width:700px)').matches)window.scrollTo(0,0)},[selected])
 const [query,setQuery]=useState('');const [filter,setFilter]=useState(initialFilter||'all');const [level,setLevel]=useState('all')
 const project=data.projects.find(p=>p.id===selected)
 const start=(track:string)=>{const list=lessons.filter(l=>l.course===track);onLesson((list.find(l=>!state.completed[l.id])||list[0]).id)}
 const progress:ProjectState|null=project?{...emptyState,...data.projectState[project.id]}:null
 const update=(patch:Partial<ProjectState>)=>{if(project&&progress)onChange(project.id,{...progress,...patch,updatedAt:Date.now()})}
 if(project&&progress&&project.tasks.length)return <main ref={container} className="hub"><div className="project-detail hands-on"><button className="back-link" onClick={()=>onSelectProject('')}><ArrowLeft size={16}/>All projects</button><span className="eyebrow">{project.visibility==='public'?'Public project':'Project practice'} · {project.level}{platformNote(project)&&` · ${platformNote(project)}`}</span><h1>{project.title}</h1><div className="project-tags">{project.tracks.map(t=><button key={t} onClick={()=>start(t)}>{courses.find(c=>c.id===t)?.title}<ArrowRight size={13}/></button>)}</div><HandsOnProject key={project.id} project={project} data={data} progress={progress} lessons={lessons} state={state} gameEnabled={gameEnabled} saveStatus={saveStatus} update={update} onLesson={onLesson} onSelectProject={onSelectProject}/></div></main>
 if(project&&progress)return <main ref={container} className="hub"><div className="project-detail"><button className="back-link" onClick={()=>onSelectProject('')}><ArrowLeft size={16}/>All projects</button><span className="eyebrow">{project.visibility==='public'?'Public project':'Project practice'} · {project.level}</span><h1>{project.title}</h1><p className="project-summary">{project.summary}</p><div className="project-tags">{project.tracks.map(t=><button key={t} onClick={()=>start(t)}>{courses.find(c=>c.id===t)?.title}<ArrowRight size={13}/></button>)}</div><div className="project-first-step"><div><h2>Why this project</h2><p>{project.why}</p></div><button className="primary-button" onClick={()=>onLesson(project.firstLesson)}>Preparation lesson: {lessons.find(l=>l.id===project.firstLesson)?.title}<ArrowRight size={15}/></button></div><section className="project-practice"><div><h2>Walkthrough</h2><p>Open the starting file, then work through the steps in order. Mark a step done when you can explain it. Notes and steps are saved on this computer.</p><div className="walkthrough-steps">{project.steps.map((step,i)=><label key={i}><input type="checkbox" checked={progress.reviewed.includes(i)} onChange={e=>update({reviewed:e.target.checked?[...progress.reviewed,i]:progress.reviewed.filter(n=>n!==i)})}/><span><small>Step {i+1}</small>{step}</span></label>)}</div><div className="project-deliverable"><strong>What to produce</strong><p>{project.deliverable}</p></div><label className="project-notes-label" htmlFor="project-notes">Notes</label><textarea id="project-notes" className="project-notes" value={progress.notes} maxLength={30000} placeholder="File paths, what must always hold, one way it can fail, how you would test it" onChange={e=>update({notes:e.target.value})}/><p className="project-save" role="status">{saveStatus} · {progress.reviewed.length}/{project.steps.length} steps done</p></div><aside className="project-evidence"><FolderGit2 size={24}/><h3>Start reading here</h3>{project.entryPoint.url&&<a className="source-entry" href={project.entryPoint.url} target="_blank" rel="noreferrer">{project.entryPoint.label}<ExternalLink size={14}/></a>}<h4>Before you begin</h4><p>{project.requirements}</p><h4>How this was checked</h4><p>{project.evidence}</p>{project.localPath&&<><h4>Local checkout</h4><code>{project.localPath}</code></>}{project.repoUrl&&<a href={project.repoUrl} target="_blank" rel="noreferrer">Open GitHub repository<ExternalLink size={14}/></a>}<p className="evidence-note">This is a link to an independent upstream project. The workshop does not install or run it for you.</p></aside></section></div></main>
 const matches=(p:Project)=>(filter==='all'||p.tracks.includes(filter))&&(level==='all'||p.level===level)&&`${p.title} ${p.summary} ${p.tracks.map(t=>courses.find(c=>c.id===t)?.title).join(' ')}`.toLowerCase().includes(query.toLowerCase())
 const cardStatus=(p:Project)=>{const saved=data.projectState[p.id];if(!p.tasks.length)return `${saved?.reviewed.length||0}/${p.steps.length} steps`;const {done,checked}=taskCounts(p,saved);return `≈ ${formatMinutes(p.minutes.setup+p.minutes.tasks)} · ${done}/${p.tasks.length} tasks · ${checked} checked`}
 return <main ref={container} className="hub"><div className="hub-inner"><div className="section-heading project-heading"><div><h1>Projects</h1><p>Each project pins a public GitHub repository to one commit. You set it up, run it, then change it in small tasks with a command to check each one. Begin at the Start small level.</p></div><FolderGit2 size={38}/></div>{data.error&&<p role="alert" className="portfolio-warning">{data.error}</p>}{data.projects.length===0?<section className="empty-projects"><h2>No projects to show</h2><p>A data/portfolio.json file replaces the built-in catalog. Fix or remove it to see the built-in projects. See docs/project-learning.md.</p></section>:<><div className="project-filters"><label className="project-search"><Search size={17}/><input aria-label="Search projects" placeholder="Search projects or paths" value={query} onChange={e=>setQuery(e.target.value)}/></label><select aria-label="Filter projects by path" value={filter} onChange={e=>setFilter(e.target.value)}><option value="all">All paths</option>{courses.map(c=><option key={c.id} value={c.id}>{c.title}</option>)}</select><select aria-label="Filter projects by level" value={level} onChange={e=>setLevel(e.target.value)}><option value="all">All levels</option><option>Start small</option><option>Build next</option><option>Capstone</option></select></div><p className="project-ladder"><strong>Start small</strong><ArrowRight size={14}/><span>Build next</span><ArrowRight size={14}/><span>Capstone</span></p><div className="project-grid">{data.projects.filter(matches).map(p=><button className="project-card" key={p.id} onClick={()=>onSelectProject(p.id)}><div className="project-card-title"><FolderGit2 size={20}/><span className={p.level==='Start small'?'starter-level':''}>{p.level}</span></div><h2>{p.title}</h2><p>{p.summary}</p>{cardBadges(p).length>0&&<div className="card-badges">{cardBadges(p).map(b=><small key={b} className="platform-badge">{b}</small>)}</div>}<div className="project-tags">{p.tracks.map(t=><span key={t}>{courses.find(c=>c.id===t)?.title}</span>)}</div><div className="project-card-bottom"><span>{cardStatus(p)}</span><strong>Open project <ArrowRight size={15}/></strong></div></button>)}</div>{!data.projects.some(matches)&&<p className="empty-projects">No projects match. Try another search or path.</p>}<RetiredProjects data={data}/><p className="hub-footnote">{data.coverage}</p></>}</div></main>
}
