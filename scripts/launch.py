"""Double-click entrypoint. Starts once, waits for readiness, opens last lesson."""
from pathlib import Path
import fcntl
import json
import os
import subprocess
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
PORT=7318
URL=f'http://127.0.0.1:{PORT}'

def health():
    try:
        with urllib.request.urlopen(URL+'/api/health',timeout=1) as response:
            return json.load(response)
    except Exception:return None

def main():
    DATA.mkdir(exist_ok=True)
    with (DATA/'launch.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        status=health()
        if not status or status.get('app')!='ml-workshop':
            if not (ROOT/'.venv/bin/python').exists() or not (ROOT/'dist/index.html').exists():
                raise RuntimeError(f'The app needs setup. Open Setup ML Workshop.command in {ROOT}.')
            log=(DATA/'server.log').open('ab')
            process=subprocess.Popen([str(ROOT/'.venv/bin/python'),str(ROOT/'backend/server.py'),'--port',str(PORT)],cwd=ROOT,stdout=log,stderr=log,start_new_session=True,stdin=subprocess.DEVNULL)
            (DATA/'server.pid').write_text(str(process.pid))
            for _ in range(80):
                if process.poll() is not None:
                    raise RuntimeError(f'ML Workshop could not start. Port {PORT} may be in use. See {DATA}/server.log.')
                status=health()
                if status and status.get('app')=='ml-workshop':break
                time.sleep(.15)
            else:raise RuntimeError(f'ML Workshop did not become ready. See {DATA}/server.log.')
        fcntl.flock(lock,fcntl.LOCK_UN)
    if '--no-open' not in sys.argv:subprocess.run(['/usr/bin/open',URL],check=True)
    print(URL)

if __name__=='__main__':main()
