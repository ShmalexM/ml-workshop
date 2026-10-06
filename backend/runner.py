"""Trusted personal-code runner, not an untrusted-code security sandbox."""
import json
import os
from pathlib import Path
try:
    import resource
except ImportError:  # Windows has no POSIX resource limits.
    resource = None
import signal
import shutil
import subprocess
import sys
import tempfile
import time
import traceback

MAX_OUTPUT=24000

def apply_limits():
    if resource is not None and sys.platform != 'win32':
        resource.setrlimit(resource.RLIMIT_CPU,(40,45))
        resource.setrlimit(resource.RLIMIT_FSIZE,(1024*1024,1024*1024))

def missing_package(exc):
    # Installed copies and clones fix this differently; the message names both.
    return (f"Missing Python module '{exc.name}'. Run the install command again, "
            "or in a clone rerun setup without --no-ml. See README.md.")

def stopped_message(language, code):
    name='JavaScript' if language=='javascript' else 'Python'
    limits=(' An infinite loop stops at the 40-second CPU limit, and output over 1 MiB stops '
            'at the file-size limit.') if resource is not None and sys.platform != 'win32' else ''
    return f'{name} stopped before finishing (exit code {code}).{limits}'

def raises(exception, function):
    try: function()
    except exception: return True
    return False

def check_torch_step(fn, mode):
    import torch
    model=torch.nn.Linear(1,1,bias=False)
    with torch.no_grad():model.weight.fill_(0)
    model.weight.grad=torch.full_like(model.weight,99.)
    opt=torch.optim.SGD(model.parameters(),lr=.1)
    x,y=torch.tensor([[1.]]),torch.tensor([[2.]])
    loss=fn(model,opt,x,y)
    if mode=='loss': return isinstance(loss,(int,float)) and abs(loss-4)<1e-5
    if mode=='update': return abs(model.weight.item()-.4)<1e-5
    fn(model,opt,x,y)
    return abs(model.weight.item()-.72)<1e-5

def check_tf_step(fn,mode):
    import tensorflow as tf
    w=tf.Variable(0.)
    opt=tf.keras.optimizers.SGD(.1)
    x,y=tf.constant([1.]),tf.constant([2.])
    loss=fn(w,opt,x,y)
    if mode=='loss': return isinstance(loss,(int,float)) and abs(loss-4)<1e-5
    if mode=='update': return abs(float(w.numpy())-.4)<1e-5
    fn(w,opt,x,y)
    return abs(float(w.numpy())-.72)<1e-5

def child(request_path, result_path):
    # Bound runaway exercises and output. Deliberately not advertised as isolation
    # from filesystem/network: Python code runs with the local user's privileges.
    apply_limits()
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8',newline='\n')
        sys.stderr.reconfigure(encoding='utf-8',newline='\n')
    request=json.loads(Path(request_path).read_text())
    ns={'__name__':'__main__','raises':raises,'check_torch_step':check_torch_step,'check_tf_step':check_tf_step}
    result={'error':None,'checks':[],'passed':False}
    try:
        exec(compile(request['code'],'exercise.py','exec'),ns)
        for check in request['checks']:
            try:
                passed=bool(eval(check['expr'],ns))
                detail='' if passed else 'The result did not match this requirement. Try a hint or inspect your output.'
            except BaseException as exc:
                passed=False
                detail=missing_package(exc) if isinstance(exc,ModuleNotFoundError) else f'{type(exc).__name__}: {exc}'[:1200]
            result['checks'].append(dict(label=check['label'],passed=passed,detail=detail))
        result['passed']=bool(result['checks']) and all(c['passed'] for c in result['checks'])
    except ModuleNotFoundError as exc:
        result['error']=missing_package(exc)
    except BaseException:
        result['error']=traceback.format_exc(limit=5)[-6000:]
    sys.stdout.flush()
    sys.stderr.flush()
    pending=Path(result_path).with_suffix('.tmp')
    pending.write_text(json.dumps(result))
    pending.replace(result_path)
    if sys.platform == 'win32':
        # Keep the tree root alive until the parent calls taskkill /T, including
        # after successful exercises that leave child processes behind.
        while True:time.sleep(60)

