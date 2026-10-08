// Headless balance simulation for the hero game.
// Bundles the real battle engine for Node (no WebGL, simulated time), then runs
// scripts/game-sim/driver.py, which drives the real backend/game.py and sends each fight here.
//
//   npm run game:sim                       class table, Auto vs standing still, curriculum runs
//   npm run game:sim -- classes            one report; also: auto, curriculum, targets, check
//   npm run game:sim -- curriculum --runs 24 --seeds 3
import {spawn} from 'node:child_process'
import {mkdtempSync,rmSync} from 'node:fs'
import {tmpdir} from 'node:os'
import path from 'node:path'
import {fileURLToPath} from 'node:url'
import * as esbuild from 'esbuild'

const root=fileURLToPath(new URL('../',import.meta.url))
const sim=path.join(root,'scripts','game-sim')
const out=mkdtempSync(path.join(tmpdir(),'game-sim-'))
const bundle=path.join(out,'fight.mjs')

// The battle engine imports its renderer from three/scene; the simulation draws nothing.
const noRenderer={name:'no-renderer',setup(build){
 build.onResolve({filter:/(^|\/)scene$/},args=>args.importer.includes(`${path.sep}src${path.sep}game${path.sep}`)?{path:path.join(sim,'scene-stub.ts')}:undefined)
}}
await esbuild.build({entryPoints:[path.join(sim,'fight.ts')],bundle:true,platform:'node',format:'esm',outfile:bundle,plugins:[noRenderer],logLevel:'warning'})

const python=path.join(root,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python')
const child=spawn(python,[path.join(sim,'driver.py'),'--bundle',bundle,...process.argv.slice(2)],{cwd:root,stdio:'inherit'})
const cleanup=()=>rmSync(out,{recursive:true,force:true})
child.on('error',error=>{cleanup();console.error(`Cannot start Python: ${error.message}. Run setup first; see README.md.`);process.exitCode=1})
child.on('exit',(code,signal)=>{cleanup();process.exitCode=code??(signal?1:0)})
