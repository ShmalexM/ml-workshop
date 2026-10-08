export type Orientation = {welcome:string;goal:string;prerequisites:string[];terms:[string,string][]}
export type GuidedExample = {code:string;output:string;steps:string[];question:string;choices:string[];answer:number;feedback:string}
export type LearningStage = 'understand'|'example'|'practice'
export type EditorPrefs = {suggestions:boolean;dark:boolean}
export type Course = {orientation:Orientation;id:string;title:string;subtitle:string;icon:string;color:string}
/** A glossary term. match lists the exact words that link it in lesson text; lesson is the lesson that teaches it. */
export type GlossaryEntry = {id:string;term:string;sense:string|null;definition:string;lesson:string|null;match:string[]}
/** glossary holds the ids of the terms in the intro and explanation, in order of first appearance. */
export type Lesson = {example:GuidedExample;language?:'python'|'javascript';id:string;course:string;title:string;minutes:number;xp:number;intro:string;concept:string;diagram:string[];explanation:string;tasks:string[];tip:string;hints:string[];starter:string;reference:{title:string;url:string};checkLabels:string[];glossary:string[]}
export type State = {draftUpdated?:Record<string,number>;drafts:Record<string,string>;notes:Record<string,string>;completed:Record<string,{at:string;xp:number}>;currentLesson:string;activity:string[]}
export type Runtime = {python:string;javascript:boolean;packages:Record<string,string|null>;cudaMode:string}
/** call, expected and got are set when the check compares one value; explanation is a plain-language line. */
export type CheckResult = {label:string;passed:boolean;detail?:string;call?:string;expected?:string;got?:string;explanation?:string}
/** summary is the error's last line with its line number; explanation is a plain-language line. */
/** stale is set in the browser when the code changes after this run. */
export type RunResult = {stdout:string;error:string|null;summary?:string|null;explanation?:string|null;checks:CheckResult[];passed:boolean;duration:number;state?:State;stale?:boolean}
