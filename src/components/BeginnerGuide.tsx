import {ArrowRight} from 'lucide-react'

export default function BeginnerGuide({newLearner, onStart}: {newLearner: boolean; onStart?: () => void}) {
  return <details className="beginner-guide" open={newLearner || undefined}>
    <summary>New to coding? Start with this quick guide</summary>
    <div className="beginner-guide-body">
      <div className="beginner-guide-grid">
        <section><h3>What is code?</h3><p>Code is a set of instructions for a computer. You’ll write small programs in Python, a language often used for machine learning, or JavaScript, a language used for websites. You don’t need to know either yet.</p><p>The <strong>editor</strong> is where you type or change those instructions. <strong>Output</strong> is what the program prints when you run it.</p></section>
        <section><h3>How a lesson works</h3><ol><li><strong>Understand:</strong> read one idea. Linked terms explain unfamiliar words.</li><li><strong>See an example:</strong> read a small program and run it to see what happens.</li><li><strong>Try it yourself:</strong> change the starter code in the editor, one task at a time.</li></ol></section>
        <section><h3>Run code and Check answer do different jobs</h3><p><strong>Run code</strong> tries your code and shows its output or an error. It’s a way to experiment.</p><p><strong>Check answer</strong> runs your code against the lesson’s tasks. Passing all checks completes the lesson. You can run and check as often as you like.</p></section>
        <section><h3>Getting stuck is part of learning</h3><p>An error is feedback, not a score. Read its message and line number, change one thing, then try again. A failed check can show what was expected and what your code returned.</p><p>Open a hint for a small nudge, or view the solution to study an approach. Your own code stays in place until you choose to load the solution.</p></section>
      </div>
      <div className="beginner-guide-bottom"><p>No coding tools to configure inside a lesson. Lessons run and progress saves on this computer. The optional AI assistant sends only the context you choose to your selected provider. You can revisit any lesson.</p>{onStart && <button className="secondary-button" onClick={onStart}>Start Python from zero<ArrowRight size={15}/></button>}</div>
    </div>
  </details>
}
