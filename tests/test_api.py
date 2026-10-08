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
from server_fixture import server_token

class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='ml-api-test-')
        project=dict(id='sample',title='Sample project',summary='Synthetic fixture',tracks=['backend'],steps=['Trace request','Test retry'],deliverable='A diagram')
        task=lambda tid:dict(id=tid,title=tid.title(),minutes=5,source=dict(path='app.py',lines=[1,2]),do='Read.',change='Edit.',verify=dict(commands=['pytest'],expect='1 passed',check=dict(type='contains',value='1 passed')))
        hands_on=dict(id='hands-on',title='Hands-on fixture',summary='Synthetic fixture',tracks=['backend'],repoUrl='https://github.com/example/app',pin=dict(ref='b'*40,label='main'),tasks=[task('first'),task('second')],stretch=task('extra'))
        (Path(cls.tmp.name)/'portfolio.json').write_text(json.dumps(dict(version=1,projects=[project,hands_on])))
        cls.book=import_book(make_epub(Path(cls.tmp.name)/'fixture.epub'),cls.tmp.name,'fixture')
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));cls.port=sock.getsockname()[1]
        cls.url=f'http://127.0.0.1:{cls.port}'
        cls.proc=subprocess.Popen([sys.executable,str(ROOT/'backend/server.py'),'--port',str(cls.port)],env={**os.environ,'ML_WORKSHOP_DATA_DIR':cls.tmp.name},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        cls.token=server_token(cls.url,cls.tmp.name,cls.proc)
    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate();cls.proc.wait();cls.tmp.cleanup()
    def request(self,path,body=None,headers=None):
        req=urllib.request.Request(self.url+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json','X-Workshop-Token':self.token,**(headers or {})})
        with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)
    def test_health_reports_the_package_version(self):
        version=json.loads((ROOT/'package.json').read_text(encoding='utf-8'))['version']
        health=self.request('/api/health')
        self.assertEqual((health['app'],health['version']),('ml-workshop',version))
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
        self.assertEqual(again['state']['completed']['foundations-1']['xp'],100)
        self.request('/api/draft',dict(lessonId='foundations-1',code=code,notes='new note',updatedAt=20))
        self.request('/api/draft',dict(lessonId='foundations-1',code='stale',notes='stale',updatedAt=10))
        saved=self.request('/api/state')
        self.assertEqual(saved['drafts']['foundations-1'],code)
        self.assertEqual(saved['notes']['foundations-1'],'new note')
        self.assertEqual(saved['draftUpdated']['foundations-1'],20)
    def test_draft_revisions_cannot_block_later_saves(self):
        def save(code, revision):
            return self.request('/api/draft', dict(lessonId='python-3', code=code, notes='', updatedAt=revision))
        self.assertTrue(save('# first', 1)['applied'])
        # A revision far ahead of the clock is saved as now, so the next normal edit still replaces it.
        self.assertTrue(save('# future', 2**53 - 1)['applied'])
        saved = self.request('/api/state')
        self.assertLessEqual(saved['draftUpdated']['python-3'], time.time() * 1000 + 1000)
        time.sleep(.01)
        self.assertTrue(save('# next edit', int(time.time() * 1000))['applied'])
        self.assertEqual(self.request('/api/state')['drafts']['python-3'], '# next edit')
        # An older revision is not applied, and the response says so.
        self.assertFalse(save('# stale', 5)['applied'])
        self.assertEqual(self.request('/api/state')['drafts']['python-3'], '# next edit')

    def test_draft_saved_before_revisions_were_checked_does_not_block(self):
        import sqlite3
        with sqlite3.connect(Path(self.tmp.name) / 'workshop.sqlite3') as db:
            db.execute('INSERT OR REPLACE INTO drafts VALUES (?,?,?,?)', ('python-4', '# poisoned', '', 2**63 - 1))
        self.assertLessEqual(self.request('/api/state')['draftUpdated']['python-4'], time.time() * 1000 + 1000)
        result = self.request('/api/draft', dict(lessonId='python-4', code='# normal', notes='', updatedAt=int(time.time() * 1000)))
        self.assertTrue(result['applied'])
        self.assertEqual(self.request('/api/state')['drafts']['python-4'], '# normal')

    def test_invalid_draft_requests_get_400(self):
        draft = dict(lessonId='python-2', code='# QA', notes='', updatedAt=1)
        for patch in ({'updatedAt': 2**63}, {'updatedAt': 2**63 - 1}, {'updatedAt': 1e300}, {'updatedAt': True},
                      {'updatedAt': 1.5}, {'updatedAt': -1}, {'updatedAt': '123'}, {'updatedAt': None},
                      {'code': 'x' * 50001}, {'notes': 'x' * 30001}, {'code': 7}):
            with self.subTest(patch=str(patch)[:40]), self.assertRaises(urllib.error.HTTPError) as error:
                self.request('/api/draft', {**draft, **patch})
            self.assertEqual(error.exception.code, 400)
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request('/api/draft', {**draft, 'notes': 'x' * 30001})
        self.assertIn('Notes are longer than 30,000 characters', json.load(error.exception)['error'])
        self.assertNotIn('python-2', self.request('/api/state')['drafts'])

    def test_project_and_reading_revisions_cannot_block_later_saves(self):
        import sqlite3
        database = Path(self.tmp.name) / 'workshop.sqlite3'
        routes = [('/api/project/state', dict(projectId='sample', notes='', reviewed=[]), 'project_state',
                   lambda: self.request('/api/portfolio')['projectState']['sample']),
                  ('/api/library/state', dict(bookId='fixture', location=1, notes='', bookmarks=[], completed=[]), 'reading_state',
                   lambda: self.request('/api/library')['readingState']['fixture'])]
        def clear():
            with sqlite3.connect(database) as db:
                db.execute("DELETE FROM project_state WHERE project='sample'")
                db.execute("DELETE FROM reading_state WHERE book='fixture'")
        clear()
        self.addCleanup(clear)
        for path, body, table, saved in routes:
            with self.subTest(path=path):
                save = lambda notes, revision: self.request(path, {**body, 'notes': notes, 'updatedAt': revision})
                # A revision far ahead of the clock is saved as now, so the next normal edit still replaces it.
                self.assertTrue(save('future', 2**53 - 1)['applied'])
                self.assertLessEqual(saved()['updatedAt'], time.time() * 1000 + 1000)
                time.sleep(.01)
                self.assertTrue(save('next edit', int(time.time() * 1000))['applied'])
                self.assertFalse(save('stale', 5)['applied'])
                self.assertEqual(saved()['notes'], 'next edit')
                # A row stored ahead of the clock before revisions were checked does not block a save.
                key = 'project' if table == 'project_state' else 'book'
                with sqlite3.connect(database) as db:
                    db.execute(f'UPDATE {table} SET notes=?, updated=? WHERE {key}=?', ('poisoned', 2**63 - 1, body.get('projectId') or body['bookId']))
                self.assertLessEqual(saved()['updatedAt'], time.time() * 1000 + 1000)
                self.assertTrue(save('normal', int(time.time() * 1000))['applied'])
                self.assertEqual(saved()['notes'], 'normal')
                for revision in (2**53, 2**63, 1e300, True, 1.5, -1, '123', None):
                    with self.assertRaises(urllib.error.HTTPError) as error:
                        save('bad', revision)
                    self.assertEqual(error.exception.code, 400, revision)
                self.assertEqual(saved()['notes'], 'normal')

    def test_deeply_nested_json_gets_400(self):
        body = b'{"a":' + b'[' * 11000 + b'0' + b']' * 11000 + b'}'
        for path in ('/api/current', '/api/draft', '/api/backup'):
            request = urllib.request.Request(self.url + path, data=body, headers={'Content-Type': 'application/json', 'X-Workshop-Token': self.token})
            with self.subTest(path=path), self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(request, timeout=60)
            self.assertEqual(error.exception.code, 400)

    def test_failed_check_and_run_do_not_complete(self):
        for mode in ['check','run']:
            result=self.request('/api/run',dict(lessonId='foundations-2',code='print("not an answer")',mode=mode))
            self.assertFalse(result['passed'])
        self.assertNotIn('foundations-2',self.request('/api/state')['completed'])
    def test_curriculum_does_not_leak_answers(self):
        lessons=self.request('/api/curriculum')['lessons']
        self.assertEqual(len(lessons),71)
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
    def test_task_progress_saves_notes_and_check_times_only(self):
        tasks=dict(first=dict(notes='Line 18 uses +=',verifiedAt=1700000000000),extra=dict(verifiedAt=1700000000500))
        payload=dict(projectId='hands-on',notes='',reviewed=[0,1],updatedAt=300,tasks=tasks)
        self.request('/api/project/state',payload)
        saved=self.request('/api/portfolio')
        self.assertEqual(saved['projects'][1]['steps'],['First','Second'])
        self.assertEqual(saved['projectState']['hands-on']['tasks'],tasks)
        # A client without task progress keeps the saved map; a stale write changes nothing.
        self.request('/api/project/state',dict(projectId='hands-on',notes='later',reviewed=[0],updatedAt=400))
        self.request('/api/project/state',{**payload,'tasks':{},'updatedAt':350})
        saved=self.request('/api/portfolio')['projectState']['hands-on']
        self.assertEqual((saved['notes'],saved['reviewed'],saved['tasks']),('later',[0],tasks))
        backup=self.request(self.request('/api/backup',{})['url'])
        self.assertEqual(backup['projectState']['hands-on']['tasks'],tasks)
        self.assertEqual(backup['version'],3)
        for bad in ({'first':{'output':'/Users/me'}},{'ghost':{}},{'first':{'verifiedAt':'now'}},{'first':{'notes':'x'*5001}},[]):
            with self.subTest(bad=str(bad)[:40]),self.assertRaises(urllib.error.HTTPError) as error:
                self.request('/api/project/state',{**payload,'updatedAt':500,'tasks':bad})
            self.assertEqual(error.exception.code,400)
        self.assertNotIn('/Users/me',json.dumps(self.request('/api/portfolio')))
    def test_old_project_table_gains_task_column(self):
        with tempfile.TemporaryDirectory(prefix='ml-api-migrate-') as directory:
            import sqlite3
            db=sqlite3.connect(Path(directory)/'workshop.sqlite3')
            with db:
                db.execute('CREATE TABLE project_state (project TEXT PRIMARY KEY, notes TEXT, reviewed TEXT, updated INTEGER)')
                db.execute("INSERT INTO project_state VALUES ('public-micrograd','old note','[0, 1, 2]',5)")
            db.close()
            code='import json,sys;sys.path.insert(0,sys.argv[1]);import server;print(json.dumps(server.project_state()))'
            for _ in range(2):
                out=subprocess.run([sys.executable,'-c',code,str(ROOT/'backend')],env={**os.environ,'ML_WORKSHOP_DATA_DIR':directory},capture_output=True,text=True,timeout=60)
                self.assertEqual(out.returncode,0,out.stderr)
                self.assertEqual(json.loads(out.stdout),{'public-micrograd':dict(notes='old note',reviewed=[0,1,2],updatedAt=5,tasks={})})
    def test_worked_example_is_separate_from_challenge(self):
        before=self.request('/api/state')
        result=self.request('/api/example',dict(lessonId='foundations-1',code='raise Exception("should not run")',mode='check'))
        self.assertIsNone(result['error']);self.assertEqual(result['stdout'].strip(),'7')
        self.assertFalse(result['passed']);self.assertEqual(result['checks'],[])
        self.assertEqual(self.request('/api/state'),before)
        result=self.request('/api/example',dict(lessonId='web-1'))
        self.assertEqual(result['stdout'].strip(),'1 3');self.assertFalse(result['passed'])
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('/api/example',dict(lessonId='unknown'))
        self.assertEqual(e.exception.code,400)
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
