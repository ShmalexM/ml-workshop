import React from 'react'
import {createRoot} from 'react-dom/client'
// Global styles load in a fixed order (base, engineering, books) before any component, so later files win.
import './styles.css'
import './engineering.css'
import './bookStyles.css'
import App from './App'
import ErrorBoundary from './components/ErrorBoundary'

// After a rebuild an open tab can request a chunk that no longer exists. Reload once to pick up the new build.
const reloadKey='workshop-chunk-reload'
addEventListener('vite:preloadError',event=>{
 try{if(sessionStorage.getItem(reloadKey))return;sessionStorage.setItem(reloadKey,'1')}catch{return}
 event.preventDefault();location.reload()
})

createRoot(document.getElementById('root')!).render(<React.StrictMode><ErrorBoundary><App/></ErrorBoundary></React.StrictMode>)

// Once this build has run for 10 seconds, clear the flag so a later rebuild can reload the tab again.
// Clearing it at startup could loop if a chunk failed on every load.
setTimeout(()=>{try{sessionStorage.removeItem(reloadKey)}catch{/* storage unavailable */}},10000)
