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
sys.path.insert(0,str(ROOT/'backend'))
from library import import_book
from book_fixture import make_epub, PNG

class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='ml-api-test-')
        project=dict(id='sample',title='Sample project',summary='Synthetic fixture',tracks=['backend'],steps=['Trace request','Test retry'],deliverable='A diagram')
        (Path(cls.tmp.name)/'portfolio.json').write_text(json.dumps(dict(version=1,projects=[project])))
        cls.book=import_book(make_epub(Path(cls.tmp.name)/'fixture.epub'),cls.tmp.name,'fixture')
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
        self.assertEqual(len(lessons),58)
        for lesson in lessons:
            self.assertNotIn('solution',lesson);self.assertNotIn('checks',lesson)
    def test_javascript_lesson_api(self):
        lesson=next(l for l in self.request('/api/curriculum')['lessons'] if l['id']=='web-1')
        self.assertEqual(lesson['language'],'javascript')
        result=self.request('/api/run',dict(lessonId='web-1',code=lesson['starter'],mode='check'))
        self.assertFalse(result['passed'])
        solution=self.request('/api/solution/web-1')['solution']
        result=self.request('/api/run',dict(lessonId='web-1',code=solution,mode='check'))
        self.assertTrue(result['passed']);self.assertIn('web-1',result['state']['completed'])
    def test_project_state_and_backup(self):
        payload=dict(projectId='sample',notes='New evidence',reviewed=[1],updatedAt=200)
        self.request('/api/project/state',payload)
        self.request('/api/project/state',{**payload,'notes':'stale','reviewed':[],'updatedAt':100})
        catalog=self.request('/api/portfolio')
        self.assertEqual(catalog['projectState']['sample']['notes'],'New evidence')
        self.assertEqual(catalog['projectState']['sample']['reviewed'],[1])
        backup=self.request(self.request('/api/backup',{})['url'])
        self.assertEqual(backup['projectState'],catalog['projectState'])
        self.assertEqual(backup['portfolio']['projects'][0]['id'],'sample')
        for patch in ({'projectId':'unknown'},{'reviewed':[2]},{'reviewed':[True]},{'reviewed':[-1]},{'updatedAt':-1},{'notes':'x'*30001}):
            with self.subTest(patch=str(patch)[:50]),self.assertRaises(urllib.error.HTTPError) as error:
                self.request('/api/project/state',{**payload,**patch})
            self.assertEqual(error.exception.code,400)
        with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/project/state',payload,{'X-Workshop-Token':'wrong'})
        self.assertEqual(error.exception.code,403)
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
    def test_book_state_rejects_stale_writes_and_is_backed_up(self):
        latest=dict(bookId='fixture',location=2,notes='A useful observation',bookmarks=[2],completed=[],updatedAt=200)
        self.request('/api/library/state',latest)
        self.request('/api/library/state',{**latest,'location':1,'notes':'stale','updatedAt':100})
        library=self.request('/api/library')
        self.assertEqual(library['readingState']['fixture']['notes'],latest['notes'])
        self.assertEqual(library['readingState']['fixture']['location'],2)
        backup=self.request('/api/backup',{})
        exported=self.request(backup['url'])
        self.assertEqual(exported['version'],3)
        self.assertEqual(exported['readingState']['fixture']['bookmarks'],[2])
        self.assertNotIn('documents',exported)
        for patch in ({'location':0},{'location':3},{'notes':'x'*30001},{'bookmarks':[3]},{'bookmarks':[True]},{'completed':['invented']},{'updatedAt':-1}):
            with self.subTest(patch=str(patch)[:60]),self.assertRaises(urllib.error.HTTPError) as e:
                self.request('/api/library/state',{**latest,**patch})
            self.assertEqual(e.exception.code,400)
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.request('/api/library/state',latest,{'X-Workshop-Token':'wrong'})
        self.assertEqual(e.exception.code,403)
    def test_book_media_ranges_and_navigation(self):
        self.assertEqual(len(self.request('/api/library/search?q=warp')['results']),2)
        self.assertEqual(self.request('/api/library/fixture/chapter/2')['title'],'Memory')
        media='/api/library/fixture/asset/'+self.book['assets'][0]['path']
        for requested,expected in [('bytes=0-7',PNG[:8]),('bytes=-8',PNG[-8:]),('bytes=8-',PNG[8:])]:
            req=urllib.request.Request(self.url+media,headers={'Range':requested})
            with urllib.request.urlopen(req) as response:
                self.assertEqual(response.status,206)
                self.assertEqual(response.read(),expected)
                self.assertIn('sandbox',response.headers['Content-Security-Policy'])
        for path,headers,status in [(media,{'Range':'bytes=99999-'},416),(media,{'Origin':'https://example.com'},403),('/api/library/fixture/asset/../book.json',{},404),('/api/library/fixture/chapter/999',{},404)]:
            with self.assertRaises(urllib.error.HTTPError) as e:self.request(path,headers=headers)
            self.assertEqual(e.exception.code,status)
if __name__=='__main__':unittest.main()
