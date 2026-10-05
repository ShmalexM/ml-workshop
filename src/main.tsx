import React from 'react'
import {createRoot} from 'react-dom/client'
// Global styles load in a fixed order (base, engineering, books) before any component, so later files win.
import './styles.css'
import './engineering.css'
import './bookStyles.css'
import App from './App'
import ErrorBoundary from './components/ErrorBoundary'

// After a rebuild an open tab can request a chunk that no longer exists. Reload once to pick up the new build.
addEventListener('vite:preloadError',event=>{
 try{if(sessionStorage.getItem('workshop-chunk-reload'))return;sessionStorage.setItem('workshop-chunk-reload','1')}catch{return}
 event.preventDefault();location.reload()
})

createRoot(document.getElementById('root')!).render(<React.StrictMode><ErrorBoundary><App/></ErrorBoundary></React.StrictMode>)
