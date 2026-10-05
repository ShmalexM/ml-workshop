import {Component,type ReactNode} from 'react'

/** Keeps a render error or a missing chunk from leaving a blank window. */
export default class ErrorBoundary extends Component<{children:ReactNode},{error:Error|null}>{
 state={error:null as Error|null}
 static getDerivedStateFromError(error:Error){return {error}}
 render(){
  if(!this.state.error)return this.props.children
  return <main className="loading-screen" role="alert">
   <h1>Engineering Workshop hit an error</h1>
   <p>Your drafts are saved in this browser and on this Mac. Reload to continue.</p>
   <p className="error-detail">{this.state.error.message}</p>
   <button className="primary-button" onClick={()=>location.reload()}>Reload</button>
  </main>
 }
}
