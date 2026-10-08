import copy
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from portfolio import load_portfolio, task_progress, RETIRED

SHA='a'*40
TASK=dict(id='first',title='Run the test',minutes=10,lessons=['backend-1'],source=dict(path='app/main.py',lines=[3,9]),
          do='Read the handler.',change='Add a check.',verify=dict(commands=['pytest -q'],expect='1 passed',check=dict(type='contains',value='1 passed')))
HANDS_ON=dict(id='hands-on',title='Hands-on',summary='Example',tracks=['backend'],repoUrl='https://github.com/example/app',
              goal='Add a check.',pin=dict(ref=SHA,label='main, 2026-10-08'),prerequisites=dict(lessons=['backend-1'],projects=[],tools=['Git']),
              minutes=dict(setup=5,tasks=10,stretch=5),setup=dict(unix=['git clone https://github.com/example/app'],windows=['git clone https://github.com/example/app']),
              run=dict(commands=['pytest -q'],expect='1 passed'),tasks=[TASK],stretch={**TASK,'id':'extra'},
              troubleshooting=[dict(problem='pytest not found',fix='Activate the virtual environment.')])

class PortfolioTests(unittest.TestCase):
    def load(self,directory,*projects):
        (Path(directory)/'portfolio.json').write_text(json.dumps(dict(version=1,projects=list(projects))))
        return load_portfolio(directory)
    def test_public_default_has_small_entry_points_and_no_local_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            catalog=load_portfolio(directory)
            projects=catalog['projects']
            self.assertNotIn('error',catalog)
            self.assertEqual(len({p['id'] for p in projects}),12)
            self.assertEqual([p['level'] for p in projects],sorted((p['level'] for p in projects),key=['Start small','Build next','Capstone'].index))
            self.assertEqual({p['level'] for p in projects},{'Start small','Build next','Capstone'})
            for project in projects:
                self.assertEqual(project['visibility'],'public')
                self.assertEqual(project['localPath'],'')
                self.assertTrue(project['entryPoint']['url'].startswith('https://github.com/'))
                self.assertTrue(project['firstLesson'] and project['requirements'])
                if '/ShmalexM/' in project['repoUrl']:
                    self.assertEqual(project['repoUrl'].rsplit('/',1)[-1],'Vigil-at-Home')
            # Starter files use /Users/you/ as a placeholder; no real home folder may appear.
            self.assertNotRegex(json.dumps(catalog),'/Users/(?!you/)')
    def test_public_projects_are_pinned_and_hands_on(self):
        with tempfile.TemporaryDirectory() as directory:
            catalog=load_portfolio(directory)
        by_id={p['id']:p for p in catalog['projects']}
        self.assertFalse(any('PokeRL' in p['repoUrl'] or 'PokemonRed' in p['entryPoint']['url'] for p in catalog['projects']))
        self.assertFalse(set(by_id)&set(RETIRED))
        self.assertEqual({p['id'] for p in catalog['retired']},set(RETIRED))
        self.assertEqual(by_id['public-fastapi-cursor-paging']['level'],'Capstone')
        self.assertTrue(any('Docker' in tool for tool in by_id['public-fastapi-cursor-paging']['prerequisites']['tools']))
        self.assertEqual(by_id['public-vigil-ai-authority']['platforms'],['macos','linux'])
        self.assertEqual(by_id['public-vigil-ai-authority']['setup']['windows'],[])
        self.assertIn('public-gymnasium-policy',by_id['public-sb3-capstone']['prerequisites']['projects'])
        patterns=[]
        for project in catalog['projects']:
            with self.subTest(project=project['id']):
                ref=project['pin']['ref']
                self.assertRegex(ref,'^[0-9a-f]{40}$')
                self.assertTrue(project['goal'] and project['run'] and project['stretch'] and project['troubleshooting'])
                self.assertTrue(3<=len(project['tasks'])<=5)
                self.assertEqual(project['steps'],[t['title'] for t in project['tasks']])
                self.assertEqual(project['minutes']['tasks'],sum(t['minutes'] for t in project['tasks']))
                self.assertTrue(project['entryPoint']['url'].startswith(f"{project['repoUrl']}/blob/{ref}/"))
                self.assertTrue(project['setup']['unix'] and any(ref in command for command in project['setup']['unix']))
                if 'windows' in project['platforms']:self.assertTrue(any(ref in command for command in project['setup']['windows']))
                for task in project['tasks']+[project['stretch']]:
                    a,b=task['source']['lines']
                    self.assertEqual(task['source']['url'],f"{project['repoUrl']}/blob/{ref}/{task['source']['path']}#L{a}-L{b}")
                    self.assertIn('check',task['verify'])
                    if task['verify']['check']['type']=='regex':patterns.append(task['verify']['check']['pattern'])
                if project['run'].get('check',{}).get('type')=='regex':patterns.append(project['run']['check']['pattern'])
        node=shutil.which('node')
        if node:
            # The browser runs these checks, so every pattern must also compile in JavaScript.
            script='const ps=JSON.parse(require("fs").readFileSync(0,"utf8"));for(const p of ps)new RegExp(p,"m");console.log(ps.length)'
            result=subprocess.run([node,'-e',script],input=json.dumps(patterns),capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
    def test_optional_and_invalid_catalogs(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'portfolio.json'
            self.assertEqual(len(load_portfolio(directory)['projects']),12)
            project=dict(id='demo',title='Demo',summary='Example',tracks=['backend'],steps=['Inspect a contract'])
            for patch in ({'tracks':['unknown']},{'repoUrl':'javascript:alert(1)'},{'repoUrl':'https://github.com.evil.test/x/y'},{'steps':[]},{'id':'../escape'}):
                path.write_text(json.dumps(dict(version=1,projects=[{**project,**patch}])))
                result=load_portfolio(directory)
                self.assertEqual(result['projects'],[]);self.assertIn('error',result)
            path.write_text(json.dumps(dict(version=1,projects=[project,project])))
            self.assertIn('error',load_portfolio(directory))
            path.write_text(json.dumps(dict(version=1,projects=[project])))
            loaded=load_portfolio(directory)['projects'][0]
            self.assertEqual(loaded['title'],'Demo')
            # A walkthrough-only entry gets empty hands-on fields.
            self.assertEqual((loaded['tasks'],loaded['stretch'],loaded['run'],loaded['pin']),([],None,None,None))
            path.write_text('{invalid')
            self.assertIn('error',load_portfolio(directory))
    def test_hands_on_fields_derive_steps_and_pinned_links(self):
        with tempfile.TemporaryDirectory() as directory:
            loaded=self.load(directory,{**HANDS_ON,'steps':['Ignored']},dict(id='next',title='Next',summary='Later',tracks=['web'],steps=['Read'],prerequisites=dict(projects=['hands-on'])))
            self.assertNotIn('error',loaded)
            project=loaded['projects'][0]
            self.assertEqual(project['steps'],['Run the test'])
            self.assertEqual(project['tasks'][0]['source']['url'],f'https://github.com/example/app/blob/{SHA}/app/main.py#L3-L9')
            self.assertEqual(project['stretch']['id'],'extra')
            self.assertEqual(project['platforms'],['macos','linux','windows'])
            self.assertEqual(loaded['projects'][1]['prerequisites']['projects'],['hands-on'])
    def test_hands_on_fields_reject_bad_values_with_clear_errors(self):
        def patched(path,value):
            project=copy.deepcopy(HANDS_ON);target=project;keys=path.split('.')
            for key in keys[:-1]:target=target[int(key)] if isinstance(target,list) else target[key]
            last=keys[-1]
            if value is KeyError:del target[last]
            elif isinstance(target,list):target[int(last)]=value
            else:target[last]=value
            return project
        cases=[('pin.ref','main','hands-on.pin.ref'),('pin',KeyError,'hands-on.pin'),('repoUrl','','hands-on.repoUrl'),
               ('tasks',[],'hands-on.tasks'),('tasks.0.source.path','../secret.py','tasks[0].source.path'),
               ('tasks.0.source.path','/etc/passwd','tasks[0].source.path'),('tasks.0.source.lines',[9,3],'tasks[0].source.lines'),
               ('tasks.0.source.lines',[0,3],'tasks[0].source.lines'),('tasks.0.lessons',['nope-9'],'unknown lesson "nope-9"'),
               ('tasks.0.id','Bad ID','tasks[0].id'),('tasks.0.verify.commands',[],'tasks[0].verify.commands'),
               ('tasks.0.verify.check',dict(type='regex',pattern='(unclosed'),'does not compile'),
               ('tasks.0.verify.check',dict(type='regex',pattern='(?P<n>x)'),'works in both Python and JavaScript'),
               ('tasks.0.verify.check',dict(type='regex',pattern='x'*301),'tasks[0].verify.check.pattern'),
               ('tasks.0.verify.check',dict(type='glob',value='*'),'tasks[0].verify.check.type'),
               ('tasks.0.starter',dict(path='a/../b.py',text='x'),'tasks[0].starter.path'),
               ('stretch.id','first','task IDs must be unique'),('prerequisites.lessons',['missing-1'],'unknown lesson'),
               ('prerequisites.projects',['ghost'],'unknown project "ghost"'),('minutes.setup',-1,'hands-on.minutes.setup'),
               ('platforms',['amiga'],'hands-on.platforms'),('platforms',['macos','linux'],'hands-on.setup.windows'),
               ('run',dict(commands=['x']),'hands-on.run.expect'),('troubleshooting',[dict(problem='x')],'troubleshooting[0].fix'),
               ('goal','','hands-on.goal')]
        with tempfile.TemporaryDirectory() as directory:
            for path,value,message in cases:
                with self.subTest(path=path,value=str(value)[:30]):
                    result=self.load(directory,patched(path,value))
                    self.assertEqual(result['projects'],[])
                    self.assertIn(message,result['error'])
    def test_task_progress_keeps_only_notes_and_check_times(self):
        project=dict(tasks=[dict(id='first'),dict(id='second')],stretch=dict(id='extra'))
        clean=task_progress(project,dict(first=dict(notes='edited line 18',verifiedAt=1700000000000),second=dict(notes='',verifiedAt=None),extra=dict(verifiedAt=5)))
        self.assertEqual(clean,dict(first=dict(notes='edited line 18',verifiedAt=1700000000000),extra=dict(verifiedAt=5)))
        for bad in (dict(first=dict(output='/Users/me/secret')),dict(ghost=dict(notes='x')),dict(first=dict(notes='x'*5001)),
                    dict(first=dict(verifiedAt=True)),dict(first=dict(verifiedAt=-1)),dict(first='done'),[],None):
            with self.subTest(bad=str(bad)[:40]),self.assertRaises(ValueError):task_progress(project,bad)
        self.assertEqual(task_progress(dict(tasks=[],stretch=None),{}),{})
        with self.assertRaises(ValueError):task_progress(dict(tasks=[],stretch=None),dict(first={}))
if __name__=='__main__':unittest.main()
