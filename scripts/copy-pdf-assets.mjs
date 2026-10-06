import { cp, mkdir } from 'node:fs/promises'
import { createRequire } from 'node:module'
import { dirname, resolve } from 'node:path'
const require = createRequire(import.meta.url)
const source = dirname(require.resolve('pdfjs-dist/package.json'))
const target = new URL('../public/pdfjs/', import.meta.url)
await mkdir(target, { recursive: true })
for (const folder of ['cmaps', 'standard_fonts', 'wasm']) {
  await cp(resolve(source, folder), new URL(folder, target), { recursive: true })
}
await cp(resolve(source, 'LICENSE'), new URL('LICENSE', target))
