// Replaces src/game/three/scene.ts in the simulation bundle: no WebGL in Node.
const noop=()=>{}
export function createRenderer(){return {setSize:noop,setPixelRatio:noop,getPixelRatio:()=>1,dispose:noop,forceContextLoss:noop,shadowMap:{},getSize:(v:any)=>v,render:noop} as any}
export function environment(){return null as any}
export function createComposer(){return {composer:{render:noop,setSize:noop,passes:[],dispose:noop,addPass:noop},bloom:{resolution:{set:noop}}} as any}
export function reducedMotion(){return true}
export function webglAvailable(){return true}
