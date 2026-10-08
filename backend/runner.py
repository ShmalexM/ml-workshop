"""Trusted personal-code runner, not an untrusted-code security sandbox."""
import ast
import json
import linecache
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
LEARNER_FILE='exercise.py'
VALUE='_workshop_value'
MISMATCH='The result did not match this requirement. Try a hint or inspect your output.'
RETURNED_NONE='Your function returned None. `print` shows a value but does not return it. Use `return`.'

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

def shown(value):
    """repr, cut to about 200 characters."""
    try:text=repr(value)
    except Exception:text=f'<{type(value).__name__} object>'
    return text if len(text)<=200 else text[:199]+'…'

def learner_only(exc):
    """A TracebackException with only the learner's frames: no runner frames or install paths."""
    report=traceback.TracebackException.from_exception(exc)
    pending,seen=[report],set()
    while pending:
        item=pending.pop()
        if item is None or id(item) in seen:continue
        seen.add(id(item))
        item.stack=traceback.StackSummary.from_list([f for f in item.stack if f.filename==LEARNER_FILE])
        pending+=[item.__cause__,item.__context__,*(item.exceptions or [])]
    return report

def error_line(report):
    """'Line 2: NameError: ...' for the learner's line closest to the error."""
    message=next((l for l in report.format_exception_only() if not l[:1].isspace()),'').strip().split('\n')[0]
    line=report.lineno if getattr(report,'filename',None)==LEARNER_FILE else report.stack[-1].lineno if report.stack else None
    return (f'Line {line}: ' if line else '')+message

def instrument(expr):
    """Wrap the learner's value and the expected value of a simple check so a failure can show both.

    Shapes: `a == b`, `a is True`, `abs(a - b) < tol` and `raises(Error, lambda: a)`. The wrapper
    returns its argument unchanged, so the check passes or fails exactly as the plain expression.
    """
    try:tree=ast.parse(expr,mode='eval')
    except SyntaxError:return None
    def value(key,node):return ast.Call(ast.Name(VALUE,ast.Load()),[ast.Constant(key),node],[])
    body=tree.body
    if isinstance(body,ast.Compare) and len(body.ops)==1:
        op,left,right=body.ops[0],body.left,body.comparators[0]
        if isinstance(op,ast.Eq) or isinstance(op,ast.Is) and isinstance(right,ast.Constant):
            got,want=(right,left) if isinstance(left,ast.Constant) and not isinstance(right,ast.Constant) else (left,right)
            call=ast.unparse(got)
            if got is left:body.left,body.comparators[0]=value('got',left),value('expected',right)
            else:body.left,body.comparators[0]=value('expected',left),value('got',right)
            shape='equal'
        elif (isinstance(op,(ast.Lt,ast.LtE)) and isinstance(left,ast.Call) and isinstance(left.func,ast.Name)
              and left.func.id=='abs' and len(left.args)==1 and not left.keywords
              and isinstance(left.args[0],ast.BinOp) and isinstance(left.args[0].op,(ast.Sub,ast.Add))):
            difference=left.args[0]
            call=ast.unparse(difference.left)
            difference.left,difference.right=value('got',difference.left),value('expected',difference.right)
            body.comparators[0]=value('tolerance',right)
            shape='near' if isinstance(difference.op,ast.Sub) else 'near-negated'
        else:return None
    elif (isinstance(body,ast.Call) and isinstance(body.func,ast.Name) and body.func.id=='raises'
          and len(body.args)==2 and not body.keywords and isinstance(body.args[1],ast.Lambda)
          and not ast.unparse(body.args[1].args)):
        call=ast.unparse(body.args[1].body)
        body.args[0]=value('expected',body.args[0])
        body.args[1].body=value('got',body.args[1].body)
        shape='raises'
    else:return None
    try:code=compile(ast.fix_missing_locations(tree),'<check>','eval')
    except (SyntaxError,ValueError):return None
    return code,shape,call[:200]

def same_items(got,want):
    try:return list(got)==list(want)
    except Exception:return False

