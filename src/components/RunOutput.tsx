import type {ReactNode} from 'react'
import type {CheckResult,RunResult} from '../types'
import './runOutput.css'

// Explanations mark code with backticks, as in `return`.
const withCode=(text:string)=>text.split('`').map((part,i)=>i%2?<code key={i}>{part}</code>:part)

/** The plain-language line first, then the error's last line. The full traceback stays closed until opened. */
/** action, such as Explain this error, goes under the error lines. */
export function ErrorResult({result,action}:{result:RunResult;action?:ReactNode}){
 return <div className="error-result"><strong>Error</strong>{result.explanation&&<p className="error-explanation">{withCode(result.explanation)}</p>}{result.summary?<><pre className="error-summary">{result.summary}</pre><details className="full-error"><summary>Full error</summary><pre>{result.error}</pre></details></>:<pre>{result.error}</pre>}{result.stdout&&<pre>{result.stdout}</pre>}{action}</div>
}

/** A failed check: its explanation, then the call with the expected and actual values when the check compares one value. */
export function CheckDetail({check}:{check:CheckResult}){
 return <>{check.explanation&&<p className="check-explanation">{withCode(check.explanation)}</p>}{check.got!==undefined?<dl className="check-values">{check.call&&<div><dt>Call</dt><dd>{check.call}</dd></div>}<div><dt>Expected</dt><dd>{check.expected}</dd></div><div><dt>Got</dt><dd className="got">{check.got}</dd></div></dl>:<p>{check.detail}</p>}</>
}
