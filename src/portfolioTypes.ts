export type Project = {level:string;firstLesson:string;entryPoint:{label:string;url:string};why:string;requirements:string;id:string;title:string;summary:string;tracks:string[];visibility:'public'|'private'|'local';repoUrl:string;localPath:string;evidence:string;steps:string[];deliverable:string}
export type ProjectState = {notes:string;reviewed:number[];updatedAt:number}
export type Portfolio = {version:number;projects:Project[];coverage:string;updatedAt:string;error?:string;projectState:Record<string,ProjectState>}
