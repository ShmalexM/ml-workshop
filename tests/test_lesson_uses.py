"""The constructs each lesson's code uses ("You'll use"), linked to the lesson that teaches them."""
import sys
import unittest
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from courses import BY_ID, LESSONS, public_curriculum
from lesson_uses import JAVASCRIPT, PYTHON, javascript_constructs, lesson_uses, python_constructs

# Taught in the lesson's explanation rather than in its code.
EXPLAINED = {'range': 'range('}


class LessonUsesTests(unittest.TestCase):
    def test_python_constructs(self):
        code = '''
import math
from copy import deepcopy

@decorate
def score(pairs, scale=2, *rest):
    """Docstring."""
    if not pairs or len(pairs) > 9:
        raise ValueError("empty")
    total = 0
    for p, t in zip(pairs, pairs[1:]):
        total += (p - t) ** 2
    squares = [x * x for x in pairs]
    grid[1, 0] = 0
    lookup = {"a": 1}
    with open("f") as f:
        pass
    while total > 1 and 0 <= total < 5:
        break
    return f"{total}", sorted(pairs, key=lambda x: -x) if pairs else None
'''
        found = python_constructs(code)
        for construct in ['import', 'decorator', 'def', 'default', 'star', 'if', 'logic', 'len', 'raise',
                          'for', 'tuple', 'zip', 'slice', 'augmented', 'power', 'comprehension', 'index',
                          'dict', 'with', 'while', 'chained', 'break', 'f-string', 'sorted', 'keyword',
                          'lambda', 'conditional']:
            self.assertIn(construct, found)
        for construct in ['class', 'try', 'set', 'yield', 'enumerate', 'in']:
            self.assertNotIn(construct, found)
        # grid[1, 0] indexes two dimensions; it is not a tuple the learner builds.
        self.assertNotIn('tuple', python_constructs('grid[1, 0] = 5'))

    def test_javascript_constructs_ignore_strings_and_comments(self):
        code = '''// const in a comment, and x => x
const text = "a => b === c";
function f(state) { return {...state, count: state.count + 1}; }
'''
        self.assertEqual(javascript_constructs(code), {'js-let-const', 'js-function', 'js-spread'})

    def test_each_construct_is_used_by_the_lesson_that_teaches_it(self):
        for id, label, teacher, url in PYTHON:
            with self.subTest(construct=id):
                self.assertTrue(label)
                self.assertTrue((teacher is None) != (url is None))
                if teacher is None:
                    continue
                lesson = BY_ID[teacher]
                found = set().union(*(python_constructs(lesson[key]) for key in ('starter', 'solution')),
                                    python_constructs(lesson['example']['code']))
                self.assertTrue(id in found or EXPLAINED.get(id, '\0') in lesson['explanation'], teacher)
        for id, label, teacher, url, _ in JAVASCRIPT:
            with self.subTest(construct=id):
                self.assertTrue((teacher is None) != (url is None))
                if teacher is None:
                    continue
                lesson = BY_ID[teacher]
                found = set().union(*(javascript_constructs(lesson[key]) for key in ('starter', 'solution')),
                                    javascript_constructs(lesson['example']['code']))
                self.assertIn(id, found, teacher)

    def test_every_lesson_lists_its_uses(self):
        lesson_ids = [lesson['id'] for lesson in LESSONS]
        served = {lesson['id']: lesson['uses'] for lesson in public_curriculum()['lessons']}
        for lesson in LESSONS:
            with self.subTest(lesson=lesson['id']):
                uses = served[lesson['id']]
                self.assertEqual(uses, lesson_uses(lesson))
                self.assertEqual(len({use['id'] for use in uses}), len(uses))
                taught = [use for use in uses if use['lesson']]
                # Lessons first, in teaching order, then documentation links.
                self.assertEqual(uses[:len(taught)], taught)
                self.assertEqual([lesson_ids.index(use['lesson']) for use in taught],
                                 sorted(lesson_ids.index(use['lesson']) for use in taught))
                for use in uses:
                    if use['lesson']:
                        self.assertIn(use['lesson'], BY_ID)
                        self.assertNotEqual(use['lesson'], lesson['id'])
                        if BY_ID[use['lesson']]['course'] == lesson['course']:
                            self.assertLess(lesson_ids.index(use['lesson']), lesson_ids.index(lesson['id']))
                    else:
                        url = urlparse(use['url'])
                        self.assertEqual(url.scheme, 'https')
                        self.assertIn(url.hostname, ['docs.python.org', 'developer.mozilla.org'])

    def test_foundations_two_names_the_python_it_needs(self):
        uses = {use['id']: use['lesson'] for use in lesson_uses(BY_ID['foundations-2'])}
        self.assertEqual({key: uses[key] for key in ['power', 'def', 'comprehension', 'zip', 'tuple', 'raise']},
                         {'power': 'python-2', 'def': 'python-3', 'comprehension': 'python-7',
                          'zip': 'python-7', 'tuple': 'python-8', 'raise': 'python-10'})
        self.assertEqual(lesson_uses(BY_ID['python-1']), [])
        self.assertEqual(lesson_uses(BY_ID['web-0']), [])
        web = {use['id']: use['lesson'] for use in lesson_uses(BY_ID['web-2'])}
        self.assertEqual(web['js-strict'], 'web-0')
        self.assertEqual(web['js-spread'], 'web-1')
        self.assertNotIn('js-spread', {use['id'] for use in lesson_uses(BY_ID['web-1'])})


if __name__ == '__main__':
    unittest.main()
