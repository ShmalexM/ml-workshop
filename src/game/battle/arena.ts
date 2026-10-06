import * as THREE from 'three'
import {mat,glow} from '../three/materials'
import {seeded} from '../rarity'
import type {Theme} from './enemies'

type Look={ground:string;patch:string;crack:string|null;fog:string;sky:string;light:string;rim:string;prop:'tree'|'grave'|'web'|'pillar'|'spike'|'cage'|'crystal'|'anvil'|'spire';propColor:string;accent:string}
const LOOKS:Record<Theme,Look>={
 outskirts:{ground:'#56603e',patch:'#6a5a3e',crack:null,fog:'#26302a',sky:'#93a4b8',light:'#ffe6c0',rim:'#5a5248',prop:'tree',propColor:'#3a2e24',accent:'#b8ff8a'},
 bonefield:{ground:'#56503f',patch:'#68604c',crack:null,fog:'#34302a',sky:'#a8a090',light:'#fff0d8',rim:'#6a6458',prop:'grave',propColor:'#8a8478',accent:'#7ad8ff'},
 webwood:{ground:'#2f3a2a',patch:'#3e4a32',crack:null,fog:'#18221e',sky:'#6a8a7a',light:'#d8f0ff',rim:'#2a2a26',prop:'web',propColor:'#2a2420',accent:'#c8ff9a'},
 crypt:{ground:'#3e444e',patch:'#2e343c',crack:null,fog:'#161c24',sky:'#7a8aa8',light:'#c8d8ff',rim:'#4a505a',prop:'pillar',propColor:'#5a606a',accent:'#6ab8ff'},
 ember:{ground:'#3a2a22',patch:'#2a1e18',crack:'#ff6a1a',fog:'#3a1a0e',sky:'#ff9a6a',light:'#ffc890',rim:'#2a1e1a',prop:'spike',propColor:'#1e1614',accent:'#ff8a3a'},
 kennels:{ground:'#3e2622',patch:'#2e1a16',crack:'#ff4a1a',fog:'#2a1210',sky:'#c87a6a',light:'#ffc0a0',rim:'#3a2622',prop:'cage',propColor:'#2a2420',accent:'#ff6a3a'},
 void:{ground:'#1e1830',patch:'#2a2040',crack:'#b06cff',fog:'#110a20',sky:'#7a5ab8',light:'#d8c8ff',rim:'#2a2240',prop:'crystal',propColor:'#6a3ab8',accent:'#c08aff'},
 foundry:{ground:'#2e2a28',patch:'#3a3430',crack:'#ff8a2a',fog:'#2a1a10',sky:'#d89a6a',light:'#ffd0a0',rim:'#3a3430',prop:'anvil',propColor:'#4a4440',accent:'#ff9a3a'},
 citadel:{ground:'#26222e',patch:'#1e1a26',crack:'#9a4aff',fog:'#18121f',sky:'#8a7aa8',light:'#e0d0ff',rim:'#2e2838',prop:'spire',propColor:'#2e2838',accent:'#b07aff'},
 gate:{ground:'#3e1c16',patch:'#2a120e',crack:'#ff5a1a',fog:'#3a1008',sky:'#ff7a4a',light:'#ffb080',rim:'#2a1410',prop:'spike',propColor:'#1a100c',accent:'#ff6a1a'},
 abyss:{ground:'#160e1e',patch:'#22142e',crack:'#c04aff',fog:'#0a0612',sky:'#5a3a8a',light:'#c8b0ff',rim:'#1e1428',prop:'crystal',propColor:'#4a1a7a',accent:'#d08aff'},
}
export const ARENA_RADIUS=23

