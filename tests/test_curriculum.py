import ast
import importlib.util
import os
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from courses import LESSONS
from runner import execute

OFFLINE_PREFIX = """import socket
def _network_disabled(*args, **kwargs):
    raise RuntimeError('Network disabled during offline curriculum verification')
socket.socket.connect = _network_disabled
socket.socket.connect_ex = _network_disabled
socket.socket.sendto = _network_disabled
socket.create_connection = _network_disabled
socket.getaddrinfo = _network_disabled
"""

JS_OFFLINE_PREFIX = """const denyNetwork = () => {throw new Error('Network disabled during verification')};
require('node:net').Socket.prototype.connect = denyNetwork;
require('node:dgram').Socket.prototype.send = denyNetwork;
globalThis.fetch = denyNetwork;
"""

def missing_lesson_modules(lesson):
    if lesson.get('language') == 'javascript':
        return []
    modules = set()
    for code in (lesson['starter'], lesson['solution'], lesson['example']['code']):
        for node in ast.walk(ast.parse(code)):
            if isinstance(node, ast.Import):
                modules.update(alias.name.split('.')[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module.split('.')[0])
    return sorted(module for module in modules if importlib.util.find_spec(module) is None)

def require_lesson_modules(test, lesson):
    missing = missing_lesson_modules(lesson)
    if missing:
        message = f"{lesson['id']} requires {', '.join(missing)}; run setup without --no-ml."
        if os.environ.get('ML_WORKSHOP_REQUIRE_ML') == '1':
            test.fail(message)
        test.skipTest(message)

class CurriculumTests(unittest.TestCase):
    def test_every_solution_and_starter(self):
        self.assertEqual(len(LESSONS),71)
        self.assertEqual(len({l['id'] for l in LESSONS}),71)
        for lesson in LESSONS:
            with self.subTest(lesson=lesson['id']):
                require_lesson_modules(self, lesson)
                # Use the same 50-second budget as the app. A cold TensorFlow
                # import on a fresh macOS installation can exceed 20 seconds.
                prefix=JS_OFFLINE_PREFIX if lesson.get('language')=='javascript' else OFFLINE_PREFIX
                result=execute(prefix+lesson['solution'],lesson['checks'],simulator=lesson['course']=='cuda',language=lesson.get('language','python'))
                self.assertTrue(result['passed'],f"{lesson['id']} solution: {result}")
                starter=execute(prefix+lesson['starter'],lesson['checks'],simulator=lesson['course']=='cuda',language=lesson.get('language','python'))
                self.assertIsNone(starter['error'], f"{lesson['id']} starter: {starter}")
                self.assertFalse(starter['passed'],f"{lesson['id']} starter should not pass")
                print(f"{lesson['id']}: solution passed; starter did not pass",flush=True)
    def test_extra_schema_and_sources(self):
        from urllib.parse import urlparse
        for lesson in LESSONS:
            self.assertTrue(isinstance(lesson['minutes'],int) and lesson['minutes']>0)
            self.assertIn(lesson['xp'],[100,150])
            for field in ['diagram','tasks','hints']:self.assertEqual(len(lesson[field]),3)
            # Lessons whose checks expect an error show the raise statement on another example.
            if any('raises(' in check['expr'] for check in lesson['checks']):
                self.assertIn('raise ValueError(', lesson['hints'][1], lesson['id'])
            self.assertTrue(3<=len(lesson['checks'])<=5)
            domain=urlparse(lesson['reference']['url']).hostname
            self.assertIn(domain,['developers.google.com','docs.pytorch.org','www.tensorflow.org','huggingface.co','reference.langchain.com','developers.llamaindex.ai','nvidia.github.io','docs.python.org','www.rfc-editor.org','react.dev','gymnasium.farama.org','opentelemetry.io','developer.mozilla.org'])
    def test_constant_answer_does_not_pass(self):
        lesson=next(l for l in LESSONS if l['id']=='foundations-3')
        self.assertFalse(execute('def step(weight,target,learning_rate):return 0.6',lesson['checks'])['passed'])
    def test_cuda_missing_bounds_guard_fails(self):
        lesson=next(l for l in LESSONS if l['id']=='cuda-2')
        require_lesson_modules(self, lesson)
        broken=lesson['solution'].replace('    if i < out.size:\n        out[i] = a[i] + b[i]', '    out[i] = a[i] + b[i]')
        self.assertNotEqual(broken, lesson['solution'])
        result=execute(OFFLINE_PREFIX+broken,lesson['checks'],simulator=True)
        self.assertFalse(result['passed'])
    def test_timeout_and_error_reporting(self):
        self.assertIn('Execution stopped',execute('while True: pass',[],timeout=1)['error'])
        self.assertIn('ZeroDivisionError',execute('1/0',[])['error'])
    def test_javascript_timeout_and_error_reporting(self):
        self.assertIn('Execution stopped',execute('while(true){}',[],timeout=1,language='javascript')['error'])
        self.assertIn('ReferenceError',execute('missingName()',[],language='javascript')['error'])
        result=execute('console.log("finished")',[dict(label='real requirement',expr='false')],language='javascript')
        self.assertFalse(result['passed']);self.assertEqual(result['stdout'].strip(),'finished')
    def test_javascript_stale_response_mutation_fails(self):
        lesson=next(l for l in LESSONS if l['id']=='web-2')
        result=execute('function applyResponse(state, response) {return {...state, items:response.items, status:"ready"}}',lesson['checks'],language='javascript')
        self.assertFalse(result['passed'])
    def test_stdout_is_not_an_answer(self):
        result=execute('print("all checks passed")',[{'label':'real result','expr':'False'}])
        self.assertFalse(result['passed'])
        self.assertEqual(result['stdout'].strip(),'all checks passed')
if __name__=='__main__':unittest.main()
