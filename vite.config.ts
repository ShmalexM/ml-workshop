import { existsSync, readdirSync, readFileSync } from 'node:fs'
import { basename, dirname, join } from 'node:path'
import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'

type Manifest = { name?: string; version?: string; license?: string; repository?: string | { url?: string }; homepage?: string }
const LICENSE_FILE = /^(licen[cs]e|copying|notice)([.-].*)?$/i
// These packages ship without a license file, so the text comes from their repository.
const LICENSE_FROM_REPO: Record<string, string> = {
  '@uiw/codemirror-extensions-basic-setup': 'scripts/licenses/uiw-react-codemirror.txt',
  '@uiw/react-codemirror': 'scripts/licenses/uiw-react-codemirror.txt',
}
const HEADER = `Engineering Workshop's interface includes the open-source packages below.
Each package's license text follows its name. The Engineering Workshop code
itself is under the MIT License; see LICENSE.`
const FOOTER = `The PDF reader's fonts, character maps, decoders and color profiles in pdfjs/ carry their own
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
  let projectRoot = process.cwd()
  return {
    name: 'third-party-licenses', apply: 'build',
    configResolved(config) { projectRoot = config.root },
    generateBundle() {
      const packages = new Map<string, { dir: string; pkg: Manifest }>()
      for (const id of this.getModuleIds()) {
        const file = id.replace(/^\0/, '').split('?')[0]
        const found = file.includes('/node_modules/') ? packageRoot(file) : undefined
        if (found) packages.set(`${found.pkg.name} ${found.pkg.version}`, found)
      }
      const sections = [...packages].sort(([a], [b]) => (a < b ? -1 : 1)).map(([title, { dir, pkg }]) => {
        const url = (typeof pkg.repository === 'string' ? pkg.repository : pkg.repository?.url)?.replace(/^git\+/, '').replace(/\.git$/, '') ?? pkg.homepage
        const files = readdirSync(dir, { withFileTypes: true }).filter(entry => entry.isFile() && LICENSE_FILE.test(entry.name)).map(entry => join(dir, entry.name)).sort()
        const fromRepo = !files.length && pkg.name ? LICENSE_FROM_REPO[pkg.name] : undefined
        if (fromRepo) files.push(join(projectRoot, fromRepo))
        if (!files.length) this.warn(`${title} does not include a license file`)
        const texts = files.map(file => readFileSync(file, 'utf8').replace(/\r\n?/g, '\n').replace(/^\s*\n/, '').trimEnd())
        const note = fromRepo ? ['The package has no license file. This text is the license file in its repository.'] : []
        return [title, `License: ${pkg.license ?? 'not stated'}`, ...(url ? [url] : []), ...note, '', texts.join('\n\n') || 'This package does not include a license file.'].join('\n')
      })
      const source = [HEADER, ...sections, FOOTER].join(`\n\n${'='.repeat(80)}\n\n`) + '\n'
      this.emitFile({ type: 'asset', fileName: 'THIRD_PARTY_LICENSES.txt', source })
    },
  }
}

export default defineConfig({ plugins: [react(), thirdPartyLicenses()], build: { chunkSizeWarningLimit: 900 } })
