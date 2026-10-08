from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime, timezone
from importlib.metadata import version, PackageNotFoundError
from urllib.parse import urlparse, unquote, parse_qs
import argparse
import hmac
import json
import mimetypes
import os
import re
import sqlite3
import sys
import threading
import tempfile
import time
import traceback

from courses import BY_ID, public_curriculum
from runner import execute, node_binary
from portfolio import load_portfolio, task_progress
from library import Library, MAX_BOOK_BYTES
from book_import import import_upload, ImportConflict, SUGGESTED
from book_study import study_guides
import game
import assistant

ROOT=Path(__file__).resolve().parents[1]
# Same rule as the launcher: data/ in a clone, the data folder next to app/ in an installed copy.
sys.path.append(str(ROOT/'scripts'))
from platform_paths import data_dir, session_token
SESSION_HELP='Open Engineering Workshop from its shortcut or start command to connect this browser.'
# Health is polled by the launcher. Book files load by URL from <img> and the PDF viewer, which cannot send the header.
PUBLIC_API=re.compile(r'/api/health|/api/library/[^/]+/asset/.+')
BACKUP_NAME=re.compile(r'ml-workshop-\d{8}-\d{6}-\d{6}\.json')
KEEP_BACKUPS=10
RUN_LOCK=threading.Lock()
IMPORT_LOCK=threading.Lock()
VERSION=json.loads((ROOT/'package.json').read_text(encoding='utf-8'))['version']
# Set by open_data(), which main() calls after reading the command line, so --help changes nothing on disk.
# ASSISTANT is the optional AI assistant. Its settings and API key are in data/assistant.json, outside SQLite and backups.
DATA=DB=TOKEN=LIBRARY=ASSISTANT=None

def open_data():
    """Create the data folder and database if needed, and load the session token."""
    global DATA,DB,TOKEN,LIBRARY,ASSISTANT
    # Files and folders this server creates are private to the user: 0600 files, 0700 folders.
    os.umask(0o077)
    DATA=data_dir()
    DATA.mkdir(parents=True,exist_ok=True)
    if os.name!='nt':
        # Older versions created the data folder as 0755. A 0700 folder also protects the 0644 files inside it.
        try:DATA.chmod(0o700)
        except OSError:pass
    DB=DATA/'workshop.sqlite3'
    # The token stays the same across restarts. The launcher reads it from the data folder and gives
    # it to the browser in the URL fragment; no endpoint returns it.
    TOKEN=session_token(DATA).encode()
    LIBRARY=Library(DATA)
    ASSISTANT=assistant.Assistant(DATA)
    with connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS drafts (lesson TEXT PRIMARY KEY, code TEXT, notes TEXT, updated INTEGER)')
        db.execute('CREATE TABLE IF NOT EXISTS completions (lesson TEXT PRIMARY KEY, at TEXT, xp INTEGER)')
        db.execute('CREATE TABLE IF NOT EXISTS activity (day TEXT PRIMARY KEY)')
        db.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
        db.execute('CREATE TABLE IF NOT EXISTS project_state (project TEXT PRIMARY KEY, notes TEXT, reviewed TEXT, updated INTEGER)')
        # Per-task notes and check times. Older databases gain the column with an empty map.
        if 'tasks' not in {r[1] for r in db.execute('PRAGMA table_info(project_state)')}:
            db.execute("ALTER TABLE project_state ADD COLUMN tasks TEXT NOT NULL DEFAULT '{}'")
        db.execute('CREATE TABLE IF NOT EXISTS reading_state (book TEXT PRIMARY KEY, location INTEGER, notes TEXT, bookmarks TEXT, completed TEXT, updated INTEGER)')
        game.ensure_schema(db)

def connect():
    db=sqlite3.connect(DB,timeout=10)
    db.execute('PRAGMA journal_mode=WAL')
    return db

def now_ms():
    return time.time_ns()//1_000_000

def revision(value):
    """A client revision, at most now: one ahead of this computer's clock would block later saves."""
    if type(value) is not int or not 0<=value<=2**53-1:raise ValueError('Invalid timestamp')
    return min(value,now_ms())