/** Small seamless detail texture, repeated across the arena, so the ground reads at the camera's distance. */
function detailTexture(look:Look,seed:number){
 const size=512;const c=document.createElement('canvas');c.width=c.height=size;const g=c.getContext('2d')!;const rand=seeded(seed)
 g.fillStyle=look.ground;g.fillRect(0,0,size,size)
 const wrap=(x:number,y:number,r:number,draw:(x:number,y:number)=>void)=>{for(const dx of [-size,0,size])for(const dy of [-size,0,size])if(x+dx>-r&&x+dx<size+r&&y+dy>-r&&y+dy<size+r)draw(x+dx,y+dy)}
 for(let i=0;i<700;i++){const x=rand()*size,y=rand()*size,r=3+rand()*14;g.globalAlpha=.05+rand()*.09;g.fillStyle=rand()<.6?look.patch:rand()<.8?'#000':'#fff'
  wrap(x,y,r,(px,py)=>{g.beginPath();g.ellipse(px,py,r,r*(.5+rand()*.5),rand()*3,0,Math.PI*2);g.fill()})}
 g.globalAlpha=.22
 for(let i=0;i<160;i++){const x=rand()*size,y=rand()*size,r=1+rand()*2;g.fillStyle=rand()<.7?'#000':'#ffffff';wrap(x,y,r,(px,py)=>{g.beginPath();g.arc(px,py,r,0,Math.PI*2);g.fill()})}
 g.globalAlpha=.22;g.strokeStyle='#000';g.lineWidth=1.2
 for(let i=0;i<60;i++){const x=rand()*size,y=rand()*size;const pts:[number,number][]=[[x,y]];let px=x,py=y;for(let k=0;k<3;k++){px+=(rand()-.5)*26;py+=(rand()-.5)*26;pts.push([px,py])}
  wrap(x,y,60,(ox,oy)=>{g.beginPath();g.moveTo(ox,oy);for(const [qx,qy] of pts.slice(1))g.lineTo(qx+ox-x,qy+oy-y);g.stroke()})}
 g.globalAlpha=1
 const map=new THREE.CanvasTexture(c);map.colorSpace=THREE.SRGBColorSpace;map.wrapS=map.wrapT=THREE.RepeatWrapping;map.repeat.set(9,9);map.anisotropy=8
 return map
}

/** Large, soft overlays: shade patches break up the repetition; glowing cracks for the fire stages. */
function overlayTexture(look:Look,seed:number,kind:'shade'|'cracks'){
 const size=1024;const c=document.createElement('canvas');c.width=c.height=size;const g=c.getContext('2d')!;const rand=seeded(seed*7+(kind==='shade'?1:2))
 if(kind==='shade'){for(let i=0;i<40;i++){const x=rand()*size,y=rand()*size,r=40+rand()*120;const grad=g.createRadialGradient(x,y,0,x,y,r);const tone=rand()<.6?'0,0,0':'255,255,255';grad.addColorStop(0,`rgba(${tone},${rand()<.6?.22:.1})`);grad.addColorStop(1,`rgba(${tone},0)`);g.fillStyle=grad;g.fillRect(x-r,y-r,r*2,r*2)}}
 else{g.strokeStyle='#fff';g.lineCap='round';for(let i=0;i<40;i++){let x=rand()*size,y=rand()*size;g.lineWidth=1.5+rand()*3.5;g.beginPath();g.moveTo(x,y);for(let k=0;k<6;k++){x+=(rand()-.5)*110;y+=(rand()-.5)*110;g.lineTo(x,y)}g.stroke()}}
 const tex=new THREE.CanvasTexture(c);tex.colorSpace=THREE.SRGBColorSpace;return tex
}

