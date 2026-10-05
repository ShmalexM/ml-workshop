"""Optional, local-only project catalog. Never scans or executes project code."""
import json
import re
from pathlib import Path
from urllib.parse import urlparse
from courses import COURSES


def load_portfolio(data):
    path=Path(data)/'portfolio.json'
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
            clean.append(dict(id=pid,title=text(p.get('title'),120),summary=text(p.get('summary')),tracks=list(dict.fromkeys(tracks)),visibility=visibility,repoUrl=url,evidence=text(p.get('evidence','')),localPath=text(p.get('localPath',''),1000),steps=[text(s) for s in steps],deliverable=text(p.get('deliverable',''))))
        return dict(version=1,projects=clean,coverage=text(raw.get('coverage','')),updatedAt=text(raw.get('updatedAt',''),100))
    except (OSError,ValueError,TypeError,KeyError) as error:
        return {**empty,'error':f'Could not load data/portfolio.json: {error}'}
