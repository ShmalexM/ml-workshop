"""Integration checks use a separate loopback server and disposable SQLite."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
import urllib.error
ROOT=Path(__file__).resolve().parents[1]

class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='ml-api-test-')
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));cls.port=sock.getsockname()[1]
        cls.url=f'http://127.0.0.1:{cls.port}'
        cls.proc=subprocess.Popen([sys.executable,str(ROOT/'backend/server.py'),'--port',str(cls.port)],env={**os.environ,'ML_WORKSHOP_DATA_DIR':cls.tmp.name},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(60):
            try:
                cls.token=json.load(urllib.request.urlopen(cls.url+'/api/bootstrap'))['token'];break
            except OSError:time.sleep(.1)
        else:raise RuntimeError('Test server unavailable')
    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate();cls.proc.wait();cls.tmp.cleanup()
    def request(self,path,body=None,headers=None):
        req=urllib.request.Request(self.url+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json','X-Workshop-Token':self.token,**(headers or {})})
        with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)
    def test_origin_and_session_guards(self):
        payload={'lessonId':'foundations-1','code':'print(1)','mode':'run'}
        for headers in [{'Origin':'https://example.com'},{'X-Workshop-Token':'wrong'},{'Sec-Fetch-Site':'cross-site'},{'Host':'attacker.example'}]:
            with self.subTest(headers=headers), self.assertRaises(urllib.error.HTTPError) as e:self.request('/api/run',payload,headers)
            self.assertEqual(e.exception.code,403)
    def test_completion_once_and_draft_order(self):
        code='def predict(x, weight, bias): return x*weight+bias'
        result=self.request('/api/run',dict(lessonId='foundations-1',code=code,mode='check'))
        self.assertTrue(result['passed']);stamp=result['state']['completed']['foundations-1']['at']
        again=self.request('/api/run',dict(lessonId='foundations-1',code=code,mode='check'))
        self.assertEqual(again['state']['completed']['foundations-1']['at'],stamp)
        self.assertEqual(sum(x['xp'] for x in again['state']['completed'].values()),100)
        self.request('/api/draft',dict(lessonId='foundations-1',code=code,notes='new note',updatedAt=20))
        self.request('/api/draft',dict(lessonId='foundations-1',code='stale',notes='stale',updatedAt=10))
        saved=self.request('/api/state')
        self.assertEqual(saved['drafts']['foundations-1'],code)
        self.assertEqual(saved['notes']['foundations-1'],'new note')
        self.assertEqual(saved['draftUpdated']['foundations-1'],20)
    def test_failed_check_and_run_do_not_complete(self):
        for mode in ['check','run']:
            result=self.request('/api/run',dict(lessonId='foundations-2',code='print("not an answer")',mode=mode))
            self.assertFalse(result['passed'])
        self.assertNotIn('foundations-2',self.request('/api/state')['completed'])
    def test_curriculum_does_not_leak_answers(self):
        lessons=self.request('/api/curriculum')['lessons']
        self.assertEqual(len(lessons),30)
        self.assertNotIn('solution',lessons[0]);self.assertNotIn('checks',lessons[0])
    def test_single_exercise_at_a_time(self):
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            task=pool.submit(self.request,'/api/run',dict(lessonId='foundations-1',code='import time; time.sleep(1)',mode='run'))
            for _ in range(30):
                if self.request('/api/health')['busy']:break
                time.sleep(.02)
            with self.assertRaises(urllib.error.HTTPError) as e:
                self.request('/api/run',dict(lessonId='foundations-1',code='print(1)',mode='run'))
            self.assertEqual(e.exception.code,409)
            self.assertIsNone(task.result()['error'])
    def test_backup_is_durable_and_downloadable(self):
        backup=self.request('/api/backup',{})
        saved=json.loads((Path(self.tmp.name)/'backups'/backup['filename']).read_text())
        self.assertEqual(saved['app'],'ml-workshop')
        self.assertEqual(self.request(backup['url']),saved)
    def test_invalid_payload_is_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('/api/run',dict(lessonId='missing',code='x',mode='run'))
        self.assertEqual(e.exception.code,400)
if __name__=='__main__':unittest.main()