# Stored revisions read as at most now, and a stored revision that is still ahead never blocks a save.
# Rows from before revisions were checked can be ahead.
def project_state():
    with connect() as db:
        return {r[0]:dict(notes=r[1],reviewed=json.loads(r[2]),updatedAt=r[3],tasks=json.loads(r[4])) for r in db.execute('SELECT project,notes,reviewed,MIN(updated,?),tasks FROM project_state',(now_ms(),))}

def reading_state():
    with connect() as db:
        return {r[0]:dict(location=r[1],notes=r[2],bookmarks=json.loads(r[3]),completed=json.loads(r[4]),updatedAt=r[5]) for r in db.execute('SELECT book,location,notes,bookmarks,completed,MIN(updated,?) FROM reading_state',(now_ms(),))}

def state():
    with connect() as db:
        drafts=db.execute('SELECT lesson,code,notes,MIN(updated,?) FROM drafts',(now_ms(),)).fetchall()
        complete=db.execute('SELECT lesson,at,xp FROM completions').fetchall()
        current=db.execute("SELECT value FROM settings WHERE key='currentLesson'").fetchone()
        return dict(draftUpdated={r[0]:r[3] for r in drafts},drafts={r[0]:r[1] for r in drafts},notes={r[0]:r[2] for r in drafts},completed={r[0]:dict(at=r[1],xp=r[2]) for r in complete},currentLesson=current[0] if current and current[0] in BY_ID else 'foundations-1',activity=[r[0] for r in db.execute('SELECT day FROM activity ORDER BY day')])

def game_progress():
    with connect() as db:completed={r[0]:dict(at=r[1],xp=r[2]) for r in db.execute('SELECT lesson,at,xp FROM completions')}
    catalog=load_portfolio(DATA)
    return dict(completed=completed,projects=catalog['projects'],retiredProjects=catalog['retired'],projectState=project_state(),readingState=reading_state(),guides=study_guides(LIBRARY))