function prop(kind:Look['prop'],color:string,accent:string,rand:()=>number){
 const g=new THREE.Group();const m=mat(color,{rough:.9})
 const add=(geo:THREE.BufferGeometry,material:THREE.Material,x=0,y=0,z=0)=>{const o=new THREE.Mesh(geo,material);o.position.set(x,y,z);o.castShadow=true;o.receiveShadow=true;g.add(o);return o}
 switch(kind){
  case 'tree':{add(new THREE.CylinderGeometry(.12,.22,2.6,5),m,0,1.3,0);for(let i=0;i<4;i++){const b=add(new THREE.CylinderGeometry(.04,.08,1.2,4),m,0,1.6+i*.3,0);b.rotation.set(rand()*1.2-.6,rand()*6,.9+rand()*.4);b.translateY(.5)}break}
  case 'grave':{add(new THREE.BoxGeometry(.7,1.1,.18),m,0,.5,0).rotation.z=(rand()-.5)*.3;add(new THREE.BoxGeometry(.9,.12,1.4),mat('#4a463e'),0,.05,.7);break}
  case 'web':{add(new THREE.CylinderGeometry(.15,.25,3.2,5),m,0,1.6,0);const web=add(new THREE.CircleGeometry(1.1,8),mat('#e8e8f0',{rough:.9,opacity:.35,side:THREE.DoubleSide}),.6,2.2,0);web.rotation.y=Math.PI/2;add(new THREE.SphereGeometry(.18,6,4),mat(accent,{emissive:accent,glow:1.4}),.3,.15,.4);break}
  case 'pillar':{add(new THREE.CylinderGeometry(.45,.5,3.4,8),m,0,1.7,0);add(new THREE.BoxGeometry(1.2,.25,1.2),m,0,3.45,0);const fire=add(new THREE.ConeGeometry(.22,.6,6),glow(accent,.8),0,3.85,0);fire.userData.flicker=1;break}
  case 'spike':{for(let i=0;i<3;i++){const s=add(new THREE.ConeGeometry(.35+rand()*.25,1.6+rand()*1.6,5),m,(rand()-.5)*1.2,.9,(rand()-.5)*1.2);s.rotation.set((rand()-.5)*.4,0,(rand()-.5)*.4)}break}
  case 'cage':{for(let i=0;i<8;i++){const a=i/8*Math.PI*2;add(new THREE.CylinderGeometry(.04,.04,2,4),m,Math.cos(a)*.8,1,Math.sin(a)*.8)}add(new THREE.TorusGeometry(.8,.05,4,12),m,0,2,0).rotation.x=Math.PI/2;add(new THREE.ConeGeometry(.3,.7,6),glow(accent,.7),0,.35,0).userData.flicker=1;break}
  case 'crystal':{for(let i=0;i<4;i++){const c=add(new THREE.OctahedronGeometry(.35+rand()*.4),mat(color,{emissive:accent,glow:.9,rough:.2,metal:.2}),(rand()-.5)*1.2,.6+rand()*.6,(rand()-.5)*1.2);c.scale.y=1.8+rand()}break}
  case 'anvil':{add(new THREE.BoxGeometry(1,.5,.5),m,0,.75,0);add(new THREE.BoxGeometry(.5,.5,.4),m,0,.25,0);add(new THREE.ConeGeometry(.2,.5,4),m,.65,.85,0).rotation.z=-Math.PI/2;add(new THREE.CylinderGeometry(.5,.6,.3,8),glow(accent,.55),1.6,.15,.8);break}
  case 'spire':{add(new THREE.ConeGeometry(.6,4.5,5),m,0,2.25,0);add(new THREE.OctahedronGeometry(.25),mat(accent,{emissive:accent,glow:2}),0,4.8,0).userData.float=1;break}
 }
 return g
}

/** Hundreds of small instanced details (tufts, stones, bones, embers) so the floor is not a flat sheet. */
function scatter(group:THREE.Group,look:Look,rand:()=>number){
 const kinds:{geo:THREE.BufferGeometry;mat:THREE.Material;count:number;scale:[number,number];lift:number}[]=[
  {geo:new THREE.DodecahedronGeometry(.18,0),mat:mat(look.rim,{rough:.95}),count:140,scale:[.5,1.6],lift:.05},
  {geo:new THREE.ConeGeometry(.06,.45,4),mat:mat(look.patch,{rough:1}),count:['tree','web','grave'].includes(look.prop)?320:60,scale:[.6,1.4],lift:.2},
 ]
 if(look.crack)kinds.push({geo:new THREE.DodecahedronGeometry(.12,0),mat:mat('#2a1a14',{emissive:look.crack,glow:1.4,rough:.8}),count:70,scale:[.6,1.5],lift:.04})
 const m=new THREE.Matrix4(),q=new THREE.Quaternion(),p=new THREE.Vector3(),sc=new THREE.Vector3(),e=new THREE.Euler()
 for(const k of kinds){const inst=new THREE.InstancedMesh(k.geo,k.mat,k.count);inst.receiveShadow=true
  for(let i=0;i<k.count;i++){const a=rand()*Math.PI*2,r=Math.sqrt(rand())*(ARENA_RADIUS+1);const s=k.scale[0]+rand()*(k.scale[1]-k.scale[0]);p.set(Math.cos(a)*r,k.lift*s,Math.sin(a)*r);q.setFromEuler(e.set((rand()-.5)*.4,rand()*6,(rand()-.5)*.4));sc.setScalar(s);m.compose(p,q,sc);inst.setMatrixAt(i,m)}
  group.add(inst)}
}

export type Arena={group:THREE.Group;key:THREE.DirectionalLight;portal:THREE.Vector3;fog:THREE.Color;accent:string;animated:THREE.Object3D[];update:(t:number)=>void;dispose:()=>void}

