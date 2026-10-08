"""Worked examples must run as shown and must not masquerade as completion."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from courses import COURSES,LESSONS
from runner import execute
from test_curriculum import OFFLINE_PREFIX,JS_OFFLINE_PREFIX,require_lesson_modules

# Input changes asked about by the prediction questions.
PREDICTIONS = {'python-1': ([('cups = 2', 'cups = 5')], '17', '17'),
 'python-2': ([('print(2 + 3 * 4)', 'print(10 - 4 / 2)')], '8.0\n20\n9\n3.5', '8.0'),
 'python-3': ([('return n * 2', 'return n * 3')], '12\n30', '12'),
 'python-4': ([('bigger(2, 7)', 'bigger(4, 4)')], 'True\nTrue\n4', '4'),
 'python-5': ([('scores[1:3]', 'scores[0:2]')], '70\n65\n[70, 85]\n4', '[70, 85]'),
 'python-6': ([('numbers = [6, 1, 5]', 'numbers = [6, 1, 5, 8]')], '6\n7\n12\n20\n5.0', '5.0'),
 'python-7': ([('price * 2', 'price + 1')], '[3, 6, 4]\n[3, 6, 4]\n[11, 22]', '[3, 6, 4]'),
 'python-8': ([('factor=2', 'factor=10')], '7 9\n(7, 9)\n50 15', '50 15'),
 'python-9': ([('ages.get("dan", 0)', 'ages.get("ben", 0)')], '31\nTrue\n25\n3', '25'),
 'python-10': ([('safe_divide(6, 3)', 'safe_divide(0, 3)')], '0.0\n2.5', '0.0'),
 'python-11': ([(':.3f', ':.1f')], '3.0\nThe square root of 9 is 3.0\n0.7', '0.7'),
 'python-12': ([('loss(0 + step) - loss(0)', 'loss(3 + step) - loss(3)')], '1.0\n0.1\n0.001', '0.001'),
 'python-13': ([('count_above([3, 8, 5], 4)', 'count_above([3, 8, 5], 5)')],
               '3 False\n8 True\n5 False\n1',
               '1'),
 'foundations-1': ([('items = 3', 'items = 4')], '9', '9'),
 'foundations-2': ([('predictions = [3, 5]', 'predictions = [3, 7]')], '[(3, 1), (7, 5)]\n[4, 4]\n4.0', '4.0'),
 'foundations-3': ([('learning_rate = 0.1', 'learning_rate = 0.5')], '-6.0\n3.0', '3.0'),
 'foundations-4': ([('range(10)', 'range(7)')], '6 1 0', '6 1 0'),
 'foundations-5': ([('(6.0 - mean)', '(4.0 - mean)')], '0.0', '0.0'),
 'foundations-6': ([('range(3)', 'range(2)')], '0.4\n0.72', '0.4 then 0.72'),
 'pytorch-1': ([('[[1., 2.], [3., 4.]]', '[[1., 2.], [3., 4.], [5., 6.]]')],
               '[3, 1]\n[[4.0], [10.0], [16.0]]',
               '[3, 1]'),
 'pytorch-2': ([('tensor(3.', 'tensor(4.')], '8.0', '8.0'),
 'pytorch-3': ([('Linear(2, 1)', 'Linear(2, 4)')], '[3, 4]', '[3, 4]'),
 'pytorch-4': ([('batch_size=2', 'batch_size=3')], '[[0, 1, 2], [3, 4]]', '[[0, 1, 2], [3, 4]]'),
 'pytorch-5': ([('lr=0.1', 'lr=0.2')], '0.8', '0.8'),
 'pytorch-6': ([('range(2)', 'range(1)')], '0.4', '0.4'),
 'tensorflow-1': ([('[[1., 2.], [3., 4.]]', '[[1., 2.], [3., 4.], [5., 6.], [7., 8.]]')],
                  '[4, 1]\n[[4.0], [10.0], [16.0], [22.0]]',
                  '[4, 1]'),
 'tensorflow-2': ([('y = x * x', 'y = x * x + 3 * x')], '9.0', '9.0'),
 'tensorflow-3': ([('Dense(1)', 'Dense(4)')], '[3, 4]', '[3, 4]'),
 'tensorflow-4': ([('.batch(2)', '.batch(2, drop_remainder=True)')],
                  '[[0, 1], [2, 3]]',
                  '[[0, 1], [2, 3]]'),
 'tensorflow-5': ([('SGD(0.1)', 'SGD(0.2)')], '0.8', '0.8'),
 'tensorflow-6': ([('range(2)', 'range(1)')], '0.4', '0.4'),
 'modern-1': ([("'learn something'", "'tensors learn missing'")], '[2, 1, 0]', '[2, 1, 0]'),
 'modern-2': ([('= 2, 3, 8', '= 2, 3, 12')], '[2, 3, 12]\n6', '6'),
 'modern-3': ([("topic='tensors'", "topic='gradients'")],
              'human\nExplain gradients.',
              'Explain gradients.'),
 'modern-4': ([("'  hi  '", "'  hello  '")], '5', '5'),
 'modern-5': ([('"source": "notes"', '"source": "book"')],
              'A tensor has a shape.\nnotes:0\nbook',
              'notes:0 then book'),
 'modern-6': ([('"tensor shape"', '"tensor tensor loss"')], '1', '1'),
 'cuda-1': ([('thread_id = 1', 'thread_id = 3')], '11', '11'),
 'cuda-2': ([('= 5, 4', '= 9, 4')], '3\n[0, 1, 2, 3, 4, 5, 6, 7, 8]', '3'),
 'cuda-3': ([('device[0] = 9', 'device[1] = 7')], '[1. 2.]\n[1. 7.]', '[1. 7.]'),
 'cuda-4': ([('print(out)', 'print(out[0][1])')], '4', 'out[0][1]'),
 'cuda-5': ([('np.array([2, 3]', 'np.array([2, -3]')], '-1.0', '-1.0'),
 'cuda-6': ([('= -3, 2, 1', '= 3, 2, 1')], '7 7', '7 7'),
 'harness-1': ([('event = "start"', 'event = "approve"')], 'invalid', 'invalid'),
 'harness-2': ([("{'id': 3, 'shell': 'extra'}", "{'id': 3}")], 'True', 'True'),
 'harness-3': ([('= 7, 3, 10', '= 7, 4, 10')], 'False', 'False'),
 'harness-4': ([('"ok": True', '"ok": False')], '[]\n7', '[] then 7'),
 'backend-1': ([("'  Train a model  '", "'   '")], '\nFalse', 'A blank line, then False'),
 'backend-2': ([('key, payload = "request-1", {"x": 1}', 'key, payload = "request-1", {"x": 2}')],
               'conflict',
               'conflict'),
 'backend-3': ([('after = 7', 'after = 9')], '[12]', '[12]'),
 'backend-4': ([('[True, False]', '[]')], 'True', 'True'),
 'web-0': ([('price > 2', 'price > 3')], '10\ntea true\n[ 4, 10, 6 ]\n[ 5 ]', '[ 5 ]'),
 'web-1': ([('console.log(before.count, after.count);', 'console.log(before.count);')], '1', '1'),
 'web-2': ([('responseRequest = 2', 'responseRequest = 3')], 'true', 'true'),
 'web-3': ([("' gpu '", "' notes '")], '["GPU notes","API notes"]', '["GPU notes","API notes"]'),
 'web-4': ([('"darkMode":true', '"darkMode":false')], 'light', 'light'),
 'rl-1': ([('position, action = 1, 1', 'position, action = 0, -1')], '0', 'Position stays 0'),
 'rl-2': ([('gamma = 0.5', 'gamma = 0')], '1', '1'),
 'rl-3': ([('= 0.2, 0.1, 2', '= 0.2, 0.8, 2')], '1', '1'),
 'rl-4': ([('terminated = True', 'terminated = False')], '3.0', '3'),
 'data-1': ([("new = {'id': 'a', 'revision': 3}", "new = {'id': 'a', 'revision': 1}")], '1', '1'),
 'data-2': ([('size, overlap = 3, 1', 'size, overlap = 3, 0')],
            "['a', 'b', 'c']\n['d', 'e']",
            "['d', 'e']"),
 'data-3': ([("seen = {'a', 'b'}", "seen = {'a'}")], "['c']", "['c']"),
 'data-4': ([('ranked[:2]', 'ranked[:3]')], '1.0', '1.0'),
 'reliability-1': ([('base, cap = 2, 5', 'base, cap = 2, 3')], '[2, 3, 3, 3]', '[2, 3, 3, 3]'),
 'reliability-2': ([("print(safe['token'])", "print(safe['user'])")], 'demo', 'demo'),
 'reliability-3': ([("desired = {'api': 'v2', 'worker': 'v1'}", "desired = {'api': 'v1'}")],
                   '[]\n[]',
                   '[] then []'),
 'reliability-4': ([('latencies = [10, 20, 30, 40]', 'latencies = [10, 20, 30, 40, 500]')],
                   '500',
                   '500'),
 'interactive-1': ([('state = "active"', 'state = "paused"'),
                    ('event = "background"', 'event = "resume"')],
                   'active',
                   'active'),
 'interactive-2': ([('delta_time, max_delta = 0.5, 0.1', 'delta_time, max_delta = 0.05, 0.1')],
                   '10.2',
                   '10.2'),
 'interactive-3': ([('box_width, box_height = 300, 300', 'box_width, box_height = 100, 300')],
                   '100.0 50.0',
                   '100.0 50.0'),
 'interactive-4': ([('events = [("a", 5), ("a", 5)]', 'events = [("a", 5), ("a", 9), ("b", 2)]')],
                   '7',
                   '7')}

class GuideTests(unittest.TestCase):
    def test_every_example_prints_the_teaching_result(self):
        for lesson in LESSONS:
            with self.subTest(lesson=lesson['id']):
                require_lesson_modules(self, lesson)
                example=lesson['example'];lang=lesson.get('language','python')
                prefix=JS_OFFLINE_PREFIX if lang=='javascript' else OFFLINE_PREFIX
                result=execute(prefix+example['code'],[],language=lang,simulator=lesson['course']=='cuda')
                self.assertIsNone(result['error'],result)
                self.assertEqual(result['stdout'].strip(),example['output'],result)
                self.assertFalse(result['passed'])
                print(lesson['id']+': example output verified',flush=True)
    def test_prediction_answers_match_execution(self):
        self.assertEqual(set(PREDICTIONS), {lesson['id'] for lesson in LESSONS})
        for lesson in LESSONS:
            with self.subTest(lesson=lesson['id']):
                replacements, expected_output, correct_choice = PREDICTIONS[lesson['id']]
                guide = lesson['example']
                self.assertEqual(guide['choices'][guide['answer']], correct_choice)
                code = guide['code']
                for old, new in replacements:
                    self.assertIn(old, code)
                    code = code.replace(old, new)
                require_lesson_modules(self, lesson)
                language = lesson.get('language', 'python')
                prefix = JS_OFFLINE_PREFIX if language == 'javascript' else OFFLINE_PREFIX
                result = execute(prefix + code, [], language=language,
                                 simulator=lesson['course'] == 'cuda')
                self.assertIsNone(result['error'], result)
                # Keep leading blank lines: the blank-title question relies on one.
                self.assertEqual(result['stdout'].rstrip(), expected_output, result)

    def test_orientation_and_prediction_questions(self):
        course_ids={course['id'] for course in COURSES}
        for course in COURSES:
            self.assertEqual(len(course['orientation']['terms']),3)
            self.assertTrue(set(course['orientation']['prerequisites'])<=course_ids)
            self.assertNotIn(course['id'],course['orientation']['prerequisites'])
        answers = [lesson["example"]["answer"] for lesson in LESSONS]
        for position in range(3):
            self.assertGreaterEqual(answers.count(position), len(LESSONS) // 4)
        for lesson in LESSONS:
            guide=lesson['example']
            self.assertEqual(len(guide['choices']),3)
            self.assertIn(guide['answer'],range(3))
            self.assertTrue(guide['feedback'] and guide['question'])
            self.assertEqual(len(guide['steps']),2)
if __name__=='__main__':unittest.main()
