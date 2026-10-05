import {useId} from 'react'

type Look={body:[string,string];lid:[string,string];band:string;rivet:string;glow:string|null;lock:string}
const LOOKS:Record<number,Look>={
 1:{body:['#8a6038','#5a3c22'],lid:['#946840','#634327'],band:'#6b5238',rivet:'#8d7656',glow:null,lock:'#7a6a55'},
 2:{body:['#6a4628','#3e2814'],lid:['#74502e','#462e18'],band:'#4d535c',rivet:'#9aa3ad',glow:null,lock:'#8a929c'},
 3:{body:['#33507e','#172742'],lid:['#3d5e92','#1c2f50'],band:'#a9c1e2',rivet:'#e6f0ff',glow:'#4ea7ff',lock:'#cfe1ff'},
 4:{body:['#2a1a20','#0f080b'],lid:['#33202a','#140a0e'],band:'#4a2a30',rivet:'#a0303a',glow:'#ff2b3a',lock:'#d8cbb0'},
 5:{body:['#f0c35a','#a8711c'],lid:['#f8d478','#b47a22'],band:'#fff0c0',rivet:'#fff8e0',glow:'#ff9a1f',lock:'#ff9a1f'},
}

/** Chest illustration for each reward tier, closed or open with a light beam in `beam` color. */
export default function ChestArt({tier,open=false,beam,size=120,className=''}:{tier:number;open?:boolean;beam?:string;size?:number;className?:string}){
 const uid=useId().replace(/:/g,'');const t=Math.min(5,Math.max(1,tier));const L=LOOKS[t];const id=(n:string)=>`${uid}-${n}`
 const light=beam||L.glow||'#ffe7a8'
 return <svg viewBox="0 0 120 110" width={size} height={size*110/120} className={`chest-art tier-${t}${open?' open':''} ${className}`} aria-hidden>
  <defs>
   <linearGradient id={id('body')} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={L.body[0]}/><stop offset="1" stopColor={L.body[1]}/></linearGradient>
   <linearGradient id={id('lid')} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={L.lid[0]}/><stop offset="1" stopColor={L.lid[1]}/></linearGradient>
   <radialGradient id={id('halo')}><stop offset="0" stopColor={light} stopOpacity=".75"/><stop offset="1" stopColor={light} stopOpacity="0"/></radialGradient>
   <linearGradient id={id('beam')} x1="0" y1="1" x2="0" y2="0"><stop offset="0" stopColor={light} stopOpacity=".95"/><stop offset="1" stopColor={light} stopOpacity="0"/></linearGradient>
  </defs>
  {(t===5||open)&&<g className="chest-rays" style={{transformOrigin:'60px 58px'}}>{Array.from({length:12},(_,i)=><path key={i} d="M60 58 L56 0 L64 0Z" fill={light} opacity={open?.22:.12} transform={`rotate(${i*30} 60 58)`}/>)}</g>}
  {(L.glow||open)&&<ellipse cx="60" cy="62" rx="58" ry="42" fill={`url(#${id('halo')})`} opacity={open?1:.55}/>}
  <ellipse cx="60" cy="100" rx="44" ry="6" fill="#000" opacity=".35"/>
  {t===5&&<g fill="#b47a22">{[24,96].map(x=><path key={x} d={`M${x-7} 96 q7 -10 14 0 l-3 4 h-8z`}/>)}</g>}
  <rect x="16" y="54" width="88" height="42" rx="4" fill={`url(#${id('body')})`} stroke="#120c08" strokeWidth="1.5"/>
  {t<=2&&[30,46,62,78,94].map(x=><line key={x} x1={x} y1="56" x2={x} y2="95" stroke="#000" strokeOpacity=".22" strokeWidth="1.2"/>)}
  {t>=2&&[26,94].map(x=><g key={x}><rect x={x-5} y="54" width="10" height="42" fill={L.band}/>{[60,72,84].map(y=><circle key={y} cx={x} cy={y} r="1.6" fill={L.rivet}/>)}</g>)}
  {t===1&&<path d="M16 72 Q60 80 104 72" stroke="#c8b08a" strokeWidth="2.2" fill="none"/>}
  {t===3&&<g className="chest-runes" fill="none" stroke={L.glow!} strokeWidth="1.6" strokeLinecap="round">{[40,52,68,80].map((x,i)=><path key={x} d={i%2?`M${x} 64 l4 6 l-4 6`:`M${x} 64 v12 m-4 -6 h8`}/>)}</g>}
  {t===4&&<g className="chest-cracks" stroke={L.glow!} strokeWidth="1.4" fill="none"><path d="M34 58 l6 10 l-4 8 l7 12"/><path d="M84 57 l-5 9 l6 7 l-4 14"/><path d="M58 90 l3 -7 l-4 -5"/></g>}
  {t===5&&<g stroke={L.band} strokeWidth="1.4" fill="none"><path d="M18 60 h84 M18 90 h84"/><path d="M40 75 q20 -12 40 0 q-20 12 -40 0z"/></g>}
  <g className="chest-lid" style={{transformOrigin:'60px 54px',transformBox:'view-box'}}>
   <path d="M14 54 Q14 26 60 24 Q106 26 106 54Z" fill={`url(#${id('lid')})`} stroke="#120c08" strokeWidth="1.5"/>
   {t<=2&&<path d="M22 44 Q60 36 98 44" stroke="#000" strokeOpacity=".2" strokeWidth="1.2" fill="none"/>}
   {t>=2&&[26,94].map(x=><path key={x} d={`M${x-5} 54 Q${x-5} ${x<60?34:34} ${x} ${x<60?31:31} Q${x+5} 33 ${x+5} 54Z`} fill={L.band}/>)}
   {t===3&&<path d="M44 40 h32" stroke={L.glow!} strokeWidth="1.6" className="chest-runes"/>}
   {t===4&&[[18,40,-1],[102,40,1]].map(([x,y,s])=><path key={x} d={`M${x} ${y} q${s*10} -16 ${s*4} -26 q${s*-2} 14 ${s*-12} 20z`} fill="#d8cbb0" stroke="#3a2a20" strokeWidth=".8"/>)}
   {t===5&&<><path d="M30 46 Q60 30 90 46" stroke={L.band} strokeWidth="2" fill="none"/>{[44,60,76].map(x=><circle key={x} cx={x} cy={x===60?33:37} r="2.6" fill="#ff5a3a" stroke="#fff0c0" strokeWidth=".8"/>)}</>}
  </g>
  {open&&<path className="chest-beam" d="M28 56 L8 -10 L112 -10 L92 56Z" fill={`url(#${id('beam')})`}/>}
  <g transform="translate(60 62)">
   {t===4?<g><path d="M-8 -8 h16 v10 q-8 8 -16 0z" fill={L.lock} stroke="#3a2a20"/><circle cx="-3.5" cy="-3" r="1.7" fill={L.glow!}/><circle cx="3.5" cy="-3" r="1.7" fill={L.glow!}/></g>
   :<g><rect x="-7" y="-8" width="14" height="14" rx="2" fill={L.lock} stroke="#1a120c"/>{t>=3?<path d="M0 -6 l4 5 l-4 5 l-4 -5z" fill={L.glow||'#ff9a1f'}/>:<rect x="-1.4" y="-3" width="2.8" height="6" rx="1.2" fill="#1a120c"/>}</g>}
  </g>
  {t>=4&&<g className="chest-sparks">{[[22,30],[98,24],[60,14],[40,20],[84,40]].map(([x,y],i)=><circle key={i} cx={x} cy={y} r={t===5?1.8:1.3} fill={L.glow!} style={{animationDelay:`${i*.4}s`}}/>)}</g>}
 </svg>
}
