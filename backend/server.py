from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime, timezone
from importlib.metadata import version, PackageNotFoundError
from urllib.parse import urlparse, unquote, parse_qs
import argparse
import json
import mimetypes
import os
import secrets
import sqlite3
import sys
import threading

from courses import BY_ID, public_curriculum
from runner import execute
from library import Library
from book_study import study_guides

ROOT=Path(__file__).resolve().parents[1]
DATA=Path(os.environ.get('ML_WORKSHOP_DATA_DIR',ROOT/'data'))
DATA.mkdir(parents=True,exist_ok=True)
DB=DATA/'workshop.sqlite3'
TOKEN=secrets.token_urlsafe(32)
RUN_LOCK=threading.Lock()
LIBRARY=Library(DATA)

def connect():
    db=sqlite3.connect(DB,timeout=10)
    db.execute('PRAGMA journal_mode=WAL')
    return db

with connect() as db:
    db.execute('CREATE TABLE IF NOT EXISTS drafts (lesson TEXT PRIMARY KEY, code TEXT, notes TEXT, updated INTEGER)')
    db.execute('CREATE TABLE IF NOT EXISTS completions (lesson TEXT PRIMARY KEY, at TEXT, xp INTEGER)')
    db.execute('CREATE TABLE IF NOT EXISTS activity (day TEXT PRIMARY KEY)')
    db.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS reading_state (book TEXT PRIMARY KEY, location INTEGER, notes TEXT, bookmarks TEXT, completed TEXT, updated INTEGER)')

def reading_state():
    with connect() as db:
        return {r[0]:dict(location=r[1],notes=r[2],bookmarks=json.loads(r[3]),completed=json.loads(r[4]),updatedAt=r[5]) for r in db.execute('SELECT book,location,notes,bookmarks,completed,updated FROM reading_state')}

def state():
    with connect() as db:
        drafts=db.execute('SELECT lesson,code,notes,updated FROM drafts').fetchall()
        complete=db.execute('SELECT lesson,at,xp FROM completions').fetchall()
        current=db.execute("SELECT value FROM settings WHERE key='currentLesson'").fetchone()
        return dict(draftUpdated={r[0]:r[3] for r in drafts},drafts={r[0]:r[1] for r in drafts},notes={r[0]:r[2] for r in drafts},completed={r[0]:dict(at=r[1],xp=r[2]) for r in complete},currentLesson=current[0] if current and current[0] in BY_ID else 'foundations-1',activity=[r[0] for r in db.execute('SELECT day FROM activity ORDER BY day')])

def runtime():
    packages={}
    for name in ['torch','tensorflow','transformers','tokenizers','langchain-core','llama-index-core','numba']:
        try:packages[name]=version(name)
        except PackageNotFoundError:packages[name]=None
    return dict(python=sys.version.split()[0],packages=packages,cudaMode='CPU simulator (Numba); no NVIDIA GPU execution')

