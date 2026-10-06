// Pixel-grid loader adapted from beautiful-ui LoadingState (github.com/slev12397/beautiful-ui), MIT License, Copyright (c) 2026 Shane Levine; see THIRD_PARTY_NOTICES.md.
import {useEffect,useState} from 'react'
import './runStatus.css'

// 3×3 cells light up column by column, middle row first, so a chevron sweeps to the right.
const delays=Array.from({length:9},(_,i)=>(i%3+Math.abs(Math.floor(i/3)-1))*90)

export function PixelLoader(){
 return <span className="pixel-loader" aria-hidden="true">{delays.map((delay,i)=><i key={i} style={{animationDelay:delay+'ms'}}/>)}</span>
}

/** Loader, label and seconds since the run started. The timer is hidden from screen readers so it is not read out on every tick. */
export function RunStatus(){
 const [start]=useState(()=>performance.now());const [now,setNow]=useState(start)
 useEffect(()=>{const timer=setInterval(()=>setNow(performance.now()),100);return()=>clearInterval(timer)},[])
 return <span className="run-status"><PixelLoader/><span>Running…</span><span className="run-elapsed" aria-hidden="true">{((now-start)/1000).toFixed(1)}s</span></span>
}