export function buildArena(theme:Theme,seed:number):Arena{
 const look=LOOKS[theme];const group=new THREE.Group();const rand=seeded(seed||1);const animated:THREE.Object3D[]=[]
 // Textures and materials made for this arena only; shared materials from mat() and glow() stay cached.
 const own:{dispose:()=>void}[]=[];const keep=<T extends {dispose:()=>void}>(x:T)=>{own.push(x);return x}
 const ground=new THREE.Mesh(new THREE.CircleGeometry(ARENA_RADIUS+9,64),keep(new THREE.MeshStandardMaterial({map:keep(detailTexture(look,seed)),roughness:.95,metalness:0})));ground.rotation.x=-Math.PI/2;ground.receiveShadow=true;group.add(ground)
 const shade=new THREE.Mesh(new THREE.CircleGeometry(ARENA_RADIUS+9,64),keep(new THREE.MeshBasicMaterial({map:keep(overlayTexture(look,seed,'shade')),transparent:true,depthWrite:false})));shade.rotation.x=-Math.PI/2;shade.position.y=.006;group.add(shade)
 if(look.crack){const cracks=new THREE.Mesh(new THREE.CircleGeometry(ARENA_RADIUS+9,64),keep(new THREE.MeshBasicMaterial({color:look.crack,alphaMap:keep(overlayTexture(look,seed,'cracks')),transparent:true,depthWrite:false,blending:THREE.AdditiveBlending})));cracks.rotation.x=-Math.PI/2;cracks.position.y=.012;group.add(cracks)}
 scatter(group,look,rand)
 const outer=new THREE.Mesh(new THREE.RingGeometry(ARENA_RADIUS+9,90,48),mat(look.fog,{rough:1}));outer.rotation.x=-Math.PI/2;outer.position.y=-.02;group.add(outer)
 // A broken wall of rocks marks the edge of the fight.
 for(let i=0;i<46;i++){const a=i/46*Math.PI*2+rand()*.05;const r=ARENA_RADIUS+1.6+rand()*1.2
  const rock=new THREE.Mesh(new THREE.DodecahedronGeometry(.9+rand()*1.1,0),mat(look.rim,{rough:.95}));rock.position.set(Math.cos(a)*r,.4+rand()*.6,Math.sin(a)*r);rock.rotation.set(rand()*3,rand()*3,rand()*3);rock.scale.y=.6+rand()*.9;rock.castShadow=true;rock.receiveShadow=true;group.add(rock)}
 for(let i=0;i<16;i++){const a=rand()*Math.PI*2;const r=13+rand()*(ARENA_RADIUS-13);const p=prop(look.prop,look.propColor,look.accent,rand);p.position.set(Math.cos(a)*r,0,Math.sin(a)*r);p.rotation.y=rand()*6;if(Math.abs(Math.cos(a)*r)<5&&Math.sin(a)*r<-12)continue;group.add(p);p.traverse(o=>{if(o.userData.flicker||o.userData.float)animated.push(o)})}
 const portal=new THREE.Vector3(0,0,-(ARENA_RADIUS-3))
 const gate=new THREE.Group();gate.position.copy(portal);group.add(gate)
 const ring=new THREE.Mesh(new THREE.TorusGeometry(2.3,.32,6,24),mat(look.rim,{rough:.8}));ring.position.y=2.6;gate.add(ring)
 const swirl=new THREE.Mesh(new THREE.CircleGeometry(2.05,32),glow(look.accent,.55,THREE.DoubleSide));swirl.position.y=2.6;swirl.userData.spin=1;gate.add(swirl);animated.push(swirl)
 for(const s of [-1,1]){const pillar=new THREE.Mesh(new THREE.CylinderGeometry(.35,.45,3.2,6),mat(look.rim,{rough:.9}));pillar.position.set(s*2.5,1.6,0);pillar.castShadow=true;gate.add(pillar)}
 const portalLight=new THREE.PointLight(look.accent,7,10,2);portalLight.position.set(0,2.6,1.4);gate.add(portalLight)
 group.add(new THREE.HemisphereLight(look.sky,look.ground,.65))
 const key=new THREE.DirectionalLight(look.light,1.5);key.castShadow=true;key.shadow.mapSize.set(2048,2048)
 const cam=key.shadow.camera;cam.left=-18;cam.right=18;cam.top=18;cam.bottom=-18;cam.near=1;cam.far=60;key.shadow.bias=-.0005
 group.add(key);group.add(key.target)
 if(look.crack)for(let i=0;i<5;i++){const l=new THREE.PointLight(look.crack,2,6,2);const a=rand()*Math.PI*2,r=rand()*ARENA_RADIUS;l.position.set(Math.cos(a)*r,.6,Math.sin(a)*r);group.add(l)}
 const update=(t:number)=>{for(const o of animated){if(o.userData.spin)o.rotation.z=t*o.userData.spin;if(o.userData.flicker)o.scale.y=1+Math.sin(t*12+o.id)*.18;if(o.userData.float)o.position.y=4.8+Math.sin(t*1.5+o.id)*.15}}
 return {group,key,portal,fog:new THREE.Color(look.fog),accent:look.accent,animated,update,dispose:()=>{for(const x of own)x.dispose();key.shadow.dispose()}}
}
