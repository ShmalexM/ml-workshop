import {useEffect,useRef,useState} from 'react'
import * as THREE from 'three'
import {createComposer,createRenderer,environment,reducedMotion,webglAvailable} from './three/scene'
import {HeroModel,type Appearance} from './three/hero'
import {Particles} from './three/fx'
import {dotTexture,mat} from './three/materials'

/** Viewer-owned glow material: recolored when the class accent changes, so it must not come from the shared cache. */
const ownGlow=(color:string,opacity:number)=>new THREE.MeshBasicMaterial({color,transparent:true,opacity,blending:THREE.AdditiveBlending,depthWrite:false,side:THREE.DoubleSide})

type Stage={renderer:THREE.WebGLRenderer;scene:THREE.Scene;camera:THREE.PerspectiveCamera;particles:Particles;ring:THREE.Mesh;aura:THREE.Sprite;hero:HeroModel|null;yaw:number;drag:number|null;idle:number}

export const lookKey=(l:Appearance)=>[l.race,l.cls,...Object.values(l.gear).map(g=>g?`${g.slot}:${g.base}:${g.rarity}:${g.seed}:${g.effect}`:'')].join('|')

/** The armory's turntable. Rebuilds the hero when the look changes and flashes on equip. */
export default function HeroViewer({look,accent,flash,label}:{look:Appearance;accent:string;flash?:{color:string;n:number}|null;label:string}){
 const canvas=useRef<HTMLCanvasElement>(null);const stage=useRef<Stage|null>(null);const [failed]=useState(()=>!webglAvailable())
 const key=lookKey(look)
 useEffect(()=>{
  const el=canvas.current;if(!el||failed)return
  const renderer=createRenderer(el,{shadows:true})
  const scene=new THREE.Scene();scene.background=new THREE.Color('#0d0f17');scene.fog=new THREE.Fog('#0d0f17',6,14);scene.environment=environment(renderer)
  const camera=new THREE.PerspectiveCamera(32,1,.05,50)
  scene.add(new THREE.HemisphereLight('#b9c6ff','#2a1d16',.55))
  const key=new THREE.DirectionalLight('#fff1dd',2.2);key.position.set(2.5,4.5,3.5);key.castShadow=true;key.shadow.mapSize.set(1024,1024);key.shadow.camera.near=1;key.shadow.camera.far=12;key.shadow.bias=-.0004;scene.add(key)
  const rim=new THREE.DirectionalLight(accent,2.4);rim.position.set(-3,2.5,-3.5);scene.add(rim)
  const fill=new THREE.PointLight('#6b7cff',1.2,8);fill.position.set(-2.5,1.2,2);scene.add(fill)
  const base=new THREE.Mesh(new THREE.CylinderGeometry(.95,1.08,.22,28),mat('#23252e',{rough:.85,metal:.1}));base.position.y=-.11;base.receiveShadow=true;scene.add(base)
  const top=new THREE.Mesh(new THREE.CylinderGeometry(.9,.9,.02,28),mat('#2d303b',{rough:.7}));top.position.y=.005;top.receiveShadow=true;scene.add(top)
  const ring=new THREE.Mesh(new THREE.RingGeometry(.72,.78,48),ownGlow(accent,.75));ring.rotation.x=-Math.PI/2;ring.position.y=.02;scene.add(ring)
  // Runes ride on the ring, which lies flat, so they are placed in the ring's own XY plane.
  for(let i=0;i<8;i++){const a=i/8*Math.PI*2;const rune=new THREE.Mesh(new THREE.PlaneGeometry(.07,.07),ring.material);rune.position.set(Math.cos(a)*.84,Math.sin(a)*.84,.001);rune.rotation.z=a+Math.PI/4;ring.add(rune)}
  // Soft backlight glow behind the hero; a sprite with a radial falloff, not a flat disc.
  const aura=new THREE.Sprite(new THREE.SpriteMaterial({map:dotTexture(),color:accent,transparent:true,opacity:.22,blending:THREE.AdditiveBlending,depthWrite:false}));aura.scale.set(4.2,4.2,1);aura.position.set(0,1.25,-1.8);scene.add(aura)
  const particles=new Particles(900);scene.add(particles.points)
  const {composer,bloom}=createComposer(renderer,scene,camera,{strength:.75,radius:.5,threshold:.93})
  const s:Stage={renderer,scene,camera,particles,ring,aura,hero:null,yaw:-.35,drag:null,idle:0};stage.current=s
  const resize=()=>{const w=el.clientWidth,h=el.clientHeight;if(!w||!h)return;renderer.setSize(w,h,false);composer.setSize(w,h);bloom.resolution.set(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();particles.setScale(h*renderer.getPixelRatio())}
  const ro=new ResizeObserver(resize);ro.observe(el);resize()
  const still=reducedMotion();let visible=true;const io=new IntersectionObserver(([e])=>{visible=e.isIntersecting});io.observe(el)
  const down=(e:PointerEvent)=>{s.drag=e.clientX;el.setPointerCapture(e.pointerId)}
  const move=(e:PointerEvent)=>{if(s.drag===null)return;s.yaw+=(e.clientX-s.drag)*.012;s.drag=e.clientX;s.idle=0}
  const up=()=>{s.drag=null}
  el.addEventListener('pointerdown',down);el.addEventListener('pointermove',move);el.addEventListener('pointerup',up);el.addEventListener('pointercancel',up)
  // Browsers already pause requestAnimationFrame in background tabs; skip work only when scrolled away.
  const timer=new THREE.Timer();let raf=0
  const frame=(now:number)=>{raf=requestAnimationFrame(frame);timer.update(now);if(!visible)return
   const dt=Math.min(.05,timer.getDelta());const t=timer.getElapsed();s.idle+=dt
   if(!still&&s.drag===null&&s.idle>2.5)s.yaw+=dt*.22
   ring.rotation.z+=dt*.15
   if(s.hero){s.hero.object.rotation.y=s.yaw;s.hero.update(dt,t,particles,1)}
   particles.update(dt);composer.render()}
  raf=requestAnimationFrame(frame)
  return ()=>{cancelAnimationFrame(raf);timer.dispose();ro.disconnect();io.disconnect();el.removeEventListener('pointerdown',down);el.removeEventListener('pointermove',move);el.removeEventListener('pointerup',up);el.removeEventListener('pointercancel',up);s.hero?.dispose();particles.dispose();for(const pass of composer.passes)pass.dispose();composer.dispose();(ring.material as THREE.Material).dispose();(aura.material as THREE.Material).dispose();key.shadow.dispose()
   // dispose() alone keeps the WebGL context; browsers allow only a few at once.
   renderer.dispose();renderer.forceContextLoss();stage.current=null}
 // The scene is built once; look and accent changes are applied by the effects below.
 // eslint-disable-next-line react-hooks/exhaustive-deps
 },[failed])
 useEffect(()=>{
  const s=stage.current;if(!s)return
  s.hero?.dispose();const hero=new HeroModel(look);s.hero=hero;s.scene.add(hero.object)
  const h=hero.height;s.camera.position.set(0,h*.6+.35,h*1.75+2.1);s.camera.lookAt(0,h*.47,0)
 // eslint-disable-next-line react-hooks/exhaustive-deps
 },[key])
 useEffect(()=>{const s=stage.current;if(!s)return;(s.ring.material as THREE.MeshBasicMaterial).color.set(accent);s.aura.material.color.set(accent)},[accent])
 useEffect(()=>{const s=stage.current;if(!s||!flash||!s.hero)return;const h=s.hero.height
  s.particles.burst(new THREE.Vector3(0,h*.55,0),{count:70,color:flash.color,speed:1.6,size:.09,life:.9,spread:1.4})
  s.particles.burst(new THREE.Vector3(0,.05,0),{count:40,color:flash.color,speed:1.1,size:.07,life:1.1,spread:.2,up:.8})},[flash])
 if(failed)return <div className="hero-viewer fallback" role="img" aria-label={label}><p>3D view needs WebGL, which this browser has turned off. Your gear and stats still work.</p></div>
 return <canvas ref={canvas} className="hero-viewer" role="img" aria-label={label}/>
}
