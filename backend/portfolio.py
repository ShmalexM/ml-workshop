"""Curated public projects with an optional local catalog override. Never scans or executes project code."""
import json
import re
from pathlib import Path
from urllib.parse import urlparse, quote
from courses import COURSES, BY_ID

SLUG=re.compile('[a-z0-9-]+')
SHA=re.compile('[0-9a-f]{40}')
PLATFORMS=('macos','linux','windows')
# Python-only regex syntax that JavaScript's RegExp rejects or reads differently.
PYTHON_ONLY=re.compile(r'\(\?P|\(\?[aiLmsux]|\\[AZ]')
# Built-in projects replaced on 2026-10-08. Learners may still have notes, ticked steps or an
# unopened chest for these IDs, so they stay known: each had three walkthrough steps.
RETIRED={
    'public-micrograd':'micrograd','public-todomvc':'TodoMVC · React','public-gymnasium':'Gymnasium · CartPole',
    'public-pytorch':'PyTorch · regression example','public-keras':'Keras · engineering introduction',
    'public-smolagents':'smolagents','public-fastapi':'Full Stack FastAPI Template',
    'public-llamaindex':'LlamaIndex · document schema','public-temporal':'Temporal · retry example',
    'public-cuda':'NVIDIA · vector addition','public-pokerl':'PokeRL · Pokémon Red','public-vigil-home':'Vigil at Home',
}
TASK_NOTES_LIMIT=5000


def need(ok,where,message):
    if not ok:raise ValueError(f'{where}: {message}')


def text(value,where,limit=4000):
    need(isinstance(value,str) and len(value)<=limit and value.strip(),where,f'expected text of 1 to {limit} characters')
    return value


def texts(value,where,most,limit):
    need(isinstance(value,list) and len(value)<=most,where,f'expected a list of up to {most} items')
    return [text(v,f'{where}[{i}]',limit) for i,v in enumerate(value)]


def whole(value,where,low,high):
    need(type(value) is int and low<=value<=high,where,f'expected a whole number from {low} to {high}')
    return value


def lessons(value,where):
    found=texts(value,where,12,80)
    for i,lesson in enumerate(found):need(lesson in BY_ID,f'{where}[{i}]',f'unknown lesson "{lesson}"')
    return found


def repo_path(value,where):
    text(value,where,300)
    need(not value.startswith('/') and '\\' not in value and not any(c in value for c in '?#') and all(ord(c)>=32 for c in value)
         and all(part not in ('','.','..') for part in value.split('/')),where,'expected a relative file path without .., empty parts, ? or #')
    return value


def check(value,where):
    need(isinstance(value,dict),where,'expected {"type": "contains", "value": ...} or {"type": "regex", "pattern": ...}')
    if value.get('type')=='contains':return dict(type='contains',value=text(value.get('value'),where+'.value',300))
    need(value.get('type')=='regex',where+'.type','expected "contains" or "regex"')
    pattern=text(value.get('pattern'),where+'.pattern',300)
    need(not PYTHON_ONLY.search(pattern),where+'.pattern','use regex syntax that works in both Python and JavaScript')
    try:re.compile(pattern,re.M)
    except re.error as error:raise ValueError(f'{where}.pattern: does not compile ({error})') from None
    return dict(type='regex',pattern=pattern)


def verify(value,where):
    need(isinstance(value,dict),where,'expected {"commands": [...], "expect": ...}')
    result=dict(commands=texts(value.get('commands'),where+'.commands',12,1000),expect=text(value.get('expect'),where+'.expect',2000))
    need(result['commands'],where+'.commands','expected at least one command')
    if 'paste' in value:result['paste']=text(value['paste'],where+'.paste',300)
    if 'check' in value:result['check']=check(value['check'],where+'.check')
    return result


def task(value,where,repo,ref):
    need(isinstance(value,dict),where,'expected a task object')
    tid=text(value.get('id'),where+'.id',60)
    need(SLUG.fullmatch(tid),where+'.id','expected a lowercase slug')
    source=value.get('source')
    need(isinstance(source,dict),where+'.source','expected {"path": ..., "lines": [first, last]}')
    path=repo_path(source.get('path'),where+'.source.path')
    span=source.get('lines')
    need(isinstance(span,list) and len(span)==2 and all(type(n) is int for n in span) and 1<=span[0]<=span[1]<=100000,
         where+'.source.lines','expected [first, last] with 1 <= first <= last')
    result=dict(id=tid,title=text(value.get('title'),where+'.title',120),minutes=whole(value.get('minutes'),where+'.minutes',1,600),
                lessons=lessons(value.get('lessons',[]),where+'.lessons'),
                source=dict(path=path,lines=span,url=f'{repo}/blob/{ref}/{quote(path)}#L{span[0]}-L{span[1]}'),
                do=text(value.get('do'),where+'.do',2000),change=text(value.get('change'),where+'.change',2000),
                verify=verify(value.get('verify'),where+'.verify'))
    if 'starter' in value:
        starter=value['starter']
        need(isinstance(starter,dict),where+'.starter','expected {"path": ..., "text": ...}')
        result['starter']=dict(path=repo_path(starter.get('path'),where+'.starter.path'),text=text(starter.get('text'),where+'.starter.text',20000))
    return result