def compared(shape,call,values,exc=None):
    """Fields for a failed check: call, expected, got, and a detail or explanation when they help."""
    if 'expected' not in values:return None
    want=values['expected']
    if shape=='raises':
        name=getattr(want,'__name__',shown(want))
        fields=dict(call=call,expected=f'raises {name}')
        if exc is not None:return fields|dict(got=f'raised {type(exc).__name__}: {exc}'[:400])
        if 'got' not in values:return None
        got=f'returned {shown(values["got"])}'
        return fields|dict(got=got,detail=f'Expected {name}, but the call {got}.')
    if 'got' not in values:return None
    got=values['got']
    if shape=='near-negated':
        try:want=-want
        except Exception:return None
    expected=shown(want)
    if 'tolerance' in values:expected+=f' (within {shown(values["tolerance"])})'
    fields=dict(call=call,expected=expected,got=shown(got),detail=f'Got {shown(got)}, expected {expected}.')
    if got is None and want is not None:
        fields['explanation']=RETURNED_NONE
    elif {type(got),type(want)}=={list,tuple} and same_items(got,want):
        fields['explanation']=(f'The values match, but you returned a {type(got).__name__} and the check expects a '
                               f'{type(want).__name__}.'+(' `return a, b, c` returns a tuple.' if type(want) is tuple else ''))
    return fields

def run_check(check,ns):
    plan=instrument(check['expr'])
    values={}
    def remember(key,value):
        values[key]=value
        return value
    ns[VALUE]=remember
    try:
        if bool(eval(plan[0] if plan else check['expr'],ns)):return dict(passed=True,detail='')
        return dict(passed=False,detail=MISMATCH)|((compared(plan[1],plan[2],values) if plan else None) or {})
    except BaseException as exc:
        if isinstance(exc,ModuleNotFoundError):return dict(passed=False,detail=missing_package(exc))
        result=dict(passed=False,detail=error_line(learner_only(exc))[:1200])
        # For `abs(None - x)`, say the function returned None instead of showing the TypeError.
        if plan and (plan[1]=='raises' or 'got' in values and values['got'] is None):
            result|=compared(plan[1],plan[2],values,exc if plan[1]=='raises' else None) or {}
        return result

def child(request_path, result_path):
    # Bound runaway exercises and output. Deliberately not advertised as isolation
    # from filesystem/network: Python code runs with the local user's privileges.
    apply_limits()
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8',newline='\n')
        sys.stderr.reconfigure(encoding='utf-8',newline='\n')
    request=json.loads(Path(request_path).read_text())
    code=request['code']
    # Tracebacks read source lines from linecache; without this entry they show no code.
    linecache.cache[LEARNER_FILE]=(len(code),None,code.splitlines(True),LEARNER_FILE)
    ns={'__name__':'__main__','raises':raises,'check_torch_step':check_torch_step,'check_tf_step':check_tf_step}
    result={'error':None,'summary':None,'checks':[],'passed':False}
    try:
        exec(compile(code,LEARNER_FILE,'exec'),ns)
        for check in request['checks']:
            result['checks'].append(dict(label=check['label'],**run_check(check,ns)))
        result['passed']=bool(result['checks']) and all(c['passed'] for c in result['checks'])
    except ModuleNotFoundError as exc:
        result['error']=missing_package(exc)
    except BaseException as exc:
        report=learner_only(exc)
        result['error']=''.join(report.format())[-6000:]
        result['summary']=error_line(report)[:600]
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
        add_explanations(data,language)
        return data

def add_explanations(data,language):
    # Imported here: the exercise process runs this file with -I, which leaves backend/ off sys.path.
    from explanations import explain
    data.setdefault('summary',None)
    data['explanation']=explain(data['summary'] or data['error'],language)
    for check in data['checks']:
        text=None if check['passed'] or check.get('explanation') else explain(check.get('detail'),language)
        if text:check['explanation']=text

if __name__=='__main__':
    if sys.argv[1]=='--javascript':javascript_child(*sys.argv[2:5])
    else:child(sys.argv[1],sys.argv[2])
