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

class CurriculumTests(unittest.TestCase):
    def test_every_solution_and_starter(self):
        self.assertEqual(len(LESSONS),30)
        self.assertEqual(len({l['id'] for l in LESSONS}),30)
        for lesson in LESSONS:
            with self.subTest(lesson=lesson['id']):
                # Use the same 50-second budget as the app. A cold TensorFlow
                # import on a fresh macOS installation can exceed 20 seconds.
                result=execute(OFFLINE_PREFIX+lesson['solution'],lesson['checks'],simulator=lesson['course']=='cuda')
                self.assertTrue(result['passed'],f"{lesson['id']} solution: {result}")
                starter=execute(OFFLINE_PREFIX+lesson['starter'],lesson['checks'],simulator=lesson['course']=='cuda')
                self.assertFalse(starter['passed'],f"{lesson['id']} starter should not pass")
                print(f"{lesson['id']}: solution passed; starter did not pass",flush=True)
    def test_extra_schema_and_sources(self):
        from urllib.parse import urlparse
        for lesson in LESSONS:
            self.assertTrue(isinstance(lesson['minutes'],int) and lesson['minutes']>0)
            self.assertIn(lesson['xp'],[100,150])
            for field in ['diagram','tasks','hints']:self.assertEqual(len(lesson[field]),3)
            self.assertTrue(3<=len(lesson['checks'])<=5)
            domain=urlparse(lesson['reference']['url']).hostname
            self.assertIn(domain,['developers.google.com','docs.pytorch.org','www.tensorflow.org','huggingface.co','reference.langchain.com','developers.llamaindex.ai','nvidia.github.io'])
    def test_constant_answer_does_not_pass(self):
        lesson=next(l for l in LESSONS if l['id']=='foundations-3')
        self.assertFalse(execute('def step(weight,target,learning_rate):return 0.6',lesson['checks'])['passed'])
    def test_cuda_missing_bounds_guard_fails(self):
        lesson=next(l for l in LESSONS if l['id']=='cuda-2')
        broken=lesson['solution'].replace('if i<out.size:out[i]=a[i]+b[i]','out[i]=a[i]+b[i]')
        result=execute(OFFLINE_PREFIX+broken,lesson['checks'],simulator=True)
        self.assertFalse(result['passed'])
    def test_timeout_and_error_reporting(self):
        self.assertIn('Execution stopped',execute('while True: pass',[],timeout=1)['error'])
        self.assertIn('ZeroDivisionError',execute('1/0',[])['error'])
    def test_stdout_is_not_an_answer(self):
        result=execute('print("all checks passed")',[{'label':'real result','expr':'False'}])
        self.assertFalse(result['passed'])
        self.assertEqual(result['stdout'].strip(),'all checks passed')
if __name__=='__main__':unittest.main()