def actionable(p,pid,url):
    """Validate the optional hands-on fields. Projects without tasks keep the walkthrough steps."""
    has_tasks='tasks' in p
    pin=None
    if 'pin' in p or has_tasks:
        pin=p.get('pin')
        need(isinstance(pin,dict),f'{pid}.pin','expected {"ref": <40-character commit SHA>, "label": ...}')
        need(isinstance(pin.get('ref'),str) and SHA.fullmatch(pin['ref']),f'{pid}.pin.ref','expected a 40-character lowercase commit SHA')
        pin=dict(ref=pin['ref'],label=text(pin.get('label'),f'{pid}.pin.label',100))
        need(url,f'{pid}.repoUrl','a pinned project needs a GitHub repository URL')
    tasks=[]
    if has_tasks:
        raw=p['tasks']
        need(isinstance(raw,list) and 1<=len(raw)<=8,f'{pid}.tasks','expected 1 to 8 tasks')
        tasks=[task(t,f'{pid}.tasks[{i}]',url,pin['ref']) for i,t in enumerate(raw)]
    stretch=task(p['stretch'],f'{pid}.stretch',url,pin['ref']) if p.get('stretch') is not None else None
    need(not stretch or has_tasks,f'{pid}.stretch','a stretch task needs tasks')
    ids=[t['id'] for t in tasks+([stretch] if stretch else [])]
    need(len(ids)==len(set(ids)),f'{pid}.tasks','task IDs must be unique, including the stretch task')
    pre=p.get('prerequisites',{})
    need(isinstance(pre,dict),f'{pid}.prerequisites','expected {"lessons": [...], "projects": [...], "tools": [...]}')
    prerequisites=dict(lessons=lessons(pre.get('lessons',[]),f'{pid}.prerequisites.lessons'),
                       projects=texts(pre.get('projects',[]),f'{pid}.prerequisites.projects',12,80),
                       tools=texts(pre.get('tools',[]),f'{pid}.prerequisites.tools',12,120))
    minutes=p.get('minutes',{})
    need(isinstance(minutes,dict),f'{pid}.minutes','expected {"setup": ..., "tasks": ..., "stretch": ...}')
    minutes=dict(setup=whole(minutes.get('setup',0),f'{pid}.minutes.setup',0,600),
                 tasks=whole(minutes.get('tasks',sum(t['minutes'] for t in tasks)),f'{pid}.minutes.tasks',0,6000),
                 stretch=whole(minutes.get('stretch',stretch['minutes'] if stretch else 0),f'{pid}.minutes.stretch',0,600))
    platforms=p.get('platforms',list(PLATFORMS))
    need(isinstance(platforms,list) and platforms and all(x in PLATFORMS for x in platforms),f'{pid}.platforms','expected some of "macos", "linux", "windows"')
    setup=p.get('setup',{})
    need(isinstance(setup,dict),f'{pid}.setup','expected {"unix": [...], "windows": [...]}')
    setup=dict(unix=texts(setup.get('unix',[]),f'{pid}.setup.unix',30,1000),windows=texts(setup.get('windows',[]),f'{pid}.setup.windows',30,1000))
    need(not setup['windows'] or 'windows' in platforms,f'{pid}.setup.windows','leave Windows setup empty when "windows" is not in platforms')
    trouble=p.get('troubleshooting',[])
    need(isinstance(trouble,list) and len(trouble)<=12,f'{pid}.troubleshooting','expected up to 12 {"problem", "fix"} items')
    troubleshooting=[]
    for i,item in enumerate(trouble):
        need(isinstance(item,dict),f'{pid}.troubleshooting[{i}]','expected {"problem": ..., "fix": ...}')
        troubleshooting.append(dict(problem=text(item.get('problem'),f'{pid}.troubleshooting[{i}].problem',300),fix=text(item.get('fix'),f'{pid}.troubleshooting[{i}].fix',1000)))
    return dict(goal=text(p['goal'],f'{pid}.goal',600) if 'goal' in p else '',pin=pin,prerequisites=prerequisites,minutes=minutes,
                platforms=platforms,setup=setup,run=verify(p['run'],f'{pid}.run') if 'run' in p else None,
                tasks=tasks,stretch=stretch,troubleshooting=troubleshooting)


def retired(ids):
    return [dict(id=key,title=title,steps=3) for key,title in RETIRED.items() if key not in ids]


