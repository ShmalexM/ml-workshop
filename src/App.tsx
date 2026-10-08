import {lazy,Suspense,useCallback,useEffect,useRef,useState,type CSSProperties} from 'react'
import {CodeXml,Settings as SettingsIcon,LoaderCircle,X} from 'lucide-react'
import {api,bootstrap,serverReachable} from './api'
import type {Course,Lesson,State,Runtime,RunResult,LearningStage} from './types'
import type {Portfolio,ProjectState} from './portfolioTypes'
import Curriculum from './components/Curriculum'
import LessonReader from './components/LessonReader'
import Workspace from './components/Workspace'
import Overview from './components/Overview'
import Settings from './components/Settings'
import Solution from './components/Solution'
import GuidedExample from './components/GuidedExample'
import PanelDivider,{clampReaderWidth} from './components/PanelDivider'
import Paths from './components/Paths'
import Projects from './components/Projects'
import LootToast,{type LootNotice} from './game/LootToast'
import {gameApi,summarize} from './game/gameApi'
import type {GameSummary} from './game/types'
import type {BookLocation,LibraryData} from './libraryTypes'
import './components/learnLayout.css'
const BookLibrary=lazy(()=>import('./components/BookLibrary'))
const HeroPage=lazy(()=>import('./game/HeroPage'))
type Page='paths'|'learn'|'projects'|'practice'|'progress'|'books'|'hero'
function routePage():Page {const name=location.hash.slice(1).split(/[/?]/)[0];return ['paths','learn','projects','practice','progress','books','hero'].includes(name)?name as Page:'paths'}
function bookRoute():BookLocation|null {const match=location.hash.match(/^#books\/([a-z0-9-]+)\/(\d+)(?:\/(.*))?$/);if(!match)return null;let anchor='';try{anchor=decodeURIComponent(match[3]||'')}catch{}return {bookId:match[1],location:Number(match[2]),anchor}}
function projectRoute(){return location.hash.match(/^#projects\/([a-z0-9-]+)$/)?.[1]||''}
function projectFilter(){return new URLSearchParams(location.hash.split('?')[1]||'').get('track')||'all'}
const localKey='ml-workshop-drafts-v1',projectKey='ml-workshop-projects-v1'
type Draft={code:string;notes:string;updatedAt:number}
function readCache<T>(key:string):Record<string,T>{try{return JSON.parse(localStorage.getItem(key)||'{}')}catch{return {}}}
const lessonsPanelKey='ml-workshop-lessons-panel',readerWidthKey='ml-workshop-reader-width'
function readPref(key:string){try{return localStorage.getItem(key)}catch{return null}}
function savePref(key:string,value:string){try{localStorage.setItem(key,value)}catch{/* storage unavailable: the choice lasts until reload */}}
function useMedia(query:string){const [matches,setMatches]=useState(()=>matchMedia(query).matches);useEffect(()=>{const list=matchMedia(query);const update=()=>setMatches(list.matches);update();list.addEventListener('change',update);return()=>list.removeEventListener('change',update)},[query]);return matches}
const emptyPortfolio:Portfolio={version:1,projects:[],coverage:'',updatedAt:'',projectState:{}}
export default function App(){
 const [library,setLibrary]=useState<LibraryData>({books:[],guides:[],readingState:{}})
 const [bookSelection,setBookSelection]=useState<BookLocation|null>(bookRoute)
 const [portfolio,setPortfolio]=useState<Portfolio>(emptyPortfolio);const portfolioRef=useRef(portfolio);portfolioRef.current=portfolio
 const [projectId,setProjectId]=useState(projectRoute);const [projectTrack,setProjectTrack]=useState(projectFilter)
 const [projectSave,setProjectSave]=useState('Saved on this computer');const projectTimers=useRef<Record<string,ReturnType<typeof setTimeout>>>({})
 const [courses,setCourses]=useState<Course[]>([]);const [lessons,setLessons]=useState<Lesson[]>([])
 const [state,setState]=useState<State|null>(null);const [runtime,setRuntime]=useState<Runtime|null>(null)
 const [stage,setStage]=useState<LearningStage>('understand');const [exampleResults,setExampleResults]=useState<Record<string,RunResult>>({})
 const [id,setId]=useState('foundations-1');const [page,setPage]=useState<Page>(routePage)
 const [drawer,setDrawer]=useState(false);const [settings,setSettings]=useState(false);const [error,setError]=useState('')
 // From 1440px the lesson list sits beside the lesson and stays open unless closed. Narrower screens open it over the lesson.
 const wide=useMedia('(min-width:1440px)');const [docked,setDocked]=useState(()=>readPref(lessonsPanelKey)!=='closed')
 const closeLessons=useCallback(()=>{if(wide){setDocked(false);savePref(lessonsPanelKey,'closed')}else setDrawer(false);requestAnimationFrame(()=>document.getElementById('lessons-toggle')?.focus())},[wide])
 const [readerWidth,setReaderWidth]=useState(()=>clampReaderWidth(Number(readPref(readerWidthKey))))
 const [busy,setBusy]=useState(false);const [results,setResults]=useState<Record<string,RunResult>>({})
 const [saveStatus,setSaveStatus]=useState('Saved on this computer');const [solution,setSolution]=useState<string|null>(null)
 const [cache,setCache]=useState(()=>readCache<Draft>(localKey));const cacheRef=useRef(cache)
 const timers=useRef<Record<string,ReturnType<typeof setTimeout>>>({});const [loaded,setLoaded]=useState(false)
 // Hero game: a summary drives the nav badge; the full state loads only on the Hero page.
 const [game,setGame]=useState<GameSummary|null>(null);const [loot,setLoot]=useState<LootNotice|null>(null);const closeLoot=useCallback(()=>setLoot(null),[])
 // Ask the server every 15 s while this tab is visible, so the header dot turns red when it stops answering.
 const [online,setOnline]=useState(true)
 useEffect(()=>{let timer:ReturnType<typeof setInterval>|undefined
  const check=()=>{void serverReachable().then(setOnline)}
  const schedule=()=>{clearInterval(timer);if(document.visibilityState==='visible'){check();timer=setInterval(check,15000)}}
  schedule();document.addEventListener('visibilitychange',schedule)
  return()=>{clearInterval(timer);document.removeEventListener('visibilitychange',schedule)}},[])
 // Finished project walkthroughs and reading guides earn chests too, so the Hero badge is refreshed after they are saved.
 const refreshGame=useCallback(()=>{gameApi.summary().then(setGame).catch(()=>{})},[]);const reviewChanged=useRef(new Set<string>())
 useEffect(()=>{if(page==='hero')setLoot(null)},[page])
 const saveProject=useCallback(async(projectId:string,value:ProjectState)=>{try{await api('/project/state',{projectId,...value});setProjectSave('Saved on this computer');if(reviewChanged.current.delete(projectId))refreshGame()}catch{setProjectSave('Saved in this browser · server not reachable')}},[refreshGame])
 useEffect(()=>{let active=true;(async()=>{try{
   await bootstrap()
   const [curriculum,s,r,books,projects]=await Promise.all([api<{courses:Course[];lessons:Lesson[]}>('/curriculum'),api<State>('/state'),api<Runtime>('/runtime'),api<LibraryData>('/library'),api<Portfolio>('/portfolio')])
   if(!active)return
   const recovered=Object.fromEntries(Object.entries(cacheRef.current).filter(([key,draft])=>curriculum.lessons.some(l=>l.id===key)&&draft.updatedAt >= (s.draftUpdated?.[key]??0)))
   cacheRef.current=recovered;setCache(recovered);try{localStorage.setItem(localKey,JSON.stringify(recovered))}catch{}
   const projectCache=readCache<ProjectState>(projectKey)
   for(const [key,value] of Object.entries(projectCache))if(projects.projects.some(p=>p.id===key)&&value.updatedAt>=(projects.projectState[key]?.updatedAt||0)){projects.projectState[key]=value;void saveProject(key,value)}
   setPortfolio(projects);portfolioRef.current=projects
   setCourses(curriculum.courses);setLessons(curriculum.lessons);setState(s)
   const requested=location.hash.match(/^#learn\/([a-z0-9-]+)$/)?.[1]
   setId(requested&&curriculum.lessons.some(l=>l.id===requested)?requested:s.currentLesson)
   setRuntime(r);setLibrary(books);setLoaded(true)
   gameApi.summary().then(g=>{if(active)setGame(g)}).catch(()=>{})
 }catch(e){if(active)setError((e as Error).message)}})();return()=>{active=false}},[saveProject])
 useEffect(()=>{const sync=()=>{setPage(routePage());setDrawer(false);setBookSelection(bookRoute());setProjectId(projectRoute());setProjectTrack(projectFilter());const requested=location.hash.match(/^#learn\/([a-z0-9-]+)$/)?.[1];if(requested&&lessons.some(l=>l.id===requested)){setId(requested);setStage('understand');setSolution(null)}};window.addEventListener('hashchange',sync);return()=>window.removeEventListener('hashchange',sync)},[lessons])
 function showPage(next:Page){setPage(next);setDrawer(false);if(next==='books')setBookSelection(null);location.hash=next==='learn'?`learn/${id}`:next}
 function showProjects(track?:string){setPage('projects');setProjectId('');setProjectTrack(track||'all');location.hash='projects'+(track?'?track='+track:'')}
 function selectProject(next:string){setProjectId(next);location.hash='projects'+(next?'/'+next:projectTrack!=='all'?'?track='+projectTrack:'')}
 const save=useCallback(async(lessonId:string,draft:Draft)=>{try{await api('/draft',{lessonId,...draft});setSaveStatus('Saved on this computer')}catch{setSaveStatus('Saved in this browser · server not reachable')}},[])
 useEffect(()=>{if(loaded)Object.entries(cacheRef.current).forEach(([lessonId,draft])=>{void save(lessonId,draft)})},[loaded,save])
 function updateDraft(lessonId:string,code:string,notes:string){const draft={code,notes,updatedAt:Date.now()};const next={...cacheRef.current,[lessonId]:draft};cacheRef.current=next;setCache(next);try{localStorage.setItem(localKey,JSON.stringify(next));setSaveStatus('Saving…')}catch{setSaveStatus('Browser storage unavailable · saving to server')};clearTimeout(timers.current[lessonId]);timers.current[lessonId]=setTimeout(()=>void save(lessonId,draft),350)}
 function updateProject(projectId:string,value:ProjectState){if(String(portfolioRef.current.projectState[projectId]?.reviewed??[])!==String(value.reviewed))reviewChanged.current.add(projectId);const next={...portfolioRef.current,projectState:{...portfolioRef.current.projectState,[projectId]:value}};portfolioRef.current=next;setPortfolio(next);try{localStorage.setItem(projectKey,JSON.stringify(next.projectState));setProjectSave('Saving…')}catch{setProjectSave('Browser storage unavailable · saving to server')};clearTimeout(projectTimers.current[projectId]);projectTimers.current[projectId]=setTimeout(()=>void saveProject(projectId,value),350)}
 function selectLesson(next:string){if(busy)return;setId(next);setStage('understand');setPage('learn');setDrawer(false);setSolution(null);setError('');location.hash='learn/'+next;setState(old=>old?{...old,currentLesson:next}:old);void api('/current',{lessonId:next}).catch(()=>setSaveStatus('Could not save your place · server not reachable'))}
 if(!state||!lessons.length)return <main className="loading-screen"><CodeXml size={44}/><h1>{error?'Could not load Engineering Workshop':'Loading Engineering Workshop…'}</h1>{error?<><p>{error}</p><button className="primary-button" onClick={()=>location.reload()}>Reload</button></>:<LoaderCircle size={23} className="spin"/>}</main>
 const lessonsOpen=wide?docked:drawer
 function toggleLessons(){if(!wide){setDrawer(open=>!open);return}const next=!docked;setDocked(next);savePref(lessonsPanelKey,next?'open':'closed')}
 function resizeReader(value:number,done:boolean){setReaderWidth(value);if(done)savePref(readerWidthKey,String(value))}
 const lesson=lessons.find(l=>l.id===id)||lessons[0];const course=courses.find(c=>c.id===lesson.course)!;const inCourse=lessons.filter(l=>l.course===lesson.course);const position=lessons.indexOf(lesson)
 const code=cache[id]?.code??state.drafts[id]??lesson.starter;const notes=cache[id]?.notes??state.notes[id]??'';const completed=!!state.completed[id]
 async function run(mode:'run'|'check'){if(busy)return;setBusy(true);setError('');try{await save(id,{code,notes,updatedAt:Date.now()});const result=await api<RunResult>('/run',{lessonId:id,code,mode});setResults(old=>({...old,[id]:result}));if(result.state)setState(result.state);if(!completed&&result.state?.completed[id]&&game?.enabled)void notifyLoot(id,lesson.title)}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 async function runExample(){if(busy)return;setStage('example');setBusy(true);try{const result=await api<RunResult>('/example',{lessonId:id});setExampleResults(old=>({...old,[id]:result}))}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 async function notifyLoot(lessonId:string,title:string){try{const g=await gameApi.state();setGame(summarize(g));if(g.enabled)setLoot({lesson:title,chest:g.chests.unopened.find(c=>c.source==='lesson:'+lessonId)||null,battles:g.battles.available})}catch{/* rewards are derived from progress, so a missed toast loses nothing */}}
 async function showSolution(){try{const r=await api<{solution:string}>('/solution/'+id);setSolution(r.solution)}catch(e){setError((e as Error).message)}}
 async function backup(){await Promise.all([...Object.entries(cacheRef.current).map(([lessonId,draft])=>api('/draft',{lessonId,...draft})),...Object.entries(library.readingState).map(([bookId,reading])=>api('/library/state',{bookId,...reading})),...Object.entries(portfolioRef.current.projectState).filter(([projectId])=>portfolioRef.current.projects.some(p=>p.id===projectId)).map(([projectId,value])=>api('/project/state',{projectId,...value}))]);return api<{url:string;filename:string}>('/backup',{})}
 return <div className="app"><header className="app-header"><div className="brand-area"><button className="brand" onClick={()=>showPage('paths')}><CodeXml size={29}/><span>Engineering Workshop</span></button></div><nav aria-label="Main navigation">{(game?.enabled?['paths','learn','projects','books','progress','hero'] as const:['paths','learn','projects','books','progress'] as const).map(p=><button key={p} className={page===p?'active':''} onClick={()=>showPage(p)}>{p[0].toUpperCase()+p.slice(1)}{p==='hero'&&game&&game.unopened>0&&<span className="nav-badge" aria-label={`${game.unopened} unopened chests`}>{game.unopened}</span>}</button>)}</nav><div className="header-right"><button className={'runtime-status'+(online?'':' offline')} title={online?'Local runtime':'Server not reachable'} onClick={()=>setSettings(true)}><span/>{online?'Local runtime':'Server not reachable'}</button><button className="icon-button" aria-label="Open settings" onClick={()=>setSettings(true)}><SettingsIcon size={20}/></button></div></header>
 {loot&&page!=='hero'&&<LootToast notice={loot} onClose={closeLoot}/>}
  {error&&<div role="alert" className="error-toast"><span>{error}</span><button aria-label="Dismiss error" onClick={()=>setError('')}><X size={17}/></button></div>}
 <div className="app-body">{page==='learn'&&<Curriculum courses={courses} lessons={lessons} state={state} current={lesson} onSelect={selectLesson} open={lessonsOpen} overlay={!wide} onClose={closeLessons}/>}
 {page==='paths'?<Paths courses={courses} lessons={lessons} state={state} portfolio={portfolio} onSelect={selectLesson} onProjects={showProjects} onPractice={()=>showPage('practice')}/>:page==='projects'?<Projects key={projectTrack} data={portfolio} courses={courses} lessons={lessons} state={state} selected={projectId} initialFilter={projectTrack} onSelectProject={selectProject} onLesson={selectLesson} onChange={updateProject} saveStatus={projectSave}/>:page==='books'?<Suspense fallback={<p className="book-hint">Loading books…</p>}><BookLibrary data={library} selection={bookSelection} onLesson={selectLesson} onGuidesSaved={refreshGame} onImported={result=>setLibrary(old=>{
      const id=result.book.id, current=old.readingState[id], incoming=result.readingState
      return {...old,books:[...old.books.filter(book=>book.id!==id),result.book],guides:[...old.guides.filter(guide=>guide.bookId!==id),...result.guides],readingState:{...old.readingState,...(incoming&&(!current||incoming.updatedAt>current.updatedAt)?{[id]:incoming}:{})}}
    })} onState={(bookId,value)=>setLibrary(old=>({...old,readingState:{...old.readingState,[bookId]:value}}))}/></Suspense>:page==='hero'?<Suspense fallback={<p className="book-hint">Opening the armory…</p>}><HeroPage onSummary={setGame}/></Suspense>:page==='learn'?<main className={'learning-layout stage-'+stage} inert={!wide&&drawer} style={{'--reader-width':readerWidth+'%'} as CSSProperties}><LessonReader key={'reader-'+id} lessonsOpen={lessonsOpen} onToggleLessons={toggleLessons} readings={library.guides.filter(g=>g.lessons.includes(lesson.id))} stage={stage} onStage={setStage} onLesson={selectLesson} allCourses={courses} lesson={lesson} course={course} index={inCourse.indexOf(lesson)} count={inCourse.length} notes={notes} onNotes={s=>updateDraft(id,code,s)} onSolution={showSolution} onPath={()=>showPage('paths')}/>{stage==='example'&&<GuidedExample lesson={lesson} result={exampleResults[id]||null} busy={busy} onRun={runExample} onPractice={()=>setStage('practice')}/>}{stage==='practice'&&<><PanelDivider value={readerWidth} onChange={resizeReader}/><Workspace key={'workspace-'+id} lesson={lesson} code={code} onCode={s=>updateDraft(id,s,notes)} onRun={run} busy={busy} result={results[id]||null} done={completed} onPrevious={()=>selectLesson(lessons[position-1].id)} onNext={()=>selectLesson(lessons[position+1].id)} hasPrevious={position>0} hasNext={position<lessons.length-1} saveStatus={saveStatus}/></>}</main>:<Overview page={page} courses={courses} lessons={lessons} state={state} drafts={cache} onSelect={selectLesson}/>}</div>
 {settings&&<Settings runtime={runtime} onBackup={backup} onClose={()=>setSettings(false)} game={game} onGameToggle={async enabled=>{const {game:g}=await gameApi.settings(enabled);setGame(summarize(g));if(!enabled){setLoot(null);if(page==='hero')showPage('paths')}}}/>} {solution&&<Solution lesson={lesson} code={solution} draft={code} onClose={()=>setSolution(null)} onLoad={()=>{updateDraft(id,solution,notes);setStage('practice');setSolution(null)}}/>}</div>
}
