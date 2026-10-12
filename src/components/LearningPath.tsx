import {useEffect, useRef, useState} from 'react'
import {ArrowRight, CheckCircle2, LoaderCircle, Play} from 'lucide-react'
import {api} from '../api'
import type {Course, Lesson, State} from '../types'
import type {LearnerExperience, LearnerGoal, LearningPathResponse} from '../learningPathTypes'
import Onboarding, {experienceChoices, goalChoices} from './Onboarding'
import './learningPath.css'

export default function LearningPath({courses, lessons, state, newLearner, onSelect, onBrowse, onChange}: {
  courses: Course[]; lessons: Lesson[]; state: State; newLearner: boolean
  onSelect: (id: string) => void; onBrowse: () => void
  onChange: (data: LearningPathResponse | null) => void
}) {
  const [data, setData] = useState<LearningPathResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [saveError, setSaveError] = useState('')
  const [busy, setBusy] = useState(false)
  const [editing, setEditing] = useState(false)
  const [saved, setSaved] = useState(false)
  const [retry, setRetry] = useState(0)
  const heading = useRef<HTMLHeadingElement>(null)
  const section = useRef<HTMLElement>(null)
  const dismissed = useRef(false)
  const focusAfterChange = useRef(false)

  useEffect(() => {if (!loading) onChange(data)}, [data, loading, onChange])

  useEffect(() => {
    let active = true
    setLoading(true); setLoadError('')
    void api<LearningPathResponse>('/learning-path').then(result => {
      if (!active) return
      setData(result)
      if (!result.profile && newLearner && !dismissed.current) setEditing(true)
    }).catch(error => {if (active) setLoadError(error instanceof Error ? error.message : 'Could not load your learning path.')}).finally(() => {if (active) setLoading(false)})
    return () => {active = false}
  }, [retry, newLearner])

  useEffect(() => {
    if (!focusAfterChange.current) return
    // Opening the optional form is a user action; move to its question. Saving/skipping returns to the summary.
    const target = editing ? section.current?.querySelector<HTMLHeadingElement>('#onboarding-question') : heading.current
    target?.focus({preventScroll: true})
    target?.scrollIntoView({block: 'start'})
    focusAfterChange.current = false
  }, [editing, data])

  async function save(answers: {experience: LearnerExperience; goal: LearnerGoal}) {
    setBusy(true); setSaveError('')
    try {
      const result = await api<LearningPathResponse>('/learning-path', answers)
      if (!result.profile || !result.recommendation) throw new Error('The server did not return a saved learning path.')
      focusAfterChange.current = true
      setData(result); setEditing(false); setSaved(true)
    } catch (error) {setSaveError(error instanceof Error ? error.message : 'Could not save your answers.')}
    finally {setBusy(false)}
  }
  function edit() {setSaveError(''); setSaved(false); focusAfterChange.current = true; setEditing(true)}
  function skip() {dismissed.current = true; setSaveError(''); focusAfterChange.current = true; setEditing(false)}
  async function clearAnswers() {
    setBusy(true); setSaveError('')
    try {
      const result = await api<LearningPathResponse>('/learning-path', {reset: true})
      if (result.profile || result.recommendation) throw new Error('The server did not confirm that your answers were cleared.')
      dismissed.current = true; focusAfterChange.current = true
      setData(result); setSaved(false); setEditing(false)
    } catch (error) {setSaveError(error instanceof Error ? error.message : 'Could not clear your answers.')}
    finally {setBusy(false)}
  }

  if (loading) return <section className="personal-learning-path learning-path-loading" aria-label="Your learning path"><LoaderCircle size={18} className="spin"/><p role="status">Loading your learning path…</p></section>
  if (loadError) return <section className="personal-learning-path" aria-labelledby="learning-path-heading"><h2 id="learning-path-heading">Your learning path</h2><p className="learning-path-error" role="alert">{loadError}</p><p className="learning-path-note">You can still browse every path and use the beginner guide.</p><button className="secondary-button" onClick={() => setRetry(value => value + 1)}>Try again</button></section>
  if (editing) return <section ref={section} className="personal-learning-path"><Onboarding profile={data?.profile ?? null} busy={busy} error={saveError} onSave={answers => void save(answers)} onSkip={skip}/></section>

  const profile = data?.profile
  const recommendation = data?.recommendation
  if (!profile || !recommendation) return <section ref={section} className="personal-learning-path learning-path-invitation" aria-labelledby="learning-path-heading">
    <div><h2 ref={heading} tabIndex={-1} id="learning-path-heading">Make your own learning path</h2><p>Answer two quick questions about your experience and interests. We’ll suggest where to start and what to try next.</p><p className="learning-path-note">Optional · You can change your answers anytime.</p></div>
    <button className="primary-button" onClick={edit}>Find my starting point<ArrowRight size={16}/></button>
  </section>

  // Use the current lesson state, so completing an exercise immediately updates the route when returning here.
  const steps = recommendation.steps.map(step => ({...step, course: courses.find(course => course.id === step.courseId), lessons: lessons.filter(lesson => lesson.course === step.courseId)})).filter(step => step.course && step.lessons.length)
  const orderedLessons = steps.flatMap(step => step.lessons)
  const completed = orderedLessons.filter(lesson => state.completed[lesson.id]).length
  const total = orderedLessons.length
  const next = orderedLessons.find(lesson => !state.completed[lesson.id])
  const experience = experienceChoices.find(choice => choice.id === profile.experience)?.title
  const goal = goalChoices.find(choice => choice.id === profile.goal)?.title

  return <section ref={section} className="personal-learning-path" aria-labelledby="learning-path-heading">
    <div className="learning-path-header"><div><h2 ref={heading} tabIndex={-1} id="learning-path-heading">{recommendation.title}</h2><p>{recommendation.summary}</p></div><button className="text-button" onClick={edit} disabled={busy}>Change answers</button></div>
    <p className="learning-path-answers">Your choices: {experience} · {goal}</p>
    {saved && <p className="learning-path-saved" role="status"><CheckCircle2 size={15}/>Answers saved on this computer.</p>}
    {saveError && <p className="learning-path-error" role="alert">{saveError} Your saved path is still shown. Try clearing your answers again.</p>}
    <div className="learning-path-progress"><label htmlFor="personal-path-progress">{completed} of {total} lessons complete</label><progress id="personal-path-progress" value={completed} max={total || 1}/></div>
    <ol className="personal-path-steps">{steps.map(step => {
      const done = step.lessons.filter(lesson => state.completed[lesson.id]).length
      const nextInCourse = step.lessons.find(lesson => !state.completed[lesson.id]) ?? step.lessons[0]
      return <li key={step.courseId}><button onClick={() => onSelect(nextInCourse.id)}><span className="personal-path-title"><strong>{step.course!.title}</strong><small>{done}/{step.lessons.length} complete{done === step.lessons.length ? ' · Review' : ''}</small></span><span className="personal-path-reason">{step.reason}</span><ArrowRight size={17} aria-hidden="true"/></button></li>
    })}</ol>
    <div className="learning-path-footer">{next ? <><button className="primary-button" onClick={() => onSelect(next.id)}><Play size={16}/>{completed ? 'Resume my path' : 'Start my path'}<ArrowRight size={16}/></button><p>Up next: {next.title}</p></> : <><p className="learning-path-finished"><CheckCircle2 size={17}/>{total ? 'You’ve completed this learning path. Revisit a step or explore something new.' : 'Browse the available paths to choose your next lesson.'}</p><button className="secondary-button" onClick={onBrowse}>Explore all lessons<ArrowRight size={16}/></button></>}</div>
    <p className="learning-path-note">A suggested order, with every lesson open. Changing your answers keeps all your existing work.</p>
    <button className="text-button" onClick={() => void clearAnswers()} disabled={busy}>{busy ? 'Clearing answers…' : 'Clear answers'}</button>
  </section>
}
