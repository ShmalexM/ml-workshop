// Checks for the assistant's Markdown parser (src/assistant/markdownParser.ts). Node loads the TypeScript file
// by removing its types, so no build or package is needed. tests/test_assistant.py runs this file.
// Prints one line per check and exits with 1 when a check fails.
import assert from 'node:assert/strict'

const md = await import(new URL('../src/assistant/markdownParser.ts', import.meta.url).href)
const {parseBlocks, parseInline, withoutThinking, LONG_LINE} = md
const text = v => ({t: 'text', v})
const checks = []
const check = (name, run) => checks.push([name, run])

/** Parse an answer the way Markdown.tsx does: blocks, then the inline text of each block. */
function parseAll(source) {
  return parseBlocks(source).map(block => block.items ? block.items.map(parseInline) : 'text' in block && block.kind !== 'code' && block.kind !== 'pre' && block.kind !== 'plain' ? parseInline(block.text) : block)
}

check('headings', () => {
  assert.deepEqual(parseBlocks('# Title #'), [{kind: 'h', text: 'Title'}])
  assert.deepEqual(parseBlocks('## Using C#'), [{kind: 'h', text: 'Using C#'}])
  assert.deepEqual(parseBlocks('   ### Three   ###   '), [{kind: 'h', text: 'Three'}])
  assert.deepEqual(parseBlocks('#hashtag'), [{kind: 'p', text: '#hashtag'}])
  assert.deepEqual(parseBlocks('####### seven'), [{kind: 'p', text: '####### seven'}])
})

check('blocks', () => {
  const source = ['One', 'still one', '', '- a', '- b', '  more', '', '3. x', '4) y', '', '> q1', '> q2', '',
    '| a | b |', '|---|---|', '', '* * *', '', '```py', 'print(1)', '```', '', '````', '```', 'x', '```', '````', '', '~~~', 'open'].join('\n')
  assert.deepEqual(parseBlocks(source), [
    {kind: 'p', text: 'One\nstill one'},
    {kind: 'ul', items: ['a', 'b\nmore'], start: 1},
    {kind: 'ol', items: ['x', 'y'], start: 3},
    {kind: 'quote', text: 'q1\nq2'},
    {kind: 'pre', text: '| a | b |\n|---|---|'},
    {kind: 'hr'},
    {kind: 'code', lang: 'py', text: 'print(1)', open: false},
    {kind: 'code', lang: '', text: '```\nx\n```', open: false},
    {kind: 'code', lang: '', text: 'open', open: true},
  ])
})

check('long lines stay plain text', () => {
  const long = '**' + 'x'.repeat(LONG_LINE) + '**'
  assert.deepEqual(parseBlocks('Before\n' + long + '\nAfter'), [{kind: 'p', text: 'Before'}, {kind: 'plain', text: long}, {kind: 'p', text: 'After'}])
  assert.deepEqual(parseInline(long), [text(long)])
})

check('inline', () => {
  assert.deepEqual(parseInline('Use `x = 1`, **bold _x_**, *em*, __init__ and snake_case'), [
    text('Use '), {t: 'code', v: 'x = 1'}, text(', '), {t: 'strong', c: [text('bold _x_')]}, text(', '), {t: 'em', c: [text('em')]},
    text(', __init__ and snake_case')])
  assert.deepEqual(parseInline('a\nb'), [text('a'), {t: 'br'}, text('b')])
  assert.deepEqual(parseInline('2 * 3 * 4'), [text('2 * 3 * 4')])
  assert.deepEqual(parseInline('**a*'), [text('*'), {t: 'em', c: [text('a')]}])
  assert.deepEqual(parseInline('a ` b'), [text('a ` b')])
  assert.deepEqual(parseInline('empty `` stays'), [text('empty `` stays')])
  assert.deepEqual(parseInline('**`code` in bold**'), [{t: 'strong', c: [{t: 'code', v: 'code'}, text(' in bold')]}])
})

check('links', () => {
  const link = source => parseInline(source)[0]
  assert.deepEqual(link('[docs](https://example.com/a "title")'), {t: 'link', text: 'docs', href: 'https://example.com/a', host: 'example.com'})
  // An unsafe link keeps only its text.
  for (const unsafe of ['javascript:alert(1)', 'JaVaScRiPt:alert(1)', 'data:text/html,x', 'vbscript:x', 'file:///etc/passwd', '/relative', '//evil.example/x']) {
    const tokens = parseInline(`[x](${unsafe})`)
    assert.ok(tokens.every(token => token.t === 'text'), unsafe)
    assert.equal(tokens[0].v, 'x', unsafe)
  }
  assert.deepEqual(parseInline('![tracker](https://evil.example/p.png)'), [text('tracker')])
  assert.deepEqual(parseInline('[a]( https://x.example)'), [text('[a]( https://x.example)')])
  assert.equal(link('[x](https://openai.com@evil.example/login)').host, 'evil.example')
  assert.equal(link('[x](https://аpple.com/)').host, 'xn--pple-43d.com')
})

check('thinking', () => {
  assert.deepEqual(withoutThinking('<think>hm</think>\nAnswer'), {text: 'Answer', thinking: false})
  assert.deepEqual(withoutThinking('  <think>still going'), {text: '', thinking: true})
  assert.deepEqual(withoutThinking('No <think> here'), {text: 'No <think> here', thinking: false})
})

// Inputs that made the old regular expressions backtrack. Each is about 200,000 characters; a parser that
// is not linear needs seconds or minutes for them.
const size = 200_000
const repeat = line => (line + '\n').repeat(Math.ceil(size / (line.length + 1)))
const fit = (start, fill, end = '') => start + fill.repeat(Math.floor((LONG_LINE - start.length - end.length) / fill.length)) + end
const hostile = {
  'heading with spaces (report)': '# a' + ' '.repeat(4000) + 'b',
  'heading with spaces under the line limit': repeat(fit('# a', ' ', 'b')),
  'one line of [ (report)': '['.repeat(60_000),
  'lines of [': repeat(fit('', '[')),
  'lines of ![': repeat(fit('', '![')),
  'lines of *': repeat(fit('', '*')),
  'lines of **a': repeat(fit('', '**a')),
  'lines of `': repeat(fit('', '`')),
  'lines of [a](': repeat(fit('', '[a](')),
  'lines of [a]': repeat(fit('', '[a]')),
  'lines of ](': repeat(fit('[', '](')),
  'bullet with spaces': repeat(fit('- ', ' ', 'x y')),
  'table with spaces': repeat(fit('|', ' ', 'x')),
  'rule-like line': repeat(fit('-', ' -', 'x')),
  'quote of >': repeat(fit('>', '> ')),
  'mixed answer': ('Text **bold** *em* `code` [l](https://e.example) ![i](x) ' + '[(*`!_#>|- ').repeat(size / 70),
}
for (const [name, source] of Object.entries(hostile)) {
  check(`linear: ${name}`, () => {
    const started = performance.now()
    parseAll(source)
    const ms = performance.now() - started
    assert.ok(ms < 1000, `${Math.round(ms)} ms for ${source.length} characters`)
    return `${Math.round(ms)} ms`
  })
}

let failed = 0
for (const [name, run] of checks) {
  try {
    const note = run()
    console.log(`ok ${name}${note ? ` (${note})` : ''}`)
  } catch (error) {
    failed++
    console.log(`FAIL ${name}\n${error.stack}`)
  }
}
console.log(`${checks.length - failed} of ${checks.length} checks passed`)
process.exitCode = failed ? 1 : 0
