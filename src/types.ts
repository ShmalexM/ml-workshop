export type Orientation = {welcome:string;goal:string;prerequisites:string[];terms:[string,string][]}
export type GuidedExample = {code:string;output:string;steps:string[];question:string;choices:string[];answer:number;feedback:string}
export type LearningStage = 'understand'|'example'|'practice'
export type Course = {orientation:Orientation;id:string;title:string;subtitle:string;icon:string;color:string}
export type Lesson = {example:GuidedExample;language?:'python'|'javascript';id:string;course:string;title:string;minutes:number;xp:number;intro:string;concept:string;diagram:string[];explanation:string;tasks:string[];tip:string;hints:string[];starter:string;reference:{title:string;url:string};checkLabels:string[]}
export type State = {draftUpdated?:Record<string,number>;drafts:Record<string,string>;notes:Record<string,string>;completed:Record<string,{at:string;xp:number}>;currentLesson:string;activity:string[]}
export type Runtime = {python:string;javascript:boolean;packages:Record<string,string|null>;cudaMode:string}
export type RunResult = {stdout:string;error:string|null;checks:{label:string;passed:boolean;detail?:string}[];passed:boolean;duration:number;state?:State}
