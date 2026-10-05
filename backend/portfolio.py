"""Curated public projects with an optional local catalog override. Never scans or executes project code."""
import json
import re
from pathlib import Path
from urllib.parse import urlparse
from courses import COURSES, BY_ID


def load_portfolio(data):
    local=Path(data)/'portfolio.json'
    path=local if local.exists() else Path(__file__).with_name('public_projects.json')
    empty=dict(version=1,projects=[],coverage='',updatedAt='')
    if not path.exists():return empty
    try:
        raw=json.loads(path.read_text())
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
            steps=p.get('steps',[])
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
            clean.append(dict(level=level,firstLesson=first,entryPoint=dict(label=entry_label,url=entry_url),why=text(p.get('why','')),requirements=text(p.get('requirements','')),id=pid,title=text(p.get('title'),120),summary=text(p.get('summary')),tracks=list(dict.fromkeys(tracks)),visibility=visibility,repoUrl=url,evidence=text(p.get('evidence','')),localPath=text(p.get('localPath',''),1000),steps=[text(s) for s in steps],deliverable=text(p.get('deliverable',''))))
        return dict(version=1,projects=clean,coverage=text(raw.get('coverage','')),updatedAt=text(raw.get('updatedAt',''),100))
    except (OSError,ValueError,TypeError,KeyError) as error:
        return {**empty,'error':f'Could not load project catalog: {error}'}
