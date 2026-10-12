import {useState} from 'react'
import {ArrowRight, BookOpen, Code2, FolderGit2, Play} from 'lucide-react'
import type {Course, Lesson, State} from '../types'
import type {Portfolio} from '../portfolioTypes'
import type {LearningPathResponse} from '../learningPathTypes'
import BeginnerGuide from './BeginnerGuide'
import LearningPath from './LearningPath'
import './firstRun.css'

const routes = [
  {title: 'ML & GPU engineer', detail: 'From Python basics to GPU kernels', ids: ['python', 'foundations', 'pytorch', 'tensorflow', 'modern', 'cuda']},
  {title: 'Agent & systems engineer', detail: 'APIs, agent loops, data and reliability', ids: ['backend', 'harness', 'data', 'reliability']},
  {title: 'Product engineer', detail: 'From UI state to release checks', ids: ['web', 'backend', 'interactive', 'reliability']},
  {title: 'RL engineer', detail: 'Environments, learning and evaluation', ids: ['foundations', 'rl', 'pytorch', 'cuda']},
]
const mlPaths = ['foundations', 'pytorch', 'tensorflow', 'modern', 'cuda', 'rl']

export default function Paths({courses, lessons, state, portfolio, onSelect, onProjects, onPractice}: {
  courses: Course[]; lessons: Lesson[]; state: State; portfolio: Portfolio
  onSelect: (id: string) => void; onProjects: (track?: string) => void; onPractice: () => void
}) {
  const [filter, setFilter] = useState('all')
  const [personal, setPersonal] = useState<LearningPathResponse | null>()
  function start(id: string) {
    const list = lessons.filter(lesson => lesson.course === id)
    const next = list.find(lesson => !state.completed[lesson.id]) ?? list[0]
    if (next) onSelect(next.id)
  }
  const current = lessons.find(lesson => lesson.id === state.currentLesson) ?? lessons[0]
  const python = lessons.filter(lesson => lesson.course === 'python')
  const newLearner = !Object.keys(state.completed).length && !Object.keys(state.drafts).length
  const recommended = personal?.recommendation?.steps.flatMap(step => lessons.filter(lesson => lesson.course === step.courseId)).find(lesson => !state.completed[lesson.id])

  return <main className="hub"><div className="hub-inner">
    <section className="hub-hero">
      <div>
        <h1>Learn machine learning, from your first line of code</h1>
        <p>No coding experience needed. Start with small Python programs, then explore machine learning (ML), AI agents, websites and data. Each lesson introduces one idea and gives you room to practice.</p>
        {python.length > 0 && <p className="hub-prereq">New to programming? <button type="button" onClick={() => start('python')}>Python from zero</button> begins with typing and running your first instruction.</p>}
        <div className="hero-actions">
          {personal === undefined ? <button className="primary-button" disabled>Loading your path…</button> : personal?.profile ? recommended ? <button className="primary-button" onClick={() => onSelect(recommended.id)}><Play size={16}/>{newLearner ? 'Start learning' : 'Continue learning'}</button> : <button className="primary-button" onClick={onPractice}>Explore more lessons<ArrowRight size={16}/></button> : newLearner && python.length > 0 ? <button className="primary-button" onClick={() => start('python')}><Play size={16}/>Start Python from zero</button> : current && <button className="primary-button" onClick={() => onSelect(current.id)}><Play size={16}/>Continue learning</button>}
          <button className="secondary-button" onClick={() => onProjects()}><FolderGit2 size={17}/>Open projects</button>
        </div>
        {!newLearner && (recommended ?? current) && <small>{courses.find(course => course.id === (recommended ?? current).course)?.title} · {(recommended ?? current).title}</small>}
      </div>
      <div className="learning-loop" aria-label="Learning workflow">
        <div><BookOpen/><span><strong>Understand</strong><small>Read one idea, with unfamiliar words explained</small></span></div><ArrowRight className="loop-arrow"/>
        <div><Play/><span><strong>See an example</strong><small>Run a small program and see what happens</small></span></div><ArrowRight className="loop-arrow"/>
        <div><Code2/><span><strong>Try it yourself</strong><small>Change the code, then check your work</small></span></div>
      </div>
    </section>

    <LearningPath courses={courses} lessons={lessons} state={state} newLearner={newLearner} onSelect={onSelect} onBrowse={onPractice} onChange={setPersonal}/>
    <BeginnerGuide newLearner={newLearner} onStart={python.length ? () => start('python') : undefined}/>

    <div className="section-heading"><div><h2>Suggested order by role</h2><p>Explore the skills used in different roles. Every lesson stays open.</p></div><button className="text-button" onClick={onPractice}>All lessons<ArrowRight size={16}/></button></div>
    <div className="route-grid">{routes.map(route => <article className="route-card" key={route.title}><h3>{route.title}</h3><p>{route.detail}</p><div className="route-steps">{route.ids.filter(id => courses.some(course => course.id === id)).map((id, index) => <button key={id} onClick={() => start(id)}><span>{index + 1}</span>{courses.find(course => course.id === id)?.title}<ArrowRight size={13}/></button>)}</div></article>)}</div>

    <div className="section-heading"><div><h2>All paths</h2><p>{courses.length} paths · {lessons.length} lessons · Python and JavaScript</p></div><label className="path-filter">Show<select value={filter} onChange={event => setFilter(event.target.value)} aria-label="Filter paths"><option value="all">All paths</option><option value="ml">ML & AI</option><option value="systems">Software systems</option></select></label></div>
    <div className="skill-grid">{courses.filter(course => filter === 'all' || course.id === 'python' || (filter === 'ml') === mlPaths.includes(course.id)).map(course => {
      const list = lessons.filter(lesson => lesson.course === course.id)
      const done = list.filter(lesson => state.completed[lesson.id]).length
      const projects = portfolio.projects.filter(project => project.tracks.includes(course.id))
      return <article className="skill-card" key={course.id}>
        <div className="skill-card-top"><Code2 size={20}/><small>{done}/{list.length} completed</small></div><h3>{course.title}</h3><p>{course.subtitle}</p>
        <div className="progress-track"><div style={{width: (list.length ? done / list.length * 100 : 0) + '%'}}/></div>
        <div className="skill-actions"><button className="text-button" onClick={() => start(course.id)}>{done === list.length && done > 0 ? 'Review path' : done ? 'Continue' : 'Start path'}<ArrowRight size={15}/></button>{projects.length > 0 && <button className="project-count" onClick={() => onProjects(course.id)}>{projects.length} {projects.length === 1 ? 'project' : 'projects'}</button>}</div>
      </article>
    })}</div>
    <p className="hub-footnote">A lesson is complete when all its checks pass. Each project starts from one public source file. CUDA lessons run in a CPU simulator.</p>
  </div></main>
}
