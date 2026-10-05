import {api} from '../api'
import type {Battle,BattleResult,Chest,GameState,GameSummary,Item,Slot} from './types'

type WithGame<T={}>={game:GameState}&T

/** The few numbers the app shell needs (nav badge, toasts) from a full game state. */
export const summarize=(g:GameState):GameSummary=>({enabled:g.enabled,hero:!!g.hero,unopened:g.chests.unopened.length,battles:g.battles.available,stage:g.campaign.stage})

export const gameApi={
 state:()=>api<GameState>('/game'),
 summary:()=>api<GameSummary>('/game/summary'),
 create:(name:string,race:string,cls:string)=>api<WithGame>('/game/hero',{name,race,class:cls}),
 open:(source:string)=>api<WithGame<{chest:Chest;items:Item[]}>>('/game/open',{source}),
 equip:(itemId:number)=>api<WithGame>('/game/equip',{itemId}),
 unequip:(slot:Slot)=>api<WithGame>('/game/unequip',{slot}),
 discard:(itemIds:number[])=>api<WithGame>('/game/discard',{itemIds}),
 settings:(enabled:boolean)=>api<WithGame>('/game/settings',{enabled}),
 retire:()=>api<WithGame>('/game/retire',{confirm:'RETIRE'}),
 startBattle:()=>api<WithGame<{battle:Battle}>>('/game/battle/start',{}),
 finishBattle:(body:{battleId:number;outcome:'victory'|'defeat'|'retreat';bossDamage:number;kills:number;seconds:number})=>api<WithGame<{result:BattleResult}>>('/game/battle/finish',body),
}
