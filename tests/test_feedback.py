"""What a learner sees when code fails: trimmed tracebacks, values for failed checks, plain explanations."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from courses import BY_ID
from explanations import explain
from runner import MISMATCH, RETURNED_NONE, execute

# Text that must never reach the learner: app files, Node internals and install locations.
LEAKS = ['runner.py', 'js_runner.cjs', 'node:', str(ROOT), sys.prefix, sys.base_prefix]


def failed(result):
    return [check for check in result['checks'] if not check['passed']]


class TracebackTests(unittest.TestCase):
    def assertNoLeaks(self, text):
        for leak in LEAKS:
            self.assertNotIn(leak, text)

    def test_runtime_error_shows_the_learner_line(self):
        result = execute('def predict(x, weight, bias):\n    return wieght * x + bias\n\nprint(predict(3, 2, 1))\n', [])
        self.assertIn('File "exercise.py", line 2, in predict', result['error'])
        self.assertIn('    return wieght * x + bias', result['error'])
        self.assertTrue(result['summary'].startswith("Line 2: NameError: name 'wieght' is not defined"), result)
        self.assertIn('misspelled', result['explanation'])
        self.assertNoLeaks(result['error'])

    def test_syntax_error_has_no_app_frames(self):
        result = execute('def predict(x, weight, bias)\n    return weight * x + bias\n', [])
        self.assertNotIn('Traceback', result['error'])
        self.assertIn("SyntaxError: expected ':'", result['error'])
        self.assertEqual(result['summary'], "Line 1: SyntaxError: expected ':'")
        self.assertIn('colon', result['explanation'])
        self.assertNoLeaks(result['error'])

    def test_library_and_chained_frames_are_dropped(self):
        code = 'import json\ntry:\n    json.loads("{")\nexcept ValueError as exc:\n    raise KeyError("settings") from exc\n'
        result = execute(code, [])
        self.assertIn('JSONDecodeError', result['error'])
        self.assertIn('File "exercise.py", line 3, in <module>', result['error'])
        self.assertTrue(result['summary'].startswith("Line 5: KeyError: 'settings'"), result)
        self.assertNoLeaks(result['error'])

    def test_error_inside_a_check_names_the_line(self):
        result = execute('def predict(x, weight, bias):\n    return wieght * x\n', BY_ID['foundations-1']['checks'])
        check = failed(result)[0]
        self.assertTrue(check['detail'].startswith("Line 2: NameError: name 'wieght' is not defined"), check)
        self.assertIn('misspelled', check['explanation'])

    def test_javascript_stack_stops_after_learner_frames(self):
        result = execute('function counter(state) {\n  return missing;\n}\ncounter({});\n', [], language='javascript')
        self.assertIn('ReferenceError: missing is not defined', result['error'])
        self.assertIn('exercise.js:2', result['error'])
        self.assertEqual(result['summary'], 'Line 2: ReferenceError: missing is not defined')
        self.assertIn('JavaScript does not know this name', result['explanation'])
        self.assertNoLeaks(result['error'])

    def test_javascript_syntax_error(self):
        result = execute('function counter(state) {\n  return {...state;\n}\n', [], language='javascript')
        self.assertIn('SyntaxError', result['summary'])
        self.assertIsNotNone(result['explanation'])
        self.assertNoLeaks(result['error'])


class CheckFeedbackTests(unittest.TestCase):
    def test_wrong_value_shows_got_and_expected(self):
        result = execute('def predict(x, weight, bias):\n    return weight * x\n', BY_ID['foundations-1']['checks'])
        first = result['checks'][0]
        self.assertEqual((first['call'], first['expected'], first['got']), ('predict(3, 2, 1)', '7', '6'))
        self.assertEqual(first['detail'], 'Got 6, expected 7.')
        near = result['checks'][3]
        self.assertEqual(near['expected'], '0.5 (within 1e-09)')
        self.assertEqual(near['got'], '0.75')

    def test_print_instead_of_return(self):
        result = execute('def predict(x, weight, bias):\n    print(weight * x + bias)\n', BY_ID['foundations-1']['checks'])
        self.assertEqual(len(failed(result)), 4)
        for check in failed(result):
            self.assertEqual(check['got'], 'None')
            self.assertEqual(check['explanation'], RETURNED_NONE)
        self.assertNotIn('TypeError', result['checks'][3]['detail'])

    def test_wrong_exception_names_both(self):
        code = 'def mse(predictions, targets):\n    return sum((p - t) ** 2 for p, t in zip(predictions, targets)) / len(targets)\n'
        checks = {c['label']: c for c in execute(code, BY_ID['foundations-2']['checks'])['checks']}
        empty = checks['Empty lists rejected']
        self.assertEqual(empty['call'], 'mse([], [])')
        self.assertEqual(empty['expected'], 'raises ValueError')
        self.assertEqual(empty['got'], 'raised ZeroDivisionError: division by zero')
        self.assertIn('empty', empty['explanation'])
        mismatched = checks['Mismatched lists rejected']
        self.assertEqual(mismatched['got'], 'returned 0.0')
        self.assertEqual(mismatched['detail'], 'Expected ValueError, but the call returned 0.0.')

    def test_list_instead_of_tuple(self):
        code = 'def split_data(rows):\n    a, b = int(len(rows) * 0.6), int(len(rows) * 0.8)\n    return [rows[:a], rows[a:b], rows[b:]]\n'
        result = execute(code, BY_ID['foundations-4']['checks'])
        self.assertFalse(result['passed'])
        self.assertIn('tuple', result['checks'][0]['explanation'])

    def test_other_check_shapes_keep_the_generic_message(self):
        result = execute('x = 1', [dict(label='compound', expr='x == 1 and x == 2')])
        self.assertEqual(result['checks'][0]['detail'], MISMATCH)
        self.assertNotIn('got', result['checks'][0])

    def test_long_values_are_cut(self):
        result = execute('values = list(range(1000))', [dict(label='long', expr='values == []')])
        self.assertLessEqual(len(result['checks'][0]['got']), 200)

    def test_javascript_comparisons(self):
        checks = BY_ID['web-1']['checks']
        result = execute('function counter(state, action) {\n  console.log(state);\n}\n', checks, language='javascript')
        self.assertEqual(result['checks'][0]['got'], 'undefined')
        self.assertIn('returned undefined', result['checks'][0]['explanation'])
        result = execute('function counter(state, action) {\n  return {...state, count: state.count + (action.amount || 0)};\n}\n', checks, language='javascript')
        reset = result['checks'][1]
        self.assertEqual((reset['call'], reset['expected'], reset['got']), ('counter({count:8},{type:"reset"}).count', '0', '8'))


class CheckNamespaceTests(unittest.TestCase):
    """Learner code may use any name. Checks look up builtins and their helpers first."""

    def test_learner_names_do_not_change_check_helpers(self):
        code = ('abs = 123\nraises = 123\ncalls = None\n_workshop_value = 1\n\n'
                'def predict(x, weight, bias):\n    return weight * x + bias + _workshop_value - 1\n')
        checks = BY_ID['foundations-1']['checks'] + [dict(label='raises', expr='raises(ZeroDivisionError, lambda: 1 / 0)')]
        result = execute(code, checks)
        self.assertTrue(result['passed'], result)
        # The learner's own globals are unchanged after the checks ran.
        result = execute(code, [dict(label='kept', expr='predict(1, 1, 1) == 2')])
        self.assertTrue(result['passed'], result)

    def test_learner_helpers_cannot_pass_wrong_work(self):
        python = 'def safe_mean(values):\n    return 0\n\ndef raises(*args):\n    return True\n'
        self.assertFalse(execute(python, BY_ID['python-10']['checks'])['passed'])
        javascript = 'function counter(state) { return state; }\nfunction equal() { return true; }\n'
        self.assertFalse(execute(javascript, BY_ID['web-1']['checks'], language='javascript')['passed'])

    def test_no_lesson_asks_for_a_name_that_checks_reserve(self):
        import ast
        import builtins
        reserved = {name for name in vars(builtins) if not name.startswith('_')}
        reserved |= {'raises', 'calls', 'last_printed', 'check_torch_step', 'check_tf_step'}
        for lesson in BY_ID.values():
            if lesson.get('language') == 'javascript':
                continue
            defined = {node.name for node in ast.parse(lesson['solution']).body
                       if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
            self.assertFalse(defined & reserved, lesson['id'])


class ExplanationTests(unittest.TestCase):
    def test_common_errors(self):
        self.assertIn('colon', explain("  File \"exercise.py\", line 1\n    def f(x)\n            ^\nSyntaxError: expected ':'"))
        self.assertIn('misspelled', explain("NameError: name 'totl' is not defined"))
        self.assertIn('return', explain("TypeError: unsupported operand type(s) for -: 'NoneType' and 'float'"))
        self.assertIn('Positions start at 0', explain('IndexError: list index out of range'))
        self.assertIn('does not know this name', explain('ReferenceError: total is not defined', 'javascript'))
        self.assertIn('undefined or null', explain("TypeError: Cannot read properties of undefined (reading 'x')", 'javascript'))
        self.assertIn('could not read', explain("SyntaxError: Unexpected token '}'", 'javascript'))
        self.assertIsNone(explain('Execution stopped after 50 seconds.'))


if __name__ == '__main__':
    unittest.main()
