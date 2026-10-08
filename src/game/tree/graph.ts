import type {TreeCatalog,TreeNode} from '../types'

/** The passive tree as a graph. Mirrors the path and refund rules in backend/game_tree.py. */
export type Graph={nodes:TreeNode[];byId:Map<string,TreeNode>;adj:Map<string,string[]>;starts:Set<string>}

export function graphOf(tree:TreeCatalog):Graph{
 const byId=new Map(tree.nodes.map(n=>[n.id,n]))
 const adj=new Map(tree.nodes.map(n=>[n.id,n.links]))
 return {nodes:tree.nodes,byId,adj,starts:new Set(tree.nodes.filter(n=>n.kind==='start').map(n=>n.id))}
}

export const startOf=(g:Graph,cls:string)=>g.nodes.find(n=>n.kind==='start'&&n.class===cls)?.id||''

/** Nodes of `set` reachable from `start` through `set`. */
export function reachable(g:Graph,start:string,set:Set<string>):Set<string>{
 const seen=new Set([start]);const queue=[start]
 while(queue.length){const id=queue.shift()!;for(const next of g.adj.get(id)||[])if(set.has(next)&&!seen.has(next)){seen.add(next);queue.push(next)}}
 return seen
}

/** The shortest list of new nodes that joins `target` to the allocation, or null when another class's start blocks it. */
export function pathTo(g:Graph,start:string,allocated:Set<string>,target:string):string[]|null{
 if(allocated.has(target))return []
 const blocked=(id:string)=>g.starts.has(id)&&id!==start
 if(blocked(target))return null
 const previous=new Map<string,string|null>([...allocated].map(id=>[id,null]))
 const queue=[...allocated]
 while(queue.length){
  const id=queue.shift()!
  for(const next of [...(g.adj.get(id)||[])].sort()){
   if(previous.has(next)||blocked(next))continue
   previous.set(next,id)
   if(next===target){const path=[next];while(!allocated.has(previous.get(path[path.length-1])!))path.push(previous.get(path[path.length-1])!);return path.reverse()}
   queue.push(next)
  }
 }
 return null
}

/** Nodes that refunding `id` would cut off from the start, including `id` itself. Empty for the start. */
export function branchOf(g:Graph,start:string,allocated:Set<string>,id:string):string[]{
 if(id===start||!allocated.has(id))return []
 const rest=new Set(allocated);rest.delete(id)
 const kept=reachable(g,start,rest)
 return [...allocated].filter(n=>n!==start&&!kept.has(n))
}

/** Unallocated nodes next to the allocation: what one point can buy. */
export function frontier(g:Graph,start:string,allocated:Set<string>):Set<string>{
 const out=new Set<string>()
 for(const id of allocated)for(const next of g.adj.get(id)||[])if(!allocated.has(next)&&!(g.starts.has(next)&&next!==start))out.add(next)
 return out
}

export const sameSet=(a:Set<string>,b:Set<string>)=>a.size===b.size&&[...a].every(id=>b.has(id))

/** Where a small node sits, for lists and screen readers: the two nearest named nodes along the links. */
export function landmarks(g:Graph,id:string):string[]{
 const seen=new Set([id]);let ring=[id];const found:string[]=[]
 while(ring.length&&found.length<2){
  const next:string[]=[]
  for(const at of ring)for(const n of g.adj.get(at)||[]){if(seen.has(n))continue;seen.add(n);if(g.byId.get(n)!.kind==='small')next.push(n);else found.push(n)}
  ring=next
 }
 return found.slice(0,2)
}
