import * as THREE from 'three'
import {createComposer,createRenderer,environment,reducedMotion} from '../three/scene'
import {HeroModel,type Appearance} from '../three/hero'
import {Particles} from '../three/fx'
import {disposeTree,glow} from '../three/materials'
import {ARENA_RADIUS,buildArena,type Arena} from './arena'
import {ARCHETYPES,buildEnemy,stageDef,stageDmg,stageHp,type EnemyKind,type EnemyModel} from './enemies'
import {KITS,type Ability,type Kit} from './kits'
import type {HeroStats} from '../stats'

export type Key='Q'|'W'|'E'|'R'
export type BattleSetup={appearance:Appearance;classColor:string;stats:HeroStats;name:string;stage:number;stageName:string;bossName:string;bossHp:number;bossRemaining:number;seed:number
 /** Enemy health and damage multipliers from the server's expected power for the stage. */
 enemyHealth?:number;enemyDamage?:number}
export type Hud={hp:number;maxHp:number;shield:number;cds:Record<Key,number>;bossHp:number;bossMax:number;bossSeen:boolean;enraged:boolean;time:number;kills:number;bossDamage:number;buffs:{name:string;left:number;color:string}[];auto:boolean;paused:boolean}
export type BattleEnd={outcome:'victory'|'defeat'|'retreat';bossDamage:number;kills:number;seconds:number;timeUp:boolean}
type Callbacks={hud:(h:Hud)=>void;banner:(text:string,tone:'info'|'boss'|'danger'|'good')=>void;end:(r:BattleEnd)=>void}

type Unit={
 id:number;kind:EnemyKind;name:string;model:EnemyModel;pos:THREE.Vector3;facing:number;radius:number;speed:number
 hp:number;maxHp:number;dmg:number;range:number;interval:number;atk:number;ranged:string|null;elite:boolean;boss:boolean
 dead:boolean;deathT:number;root:number;stun:number;slow:number;slowT:number;burn:{dps:number;t:number;source:string}[];knock:THREE.Vector3|null;stunDr:{n:number;until:number}
 bar:HTMLDivElement|null;lunge:number;phase:number;cool:{slam:number;charge:number;rain:number;summon:number};charge:{dir:THREE.Vector3;t:number}|null
}
type Buff={name:string;t:number;color:string;damageUp?:number;reduce?:number;hot?:number;grow?:number}
type Shot={mesh:THREE.Mesh;pos:THREE.Vector3;vel:THREE.Vector3;range:number;fromHero:boolean;dmg:number;ability:Ability|null;hit:Set<number>;color:string}
type Zone={pos:THREE.Vector3;radius:number;t:number;tick:number;next:number;delay:number;ability:Ability|null;dmg:number;impact:number;hits:number;lingering:Ability|null;fromHero:boolean;meshes:THREE.Object3D[];color:string;once:boolean;line?:{dir:THREE.Vector3;length:number;width:number;boss:Unit}}
type Fade={obj:THREE.Object3D;t:number;life:number;grow:number;base:number}
type Float={el:HTMLDivElement;pos:THREE.Vector3;t:number;life:number}

const UP=new THREE.Vector3(0,1,0)
const BURN_STACKS=3
/** Auto-battle stays this far from the portal where enemies spawn. */
const PORTAL_KEEP=8
const flat=(v:THREE.Vector3)=>{v.y=0;return v}

/** League-style arena fight: click to move and attack, Q/W/E/R toward the cursor, boss damage carries over. */
export class BattleEngine{
 private renderer:THREE.WebGLRenderer;private scene=new THREE.Scene();private camera=new THREE.PerspectiveCamera(38,1,.5,140)
 private composer;private bloomPass;private particles=new Particles(2600);private arena:Arena;private hero:HeroModel
 private kit:Kit;private rng:()=>number
 private heroPos=new THREE.Vector3(0,0,9);private heroFacing=Math.PI;private hp:number;private maxHp:number;private shield={amount:0,t:0}
 private buffs:Buff[]=[];private cds:Record<Key,number>={Q:0,W:0,E:0,R:0};private autoT=0;private moveTo:THREE.Vector3|null=null;private target:Unit|null=null
 private spin:{t:number;next:number;ability:Ability}|null=null;private dash:{to:THREE.Vector3;speed:number;ability:Ability|null;hit:Set<number>;arc?:number;from?:THREE.Vector3;t?:number;total?:number}|null=null
 private spree:{targets:Unit[];next:number;ability:Ability}|null=null;private flurry:{n:number;next:number;ability:Ability;dir:THREE.Vector3}|null=null
 private units:Unit[]=[];private shots:Shot[]=[];private zones:Zone[]=[];private fades:Fade[]=[];private floats:Float[]=[];private lines:{line:THREE.Line;t:number}[]=[]
 private nextId=1;private time=0;private kills=0;private bossDamage=0;private boss:Unit|null=null;private bossSpawned=false;private enraged=false
 private wave=0;private nextWave=0;private over=false;private endT=-1;private outcome:BattleEnd['outcome']='defeat';private paused=false;private auto=false
 private phoenixUsed=false;private stormCount=0;private starwardT=8;private shake=0;private zoom=.88;private camPos=new THREE.Vector3()
 private mouse=new THREE.Vector2();private aim=new THREE.Vector3();private holding=false;private keys=new Set<string>();private raycaster=new THREE.Raycaster();private groundPlane=new THREE.Plane(UP,0)
 // Abilities aim at the cursor after mouse input, and at the target or nearest enemy after keyboard input.
 private lastInput:'mouse'|'key'='mouse';private reported=false
 private raf=0;private timer=new THREE.Timer();private hudT=0;private disposed=false;private still=reducedMotion()
 private ring:THREE.Mesh;private cursorRing:THREE.Mesh;private shieldMesh:THREE.Mesh
 // A flat class-colored copy of the hero, drawn on top of everything while the boss stands in front of it.
 private xray:THREE.Mesh[]=[];private xrayOn=false;private xrayMat:THREE.MeshBasicMaterial
 private cleanups:(()=>void)[]=[]
 constructor(private canvas:HTMLCanvasElement,private overlay:HTMLElement,private setup:BattleSetup,private cb:Callbacks){
  this.renderer=createRenderer(canvas,{shadows:true});this.scene.environment=environment(this.renderer);this.scene.environmentIntensity=.45
  const made=createComposer(this.renderer,this.scene,this.camera,{strength:.22,radius:.4,threshold:1.4});this.composer=made.composer;this.bloomPass=made.bloom
  let s=(setup.seed>>>0)||7;this.rng=()=>{s^=s<<13;s^=s>>>17;s^=s<<5;return (s>>>0)/4294967296}
  const def=stageDef(setup.stage);this.arena=buildArena(def.theme,setup.seed);this.scene.add(this.arena.group)
  this.scene.background=this.arena.fog.clone();this.scene.fog=new THREE.Fog(this.arena.fog,28,62)
  this.scene.add(this.particles.points)
  this.kit=KITS[setup.appearance.cls]||KITS.warrior
  this.hero=new HeroModel(setup.appearance);this.scene.add(this.hero.object)
  this.xrayMat=new THREE.MeshBasicMaterial({color:setup.classColor,transparent:true,opacity:.42,depthTest:false,depthWrite:false})
  const solid:THREE.Mesh[]=[];this.hero.object.traverse(o=>{const m=o as THREE.Mesh;if(m.isMesh&&!(m.material as THREE.Material).transparent)solid.push(m)})
  for(const m of solid){const x=new THREE.Mesh(m.geometry,this.xrayMat);x.renderOrder=20;x.visible=false;x.raycast=()=>{};m.add(x);this.xray.push(x)}
  this.maxHp=setup.stats.maxHp;this.hp=this.maxHp
  this.ring=new THREE.Mesh(new THREE.RingGeometry(.55,.68,32),glow(setup.classColor,.9,THREE.DoubleSide));this.ring.rotation.x=-Math.PI/2;this.ring.position.y=.03;this.scene.add(this.ring)
  this.cursorRing=new THREE.Mesh(new THREE.RingGeometry(.3,.42,24),glow('#7aff7a',.9,THREE.DoubleSide));this.cursorRing.rotation.x=-Math.PI/2;this.cursorRing.visible=false;this.scene.add(this.cursorRing)
  this.shieldMesh=new THREE.Mesh(new THREE.IcosahedronGeometry(1.2,2),glow('#fff4c0',.18,THREE.DoubleSide));this.shieldMesh.visible=false;this.scene.add(this.shieldMesh)
  this.camPos.copy(this.heroPos).add(this.camOffset())
  this.bindInput();this.resize()
  const ro=new ResizeObserver(()=>this.resize());ro.observe(canvas);this.cleanups.push(()=>ro.disconnect())
 }
 private camOffset(){return new THREE.Vector3(0,16.5,10.5).multiplyScalar(this.zoom)}
 private resize(){const w=this.canvas.clientWidth,h=this.canvas.clientHeight;if(!w||!h)return;this.renderer.setSize(w,h,false);this.composer.setSize(w,h);this.bloomPass.resolution.set(w,h);this.camera.aspect=w/h;this.camera.updateProjectionMatrix();this.particles.setScale(h*this.renderer.getPixelRatio())}
 start(){this.cb.banner(this.setup.stageName,'info');this.raf=requestAnimationFrame(this.frame)}
 setPaused(p:boolean){this.paused=p;this.pushHud(true)}
 setAuto(a:boolean){this.auto=a;this.pushHud(true)}
 retreat(){if(!this.over){this.over=true;this.outcome='retreat';this.finish()}}
 cast(key:Key,keyboard=false){if(keyboard)this.lastInput='key';this.tryCast(key)}
 /** Ends a fight that is being left without a result (another page, reload, closed tab) and returns what to save, so its boss damage is kept. */
 abandon():BattleEnd|null{
  // time is still 0 when React's development double mount tears the first engine down.
  if(this.reported||this.time===0)return null
  const outcome=this.over?this.outcome:'retreat';this.over=true;this.reported=true
  return this.result(outcome)
 }
 dispose(){
  this.disposed=true;cancelAnimationFrame(this.raf);for(const c of this.cleanups)c()
  this.hero.dispose();this.xrayMat.dispose();this.particles.dispose()
  for(const pass of this.composer.passes)pass.dispose();this.composer.dispose()
  this.scene.traverse(o=>{const m=o as THREE.Mesh;if(m.geometry)m.geometry.dispose()})
  this.arena.dispose()
  // dispose() alone keeps the WebGL context; browsers allow only a few at once.
  this.renderer.dispose();this.renderer.forceContextLoss();this.overlay.replaceChildren()
 }