def save_backup():
    folder=DATA/'backups';folder.mkdir(mode=0o700,exist_ok=True)
    name='ml-workshop-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')+'.json'
    with connect() as db:game_export=game.export(db)
    payload=dict(app='ml-workshop',version=3,projectState=project_state(),portfolio=load_portfolio(DATA),exportedAt=datetime.now(timezone.utc).isoformat(),readingState=reading_state(),game=game_export,**state())
    descriptor=os.open(folder/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(descriptor,'w',encoding='utf-8') as stream:stream.write(json.dumps(payload,indent=2))
    prune_backups(folder)
    return name

def prune_backups(folder,keep=KEEP_BACKUPS):
    """Keep the newest backups this server wrote. Files with any other name are left alone."""
    # The UTC timestamp in the name sorts in time order.
    names=sorted(f.name for f in folder.iterdir() if BACKUP_NAME.fullmatch(f.name) and f.is_file())
    for name in names[:-keep]:
        try:(folder/name).unlink()
        except OSError:pass

def runtime():
    packages={}
    for name in ['torch','tensorflow','transformers','tokenizers','langchain-core','llama-index-core','numba']:
        try:packages[name]=version(name)
        except PackageNotFoundError:packages[name]=None
    return dict(python=sys.version.split()[0],javascript=bool(node_binary()),packages=packages,cudaMode='CPU simulator (Numba); no NVIDIA GPU execution')

class Handler(BaseHTTPRequestHandler):
    server_version=f'MLWorkshop/{VERSION}'
    # Seconds a client may wait between bytes. A stalled connection then closes and frees its thread.
    timeout=15
    responded=False
    def log_message(self,fmt,*args):
        # Do not log request bodies or learner source.
        sys.stderr.write('%s %s\n'%(self.log_date_time_string(),fmt%args))
    def send_response(self,code,message=None):
        self.responded=True
        super().send_response(code,message)
    def guarded(self,handle):
        """Answer bad input with 400 and unexpected errors with 500, instead of dropping the connection."""
        self.responded=False;self.body_read=False
        try:handle()
        except (TimeoutError,ConnectionError):self.close_connection=True
        except Exception as exc:
            bad_input=isinstance(exc,ValueError)
            if not bad_input:traceback.print_exc()
            if self.responded:self.close_connection=True;return
            try:self.send({'error':'The server could not read this request.'} if bad_input else {'error':'The local server hit an error. Saved progress is safe. Details are in data/server.log.'},400 if bad_input else 500)
            except OSError:self.close_connection=True
    def token_ok(self):
        # Header values arrive as latin-1 text. Compare bytes, so any value is a mismatch and never an error.
        return hmac.compare_digest(self.headers.get('X-Workshop-Token','').encode('utf-8','surrogateescape'),TOKEN)
    def discard_body(self):
        # A reply sent before the request body is read can reach a client that is still
        # sending; closing then resets the connection. Read a small leftover body first.
        self.body_read=True
        try:length=int(self.headers.get('Content-Length','0'))
        except ValueError:length=0
        if 0<length<=4_000_000:
            try:
                while length>0:
                    block=self.rfile.read(min(65536,length))
                    if not block:break
                    length-=len(block)
            except OSError:self.close_connection=True
        elif length:self.close_connection=True
    def send(self,data,status=200):
        if self.command=='POST' and not getattr(self,'body_read',True):self.discard_body()
        body=json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers();self.wfile.write(body)
    def allowed(self,token=True):
        expected=f'127.0.0.1:{self.server.server_port}'
        if self.headers.get('Host')!=expected:
            self.send({'error':f'Open http://{expected}/ instead. The workshop only answers on that address.'},403);return False
        origin=self.headers.get('Origin')
        if origin and origin!=f'http://{expected}':
            self.send({'error':'Cross-origin requests are disabled.'},403);return False
        if self.headers.get('Sec-Fetch-Site')=='cross-site':
            self.send({'error':'Cross-site requests are disabled.'},403);return False
        if token and not self.token_ok():
            self.send({'error':SESSION_HELP,'code':'session-expired'},403);return False
        return True
    def do_GET(self):self.guarded(self.handle_get)
    def do_POST(self):self.guarded(self.handle_post)
    def handle_get(self):
        parsed=urlparse(self.path);path=parsed.path
        # Every API response with learner data needs the token. Static files and the public routes do not.
        if not self.allowed(token=path.startswith('/api/') and not PUBLIC_API.fullmatch(path)):return
        if path=='/api/portfolio':return self.send(dict(**load_portfolio(DATA),projectState=project_state()))
        if path=='/api/library':
            return self.send(dict(books=LIBRARY.catalog(),unreadable=LIBRARY.unreadable(),guides=study_guides(LIBRARY),readingState=reading_state()))
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
        if path=='/api/health':return self.send(dict(app='ml-workshop',version=VERSION,busy=RUN_LOCK.locked()))
        # Lets the launcher check that a running server uses this data folder's token.
        if path=='/api/session':return self.send({'ok':True})
        if path=='/api/curriculum':return self.send(public_curriculum())
        if path=='/api/state':return self.send(state())
        if path=='/api/game':
            progress=game_progress()
            with connect() as db:return self.send(game.state(db,progress))
        if path=='/api/game/summary':
            progress=game_progress()
            with connect() as db:return self.send(game.summary(db,progress))
        if path=='/api/runtime':return self.send(runtime())
        if path.startswith('/api/assistant/'):return ASSISTANT.handle_get(self,path)
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
            self.send_header('X-Content-Type-Options','nosniff')
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
        media_type=mimetypes.guess_type(file.name)[0] or 'application/octet-stream'
        # Some license notices use characters outside ASCII, such as the copyright sign.
        self.send_header('Content-Type',media_type+'; charset=utf-8' if media_type.startswith('text/') else media_type)
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
    def handle_post(self):
        if not self.allowed():return
        if urlparse(self.path).path=='/api/library/import':return self.import_book_file()
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<1 or length>128000:return self.send({'error':'Request exceeds the local exercise size limit.'},413)
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.send({'error':'Expected JSON.'},415)
            raw=self.rfile.read(length);self.body_read=True
            try:body=json.loads(raw)
            except RecursionError:raise ValueError('JSON is nested too deeply.') from None
            if not isinstance(body,dict):raise ValueError('Expected an object')
            path=urlparse(self.path).path
            # A streamed answer runs on this request's thread and takes no lock that other requests wait for.
            if path.startswith('/api/assistant/'):return ASSISTANT.handle_post(self,path,body)
            if path=='/api/project/state':
                project=next((p for p in load_portfolio(DATA)['projects'] if p['id']==body.get('projectId')),None)
                if not project:raise ValueError('Unknown project')
                notes=body.get('notes');reviewed=body.get('reviewed');updated=body.get('updatedAt')
                if not isinstance(notes,str) or len(notes)>30000:raise ValueError('Invalid project notes')
                if not isinstance(reviewed,list) or len(reviewed)>len(project['steps']) or any(type(i)!=int or not 0<=i<len(project['steps']) for i in reviewed):raise ValueError('Invalid reviewed steps')
                updated=revision(updated)
                # Clients from before task progress existed send no tasks; keep what is saved.
                tasks=json.dumps(task_progress(project,body['tasks'])) if 'tasks' in body else None
                with connect() as db:applied=db.execute("INSERT INTO project_state (project,notes,reviewed,updated,tasks) VALUES (?,?,?,?,COALESCE(?,'{}')) ON CONFLICT(project) DO UPDATE SET notes=excluded.notes,reviewed=excluded.reviewed,updated=excluded.updated,tasks=COALESCE(?,project_state.tasks) WHERE excluded.updated>=project_state.updated OR project_state.updated>?",(project['id'],notes,json.dumps(sorted(set(reviewed))),updated,tasks,tasks,now_ms())).rowcount==1
                return self.send({'ok':True,'applied':applied})
            if path=='/api/library/state':
                book_id=body.get('bookId','')
                try:book=LIBRARY.book(book_id)
                except (KeyError,TypeError):raise ValueError('Unknown book')
                location=body.get('location');notes=body.get('notes');bookmarks=body.get('bookmarks');completed=body.get('completed');updated=body.get('updatedAt')
                if type(location)!=int or not 1<=location<=book['count'] or not isinstance(notes,str) or len(notes)>30000:raise ValueError('Invalid reading state')
                if not isinstance(bookmarks,list) or len(bookmarks)>book['count'] or any(type(n)!=int or not 1<=n<=book['count'] for n in bookmarks):raise ValueError('Invalid bookmarks')
                valid={g['id'] for g in study_guides(LIBRARY) if g['bookId']==book_id}
                if not isinstance(completed,list) or any(not isinstance(s,str) or s not in valid for s in completed):raise ValueError('Unknown study guide')
                updated=revision(updated)
                with connect() as db:applied=db.execute('INSERT INTO reading_state VALUES (?,?,?,?,?,?) ON CONFLICT(book) DO UPDATE SET location=excluded.location,notes=excluded.notes,bookmarks=excluded.bookmarks,completed=excluded.completed,updated=excluded.updated WHERE excluded.updated>=reading_state.updated OR reading_state.updated>?',(book_id,location,notes,json.dumps(sorted(set(bookmarks))),json.dumps(sorted(set(completed))),updated,now_ms())).rowcount==1
                return self.send({'ok':True,'applied':applied})
            if path=='/api/library/remove':
                # Deletes data/library/<id> only. Reading state stays in SQLite, so a reimport restores notes.
                if not IMPORT_LOCK.acquire(blocking=False):return self.send({'error':'A book is being imported. Wait for it to finish, then try again.'},409)
                try:LIBRARY.remove(body.get('bookId'))
                except KeyError:return self.send({'error':'Unknown book'},404)
                finally:IMPORT_LOCK.release()
                return self.send({'ok':True})
            if path=='/api/backup':
                name=save_backup()
                return self.send(dict(filename=name,url='/api/backups/'+name))
            if path=='/api/current':
                lesson=body.get('lessonId')
                if lesson not in BY_ID:raise ValueError('Unknown lesson')
                with connect() as db:db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',('currentLesson',lesson))
                return self.send({'ok':True})
            if path.startswith('/api/game/'):
                progress=game_progress()
                with connect() as db:result=game.handle(db,path[len('/api/game/'):],body,progress)
                return self.send(result)
            lesson=BY_ID.get(body.get('lessonId'))
            if not lesson:raise ValueError('Unknown lesson')
            if path=='/api/draft':
                code,notes,stamp=body.get('code'),body.get('notes'),body.get('updatedAt')
                if not isinstance(code,str) or not isinstance(notes,str):raise ValueError('Invalid draft')
                if len(code)>50000:raise ValueError('Code is longer than 50,000 characters.')
                if len(notes)>30000:raise ValueError('Notes are longer than 30,000 characters.')
                stamp=revision(stamp)
                with connect() as db:applied=db.execute('INSERT INTO drafts VALUES (?,?,?,?) ON CONFLICT(lesson) DO UPDATE SET code=excluded.code,notes=excluded.notes,updated=excluded.updated WHERE excluded.updated>=drafts.updated OR drafts.updated>?',(lesson['id'],code,notes,stamp,now_ms())).rowcount==1
                return self.send({'ok':True,'applied':applied})
            if path in ('/api/run','/api/example'):
                is_example=path=='/api/example'
                code=lesson['example']['code'] if is_example else body.get('code');mode='run' if is_example else body.get('mode')
                if not isinstance(code,str) or len(code)>50000 or mode not in ('run','check'):raise ValueError('Invalid exercise request')
                if not RUN_LOCK.acquire(blocking=False):return self.send({'error':'Another exercise is running. Try again when it finishes.'},409)
                try:
                    result=execute(code,lesson['checks'] if mode=='check' else [],simulator=lesson['course']=='cuda',language=lesson.get('language','python'))
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
        except (TimeoutError,ConnectionError):raise
        except Exception:
            traceback.print_exc()
            self.send({'error':'The local server hit an error. Saved progress is safe. Details are in data/server.log.'},500)

    def import_book_file(self):
        """Receive raw file bytes, with separate limits from small JSON exercise writes."""
        try:
            length=int(self.headers.get('Content-Length','0'))
        except ValueError:
            return self.send({'error':'Invalid file size.'},400)
        if length<1 or length>MAX_BOOK_BYTES:
            return self.send({'error':'Choose a non-empty PDF or EPUB no larger than 100 MB.'},413)
        if self.headers.get('Transfer-Encoding') or self.headers.get('Content-Type','').split(';')[0]!='application/octet-stream':
            return self.send({'error':'Expected a PDF or EPUB file upload.'},415)
        query=parse_qs(urlparse(self.path).query)
        filename=query.get('filename',[''])[0]
        suggested=query.get('book',[''])[0]
        extension=Path(filename).suffix.lower()
        if not filename or len(filename)>240 or '/' in filename or '\\' in filename or any(ord(c)<32 for c in filename) or extension not in ('.pdf','.epub'):
            return self.send({'error':'Choose a PDF or EPUB file.'},400)
        if suggested and suggested not in SUGGESTED:
            return self.send({'error':'Unknown suggested book.'},400)
        if not IMPORT_LOCK.acquire(blocking=False):
            return self.send({'error':'Another book is being imported. Wait for it to finish, then try again.'},409)
        previous_timeout=self.connection.gettimeout()
        try:
            with tempfile.TemporaryDirectory(prefix='.upload-',dir=DATA) as temporary:
                source=Path(temporary)/('upload'+extension)
                deadline=time.monotonic()+60
                with source.open('wb') as stream:
                    remaining=length;self.body_read=True
                    while remaining:
                        timeout=deadline-time.monotonic()
                        if timeout<=0:raise TimeoutError()
                        self.connection.settimeout(min(timeout,15))
                        block=self.rfile.read1(min(65536,remaining))
                        if not block:raise ValueError('The file upload was interrupted. Choose the file again to retry.')
                        stream.write(block);remaining-=len(block)
                self.connection.settimeout(previous_timeout)
                book_id,already=import_upload(source,DATA,filename,suggested)
                self.send(dict(book=LIBRARY.summary(book_id),guides=[g for g in study_guides(LIBRARY) if g['bookId']==book_id],
                               readingState=reading_state().get(book_id),alreadyImported=already))
        except ImportConflict as exc:self.send({'error':str(exc)},409)
        except ValueError as exc:self.send({'error':str(exc)},400)
        except TimeoutError:self.send({'error':'The upload timed out. Choose the file again to retry.'},408)
        except (BrokenPipeError,ConnectionResetError):pass
        except Exception:
            self.send({'error':'Could not import this book. Check available disk space, then try again. Existing books and notes are safe.'},500)
        finally:
            self.connection.settimeout(previous_timeout)
            IMPORT_LOCK.release()

def main():
    parser=argparse.ArgumentParser(description='Serve Engineering Workshop on 127.0.0.1. The data folder is ML_WORKSHOP_DATA_DIR, or data/ by default.')
    parser.add_argument('--port',type=int,default=7318)
    args=parser.parse_args()
    open_data()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'Engineering Workshop http://127.0.0.1:{args.port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':
    main()
