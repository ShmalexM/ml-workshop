import type {Check} from './portfolioTypes'

/** Windows line endings and trailing spaces differ between terminals, so checks ignore them. */
export function normalizeOutput(text:string){
 return text.replace(/\r\n?/g,'\n').split('\n').map(line=>line.replace(/[ \t]+$/,'')).join('\n')
}

/** Runs in the browser only. Returns null when this browser cannot compile the pattern. */
export function runCheck(check:Check,text:string):boolean|null{
 const output=normalizeOutput(text)
 if(check.type==='contains')return output.includes(check.value)
 try{return new RegExp(check.pattern,'m').test(output)}catch{return null}
}

export function formatMinutes(total:number){
 const hours=Math.floor(total/60),minutes=total%60
 return hours?`${hours} h${minutes?` ${minutes} min`:''}`:`${minutes} min`
}
