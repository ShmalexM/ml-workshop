export type Check = {type:'contains';value:string}|{type:'regex';pattern:string}
export type Verify = {commands:string[];expect:string;paste?:string;check?:Check}
export type ProjectTask = {id:string;title:string;minutes:number;lessons:string[];source:{path:string;lines:[number,number];url:string};do:string;change:string;starter?:{path:string;text:string};verify:Verify}
export type Platform = 'macos'|'linux'|'windows'
export type Project = {level:string;firstLesson:string;entryPoint:{label:string;url:string};why:string;requirements:string;id:string;title:string;summary:string;tracks:string[];visibility:'public'|'private'|'local';repoUrl:string;localPath:string;evidence:string;steps:string[];deliverable:string
 // Hands-on fields. A project with an empty task list shows the walkthrough steps instead.
 goal:string;pin:{ref:string;label:string}|null;prerequisites:{lessons:string[];projects:string[];tools:string[]};minutes:{setup:number;tasks:number;stretch:number};platforms:Platform[];setup:{unix:string[];windows:string[]};run:Verify|null;tasks:ProjectTask[];stretch:ProjectTask|null;troubleshooting:{problem:string;fix:string}[]}
/** Saved per task: notes and when a pasted output last passed its check. Pasted text itself is never saved. */
export type TaskProgress = {notes?:string;verifiedAt?:number}
export type ProjectState = {notes:string;reviewed:number[];updatedAt:number;tasks?:Record<string,TaskProgress>}
export type RetiredProject = {id:string;title:string;steps:number}
export type Portfolio = {version:number;projects:Project[];coverage:string;updatedAt:string;error?:string;retired?:RetiredProject[];projectState:Record<string,ProjectState>}
