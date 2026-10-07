import { cp, mkdir, rm } from 'node:fs/promises'
import { createRequire } from 'node:module'
import { basename, dirname, resolve } from 'node:path'
const require = createRequire(import.meta.url)
const source = dirname(require.resolve('pdfjs-dist/package.json'))
const target = new URL('../public/pdfjs/', import.meta.url)
// Start clean so that files left out below do not linger from older builds.
await rm(target, { recursive: true, force: true })
await mkdir(target, { recursive: true })
// The app never runs scripts inside PDFs, so pdf.js's script engine (QuickJS) stays out.
const wanted = path => !basename(path).startsWith('quickjs-eval')
for (const folder of ['cmaps', 'standard_fonts', 'wasm']) {
  await cp(resolve(source, folder), new URL(folder, target), { recursive: true, filter: wanted })
}
await cp(resolve(source, 'LICENSE'), new URL('LICENSE', target))