class Handler(BaseHTTPRequestHandler):
    server_version='MLWorkshop/1.0'
    def log_message(self,fmt,*args):
        # Do not log request bodies or learner source.
        sys.stderr.write('%s %s\n'%(self.log_date_time_string(),fmt%args))
    def send(self,data,status=200):
        body=json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers();self.wfile.write(body)
    def allowed(self,write=False):
        expected=f'127.0.0.1:{self.server.server_port}'
        if self.headers.get('Host')!=expected:
            self.send({'error':'This app accepts only its loopback host.'},403);return False
        origin=self.headers.get('Origin')
        if origin and origin!=f'http://{expected}':
            self.send({'error':'Cross-origin requests are disabled.'},403);return False
        if self.headers.get('Sec-Fetch-Site')=='cross-site':
            self.send({'error':'Cross-site requests are disabled.'},403);return False
        if write and not secrets.compare_digest(self.headers.get('X-Workshop-Token',''),TOKEN):
            self.send({'error':'Session expired. Reload the page to reconnect.'},403);return False
        return True
    def do_GET(self):
        if not self.allowed():return
        parsed=urlparse(self.path);path=parsed.path
        if path=='/api/library':
            return self.send(dict(books=LIBRARY.catalog(),guides=study_guides(LIBRARY),readingState=reading_state()))
        if path=='/api/library/search':
            query=parse_qs(parsed.query)
            try:return self.send(dict(results=LIBRARY.search(query.get('q',[''])[0],query.get('book',[None])[0])))
            except KeyError:return self.send({'error':'Unknown book'},404)
        if path.startswith('/api/library/'):
            parts=path.split('/')
            try:
                book_id=parts[3]
                if len(parts)==6 and parts[4]=='chapter':
                    return self.send(LIBRARY.chapter(book_id,int(parts[5])))
                if len(parts)>=6 and parts[4]=='asset':
                    file,media_type=LIBRARY.asset(book_id,unquote('/'.join(parts[5:])))
                    return self.send_book_file(file,media_type)
                return self.send({'error':'Unknown library endpoint'},404)
            except (KeyError,ValueError):return self.send({'error':'Unknown book page or asset'},404)
        if path=='/api/health':return self.send(dict(app='ml-workshop',version='1.0',busy=RUN_LOCK.locked()))
        if path=='/api/bootstrap':return self.send(dict(token=TOKEN))
        if path=='/api/curriculum':return self.send(public_curriculum())
        if path=='/api/state':return self.send(state())
        if path=='/api/runtime':return self.send(runtime())
        if path.startswith('/api/backups/'):
            name=path.rsplit('/',1)[-1]
            if not name.startswith('ml-workshop-') or not name.endswith('.json') or '/' in name or '..' in name:
                return self.send({'error':'Unknown backup'},404)
            file=DATA/'backups'/name
            if not file.is_file():return self.send({'error':'Unknown backup'},404)
            body=file.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Disposition',f'attachment; filename="{name}"')
            self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store')
            self.end_headers();self.wfile.write(body);return
        if path.startswith('/api/solution/'):
            lesson=BY_ID.get(path.rsplit('/',1)[-1])
            return self.send({'solution':lesson['solution']} if lesson else {'error':'Unknown lesson'},200 if lesson else 404)
        if path.startswith('/api/'):return self.send({'error':'Unknown endpoint'},404)
        dist=ROOT/'dist'; file=(dist/unquote(path).lstrip('/')).resolve()
        if not file.is_relative_to(dist):return self.send({'error':'Invalid path'},400)
        if not file.is_file():file=dist/'index.html'
        if not file.exists():return self.send({'error':'Frontend not built. Run npm run build.'},503)
        body=file.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type',mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-cache')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; worker-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; font-src 'self' blob:; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers();self.wfile.write(body)
    def send_book_file(self,file,media_type):
        size=file.stat().st_size;start=0;end=size-1;status=200
        requested=self.headers.get('Range')
        if requested:
            import re
            match=re.fullmatch(r'bytes=(\d*)-(\d*)',requested)
            if not match or not any(match.groups()):
                return self.send({'error':'Unsupported byte range'},416)
            first,last=match.groups()
            if first:start=int(first);end=min(int(last),end) if last else end
            else:start=max(0,size-int(last))
            if start>end or start>=size:
                self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.send_header('Content-Length','0');self.end_headers();return
            status=206
        self.send_response(status)
        self.send_header('Content-Type',media_type)
        self.send_header('Content-Length',str(end-start+1))
        self.send_header('Accept-Ranges','bytes')
        if status==206:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.send_header('Cache-Control','private, max-age=3600')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'none'; sandbox")
        self.end_headers()
        with file.open('rb') as stream:
            stream.seek(start);remaining=end-start+1
            while remaining:
                block=stream.read(min(65536,remaining))
                if not block:break
                self.wfile.write(block);remaining-=len(block)
    def do_POST(self):
        if not self.allowed(write=True):return
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<1 or length>128000:return self.send({'error':'Request exceeds the local exercise size limit.'},413)
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.send({'error':'Expected JSON.'},415)
            body=json.loads(self.rfile.read(length))
            if not isinstance(body,dict):raise ValueError('Expected an object')
            path=urlparse(self.path).path
            if path=='/api/library/state':
                book_id=body.get('bookId','')
                try:book=LIBRARY.book(book_id)
                except (KeyError,TypeError):raise ValueError('Unknown book')
                location=body.get('location');notes=body.get('notes');bookmarks=body.get('bookmarks');completed=body.get('completed');updated=body.get('updatedAt')
                if type(location)!=int or not 1<=location<=book['count'] or not isinstance(notes,str) or len(notes)>30000:raise ValueError('Invalid reading state')
                if not isinstance(bookmarks,list) or len(bookmarks)>book['count'] or any(type(n)!=int or not 1<=n<=book['count'] for n in bookmarks):raise ValueError('Invalid bookmarks')
                valid={g['id'] for g in study_guides(LIBRARY) if g['bookId']==book_id}
                if not isinstance(completed,list) or any(not isinstance(s,str) or s not in valid for s in completed):raise ValueError('Unknown study guide')
                if type(updated)!=int or not 0<=updated<=2**53-1:raise ValueError('Invalid timestamp')
                with connect() as db:db.execute('INSERT INTO reading_state VALUES (?,?,?,?,?,?) ON CONFLICT(book) DO UPDATE SET location=excluded.location,notes=excluded.notes,bookmarks=excluded.bookmarks,completed=excluded.completed,updated=excluded.updated WHERE excluded.updated>=reading_state.updated',(book_id,location,notes,json.dumps(sorted(set(bookmarks))),json.dumps(sorted(set(completed))),updated))
                return self.send({'ok':True})
            if path=='/api/backup':
                folder=DATA/'backups';folder.mkdir(exist_ok=True)
                name='ml-workshop-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')+'.json'
                payload=dict(app='ml-workshop',version=2,exportedAt=datetime.now(timezone.utc).isoformat(),readingState=reading_state(),**state())
                (folder/name).write_text(json.dumps(payload,indent=2))
                return self.send(dict(filename=name,url='/api/backups/'+name))
            if path=='/api/current':
                lesson=body.get('lessonId')
                if lesson not in BY_ID:raise ValueError('Unknown lesson')
                with connect() as db:db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',('currentLesson',lesson))
                return self.send({'ok':True})
            lesson=BY_ID.get(body.get('lessonId'))
            if not lesson:raise ValueError('Unknown lesson')
            if path=='/api/draft':
                code,notes=body.get('code'),body.get('notes')
                if not isinstance(code,str) or not isinstance(notes,str) or len(code)>50000 or len(notes)>30000:raise ValueError('Invalid draft size')
                stamp=int(body.get('updatedAt',0))
                with connect() as db:db.execute('INSERT INTO drafts VALUES (?,?,?,?) ON CONFLICT(lesson) DO UPDATE SET code=excluded.code,notes=excluded.notes,updated=excluded.updated WHERE excluded.updated>=drafts.updated',(lesson['id'],code,notes,stamp))
                return self.send({'ok':True})
            if path=='/api/run':
                code=body.get('code');mode=body.get('mode')
                if not isinstance(code,str) or len(code)>50000 or mode not in ('run','check'):raise ValueError('Invalid exercise request')
                if not RUN_LOCK.acquire(blocking=False):return self.send({'error':'Another exercise is running. Try again when it finishes.'},409)
                try:
                    result=execute(code,lesson['checks'] if mode=='check' else [],simulator=lesson['course']=='cuda')
                    if mode=='check' and result['passed']:
                        now=datetime.now(timezone.utc).isoformat()
                        # Activity uses the user's local system date, not UTC midnight.
                        day=datetime.now().astimezone().date().isoformat()
                        with connect() as db:
                            db.execute('INSERT OR IGNORE INTO completions VALUES (?,?,?)',(lesson['id'],now,lesson['xp']))
                            db.execute('INSERT OR IGNORE INTO activity VALUES (?)',(day,))
                        result['state']=state()
                    return self.send(result)
                finally:RUN_LOCK.release()
            return self.send({'error':'Unknown endpoint'},404)
        except (ValueError,TypeError,json.JSONDecodeError) as exc:self.send({'error':str(exc)},400)
        except Exception:
            import traceback
            traceback.print_exc()
            self.send({'error':'The local server hit an error. Your previously saved progress is intact.'},500)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=7318)
    args=parser.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'ML Workshop http://127.0.0.1:{args.port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