def load_portfolio(data):
    local=Path(data)/'portfolio.json'
    path=local if local.exists() else Path(__file__).with_name('public_projects.json')
    empty=dict(version=1,projects=[],coverage='',updatedAt='',retired=retired(set()))
    if not path.exists():return empty
    try:
        raw=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(raw,dict) or raw.get('version')!=1:raise ValueError('Expected catalog version 1')
        projects=raw.get('projects')
        if not isinstance(projects,list) or len(projects)>500:raise ValueError('Expected up to 500 projects')
        ids=set();courses={c['id'] for c in COURSES};clean=[]
        def text(value,limit=4000):
            if not isinstance(value,str) or len(value)>limit:raise ValueError('Invalid project text')
            return value
        for p in projects:
            if not isinstance(p,dict):raise ValueError('Invalid project')
            pid=text(p.get('id'),80)
            if not re.fullmatch('[a-z0-9-]+',pid) or pid in ids:raise ValueError('Project IDs must be unique slugs')
            ids.add(pid)
            tracks=p.get('tracks',[])
            if not isinstance(tracks,list) or not tracks or any(not isinstance(t,str) or t not in courses for t in tracks):raise ValueError('Unknown learning path')
            visibility=p.get('visibility','local')
            if visibility not in ('public','private','local'):raise ValueError('Unknown visibility')
            url=text(p.get('repoUrl',''),500)
            if url:
                parsed=urlparse(url)
                if parsed.scheme!='https' or parsed.netloc!='github.com' or parsed.query or parsed.fragment:raise ValueError('Use an HTTPS GitHub repository URL')
            extra=actionable(p,pid,url.rstrip('/'))
            # Progress, export and chests count steps, so a hands-on project uses its task titles as steps.
            steps=[t['title'] for t in extra['tasks']] if extra['tasks'] else p.get('steps',[])
            if not isinstance(steps,list) or not 1<=len(steps)<=8:raise ValueError('Provide 1–8 walkthrough steps')
            level=text(p.get('level','Build next'),40)
            if level not in ('Start small','Build next','Capstone'):raise ValueError('Unknown project level')
            first=text(p.get('firstLesson',tracks[0]+'-1'),80)
            if first not in BY_ID or BY_ID[first]['course'] not in tracks:raise ValueError('Unknown preparation lesson')
            entry=p.get('entryPoint',dict(label='Repository',url=url))
            if not isinstance(entry,dict):raise ValueError('Invalid starting file')
            entry_label=text(entry.get('label',''),250);entry_url=text(entry.get('url',''),1000)
            if entry_url:
                parsed=urlparse(entry_url)
                if parsed.scheme!='https' or parsed.netloc!='github.com':raise ValueError('Use an HTTPS GitHub source URL')
            clean.append(dict(level=level,firstLesson=first,entryPoint=dict(label=entry_label,url=entry_url),why=text(p.get('why','')),requirements=text(p.get('requirements','')),id=pid,title=text(p.get('title'),120),summary=text(p.get('summary')),tracks=list(dict.fromkeys(tracks)),visibility=visibility,repoUrl=url,evidence=text(p.get('evidence','')),localPath=text(p.get('localPath',''),1000),steps=[text(s) for s in steps],deliverable=text(p.get('deliverable','')),**extra))
        for p in clean:
            for i,other in enumerate(p['prerequisites']['projects']):
                need(other in ids and other!=p['id'],f"{p['id']}.prerequisites.projects[{i}]",f'unknown project "{other}"')
        return dict(version=1,projects=clean,coverage=text(raw.get('coverage','')),updatedAt=text(raw.get('updatedAt',''),100),retired=retired(ids))
    except (OSError,ValueError,TypeError,KeyError) as error:
        return {**empty,'error':f'Could not load project catalog: {error}'}


def task_progress(project,value):
    """Clean per-task notes and check times. Pasted output is never accepted, so it cannot be stored."""
    known={t['id'] for t in project['tasks']}|({project['stretch']['id']} if project.get('stretch') else set())
    if not isinstance(value,dict) or len(value)>len(known):raise ValueError('Invalid task progress')
    clean={}
    for key,entry in value.items():
        if key not in known:raise ValueError(f'Unknown task "{key}"')
        if not isinstance(entry,dict) or set(entry)-{'notes','verifiedAt'}:raise ValueError('Task progress holds only notes and verifiedAt')
        notes=entry.get('notes','');at=entry.get('verifiedAt')
        if not isinstance(notes,str) or len(notes)>TASK_NOTES_LIMIT:raise ValueError('Invalid task notes')
        if at is not None and (type(at)!=int or not 0<at<=2**53-1):raise ValueError('Invalid check time')
        if notes or at:clean[key]={**({'notes':notes} if notes else {}),**({'verifiedAt':at} if at else {})}
    return clean
