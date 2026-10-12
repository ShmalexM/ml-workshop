import {useEffect, useRef, useState} from 'react'
import type {FormEvent} from 'react'
import {ArrowLeft, ArrowRight, LoaderCircle} from 'lucide-react'
import type {LearnerExperience, LearnerGoal, LearnerProfile} from '../learningPathTypes'

export const experienceChoices: {id: LearnerExperience; title: string; detail: string}[] = [
  {id: 'new', title: 'I’m starting from zero', detail: 'I’ve never coded, or I’m not sure where to begin.'},
  {id: 'some', title: 'I’ve tried a little code', detail: 'I’d like a refresher before the more advanced ideas.'},
  {id: 'confident', title: 'I’m comfortable with Python', detail: 'I can already use functions, lists and loops.'},
]
export const goalChoices: {id: LearnerGoal; title: string; detail: string}[] = [
  {id: 'explore', title: 'Explore and find my direction', detail: 'Try a little ML, web, data and AI agent work.'},
  {id: 'ml', title: 'Understand machine learning', detail: 'Learn how models work and practice ML engineering skills.'},
  {id: 'agents', title: 'Learn AI agent engineering', detail: 'Practice agent loops, tool contracts and evaluation with local examples.'},
  {id: 'web', title: 'Build websites and apps', detail: 'Practice the skills used in product and software engineering.'},
  {id: 'data', title: 'Work with data', detail: 'Practice data pipelines, services and reliability.'},
]

export default function Onboarding({profile, busy, error, onSave, onSkip}: {
  profile: LearnerProfile | null
  busy: boolean
  error: string
  onSave: (answers: {experience: LearnerExperience; goal: LearnerGoal}) => void
  onSkip: () => void
}) {
  const [step, setStep] = useState(1)
  const [experience, setExperience] = useState<LearnerExperience | null>(profile?.experience ?? null)
  const [goal, setGoal] = useState<LearnerGoal | null>(profile?.goal ?? null)
  const heading = useRef<HTMLHeadingElement>(null)
  const shouldFocus = useRef(false)

  useEffect(() => {
    if (shouldFocus.current && heading.current) {
      heading.current.focus({preventScroll: true})
      heading.current.scrollIntoView({block: 'start'})
    }
    shouldFocus.current = false
  }, [step])

  function move(next: number) {shouldFocus.current = true; setStep(next)}
  function submit(event: FormEvent) {
    event.preventDefault()
    if (busy || !experience) return
    if (step === 1) move(2)
    else if (goal) onSave({experience, goal})
  }

  return <form className="learner-onboarding" onSubmit={submit} aria-labelledby="onboarding-question" aria-busy={busy}>
    <p className="onboarding-step" aria-live="polite">Your learning path · Question {step} of 2</p>
    <h2 id="onboarding-question" tabIndex={-1} ref={heading}>{step === 1 ? 'How comfortable are you with code?' : 'What would you like to learn or build?'}</h2>
    <p className="onboarding-intro">{step === 1 ? 'There’s no test and no wrong starting point. We’ll suggest an order you can change anytime.' : 'Pick what interests you most right now. These are practice paths for exploring skills and career directions.'}</p>
    <fieldset disabled={busy} className="onboarding-choices">
      <legend className="onboarding-legend">{step === 1 ? 'Choose your coding experience' : 'Choose your main learning goal'}</legend>
      {step === 1 ? experienceChoices.map(choice => <label key={choice.id} className={'onboarding-choice' + (experience === choice.id ? ' selected' : '')}>
        <input type="radio" name="experience" value={choice.id} checked={experience === choice.id} onChange={() => setExperience(choice.id)}/>
        <span><strong>{choice.title}</strong><small>{choice.detail}</small></span>
      </label>) : goalChoices.map(choice => <label key={choice.id} className={'onboarding-choice' + (goal === choice.id ? ' selected' : '')}>
        <input type="radio" name="goal" value={choice.id} checked={goal === choice.id} onChange={() => setGoal(choice.id)}/>
        <span><strong>{choice.title}</strong><small>{choice.detail}</small></span>
      </label>)}
    </fieldset>
    {error && <p className="learning-path-error" role="alert">{error} Your answers haven’t been confirmed as saved. Try again or skip for now.</p>}
    <div className="onboarding-actions">
      {step === 2 && <button type="button" className="secondary-button" onClick={() => move(1)} disabled={busy}><ArrowLeft size={16}/>Back</button>}
      <button type="submit" className="primary-button" disabled={busy || (step === 1 ? !experience : !goal)}>{busy ? <><LoaderCircle size={16} className="spin"/>Saving…</> : step === 1 ? <>Next<ArrowRight size={16}/></> : <>Show my learning path<ArrowRight size={16}/></>}</button>
      <button type="button" className="text-button onboarding-skip" disabled={busy} onClick={onSkip}>{profile ? 'Keep my current path' : 'Skip for now'}</button>
    </div>
    <p className="learning-path-note">Optional · All lessons stay open. Answers are saved on this computer when you finish.</p>
  </form>
}
