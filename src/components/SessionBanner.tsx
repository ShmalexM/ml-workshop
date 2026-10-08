import {useEffect,useState} from 'react'
import {connectMessage,onSessionChange} from '../api'

/** A plain notice while this browser has no valid session token. The rest of the page stays open. */
export default function SessionBanner(){
 const [connected,setConnected]=useState(true)
 useEffect(()=>onSessionChange(setConnected),[])
 return connected?null:<p className="session-banner" role="status">{connectMessage}</p>
}
