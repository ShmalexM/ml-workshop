"""The glossary: every linked term exists, definitions are plain and short, and links land on the right words."""
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from courses import COURSES, LESSONS, public_curriculum
from glossary import BY_TERM_ID, GLOSSARY, PATH_IDS, entries_for, lesson_texts, linked_terms
from runner import node_binary

# Terms the glossary must define, beyond the three each path introduces.
REQUIRED = ['variable', 'function', 'parameter', 'argument', 'return', 'list', 'tuple', 'dictionary',
            'loop', 'comprehension', 'exception', 'import', 'module', 'class', 'method', 'attribute',
            'tensor', 'gradient', 'loss', 'batch', 'epoch', 'shape', 'token', 'embedding',
            'idempotency', 'latency', 'derivative', 'slope', 'learning-rate']


class GlossaryTests(unittest.TestCase):
    def test_entries_are_complete_and_short(self):
        self.assertEqual(len({entry['id'] for entry in GLOSSARY}), len(GLOSSARY))
        lesson_ids = {lesson['id'] for lesson in LESSONS}
        for entry in GLOSSARY:
            with self.subTest(term=entry['id']):
                self.assertTrue(entry['term'].strip())
                definition = entry['definition']
                self.assertTrue(definition.strip())
                self.assertTrue(definition.endswith('.'), definition)
                # One or two sentences: a full stop followed by a space or the end.
                self.assertLessEqual(len(re.findall(r'\.(?:\s|$)', definition)), 2, definition)
                self.assertLessEqual(len(definition), 240, definition)
                self.assertTrue(entry['match'], 'every term links somewhere it appears')
                if entry['paths'] is not None:
                    self.assertTrue(set(entry['paths']) <= set(PATH_IDS))
                if entry['lesson'] is not None:
                    self.assertIn(entry['lesson'], lesson_ids)
        self.assertEqual(set(PATH_IDS), {course['id'] for course in COURSES})
        for term_id in REQUIRED:
            self.assertIn(term_id, BY_TERM_ID)

    def test_path_terms_come_from_the_glossary(self):
        pairs = {(entry['term'], entry['definition']) for entry in GLOSSARY}
        for course in COURSES:
            for term, definition in course['orientation']['terms']:
                self.assertIn((term, definition), pairs, course['id'])

    def test_one_meaning_per_word_in_each_path(self):
        for path in PATH_IDS:
            owners = {}
            for entry in entries_for(path):
                for form in entry['match']:
                    self.assertNotIn(form, owners, f'{path}: {form!r} links {owners.get(form)} and {entry["id"]}')
                    owners[form] = entry['id']

    def test_every_linked_term_exists_and_applies_to_its_path(self):
        curriculum = public_curriculum()
        served = {entry['id']: entry for entry in curriculum['glossary']}
        self.assertEqual(set(served), set(BY_TERM_ID))
        self.assertTrue(all('paths' not in entry for entry in curriculum['glossary']))
        for lesson in curriculum['lessons']:
            with self.subTest(lesson=lesson['id']):
                self.assertEqual(len(lesson['glossary']), len(set(lesson['glossary'])))
                for term_id in lesson['glossary']:
                    self.assertIn(term_id, served)
                    self.assertTrue(served[term_id]['definition'])
                    self.assertIn(term_id, {entry['id'] for entry in entries_for(lesson['course'])})
        self.assertIs(public_curriculum(), curriculum)

    def test_links_follow_the_meaning_each_path_uses(self):
        by_id = {lesson['id']: lesson['glossary'] for lesson in public_curriculum()['lessons']}
        self.assertEqual(by_id['foundations-3'][:6],
                         ['gradient', 'loss', 'parameter-ml', 'derivative', 'slope', 'gradient-descent'])
        self.assertIn('parameter', by_id['python-3'])
        self.assertNotIn('parameter-ml', by_id['python-3'])
        self.assertIn('state-ui', by_id['web-1'])
        self.assertIn('state-run', by_id['harness-1'])
        self.assertIn('return-rl', by_id['rl-2'])
        self.assertNotIn('return', by_id['rl-2'])
        self.assertIn('tf-variable', by_id['tensorflow-1'])
        # "loss" appears only inside a quoted topic in modern-3, which is data.
        self.assertNotIn('loss', by_id['modern-3'])

    def test_matching_rules(self):
        texts = ['A loss function turns errors into a loss.', 'Gradients and the gradient.']
        self.assertEqual(linked_terms(texts, 'foundations'), ['loss', 'gradient'])
        self.assertEqual(linked_terms(['The topic is "loss".'], 'foundations'), [])
        self.assertEqual(linked_terms(['set_random_seed, reset and settings'], 'data'), [])
        self.assertEqual(linked_terms(['None of them', 'none'], 'python'), ['none'])
        self.assertEqual(lesson_texts({'intro': 'a\n\nb', 'explanation': 'c'}), ['a', 'b', 'c'])

    def test_browser_links_the_same_terms(self):
        """src/glossary.ts must find the terms the server listed, in the same order."""
        typescript = ROOT / 'node_modules' / 'typescript'
        node = node_binary()
        if not typescript.is_dir() or not node:
            self.skipTest('needs Node.js and the TypeScript package from npm install')
        script = r'''
const fs = require('fs');
const ts = require(process.argv[1]);
const source = fs.readFileSync(process.argv[2], 'utf8');
const js = ts.transpileModule(source, {compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022}}).outputText;
const mod = {exports: {}};
new Function('module', 'exports', 'require', js)(mod, mod.exports, require);
const data = JSON.parse(fs.readFileSync(0, 'utf8'));
const byId = new Map(data.glossary.map(entry => [entry.id, entry]));
const out = {};
for (const lesson of data.lessons) {
  const texts = [...lesson.intro.split('\n\n'), ...lesson.explanation.split('\n\n')];
  const pieces = mod.exports.linkTerms(texts, lesson.glossary.map(id => byId.get(id)));
  out[lesson.id] = pieces.flat().filter(piece => typeof piece !== 'string').map(piece => piece.entry.id);
}
process.stdout.write(JSON.stringify(out));
'''
        curriculum = public_curriculum()
        result = subprocess.run([node, '-e', script, str(typescript), str(ROOT / 'src' / 'glossary.ts')],
                                input=json.dumps(curriculum), capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        linked = json.loads(result.stdout)
        for lesson in curriculum['lessons']:
            self.assertEqual(linked[lesson['id']], lesson['glossary'], lesson['id'])


if __name__ == '__main__':
    unittest.main()
