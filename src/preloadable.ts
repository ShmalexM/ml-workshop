import {lazy,type ComponentType} from 'react'

type Loaded<T>={default:T}

/** React.lazy with a preload() that starts the download early, for example on hover. Once the module has
 * loaded, the component renders at once: React.lazy alone would show the fallback for a frame first. */
export function preloadable<T extends ComponentType<any>>(load:()=>Promise<Loaded<T>>){
 let loaded:Loaded<T>|undefined,pending:Promise<Loaded<T>>|undefined
 // A failed download is tried again on the next call.
 const preload=()=>pending??=load().then(module=>loaded=module,error=>{pending=undefined;throw error})
 // React.lazy takes any thenable. This one calls back at once when the module is already here, so nothing suspends.
 const Component=lazy(()=>(loaded?{then:(resolve:(module:Loaded<T>)=>void)=>resolve(loaded!)}:preload()) as Promise<Loaded<T>>)
 return Object.assign(Component,{
  /** Starts loading the module. Errors are left to the component, which shows them when it renders. */
  preload:()=>{preload().catch(()=>{})},
 })
}