 // ---------- input ----------
 private bindInput(){
  const c=this.canvas
  const toGround=(e:PointerEvent)=>{this.lastInput='mouse';const r=c.getBoundingClientRect();this.mouse.set((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1);this.raycaster.setFromCamera(this.mouse,this.camera);this.raycaster.ray.intersectPlane(this.groundPlane,this.aim)}
  const command=()=>{if(this.over)return;const enemy=this.pick();if(enemy){this.target=enemy;this.moveTo=null}else{this.target=null;this.moveTo=this.clampArena(this.aim.clone());this.cursorRing.position.set(this.moveTo.x,.04,this.moveTo.z);this.cursorRing.visible=true;this.cursorRing.scale.setScalar(1)}}
  const down=(e:PointerEvent)=>{e.preventDefault();c.focus();toGround(e);if(e.button===0||e.button===2){this.holding=true;command()}}
  const move=(e:PointerEvent)=>{toGround(e);if(this.holding&&!this.pick()){this.target=null;this.moveTo=this.clampArena(this.aim.clone())}}
  const up=()=>{this.holding=false}
  const menu=(e:Event)=>e.preventDefault()
  const wheel=(e:WheelEvent)=>{e.preventDefault();this.zoom=THREE.MathUtils.clamp(this.zoom+e.deltaY*.0008,.72,1.3)}
  const keydown=(e:KeyboardEvent)=>{
   // Leave browser shortcuts alone: Cmd+R must reload and Cmd+T must open a tab.
   if(e.metaKey||e.ctrlKey||e.altKey)return
   const k=e.key.length===1?e.key.toUpperCase():e.key
   if(['Q','W','E','R'].includes(k)){e.preventDefault();this.lastInput='key';this.tryCast(k as Key);return}
   if(k==='Escape'){e.preventDefault();if(!e.repeat)this.setPaused(!this.paused);return}
   if(k==='S'){this.moveTo=null;this.target=null;return}
   if(k==='T'){if(!e.repeat)this.setAuto(!this.auto);return}
   if(k.startsWith('Arrow')){e.preventDefault();this.lastInput='key';this.keys.add(k)}
  }
  const keyup=(e:KeyboardEvent)=>this.keys.delete(e.key)
  // A key released in another window never sends keyup here.
  const blur=()=>this.keys.clear()
  c.addEventListener('pointerdown',down);c.addEventListener('pointermove',move);addEventListener('pointerup',up);c.addEventListener('contextmenu',menu);c.addEventListener('wheel',wheel,{passive:false})
  addEventListener('keydown',keydown);addEventListener('keyup',keyup);addEventListener('blur',blur)
  this.cleanups.push(()=>{c.removeEventListener('pointerdown',down);c.removeEventListener('pointermove',move);removeEventListener('pointerup',up);c.removeEventListener('contextmenu',menu);c.removeEventListener('wheel',wheel);removeEventListener('keydown',keydown);removeEventListener('keyup',keyup);removeEventListener('blur',blur)})
 }
 private aimPoint(){
  if(this.lastInput==='mouse')return this.aim.clone()
  const t=this.target&&!this.target.dead?this.target:this.nearestEnemy(this.heroPos,40)
  return t?t.pos.clone():this.heroPos.clone().add(new THREE.Vector3(Math.sin(this.heroFacing),0,Math.cos(this.heroFacing)).multiplyScalar(6))
 }
 private pick(){let best:Unit|null=null,bd=Infinity;for(const u of this.units){if(u.dead)continue;const d=flat(u.pos.clone().sub(this.aim)).length()-u.radius;if(d<.9&&d<bd){bd=d;best=u}}return best}
 private clampArena(v:THREE.Vector3){flat(v);const r=ARENA_RADIUS-.6;if(v.length()>r)v.setLength(r);return v}

 // ---------- main loop ----------
 private frame=(now:number)=>{
  if(this.disposed)return;this.raf=requestAnimationFrame(this.frame);this.timer.update(now)
  const dt=Math.min(.05,this.timer.getDelta())
  if(!this.paused)this.update(dt)
  this.render(dt)
 }
 private update(dt:number){
  this.time+=dt
  if(!this.over)this.spawner()
  this.updateHero(dt);this.updateUnits(dt);this.updateShots(dt);this.updateZones(dt);this.updateFx(dt)
  if(!this.over&&this.time>240){this.cb.banner('Time ran out','danger');this.over=true;this.outcome='defeat';this.endT=1.2}
  if(this.endT>0){this.endT-=dt;if(this.endT<=0)this.finish()}
  this.hudT-=dt;if(this.hudT<=0)this.pushHud()
 }
 private pushHud(force=false){
  if(!force&&this.hudT>0)return;this.hudT=.1
  const boss=this.boss
  this.cb.hud({hp:Math.max(0,Math.round(this.hp)),maxHp:this.maxHp,shield:Math.round(this.shield.amount),cds:{...this.cds},bossHp:boss?Math.max(0,Math.round(boss.hp)):this.setup.bossRemaining,bossMax:this.setup.bossHp,bossSeen:this.bossSpawned,enraged:this.enraged,time:this.time,kills:this.kills,bossDamage:Math.round(this.bossDamage),buffs:this.buffs.map(b=>({name:b.name,left:b.t,color:b.color})),auto:this.auto,paused:this.paused})
 }
 private result(outcome:BattleEnd['outcome']):BattleEnd{
  return {outcome,bossDamage:Math.round(Math.min(this.bossDamage,this.setup.bossRemaining)),kills:this.kills,seconds:Math.round(this.time),timeUp:outcome==='defeat'&&this.time>240}
 }
 private finish(){
  if(this.disposed||this.reported)return
  this.reported=true;this.cb.end(this.result(this.outcome))
  this.endT=-1
 }

 // ---------- spawning ----------
 private spawner(){
  const def=stageDef(this.setup.stage)
  if(this.wave===0&&this.time>=.6){this.wave=1;this.spawnGroup(4,false);this.nextWave=12}
  else if(this.wave===1&&this.time>=this.nextWave){this.wave=2;this.cb.banner('Second wave','info');this.spawnGroup(5,this.setup.stage>=2)}
  else if(this.wave===2&&this.time>=20&&!this.bossSpawned){this.wave=3;this.spawnBoss(def.boss.kind,def.boss.scale,def.boss.variant)}
  if(this.boss&&!this.boss.dead){
   if(!this.enraged&&this.time>=150){this.enraged=true;this.cb.banner(`${this.setup.bossName} is enraged`,'danger');this.boss.dmg*=3;this.boss.speed*=1.2}
  }
 }
 private alive(){return this.units.filter(u=>!u.dead).length}
 private spawnGroup(n:number,elite:boolean){
  const def=stageDef(this.setup.stage)
  for(let i=0;i<n&&this.alive()<14;i++){const kind=def.minions[Math.floor(this.rng()*def.minions.length)];this.spawn(kind,elite&&i===0)}
 }
 private spawn(kind:EnemyKind,elite:boolean){
  const a=ARCHETYPES[kind];const s=this.setup.stage;const model=buildEnemy(kind,'',elite?1.35:1)
  const pos=this.arena.portal.clone().add(new THREE.Vector3((this.rng()-.5)*4,0,1+this.rng()*2))
  const hpMult=(this.setup.enemyHealth??stageHp(s))*(elite?2.6:1);const dmgMult=(this.setup.enemyDamage??stageDmg(s))*(elite?1.5:1)
  const u=this.makeUnit(kind,(elite?'Elite ':'')+a.name,model,pos,a.radius*(elite?1.35:1),a.speed,a.hp*hpMult*.62,a.dmg*dmgMult*.72,a.range,a.interval,a.ranged??null,elite,false)
  this.particles.burst(pos.clone().setY(1),{count:24,color:this.arena.accent,speed:2.5,size:.12,life:.6})
  return u
 }
 private spawnBoss(kind:EnemyKind,scale:number,variant:string){
  const model=buildEnemy(kind,variant,scale);const pos=this.arena.portal.clone().add(new THREE.Vector3(0,0,2.5))
  const a=ARCHETYPES[kind];const dmg=17*(this.setup.enemyDamage??stageDmg(this.setup.stage))
  const boss=this.makeUnit(kind,this.setup.bossName,model,pos,a.radius*scale*.75,Math.min(a.speed,3.6)*.9,this.setup.bossRemaining,dmg,a.ranged?6.5:1.6+a.radius*scale*.6,1.4,a.ranged??null,true,true)
  boss.maxHp=this.setup.bossHp;boss.cool={slam:6,charge:10,rain:8,summon:16}
  this.boss=boss;this.bossSpawned=true;this.shake=.6
  this.particles.burst(pos.clone().setY(2),{count:120,color:this.arena.accent,speed:6,size:.2,life:1.2})
  this.cb.banner(`${this.setup.bossName} emerges`,'boss')
  this.spawnGroup(2,false)
 }
 private makeUnit(kind:EnemyKind,name:string,model:EnemyModel,pos:THREE.Vector3,radius:number,speed:number,hp:number,dmg:number,range:number,interval:number,ranged:string|null,elite:boolean,boss:boolean):Unit{
  model.object.position.copy(pos);this.scene.add(model.object)
  const bar=boss?null:document.createElement('div')
  if(bar){bar.className='unit-bar'+(elite?' elite':'');bar.innerHTML='<i></i>';this.overlay.appendChild(bar)}
  const u:Unit={id:this.nextId++,kind,name,model,pos:pos.clone(),facing:0,radius,speed,hp,maxHp:hp,dmg,range,interval,atk:interval*(.5+this.rng()*.5),ranged,elite,boss,dead:false,deathT:0,root:0,stun:0,slow:0,slowT:0,burn:[],knock:null,stunDr:{n:0,until:0},bar,lunge:0,phase:this.rng()*6,cool:{slam:0,charge:0,rain:0,summon:0},charge:null}
  this.units.push(u);return u
 }

 // ---------- hero ----------
 private buffSum(key:'damageUp'|'reduce'|'hot'){return this.buffs.reduce((s,b)=>s+(b[key]||0),0)}
 private has(effect:string){return this.setup.stats.effects.includes(effect)}
 private moveSpeed(){return 6.2*(this.has('galeforce')?1.25:1)*(this.spin?.7:1)}
 private updateHero(dt:number){
  if(this.hero.dead){if(this.xrayOn){this.xrayOn=false;for(const x of this.xray)x.visible=false}this.hero.speed=0;this.hero.update(dt,this.time,this.particles);return}
  for(const k of Object.keys(this.cds) as Key[])this.cds[k]=Math.max(0,this.cds[k]-dt)
  for(const b of this.buffs)b.t-=dt;this.buffs=this.buffs.filter(b=>b.t>0)
  const hot=this.buffSum('hot');if(hot)this.heal(this.maxHp*hot*dt,false)
  if(this.shield.amount>0){this.shield.t-=dt;if(this.shield.t<=0)this.shield.amount=0}
  if(this.has('starward')){this.starwardT-=dt;if(this.starwardT<=0){this.starwardT=8;this.shield={amount:Math.max(this.shield.amount,this.maxHp*.15),t:8}}}
  const grow=this.buffs.reduce((g,b)=>Math.max(g,b.grow||1),1);this.hero.object.scale.setScalar(THREE.MathUtils.lerp(this.hero.object.scale.x,grow,dt*6))
  let moving=false
  if(this.dash){
   const d=this.dash
   if(d.arc!==undefined&&d.from&&d.total){d.t=(d.t||0)+dt;const p=Math.min(1,d.t/d.total);this.heroPos.lerpVectors(d.from,d.to,p);this.hero.object.position.y=Math.sin(p*Math.PI)*d.arc;if(p>=1){this.hero.object.position.y=0;this.land(d)}}
   else{const step=flat(d.to.clone().sub(this.heroPos));const len=step.length();const travel=d.speed*dt
    if(len<=travel){this.heroPos.copy(d.to);this.land(d)}else{this.heroPos.add(step.setLength(travel));this.dashHits(d)}}
   moving=true;this.particles.spawn(this.heroPos.clone().setY(1),new THREE.Vector3(0,.3,0),new THREE.Color(this.setup.classColor),.18,.4)
  }else if(this.spree){
   this.spree.next-=dt
   if(this.spree.next<=0){const t=this.spree.targets.shift();if(t&&!t.dead){const behind=t.pos.clone().add(flat(t.pos.clone().sub(this.heroPos)).setLength(t.radius+.7));this.blinkTo(behind);this.face(t.pos);this.hero.play('attack');this.damage(t,this.power()*this.spree.ability.power,this.spree.ability)}
    this.spree.next=.28;if(!this.spree.targets.length)this.spree=null}
  }else{
   const arrows=new THREE.Vector3((this.keys.has('ArrowRight')?1:0)-(this.keys.has('ArrowLeft')?1:0),0,(this.keys.has('ArrowDown')?1:0)-(this.keys.has('ArrowUp')?1:0))
   if(arrows.lengthSq()>0){this.moveTo=this.clampArena(this.heroPos.clone().add(arrows.setLength(1.5)));this.target=null}
   if(this.target&&this.target.dead)this.target=null
   if(this.auto&&!this.moveTo&&!this.holding)this.autoTarget()
   if(!this.target&&!this.moveTo){const near=this.nearestEnemy(this.heroPos,this.kit.auto.range+1.5);if(near)this.target=near}
   let goal:THREE.Vector3|null=null
   if(this.target){const dist=flat(this.target.pos.clone().sub(this.heroPos)).length()-this.target.radius;if(dist>this.kit.auto.range)goal=this.target.pos;else this.autoAttack(dt)}
   else if(this.moveTo){goal=this.moveTo;if(flat(this.moveTo.clone().sub(this.heroPos)).length()<.15){this.moveTo=null;goal=null}}
   // Auto waits for melee enemies outside the spawn area instead of walking into new waves.
   if(goal&&this.auto&&this.target&&!this.target.ranged&&this.gap(this.target)>this.kit.auto.range+2&&this.nearPortal(goal)&&this.nearPortal(this.heroPos,PORTAL_KEEP+1.5))goal=null
   if(goal){const dir=flat(goal.clone().sub(this.heroPos));const len=dir.length();if(len>.05){const step=Math.min(len,this.moveSpeed()*dt);this.heroPos.add(dir.setLength(step));this.heroFacing=Math.atan2(dir.x,dir.z);moving=true}}
   if(this.auto)this.autoCast()
  }
  if(this.flurry){this.flurry.next-=dt;if(this.flurry.next<=0){this.coneHit(this.flurry.ability,this.flurry.dir);this.flurry.n--;this.flurry.next=.3;if(this.flurry.n<=0)this.flurry=null}}
  if(this.spin){this.spin.t-=dt;this.spin.next-=dt;if(this.spin.next<=0){this.spin.next=this.spin.ability.tick||.4;this.areaHit(this.heroPos,this.spin.ability.radius||3,this.power()*this.spin.ability.power,this.spin.ability);this.ringFx(this.heroPos,this.spin.ability.radius||3,this.spin.ability.color,.3)}
   if(this.spin.t<=0){this.spin=null;this.hero.stopSpin()}}
  this.clampArena(this.heroPos);this.resolveOverlap(this.heroPos,.5)
  this.hero.speed=THREE.MathUtils.lerp(this.hero.speed,moving?1:0,dt*10)
  this.hero.object.position.x=this.heroPos.x;this.hero.object.position.z=this.heroPos.z
  this.hero.object.rotation.y=THREE.MathUtils.lerp(this.hero.object.rotation.y,this.shortest(this.hero.object.rotation.y,this.heroFacing),dt*14)
  this.hero.update(dt,this.time,this.particles,1)
  this.ring.position.set(this.heroPos.x,.03,this.heroPos.z)
  const covered=this.coveredByBoss();if(covered!==this.xrayOn){this.xrayOn=covered;for(const x of this.xray)x.visible=covered}
  this.shieldMesh.visible=this.shield.amount>0;if(this.shieldMesh.visible){this.shieldMesh.position.set(this.heroPos.x,1,this.heroPos.z);this.shieldMesh.rotation.y+=dt}
  if(this.cursorRing.visible){this.cursorRing.scale.multiplyScalar(1-dt*2.2);if(this.cursorRing.scale.x<.2)this.cursorRing.visible=false}
 }
 /** The camera looks north from above, so a boss slightly south of the hero and as wide as it hides the hero. */
 private coveredByBoss(){
  const b=this.boss;if(!b||b.dead||this.hero.dead)return false
  const dz=b.pos.z-this.heroPos.z;const dx=Math.abs(b.pos.x-this.heroPos.x)
  return dz>-.3&&dz<b.model.height*.65+b.radius&&dx<b.radius+.6
 }
 private shortest(from:number,to:number){let d=(to-from)%(Math.PI*2);if(d>Math.PI)d-=Math.PI*2;if(d<-Math.PI)d+=Math.PI*2;return from+d}
 private face(p:THREE.Vector3){const d=flat(p.clone().sub(this.heroPos));if(d.lengthSq()>1e-4)this.heroFacing=Math.atan2(d.x,d.z)}
 private power(){return this.setup.stats.power}
 private nearestEnemy(p:THREE.Vector3,range:number){let best:Unit|null=null,bd=range;for(const u of this.units){if(u.dead)continue;const d=flat(u.pos.clone().sub(p)).length()-u.radius;if(d<bd){bd=d;best=u}}return best}
 private autoAttack(dt:number){
  const t=this.target!;this.face(t.pos);this.autoT-=dt;if(this.autoT>0)return
  this.autoT=this.kit.auto.interval/(1+this.setup.stats.haste)
  const dmg=this.power()*this.kit.auto.power
  if(this.kit.auto.projectile){this.hero.play(this.setup.appearance.role==='ranged'?'shoot':'cast',.32);this.fire(this.heroPos,t.pos,dmg,null,this.kit.auto.projectile,24,this.kit.auto.range+3,true)}
  else{this.hero.play('attack');const target=t;setTimeout(()=>{if(!target.dead&&!this.disposed&&flat(target.pos.clone().sub(this.heroPos)).length()-target.radius<=this.kit.auto.range+.6){this.damage(target,dmg,null);if(this.kit.auto.slow)this.slowUnit(target,this.kit.auto.slow,2)}},140)}
 }
 // ---------- auto-battle ----------
 /** Fight the nearest enemy, but finish one already in reach before turning to another. */
 private autoTarget(){
  const near=this.nearestEnemy(this.heroPos,40);if(!near)return
  const t=this.target;if(t&&t!==near&&this.gap(t)<=this.kit.auto.range)return
  this.target=near
 }
 private gap(u:Unit,from=this.heroPos){return flat(u.pos.clone().sub(from)).length()-u.radius}
 private enemiesNear(p:THREE.Vector3,r:number){let n=0;for(const u of this.units)if(!u.dead&&this.gap(u,p)<=r)n++;return n}
 private nearPortal(p:THREE.Vector3,r=PORTAL_KEEP){return flat(p.clone().sub(this.arena.portal)).length()<r}
 /** A dash, leap or blink may end here: away from the spawn portal and not inside a pack. */
 private safeLanding(p:THREE.Vector3,crowd:number){return !this.nearPortal(p)&&this.enemiesNear(p,3.5)<=crowd}
 private autoCast(){
  const near=this.nearestEnemy(this.heroPos,16);const hp=this.hp/this.maxHp;const boss=this.boss&&!this.boss.dead?this.boss:null
  const melee=this.enemiesNear(this.heroPos,2.5)
  for(const a of this.kit.abilities){if(this.cds[a.key]>0)continue
   const big=a.cd>=25
   let aim:THREE.Vector3|null=near?.pos||null;let go=false
   switch(a.kind){
    case 'heal':go=hp<.5;break
    case 'shield':go=hp<.75&&melee>0||hp<.5;break
    case 'buff':go=a.reduce&&!a.damageUp?melee>=2||hp<.6&&melee>0:!!near&&(boss!==null&&this.gap(boss)<6||!big&&this.enemiesNear(this.heroPos,5)>=3);break
    case 'nova':case 'spin':{const r=(a.radius||3)+.3;const n=this.enemiesNear(this.heroPos,r);go=big?n>=4||(boss!==null&&this.gap(boss)<=r):n>=1;break}
    case 'cone':{const r=a.radius||3;const t=big&&boss&&this.gap(boss)<=r?boss:this.nearestEnemy(this.heroPos,r);aim=t?.pos||null;go=!!t&&(!big||t===boss||this.enemiesNear(this.heroPos,r)>=4);break}
    case 'projectile':case 'chain':go=!!near&&this.gap(near)<=(a.range||10);break
    case 'ground':{const reach=(a.range||0)+(a.radius||3)*.6;const t=big&&boss&&this.gap(boss)<=reach?boss:near;aim=t?.pos||null;go=!!t&&this.gap(t)<=reach&&(!big||t===boss||this.enemiesNear(t.pos,a.radius||3)>=4);break}
    case 'dash':{if(!near)break;const d=this.gap(near);const dir=flat(near.pos.clone().sub(this.heroPos)).normalize()
     const end=a.pierce?this.clampArena(this.heroPos.clone().add(dir.multiplyScalar(a.range||8))):near.pos
     go=d>=1.5&&d<=(a.range||8)&&(a.pierce?this.safeLanding(end,1):!this.nearPortal(end));break}
    case 'leap':{if(!near)break;const t=boss&&this.gap(boss)<=(a.range||9)?boss:near;aim=t.pos;go=this.gap(t)<=(a.range||9)&&this.safeLanding(t.pos,4)&&(t===boss||this.enemiesNear(t.pos,a.radius||4)>=4);break}
    case 'blink':
     if(a.power>0){go=!!near&&this.gap(near)<=(a.range||10)&&this.safeLanding(near.pos,3)}
     else if(near&&(melee>=2||hp<.5&&melee>0)){const away=flat(this.heroPos.clone().sub(near.pos));if(away.lengthSq()<1e-4)away.set(0,0,1);aim=this.clampArena(this.heroPos.clone().add(away.setLength(a.range||8)));go=this.safeLanding(aim,1)}
     break
    case 'disengage':if(near&&melee>0&&hp<.8){const end=this.clampArena(this.heroPos.clone().add(flat(this.heroPos.clone().sub(near.pos)).setLength(a.range||7)));go=this.safeLanding(end,1)}break
    case 'spree':go=!!near&&(boss!==null&&this.gap(boss)<=(a.range||8)||this.enemiesNear(this.heroPos,a.range||8)>=4);break
   }
   if(!go)continue
   if(aim)this.aim.copy(aim)
   this.lastInput='mouse';this.tryCast(a.key);break}
 }
 private tryCast(key:Key){
  if(this.over||this.paused||this.hero.dead||this.cds[key]>0||this.dash||this.spree)return
  const a=this.kit.abilities.find(x=>x.key===key);if(!a)return
  const aim=this.clampArena(this.aimPoint());const dir=flat(aim.clone().sub(this.heroPos));if(dir.lengthSq()<1e-4)dir.set(Math.sin(this.heroFacing),0,Math.cos(this.heroFacing));dir.normalize()
  const within=(range:number)=>{const v=aim.clone().sub(this.heroPos);if(v.length()>range)v.setLength(range);return this.heroPos.clone().add(v)}
  const pow=this.power()*a.power
  switch(a.kind){
   case 'projectile':{this.hero.play(this.setup.appearance.role==='melee'?'attack':'cast',.35);const n=a.count||1;for(let i=0;i<n;i++){const ang=n>1?(i/(n-1)-.5)*(a.spread||.5)*2:0;const d=dir.clone().applyAxisAngle(UP,ang);this.fire(this.heroPos,this.heroPos.clone().add(d.multiplyScalar(10)),pow,a,a.color,a.speed||20,a.range||10,true)}break}
   case 'nova':{this.hero.play(a.knock?'cast':'attack');this.areaHit(this.heroPos,a.radius||3,pow,a);this.ringFx(this.heroPos,a.radius||3,a.color,.45);this.particles.burst(this.heroPos.clone().setY(1),{count:60,color:a.color,speed:a.radius||3,size:.14,life:.5,spread:.3});break}
   case 'ground':{this.hero.play('cast');this.zone(a.range?within(a.range):this.heroPos.clone(),a,pow);break}
   case 'dash':{this.dash={to:this.clampArena(this.heroPos.clone().add(dir.clone().multiplyScalar(a.range||8))),speed:24,ability:a,hit:new Set()};this.face(this.dash.to);this.trail();break}
   case 'blink':{
    if(a.power>0){const t=this.nearestEnemy(aim,4)||this.nearestEnemy(this.heroPos,a.range||10);if(!t)return;const behind=t.pos.clone().add(flat(t.pos.clone().sub(this.heroPos)).setLength(t.radius+.7));this.blinkTo(behind);this.face(t.pos);this.hero.play('attack');this.damage(t,pow,a);if(a.stun)this.stunUnit(t,a.stun)}
    else this.blinkTo(this.clampArena(within(a.range||8)))
    this.trail();break}
   case 'disengage':{this.dash={to:this.clampArena(this.heroPos.clone().sub(dir.clone().multiplyScalar(a.range||7))),speed:22,ability:null,hit:new Set(),arc:1.6,from:this.heroPos.clone(),t:0,total:.45};this.trail();break}
   case 'leap':{this.dash={to:this.clampArena(within(a.range||9)),speed:0,ability:a,hit:new Set(),arc:3,from:this.heroPos.clone(),t:0,total:.55};this.face(this.dash.to);break}
   case 'heal':{this.hero.play('cast');this.heal(this.maxHp*(a.heal||.25),true);if(a.hot)this.buffs.push({name:a.name,t:a.duration||6,color:a.color,hot:a.hot});this.particles.burst(this.heroPos.clone().setY(1),{count:50,color:a.color,speed:1.4,size:.12,life:1,up:1.2});break}
   case 'shield':{this.hero.play('cast');this.shield={amount:this.maxHp*(a.heal||.3),t:a.duration||8};break}
   case 'buff':{this.hero.play('cast');this.buffs.push({name:a.name,t:a.duration||6,color:a.color,damageUp:a.damageUp,reduce:a.reduce,hot:a.hot,grow:a.grow});this.ringFx(this.heroPos,2.2,a.color,.6);this.particles.burst(this.heroPos.clone().setY(1.2),{count:60,color:a.color,speed:2,size:.13,life:.9,up:.8});break}
   case 'spin':{this.spin={t:a.duration||3,next:0,ability:a};this.hero.play('spin',a.duration||3);if(a.hot)this.buffs.push({name:a.name,t:a.duration||5,color:a.color,hot:a.hot});break}
   case 'cone':{this.hero.play('attack');this.face(aim);if((a.count||1)>1)this.flurry={n:a.count||1,next:0,ability:a,dir};else this.coneHit(a,dir);if(a.heal)this.heal(this.maxHp*a.heal,true);break}
   case 'chain':{this.hero.play('cast');this.chain(a,aim,pow);break}
   case 'spree':{const t=this.units.filter(u=>!u.dead&&u.pos.distanceTo(this.heroPos)<(a.range||8)).slice(0,a.count||5);if(!t.length)return;this.spree={targets:t,next:0,ability:a};break}
  }
  if(a.barrier)this.shield={amount:Math.max(this.shield.amount,this.maxHp*a.barrier),t:6}
  this.cds[key]=a.cd/(1+this.setup.stats.haste*.5)
  if(this.has('riftwalk')&&this.rng()<.25){this.cds[key]=0;this.floatText(this.heroPos,'Reset','#c08aff',1.4)}
 }
 private land(d:NonNullable<BattleEngine['dash']>){
  this.dash=null
  if(d.ability?.kind==='leap'){const a=d.ability;this.areaHit(this.heroPos,a.radius||4,this.power()*a.power,a);this.ringFx(this.heroPos,a.radius||4,a.color,.5);this.shake=.35;this.particles.burst(this.heroPos.clone().setY(.4),{count:90,color:a.color,speed:5,size:.16,life:.7,spread:.25})
   if(a.damageUp)this.buffs.push({name:a.name,t:a.duration||10,color:a.color,damageUp:a.damageUp,grow:a.grow})}
  if(this.has('galeforce'))this.zone(this.heroPos.clone(),{key:'Q',name:'Cyclone',kind:'ground',cd:0,power:.5,radius:2,duration:3,tick:.5,color:'#c8ffe0',text:''},this.power()*.5)
 }
 private dashHits(d:NonNullable<BattleEngine['dash']>){
  if(!d.ability)return
  for(const u of this.units){if(u.dead||d.hit.has(u.id))continue;if(flat(u.pos.clone().sub(this.heroPos)).length()<u.radius+.8){d.hit.add(u.id);this.damage(u,this.power()*d.ability.power,d.ability);if(d.ability.stun)this.stunUnit(u,d.ability.stun);if(!d.ability.pierce){this.dash=null;this.hero.play('attack');if(this.has('galeforce'))this.land({...d,ability:null});return}}}
 }
 private blinkTo(p:THREE.Vector3){this.particles.burst(this.heroPos.clone().setY(1),{count:30,color:this.setup.classColor,speed:2,size:.12,life:.5});this.heroPos.copy(this.clampArena(p));this.particles.burst(this.heroPos.clone().setY(1),{count:30,color:this.setup.classColor,speed:2,size:.12,life:.5});if(this.has('galeforce'))this.land({to:this.heroPos.clone(),speed:0,ability:null,hit:new Set()})}
 private trail(){for(let i=0;i<20;i++)this.particles.spawn(this.heroPos.clone().add(new THREE.Vector3((this.rng()-.5),1+this.rng(),(this.rng()-.5))),new THREE.Vector3(0,.4,0),new THREE.Color(this.setup.classColor),.14,.5)}
 private heal(amount:number,show:boolean){const before=this.hp;this.hp=Math.min(this.maxHp,this.hp+amount);if(show&&this.hp-before>=1)this.floatText(this.heroPos,'+'+Math.round(this.hp-before),'#5aff7a',1.1)}
 private hurtHero(amount:number){
  if(this.over||this.hero.dead||this.spree)return
  const st=this.setup.stats;let d=amount*(1-st.damageReduction)*(1-st.versatility/2)*(1-Math.min(.8,this.buffSum('reduce')))
  if(this.shield.amount>0){const absorbed=Math.min(this.shield.amount,d);this.shield.amount-=absorbed;d-=absorbed}
  d=Math.round(d);if(d<=0)return
  this.hp-=d;this.floatText(this.heroPos,'-'+d,'#ff5a5a',.9);this.hero.play('hit')
  if(this.hp<=0){
   if(this.has('phoenix')&&!this.phoenixUsed){this.phoenixUsed=true;this.hp=this.maxHp*.5;this.cb.banner('Phoenix Rebirth','good');this.particles.burst(this.heroPos.clone().setY(1),{count:160,color:'#ff9a3a',speed:5,size:.2,life:1.2});this.areaHit(this.heroPos,4,this.power()*2,null);return}
   this.hp=0;this.hero.play('death');this.over=true;this.outcome='defeat';this.endT=1.6;this.cb.banner('Defeated','danger')
  }
 }

 // ---------- damage ----------
 private damage(u:Unit,base:number,ability:Ability|null,opts:{noProc?:boolean;color?:string}={}){
  if(u.dead||this.over)return
  const st=this.setup.stats
  let d=base*(1+st.versatility)*(1+this.buffSum('damageUp'))*(ability?1+st.mastery:1)
  if(this.has('kingslayer')&&(u.elite||u.boss))d*=1.35
  if(this.has('wintergrasp')&&u.slowT>0)d*=1.15
  const crit=this.rng()<st.critChance;if(crit)d*=2
  d=Math.max(1,Math.round(d*(.92+this.rng()*.16)))
  const before=u.hp;u.hp-=d
  if(u.boss)this.bossDamage+=Math.min(d,Math.max(0,before))
  this.floatText(u.pos.clone().setY(u.model.height*.9),(crit?'':'')+d,crit?'#ffb340':opts.color||'#ffffff',crit?1.45:1)
  u.lunge=-.12
  if(ability?.burn)this.burn(u,this.power()*ability.burn,6,ability.name)
  if(ability?.slow)this.slowUnit(u,ability.slow,3)
  if(ability?.root)u.root=u.boss?Math.max(u.root,ability.root*.4):Math.max(u.root,ability.root)
  if(ability?.drain)this.heal(d*ability.drain,true)
  if(!opts.noProc){
   if(this.has('bloodsong'))this.heal(d*.08,false)
   if(this.has('inferno'))this.burn(u,d*.4/3,3,'inferno')
   if(this.has('wintergrasp'))this.slowUnit(u,.3,2)
   if(this.has('stormcall')){this.stormCount++;if(this.stormCount%4===0)this.chain({key:'Q',name:'Stormcall',kind:'chain',cd:0,power:.6,range:8,bounces:2,color:'#9ad8ff',text:''},u.pos,this.power()*.6,true)}
  }
  if(u.hp<=0)this.kill(u)
 }
 private slowUnit(u:Unit,amount:number,t:number){u.slow=Math.max(u.slow,amount);u.slowT=Math.max(u.slowT,t)}
 /** At most 3 burns from one source on one enemy; a new one replaces the oldest. */
 private burn(u:Unit,dps:number,t:number,source:string){
  const same=u.burn.filter(b=>b.source===source)
  if(same.length>=BURN_STACKS){const oldest=same.reduce((a,b)=>b.t<a.t?b:a);u.burn.splice(u.burn.indexOf(oldest),1)}
  u.burn.push({dps,t,source})
 }
 /** Bosses take half-length stuns, each further stun within 15 sec is halved again, and a fourth is ignored. A stun never extends a running one. Roots on bosses last 40%. */
 private stunUnit(u:Unit,t:number){
  if(!u.boss){u.stun=Math.max(u.stun,t);return}
  if(u.stun>0)return
  if(this.time>=u.stunDr.until)u.stunDr.n=0
  if(u.stunDr.n>=3)return
  u.stunDr.n++;u.stun=t*.5**u.stunDr.n;u.stunDr.until=this.time+15
 }
 private kill(u:Unit){
  u.dead=true;u.deathT=0;this.kills++;u.bar?.remove();u.bar=null
  this.particles.burst(u.pos.clone().setY(u.model.height*.5),{count:u.boss?160:26,color:u.boss?'#ffb340':this.arena.accent,speed:u.boss?6:2.5,size:u.boss?.2:.12,life:u.boss?1.4:.7})
  if(this.target===u)this.target=null
  if(this.has('dawnfire')){this.areaHit(u.pos,3,this.power()*.8,null,true);this.ringFx(u.pos,3,'#ffe08a',.4)}
  if(u.boss&&!this.over){this.over=true;this.outcome='victory';this.endT=2.2;this.cb.banner(`${u.name} falls`,'good');this.shake=.8;for(const o of this.units)if(!o.dead&&!o.boss){o.hp=0;this.kill(o)}}
 }
 private areaHit(p:THREE.Vector3,radius:number,dmg:number,a:Ability|null,noProc=false){
  for(const u of this.units){if(u.dead)continue;if(flat(u.pos.clone().sub(p)).length()<=radius+u.radius){this.damage(u,dmg,a,{noProc});if(a?.stun)this.stunUnit(u,a.stun);if(a?.knock&&!u.boss)u.knock=flat(u.pos.clone().sub(p)).setLength(a.knock*3)}}
 }
 private coneHit(a:Ability,dir:THREE.Vector3){
  const r=a.radius||3,half=a.spread||.8
  for(const u of this.units){if(u.dead)continue;const v=flat(u.pos.clone().sub(this.heroPos));if(v.length()>r+u.radius)continue;if(v.lengthSq()>.01&&v.normalize().angleTo(dir)>half)continue;this.damage(u,this.power()*a.power,a);if(a.stun)this.stunUnit(u,a.stun)}
  this.particles.burst(this.heroPos.clone().add(dir.clone().multiplyScalar(r*.6)).setY(1),{count:30,color:a.color,speed:3,size:.12,life:.4,spread:.4})
 }
 private chain(a:Ability,near:THREE.Vector3,dmg:number,noProc=false){
  let current=this.nearestEnemy(near,4)||this.nearestEnemy(this.heroPos,a.range||9);if(!current)return
  const hit=new Set<number>();let from=this.heroPos.clone().setY(1.2);let d=dmg
  for(let i=0;i<=(a.bounces||3)&&current;i++){hit.add(current.id);const to=current.pos.clone().setY(current.model.height*.6);this.bolt(from,to,a.color);this.damage(current,d,noProc?null:a,{noProc});from=to;d*=.85
   let next:Unit|null=null,bd=6;for(const u of this.units){if(u.dead||hit.has(u.id))continue;const dist=u.pos.distanceTo(current.pos);if(dist<bd){bd=dist;next=u}}current=next}
 }
 private bolt(a:THREE.Vector3,b:THREE.Vector3,color:string){
  const pts:THREE.Vector3[]=[];for(let i=0;i<=8;i++){const p=a.clone().lerp(b,i/8);if(i>0&&i<8)p.add(new THREE.Vector3((this.rng()-.5)*.5,(this.rng()-.5)*.5,(this.rng()-.5)*.5));pts.push(p)}
  const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),new THREE.LineBasicMaterial({color,transparent:true,opacity:1,blending:THREE.AdditiveBlending}));this.scene.add(line);this.lines.push({line,t:.22})
 }

 // ---------- enemies ----------
 private updateUnits(dt:number){
  for(const u of this.units){
   const m=u.model
   if(u.dead){u.deathT+=dt;m.object.position.y=-u.deathT*.8;m.object.scale.setScalar(Math.max(.01,m.object.scale.x*(1-dt*1.5)));if(u.deathT>1.2){m.object.removeFromParent();disposeTree(m.object);u.deathT=99}continue}
   if(!this.over){for(const b of u.burn){b.t-=dt;const d=Math.min(b.dps*dt,Math.max(0,u.hp));u.hp-=b.dps*dt;if(u.boss)this.bossDamage+=d}
    u.burn=u.burn.filter(b=>b.t>0);if(u.hp<=0){this.kill(u);continue}}
   u.stun=Math.max(0,u.stun-dt);u.root=Math.max(0,u.root-dt);u.slowT=Math.max(0,u.slowT-dt);if(u.slowT<=0)u.slow=0
   if(u.knock){u.pos.add(u.knock.clone().multiplyScalar(dt));u.knock.multiplyScalar(1-dt*6);if(u.knock.length()<.2)u.knock=null}
   const toHero=flat(this.heroPos.clone().sub(u.pos));const dist=toHero.length()-u.radius-.5
   let moving=false
   if(!this.hero.dead&&!this.over&&u.stun<=0){
    if(u.boss)this.bossBrain(u,dt,toHero)
    if(u.charge){const step=u.charge.dir.clone().multiplyScalar(14*dt);u.pos.add(step);u.charge.t-=dt;moving=true;if(flat(this.heroPos.clone().sub(u.pos)).length()<u.radius+.6){this.hurtHero(u.dmg*2.5);u.charge=null}if(u.charge&&u.charge.t<=0)u.charge=null}
    else{
     const want=u.ranged?u.range-1:u.range
     if(dist>want&&u.root<=0){const speed=u.speed*(1-u.slow);u.pos.add(toHero.clone().setLength(Math.min(dist,speed*dt)));moving=true}
     u.facing=Math.atan2(toHero.x,toHero.z)
     u.atk-=dt
     if(dist<=u.range&&u.atk<=0){u.atk=u.interval;u.lunge=.35
      if(u.ranged)this.fire(u.pos,this.heroPos,u.dmg,null,u.ranged,13,u.range+4,false)
      else this.hurtHero(u.dmg)}
    }
   }
   this.resolveOverlap(u.pos,u.radius,u);this.clampArena(u.pos)
   m.object.position.x=u.pos.x;m.object.position.z=u.pos.z;m.object.rotation.y=THREE.MathUtils.lerp(m.object.rotation.y,this.shortest(m.object.rotation.y,u.facing),dt*8)
   this.animateEnemy(u,dt,moving)
   if(u.bar){const p=this.project(u.pos.clone().setY(m.height+.35));u.bar.style.transform=`translate(${p.x}px,${p.y}px)`;(u.bar.firstChild as HTMLElement).style.width=`${Math.max(0,u.hp/u.maxHp*100)}%`;u.bar.style.display=p.z>1?'none':''}
  }
  this.units=this.units.filter(u=>u.deathT<99)
 }
 private bossBrain(b:Unit,dt:number,toHero:THREE.Vector3){
  const c=b.cool;const ratio=b.hp/b.maxHp;const speedUp=ratio<.5?.8:1;const s=this.setup.stage
  c.slam-=dt;c.charge-=dt;c.rain-=dt;c.summon-=dt
  if(c.slam<=0){c.slam=9*speedUp;this.telegraph(this.heroPos.clone(),3.2,1.4,b.dmg*3,b)}
  if(s>=3&&c.charge<=0&&toHero.length()>4){c.charge=14*speedUp;const dir=toHero.clone().normalize();this.telegraphLine(b,dir,12,2.2,1.1)}
  if(s>=5&&c.rain<=0){c.rain=12*speedUp;for(let i=0;i<4;i++){const p=this.heroPos.clone().add(new THREE.Vector3((this.rng()-.5)*8,0,(this.rng()-.5)*8));this.telegraph(this.clampArena(p),2,1.3,b.dmg*1.6,b)}}
  if(c.summon<=0){c.summon=18;this.spawnGroup(3,this.rng()<.25);this.cb.banner('Reinforcements','info')}
 }
 private animateEnemy(u:Unit,dt:number,moving:boolean){
  const m=u.model;u.phase+=dt*(moving?10:2);const sw=Math.sin(u.phase)
  m.legs.forEach((l,i)=>{l.rotation.x=moving?sw*(i%2?.6:-.6):0})
  m.arms.forEach((a,i)=>{a.rotation.x=(moving?-sw*(i%2?.4:-.4):0)-u.lunge*3})
  m.wings.forEach((w,i)=>{w.rotation.y=(i?-1:1)*(.5+Math.sin(this.time*8+u.id)*.35)})
  if(m.floats)m.object.position.y=.35+Math.sin(this.time*2+u.id)*.15
  if(m.head)m.head.rotation.x=-u.lunge*.8
  u.lunge=THREE.MathUtils.lerp(u.lunge,0,dt*6)
  if(m.emit&&m.emitColor&&this.rng()<dt*(u.boss?40:8)){const p=new THREE.Vector3();m.emit.getWorldPosition(p);this.particles.spawn(p.add(new THREE.Vector3((this.rng()-.5)*.6,this.rng()*.4,(this.rng()-.5)*.6)),new THREE.Vector3(0,.8,0),new THREE.Color(m.emitColor),u.boss?.22:.12,.8)}
  if(u.boss&&this.enraged&&this.rng()<dt*30)this.particles.spawn(u.pos.clone().setY(this.rng()*m.height),new THREE.Vector3(0,1,0),new THREE.Color('#ff2a2a'),.2,.7)
 }
 private resolveOverlap(p:THREE.Vector3,r:number,self?:Unit){
  for(const u of this.units){if(u.dead||u===self)continue;const d=flat(p.clone().sub(u.pos));const min=r+u.radius*.9;const len=d.length();if(len>0&&len<min){p.add(d.setLength((min-len)*(self?.5:.8)))}}
 }

 // ---------- projectiles, zones, telegraphs ----------
 private fire(from:THREE.Vector3,to:THREE.Vector3,dmg:number,a:Ability|null,color:string,speed:number,range:number,fromHero:boolean){
  const dir=flat(to.clone().sub(from)).normalize()
  const mesh=new THREE.Mesh(new THREE.IcosahedronGeometry(a?.explode?.28:.17,1),glow(color,1));mesh.position.copy(from).setY(1.1);this.scene.add(mesh)
  this.shots.push({mesh,pos:mesh.position,vel:dir.multiplyScalar(speed),range,fromHero,dmg,ability:a,hit:new Set(),color})
 }
 private updateShots(dt:number){
  for(const s of this.shots){
   const step=s.vel.clone().multiplyScalar(dt);s.pos.add(step);s.range-=step.length()
   if(this.rng()<.8)this.particles.spawn(s.pos.clone(),new THREE.Vector3(0,.2,0),new THREE.Color(s.color),.14,.3)
   if(s.fromHero){for(const u of this.units){if(u.dead||s.hit.has(u.id))continue;if(flat(u.pos.clone().sub(s.pos)).length()<u.radius+.3){s.hit.add(u.id);this.impact(s,u);s.range=-1;break}}}
   else if(!this.hero.dead&&flat(this.heroPos.clone().sub(s.pos)).length()<.6){this.hurtHero(s.dmg);s.range=-1}
   if(s.range<0){s.mesh.removeFromParent();s.mesh.geometry.dispose()}
  }
  this.shots=this.shots.filter(s=>s.range>=0)
 }
 private impact(s:Shot,u:Unit){
  const a=s.ability
  if(a?.explode){this.areaHit(s.pos,a.explode,s.dmg,a);this.ringFx(s.pos,a.explode,a.color,.35);this.particles.burst(s.pos.clone(),{count:50,color:a.color,speed:4,size:.16,life:.6})}
  else this.damage(u,s.dmg,a)
  if(a?.pull&&!u.boss){u.pos.copy(this.heroPos.clone().add(flat(u.pos.clone().sub(this.heroPos)).setLength(1.4)))}
  if(a?.stun)this.stunUnit(u,a.stun)
  this.particles.burst(s.pos.clone(),{count:10,color:s.color,speed:1.5,size:.1,life:.3})
 }
 /** A hero zone hits once per tick for `dmg`. Its first hit can be a bigger impact, and stuns, roots and burns land only with that first hit. */
 private zone(p:THREE.Vector3,a:Ability,dmg:number){
  const meshes=this.decal(p,a.radius||3,a.color,.28)
  const impact=a.impact!==undefined?this.power()*a.impact:dmg
  this.zones.push({pos:p.clone(),radius:a.radius||3,t:(a.duration||.1)+(a.delay||0),tick:a.tick||.5,next:a.delay||0,delay:a.delay||0,ability:a,dmg,impact,hits:0,lingering:{...a,stun:undefined,root:undefined,burn:undefined},fromHero:true,meshes,color:a.color,once:(a.duration||.1)<=.15})
 }
 private telegraph(p:THREE.Vector3,r:number,delay:number,dmg:number,boss:Unit){
  const meshes=this.decal(p,r,'#ff2a2a',.18,true)
  this.zones.push({pos:p.clone(),radius:r,t:delay,tick:0,next:delay,delay,ability:null,dmg,impact:dmg,hits:0,lingering:null,fromHero:false,meshes,color:'#ff2a2a',once:true});void boss
 }
 private telegraphLine(b:Unit,dir:THREE.Vector3,length:number,width:number,delay:number){
  const plane=new THREE.Mesh(new THREE.PlaneGeometry(width,length),glow('#ff2a2a',.25,THREE.DoubleSide));plane.rotation.x=-Math.PI/2;plane.rotation.z=-Math.atan2(dir.x,dir.z);const mid=b.pos.clone().add(dir.clone().multiplyScalar(length/2));plane.position.set(mid.x,.05,mid.z);this.scene.add(plane)
  this.zones.push({pos:b.pos.clone(),radius:0,t:delay,tick:0,next:delay,delay,ability:null,dmg:0,impact:0,hits:0,lingering:null,fromHero:false,meshes:[plane],color:'#ff2a2a',once:true,line:{dir,length,width,boss:b}})
 }
 private decal(p:THREE.Vector3,r:number,color:string,opacity:number,grow=false){
  const fill=new THREE.Mesh(new THREE.CircleGeometry(r,40),glow(color,opacity,THREE.DoubleSide));fill.rotation.x=-Math.PI/2;fill.position.set(p.x,.05,p.z)
  const edge=new THREE.Mesh(new THREE.RingGeometry(r*.94,r,48),glow(color,.85,THREE.DoubleSide));edge.rotation.x=-Math.PI/2;edge.position.set(p.x,.06,p.z)
  if(grow)fill.scale.setScalar(.05)
  this.scene.add(fill,edge);return [fill,edge]
 }
 private updateZones(dt:number){
  for(const z of this.zones){
   z.t-=dt;z.next-=dt
   if(!z.fromHero&&z.delay>0&&z.meshes[0]&&!z.line){const p=1-Math.max(0,z.next)/z.delay;z.meshes[0].scale.setScalar(Math.max(.05,p))}
   if(z.next<=0){
    if(z.line){const b=z.line.boss;if(!b.dead){b.charge={dir:z.line.dir.clone(),t:z.line.length/14}}}
    else if(z.fromHero){if(this.rng()<.9)this.particles.burst(z.pos.clone().add(new THREE.Vector3((this.rng()-.5)*z.radius,2.5,(this.rng()-.5)*z.radius)),{count:6,color:z.color,speed:1,size:.14,life:.6,gravity:6})
     const first=z.hits++===0
     this.areaHit(z.pos,z.radius,first?z.impact:z.dmg,first?z.ability:z.lingering)
     if(first&&(z.once||z.ability?.impact)){this.particles.burst(z.pos.clone().setY(.5),{count:90,color:z.color,speed:5,size:.18,life:.7,spread:.3});this.shake=Math.max(this.shake,.25)}
     z.next=z.once?99:z.tick}
    else{if(flat(this.heroPos.clone().sub(z.pos)).length()<=z.radius)this.hurtHero(z.dmg);this.particles.burst(z.pos.clone().setY(.3),{count:40,color:'#ff4a2a',speed:3.5,size:.15,life:.5,spread:.3});this.shake=Math.max(this.shake,.2);z.t=0}
   }
   if(z.t<=0){for(const m of z.meshes){m.removeFromParent();(m as THREE.Mesh).geometry.dispose()}}
  }
  this.zones=this.zones.filter(z=>z.t>0)
 }

 // ---------- feedback ----------
 private ringFx(p:THREE.Vector3,r:number,color:string,life:number){const ring=new THREE.Mesh(new THREE.RingGeometry(.85,1,48),glow(color,.9,THREE.DoubleSide));ring.rotation.x=-Math.PI/2;ring.position.set(p.x,.08,p.z);ring.scale.setScalar(r*.3);this.scene.add(ring);this.fades.push({obj:ring,t:0,life,grow:r,base:r*.3})}
 private floatText(p:THREE.Vector3,text:string,color:string,scale:number){
  if(this.floats.length>60){const old=this.floats.shift();old?.el.remove()}
  const el=document.createElement('div');el.className='float-text';el.textContent=text;el.style.color=color;el.style.fontSize=`${Math.round(15*scale)}px`;this.overlay.appendChild(el)
  this.floats.push({el,pos:p.clone().add(new THREE.Vector3((this.rng()-.5)*.6,this.rng()*.4,0)),t:0,life:.9})
 }
 private project(p:THREE.Vector3){const v=p.clone().project(this.camera);return {x:(v.x+1)/2*this.canvas.clientWidth,y:(1-v.y)/2*this.canvas.clientHeight,z:v.z}}
 private updateFx(dt:number){
  for(const f of this.fades){f.t+=dt;const p=f.t/f.life;f.obj.scale.setScalar(f.base+(f.grow-f.base)*Math.min(1,p*1.4));((f.obj as THREE.Mesh).material as THREE.Material).opacity=0.9*(1-p)}
  for(const f of this.fades)if(f.t>=f.life){f.obj.removeFromParent();(f.obj as THREE.Mesh).geometry.dispose()}
  this.fades=this.fades.filter(f=>f.t<f.life)
  for(const l of this.lines){l.t-=dt;(l.line.material as THREE.LineBasicMaterial).opacity=Math.max(0,l.t/.22);if(l.t<=0){l.line.removeFromParent();l.line.geometry.dispose();(l.line.material as THREE.Material).dispose()}}
  this.lines=this.lines.filter(l=>l.t>0)
  for(const f of this.floats){f.t+=dt;const p=this.project(f.pos.clone().setY(f.pos.y+f.t*1.2));f.el.style.transform=`translate(${p.x}px,${p.y}px) translate(-50%,-50%)`;f.el.style.opacity=String(Math.max(0,1-f.t/f.life))}
  for(const f of this.floats)if(f.t>=f.life)f.el.remove()
  this.floats=this.floats.filter(f=>f.t<f.life)
  this.particles.update(dt);this.arena.update(this.time)
 }
 private render(dt:number){
  const want=this.heroPos.clone().add(this.camOffset());this.camPos.lerp(want,Math.min(1,dt*6))
  this.camera.position.copy(this.camPos)
  if(this.shake>0&&!this.still){this.camera.position.add(new THREE.Vector3((this.rng()-.5)*this.shake,(this.rng()-.5)*this.shake,0));this.shake=Math.max(0,this.shake-dt*1.6)}
  this.camera.lookAt(this.camPos.x,0,this.camPos.z-this.camOffset().z+.4)
  const k=this.arena.key;k.position.set(this.heroPos.x+9,22,this.heroPos.z+7);k.target.position.set(this.heroPos.x,0,this.heroPos.z)
  this.composer.render()
 }
}
