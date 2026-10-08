/** Battle graphics from Settings → Hero game. Light draws at most 1.5 pixels per CSS pixel and skips bloom.
 * The choice is kept in this browser, because it depends on this computer's graphics. */
export type BattleGraphics='standard'|'light'
export const LIGHT_PIXEL_RATIO=1.5

const key='ml-workshop-battle-graphics'
// The choice made on this page. It still applies when the browser cannot store it.
let chosen:BattleGraphics|null=null

export function readBattleGraphics():BattleGraphics{
 if(chosen)return chosen
 try{return localStorage.getItem(key)==='light'?'light':'standard'}catch{return 'standard'}
}

export function saveBattleGraphics(value:BattleGraphics){
 chosen=value
 try{localStorage.setItem(key,value)}catch{/* storage unavailable: the choice lasts until reload */}
}
