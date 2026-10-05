from pathlib import Path
import os,signal,subprocess
ROOT=Path(__file__).resolve().parents[1]
pid_file=ROOT/'data/server.pid'
if not pid_file.exists():print('ML Workshop is already stopped.');raise SystemExit
pid=int(pid_file.read_text())
command=subprocess.run(['/bin/ps','-p',str(pid),'-o','command='],capture_output=True,text=True).stdout
if str(ROOT/'backend/server.py') not in command:
    print('No matching ML Workshop process is running.');raise SystemExit
os.kill(pid,signal.SIGTERM)
pid_file.unlink(missing_ok=True)
print('ML Workshop stopped. Your progress is saved.')
