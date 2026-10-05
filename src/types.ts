export type Course = {id:string;title:string;subtitle:string;icon:string;color:string}
export type Lesson = {id:string;course:string;title:string;minutes:number;xp:number;intro:string;concept:string;diagram:string[];explanation:string;tasks:string[];tip:string;hints:string[];starter:string;reference:{title:string;url:string};checkLabels:string[]}
export type State = {draftUpdated?:Record<string,number>;drafts:Record<string,string>;notes:Record<string,string>;completed:Record<string,{at:string;xp:number}>;currentLesson:string;activity:string[]}
export type Runtime = {python:string;packages:Record<string,string|null>;cudaMode:string}
export type RunResult = {stdout:string;error:string|null;checks:{label:string;passed:boolean;detail?:string}[];passed:boolean;duration:number;state?:State}