def node_binary():
    candidates=[shutil.which('node'),'/opt/homebrew/bin/node','/usr/local/bin/node',str(Path.home()/'.local/bin/node'),'/usr/bin/node']
    if sys.platform == 'win32':
        candidates.append(str(Path(os.environ.get('ProgramFiles',r'C:\Program Files'))/'nodejs/node.exe'))
    return next((str(Path(p).resolve()) for p in candidates if p and Path(p).is_file() and os.access(p,os.X_OK)),None)

def javascript_child(node, request_path, result_path):
    # Apply limits in this isolated Python process, then replace it with Node.
    # Do not use preexec_fn from the multithreaded HTTP server.
    apply_limits()
    os.execve(node,[node,str(Path(__file__).with_name('js_runner.cjs')),request_path,result_path],os.environ)

def cleanup_process(process):
    if sys.platform == 'win32':
        # taskkill reports a nonzero code if the process already exited.
        try:
            subprocess.run(['taskkill','/T','/F','/PID',str(process.pid)],
                           stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
        finally:
            if process.poll() is None:process.kill()
            process.wait()
    else:
        try:os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        process.wait()

def wait_for_result(process,result,timeout):
    if sys.platform != 'win32':
        process.wait(timeout=timeout)
        return
    deadline=time.monotonic()+timeout
    while not result.exists() and process.poll() is None:
        if time.monotonic() >= deadline:
            raise subprocess.TimeoutExpired(process.args,timeout)
        time.sleep(.02)

def execute(code, checks, timeout=50, simulator=False, language='python'):
    if language not in ('python','javascript'):raise ValueError('Unsupported exercise language')
    node=node_binary() if language=='javascript' else None
    if language=='javascript' and not node:
        return dict(error='Node.js is missing. Run the install command again, or in a clone install Node.js 22.13 or newer and rerun setup. See README.md.',checks=[],passed=False,stdout='',duration=0)
    start=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='ml-workshop-') as directory:
        work=Path(directory)
        request=work/'request.json';result=work/'result.json';output=work/'stdout.txt'
        request.write_text(json.dumps(dict(code=code,checks=checks)))
        allowed=('PATH','HOME','TMPDIR','LANG','SYSTEMROOT')
        if sys.platform == 'win32':allowed+=('TEMP','TMP','PATHEXT','WINDIR','USERPROFILE')
        env={k:os.environ[k] for k in allowed if k in os.environ}
        env.update(PYTHONUNBUFFERED='1',TF_CPP_MIN_LOG_LEVEL='3',CUDA_VISIBLE_DEVICES='-1',OMP_NUM_THREADS='1',TF_NUM_INTRAOP_THREADS='1',TF_NUM_INTEROP_THREADS='1',TOKENIZERS_PARALLELISM='false',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',MPLBACKEND='Agg',NUMBA_ENABLE_CUDASIM='1' if simulator else '0',PYTORCH_ENABLE_MPS_FALLBACK='1')
        with output.open('wb') as out:
            args=[sys.executable,'-I','-X','utf8',str(Path(__file__).resolve())]+(['--javascript',node] if node else [])+[str(request),str(result)]
            options=dict(start_new_session=True)
            if sys.platform == 'win32':
                options=dict(creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
                if node:args=[node,str(Path(__file__).with_name('js_runner.cjs')),str(request),str(result)]
            process=subprocess.Popen(args,cwd=work,env=env,stdout=out,stderr=out,**options)
            try:
                wait_for_result(process,result,timeout)
                data=json.loads(result.read_text()) if result.exists() else dict(error=stopped_message(language,process.returncode),checks=[],passed=False)
            except subprocess.TimeoutExpired:
                data=dict(error=f'Execution stopped after {timeout} seconds. Check for an infinite loop or reduce the workload.',checks=[],passed=False)
            finally:
                # Clean up any exercise-created child processes as well.
                cleanup_process(process)
        with output.open('rb') as stream:raw=stream.read(MAX_OUTPUT+1)
        data['stdout']=raw[:MAX_OUTPUT].decode('utf-8',errors='replace')+ ('\n[Output truncated]' if len(raw)>MAX_OUTPUT else '')
        data['duration']=round(time.monotonic()-start,2)
        return data

if __name__=='__main__':
    if sys.argv[1]=='--javascript':javascript_child(*sys.argv[2:5])
    else:child(sys.argv[1],sys.argv[2])
