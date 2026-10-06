import { existsSync, readdirSync, readFileSync } from 'node:fs'
import { basename, dirname, join } from 'node:path'
import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'

type Manifest = { name?: string; version?: string; license?: string; repository?: string | { url?: string }; homepage?: string }
const LICENSE_FILE = /^(licen[cs]e|copying|notice)([.-].*)?$/i
const HEADER = `Engineering Workshop's interface includes the open-source packages below.
Each package's license text follows its name. The Engineering Workshop code
itself is under the MIT License; see LICENSE.`
const FOOTER = `The PDF reader's fonts, character maps and decoders in pdfjs/ carry their own
license files next to them.`

// The nearest folder at or above a bundled file whose package.json has a name.
function packageRoot(file: string) {
  for (let dir = dirname(file); basename(dir) !== 'node_modules' && dir !== dirname(dir); dir = dirname(dir)) {
    const manifest = join(dir, 'package.json')
    if (!existsSync(manifest)) continue
    const pkg: Manifest = JSON.parse(readFileSync(manifest, 'utf8'))
    if (pkg.name) return { dir, pkg }
  }
}

// Minifying drops the license comments of some packages, so the build writes the
// license of every bundled package to dist/THIRD_PARTY_LICENSES.txt.
function thirdPartyLicenses(): Plugin {
  return {
    name: 'third-party-licenses', apply: 'build',
    generateBundle() {
      const packages = new Map<string, { dir: string; pkg: Manifest }>()
      for (const id of this.getModuleIds()) {
        const file = id.replace(/^\0/, '').split('?')[0]
        const root = file.includes('/node_modules/') ? packageRoot(file) : undefined
        if (root) packages.set(`${root.pkg.name} ${root.pkg.version}`, root)
      }
      const sections = [...packages].sort(([a], [b]) => (a < b ? -1 : 1)).map(([title, { dir, pkg }]) => {
        const url = (typeof pkg.repository === 'string' ? pkg.repository : pkg.repository?.url)?.replace(/^git\+/, '').replace(/\.git$/, '') ?? pkg.homepage
        const texts = readdirSync(dir, { withFileTypes: true }).filter(entry => entry.isFile() && LICENSE_FILE.test(entry.name)).map(entry => entry.name).sort()
          .map(name => readFileSync(join(dir, name), 'utf8').replace(/\r\n?/g, '\n').replace(/^\s*\n/, '').trimEnd())
        if (!texts.length) this.warn(`${title} does not include a license file`)
        return [title, `License: ${pkg.license ?? 'not stated'}`, ...(url ? [url] : []), '', texts.join('\n\n') || 'This package does not include a license file.'].join('\n')
      })
      // The server sends text/plain without a charset, and some notices use characters
      // outside ASCII, such as the copyright sign. A byte order mark makes browsers read
      // the file as UTF-8.
      const source = '\uFEFF' + [HEADER, ...sections, FOOTER].join(`\n\n${'='.repeat(80)}\n\n`) + '\n'
      this.emitFile({ type: 'asset', fileName: 'THIRD_PARTY_LICENSES.txt', source })
    },
  }
}

export default defineConfig({ plugins: [react(), thirdPartyLicenses()], build: { chunkSizeWarningLimit: 900 } })
