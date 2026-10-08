"""Trusted personal-code runner, not an untrusted-code security sandbox."""
import ast
import builtins
import importlib
import json
import linecache
import os
from pathlib import Path
try:
    import resource
except ImportError:  # Windows has no POSIX resource limits.
    resource = None
import secrets
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
IS_NONE='This value is None. Set it to the value that the task asks for.'
# Every exercise process gets this variable with a value unique to the run. With the exercise folder as the
# working folder, it lets cleanup find processes that left the exercise's session (see run_processes).
RUN_MARKER='WORKSHOP_EXERCISE_RUN'
# RLIMIT_NPROC counts all of the user's processes (on Linux, all threads), so the limit is the count when
# the exercise starts plus this many. Lessons that start a few processes or threads stay far below it.
EXTRA_PROCESSES=256
MEMORY_LIMIT=4<<30

def apply_limits():
    if resource is not None and sys.platform != 'win32':
        resource.setrlimit(resource.RLIMIT_CPU,(40,45))
        resource.setrlimit(resource.RLIMIT_FSIZE,(1024*1024,1024*1024))
        limit_processes()
        limit_memory()

def limit_memory():
    """Linux only: cap the exercise's heap and other private writable memory at MEMORY_LIMIT.

    macOS has no memory limit: it refuses RLIMIT_AS and RLIMIT_DATA below the address space that every
    process already reserves, about 400 GB. RLIMIT_AS is not used on Linux: TensorFlow needs more than
    2 GB of address space just to start.
    """
    if not sys.platform.startswith('linux'):return
    hard=resource.getrlimit(resource.RLIMIT_DATA)[1]
    limit=MEMORY_LIMIT if hard==resource.RLIM_INFINITY else min(MEMORY_LIMIT,hard)
    try:resource.setrlimit(resource.RLIMIT_DATA,(limit,limit))
    except (ValueError,OSError):pass

def limit_processes():
    """Stop a fork bomb at EXTRA_PROCESSES more processes than the user had when the exercise started."""
    count=user_process_count()
    if count is None:return
    limit=count+EXTRA_PROCESSES
    for current in resource.getrlimit(resource.RLIMIT_NPROC):
        if current!=resource.RLIM_INFINITY:limit=min(limit,current)
    try:resource.setrlimit(resource.RLIMIT_NPROC,(limit,limit))
    except (ValueError,OSError):pass

# Process lists without psutil: libproc through ctypes on macOS, /proc on Linux. Windows uses taskkill instead.
_PROC_UID_ONLY,_PROC_RUID_ONLY,_PROC_PIDVNODEPATHINFO,_PROC_PIDFDVNODEPATHINFO=4,5,9,2
# struct proc_vnodepathinfo (pvi_cdir.vip_path at 152) and struct vnode_fdinfowithpath (pvip.vip_path at 176).
_CWD_INFO,_CWD_PATH,_FD_INFO,_FD_PATH=2352,152,1200,176
_darwin_libc=None

def _darwin():
    global _darwin_libc
    if _darwin_libc is None:
        import ctypes
        libc=ctypes.CDLL(None,use_errno=True)
        libc.proc_listpids.argtypes=[ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_int]
        libc.proc_pidinfo.argtypes=[ctypes.c_int,ctypes.c_int,ctypes.c_uint64,ctypes.c_void_p,ctypes.c_int]
        libc.proc_pidfdinfo.argtypes=[ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_void_p,ctypes.c_int]
        libc.sysctl.argtypes=[ctypes.POINTER(ctypes.c_int),ctypes.c_uint,ctypes.c_void_p,ctypes.POINTER(ctypes.c_size_t),ctypes.c_void_p,ctypes.c_size_t]
        _darwin_libc=libc
    return _darwin_libc

def _darwin_pids(kind,uid):
    import ctypes
    libc=_darwin()
    size=libc.proc_listpids(kind,uid,None,0)
    if size<=0:raise OSError(ctypes.get_errno(),'Cannot list processes')
    # Room for processes that start between the two calls.
    buffer=(ctypes.c_int*(size//4+64))()
    size=libc.proc_listpids(kind,uid,buffer,ctypes.sizeof(buffer))
    if size<=0:raise OSError(ctypes.get_errno(),'Cannot list processes')
    return [pid for pid in buffer[:size//4] if pid>0]

def _darwin_processes():
    """(pid, paths, environment) for each of this user's live processes. Paths are the working folder and the
    files open as stdout and stderr. macOS leaves out the environment of its own programs, such as sleep and sh."""
    import ctypes
    libc=_darwin()
    folder=ctypes.create_string_buffer(_CWD_INFO);open_file=ctypes.create_string_buffer(_FD_INFO)
    limit=ctypes.c_int();size=ctypes.c_size_t(ctypes.sizeof(limit))
    libc.sysctl((ctypes.c_int*2)(1,8),2,ctypes.byref(limit),ctypes.byref(size),None,0)  # kern.argmax
    arguments=ctypes.create_string_buffer(max(limit.value,1<<20))
    for pid in _darwin_pids(_PROC_UID_ONLY,os.getuid()):
        # Fails for processes that already exited, including zombies.
        if libc.proc_pidinfo(pid,_PROC_PIDVNODEPATHINFO,0,folder,_CWD_INFO)!=_CWD_INFO:continue
        paths=[ctypes.string_at(ctypes.addressof(folder)+_CWD_PATH)]
        for fd in (1,2):
            if libc.proc_pidfdinfo(pid,fd,_PROC_PIDFDVNODEPATHINFO,open_file,_FD_INFO)==_FD_INFO:
                paths.append(ctypes.string_at(ctypes.addressof(open_file)+_FD_PATH))
        # kern.procargs2 holds argc, the executable path, the arguments and then the environment.
        size=ctypes.c_size_t(len(arguments))
        found=libc.sysctl((ctypes.c_int*3)(1,49,pid),3,arguments,ctypes.byref(size),None,0)==0
        yield pid,[os.fsdecode(path) for path in paths],(ctypes.string_at(arguments,size.value) if found else b'')

def _linux_processes():
    for name in os.listdir('/proc'):
        if not name.isdigit():continue
        try:
            # Other users' processes and exited ones raise OSError.
            paths=[os.readlink(f'/proc/{name}/cwd')]
            for fd in (1,2):
                try:paths.append(os.readlink(f'/proc/{name}/fd/{fd}'))
                except OSError:pass
            with open(f'/proc/{name}/environ','rb') as stream:environment=stream.read()
        except OSError:continue
        yield int(name),paths,environment

def run_processes(work,marker):
    """This user's live processes from one exercise run. A process belongs to the run when its working folder
    or its stdout or stderr file is inside `work`, or when its environment holds `marker` (NAME=value).
    Processes inherit all three, and setsid() changes none of them, unlike the process group.

    None on platforms without a process list here. Raises OSError when the list cannot be read.
    """
    work=os.path.realpath(work)
    if sys.platform=='darwin':processes=_darwin_processes()
    elif sys.platform.startswith('linux'):processes=_linux_processes()
    else:return None
    entry=marker.encode()
    found={pid for pid,paths,environment in processes
           if any(path==work or path.startswith(work+os.sep) for path in paths) or entry in environment.split(b'\0')}
    found.discard(os.getpid())
    return found

def user_process_count():
    """The number RLIMIT_NPROC compares with: the user's processes, and on Linux their threads. None if unknown."""
    try:
        if sys.platform=='darwin':return len(_darwin_pids(_PROC_RUID_ONLY,os.getuid()))
        if not sys.platform.startswith('linux'):return None
        uid,total=str(os.getuid()),0
        for name in os.listdir('/proc'):
            if not name.isdigit():continue
            try:
                with open(f'/proc/{name}/status','rb') as stream:lines=stream.read().decode('utf-8','replace').splitlines()
            except OSError:continue
            fields=dict(line.split(':',1) for line in lines if ':' in line)
            if fields.get('Uid','').split()[:1]==[uid]:total+=int(fields.get('Threads','1'))
        return total
    except (OSError,ValueError):
        return None

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

def watched(match, function):
    """Run function() with a profiler on this thread. Returns (the number of profiler events that match(frame,
    event, arg) accepted, what function() returned). A profiler sees every call that Python code makes,
    including calls through a name the learner saved earlier, such as `from builtins import sum as add`."""
    count = 0
    def profile(frame, event, arg):
        nonlocal count
        if match(frame, event, arg): count += 1
    previous = sys.getprofile()
    sys.setprofile(profile)
    try: result = function()
    finally: sys.setprofile(previous)
    return count, result

def calls(name, function):
    """True when function() calls name: a builtin such as "sum", or a path such as "torch.Tensor.backward".

    The profiler finds calls through any name, including one saved before the check ran. The attribute is also
    replaced while function() runs, so that C code that calls it, such as map(sum, rows), is found too."""
    *path, attribute = name.split('.')
    owner = builtins
    if path:
        owner = importlib.import_module(path[0])
        for part in path[1:]: owner = getattr(owner, part)
    original, seen = getattr(owner, attribute), []
    code = getattr(original, '__code__', None)
    def spy(*args, **kwargs):
        seen.append(True)
        return original(*args, **kwargs)
    def match(frame, event, arg):
        return event == 'c_call' and arg is original or event == 'call' and code is not None and frame.f_code is code
    own = attribute in vars(owner)
    setattr(owner, attribute, spy)
    try: count, _ = watched(match, function)
    finally:
        if own: setattr(owner, attribute, original)
        else: delattr(owner, attribute)
    return bool(seen) or count > 0

def launches(kernel, function):
    """(launches, result): how many times function() launched kernel, a @cuda.jit kernel run by the Numba CUDA
    simulator, and what function() returned. A launch counts however the code names the kernel. Anything that is
    not a simulator kernel, such as a plain function, is never launched."""
    code = getattr(getattr(type(kernel), '__call__', None), '__code__', None)
    def match(frame, event, arg):
        return event == 'call' and code is not None and frame.f_code is code and frame.f_locals.get('self') is kernel
    return watched(match, function)

def last_printed(output):
    """The last line the exercise printed, or '' if it printed nothing."""
    sys.stdout.flush()
    sys.stderr.flush()
    try: lines = output.read_text(encoding='utf-8', errors='replace').splitlines()
    except OSError: return ''
    return next((line.strip() for line in reversed(lines) if line.strip()), '')

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

def check_helpers(output):
    """Names a check can use. They are layered over a copy of the learner's names, so learner
    code that reuses a name such as abs, raises or _workshop_value changes neither side."""
    return {**{k: v for k, v in vars(builtins).items() if not k.startswith('_')},
            'raises': raises, 'calls': calls, 'launches': launches, 'last_printed': lambda: last_printed(output),
            'check_torch_step': check_torch_step, 'check_tf_step': check_tf_step}

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
    Returns the code, the shape, the learner's expression, and whether that expression is a call.
    """
    try:tree=ast.parse(expr,mode='eval')
    except SyntaxError:return None
    def value(key,node):return ast.Call(ast.Name(VALUE,ast.Load()),[ast.Constant(key),node],[])
    body=tree.body
    if isinstance(body,ast.Compare) and len(body.ops)==1:
        op,left,right=body.ops[0],body.left,body.comparators[0]
        if isinstance(op,ast.Eq) or isinstance(op,ast.Is) and isinstance(right,ast.Constant):
            got,want=(right,left) if isinstance(left,ast.Constant) and not isinstance(right,ast.Constant) else (left,right)
            call,called=ast.unparse(got),isinstance(got,ast.Call)
            if got is left:body.left,body.comparators[0]=value('got',left),value('expected',right)
            else:body.left,body.comparators[0]=value('expected',left),value('got',right)
            shape='equal'
        elif (isinstance(op,(ast.Lt,ast.LtE)) and isinstance(left,ast.Call) and isinstance(left.func,ast.Name)
              and left.func.id=='abs' and len(left.args)==1 and not left.keywords
              and isinstance(left.args[0],ast.BinOp) and isinstance(left.args[0].op,(ast.Sub,ast.Add))):
            difference=left.args[0]
            call,called=ast.unparse(difference.left),isinstance(difference.left,ast.Call)
            difference.left,difference.right=value('got',difference.left),value('expected',difference.right)
            body.comparators[0]=value('tolerance',right)
            shape='near' if isinstance(difference.op,ast.Sub) else 'near-negated'
        else:return None
    elif (isinstance(body,ast.Call) and isinstance(body.func,ast.Name) and body.func.id=='raises'
          and len(body.args)==2 and not body.keywords and isinstance(body.args[1],ast.Lambda)
          and not ast.unparse(body.args[1].args)):
        call,called=ast.unparse(body.args[1].body),True
        body.args[0]=value('expected',body.args[0])
        body.args[1].body=value('got',body.args[1].body)
        shape='raises'
    else:return None
    try:code=compile(ast.fix_missing_locations(tree),'<check>','eval')
    except (SyntaxError,ValueError):return None
    return code,shape,call[:200],called

def same_items(got,want):
    try:return list(got)==list(want)
    except Exception:return False

def compared(plan,values,exc=None):
    """Fields for a failed check: call, expected, got, and a detail or explanation when they help."""
    _,shape,call,called=plan
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
        # Return advice fits a function call only; a variable that is None needs a value instead.
        fields['explanation']=RETURNED_NONE if called else IS_NONE
    elif {type(got),type(want)}=={list,tuple} and same_items(got,want):
        fields['explanation']=(f'The values match, but you returned a {type(got).__name__} and the check expects a '
                               f'{type(want).__name__}.'+(' `return a, b, c` returns a tuple.' if type(want) is tuple else ''))
    return fields

def run_check(check,ns,helpers):
    plan=instrument(check['expr'])
    values={}
    def remember(key,value):
        values[key]=value
        return value
    # A fresh copy per check: the learner's functions still run in ns, and nothing the check adds stays there.
    scope={**ns,**helpers,VALUE:remember}
    try:
        if bool(eval(plan[0] if plan else check['expr'],scope)):return dict(passed=True,detail='')
        return dict(passed=False,detail=MISMATCH)|((compared(plan,values) if plan else None) or {})
    except BaseException as exc:
        if isinstance(exc,ModuleNotFoundError):return dict(passed=False,detail=missing_package(exc))
        result=dict(passed=False,detail=error_line(learner_only(exc))[:1200])
        # For `abs(None - x)`, say the function returned None instead of showing the TypeError.
        if plan and (plan[1]=='raises' or 'got' in values and values['got'] is None):
            result|=compared(plan,values,exc if plan[1]=='raises' else None) or {}
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
    ns={'__name__':'__main__'}
    # execute() writes the exercise's output to stdout.txt beside the result file.
    helpers=check_helpers(Path(result_path).with_name('stdout.txt'))
    result={'error':None,'summary':None,'checks':[],'passed':False}
    try:
        exec(compile(code,LEARNER_FILE,'exec'),ns)
        for check in request['checks']:
            result['checks'].append(dict(label=check['label'],**run_check(check,ns,helpers)))
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

def cleanup_process(process,work=None,marker=None):
    if sys.platform == 'win32':
        # Windows only: taskkill /T ends the tree by parent PID. The exercise keeps its root process alive
        # until this call (see child and js_runner.cjs), so its children are still linked to it.
        # taskkill reports a nonzero code if the process already exited.
        try:
            subprocess.run(['taskkill','/T','/F','/PID',str(process.pid)],
                           stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
        finally:
            if process.poll() is None:process.kill()
            process.wait()
        return
    # macOS and Linux: the exercise runs in its own session and process group. Kill the group, then
    # every process left from this run, such as a child that called setsid() and outlived its parent.
    try:os.killpg(process.pid,signal.SIGKILL)
    except (ProcessLookupError,PermissionError):pass
    if work is not None:sweep(work,marker)
    process.wait()

def sweep(work,marker,rounds=50):
    """Kill the run's processes until none are left. Each round also catches processes forked during the last one."""
    for _ in range(rounds):
        try:pids=run_processes(work,marker)
        except OSError:return  # The process list is unreadable, for example in a sandbox. The group kill still ran.
        if not pids:return
        for pid in pids:
            # killpg(pid) ends the group this process leads, if any; group IDs are not reused while a group exists.
            for kill in (os.killpg,os.kill):
                try:kill(pid,signal.SIGKILL)
                except (ProcessLookupError,PermissionError):pass
        time.sleep(.02)

def wait_for_result(process,result,timeout):
    if sys.platform != 'win32':
        process.wait(timeout=timeout)
        return
    deadline=time.monotonic()+timeout
    while not result.exists() and process.poll() is None:
        if time.monotonic() >= deadline:
            raise subprocess.TimeoutExpired(process.args,timeout)
        time.sleep(.02)

def read_result(path):
    """The exercise's result.json. On Windows, antivirus scanning can hold the new file for a moment, so retry for 1 second."""
    deadline=time.monotonic()+1
    while True:
        try:return json.loads(path.read_text(encoding='utf-8'))
        except OSError:
            if sys.platform != 'win32' or time.monotonic() >= deadline:raise
            time.sleep(.05)

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
        allowed=('PATH','HOME','LANG','SYSTEMROOT')
        if sys.platform == 'win32':allowed+=('PATHEXT','WINDIR','USERPROFILE')
        env={k:os.environ[k] for k in allowed if k in os.environ}
        env.update(PYTHONUNBUFFERED='1',TF_CPP_MIN_LOG_LEVEL='3',CUDA_VISIBLE_DEVICES='-1',OMP_NUM_THREADS='1',TF_NUM_INTRAOP_THREADS='1',TF_NUM_INTEROP_THREADS='1',TOKENIZERS_PARALLELISM='false',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',MPLBACKEND='Agg',NUMBA_ENABLE_CUDASIM='1' if simulator else '0',PYTORCH_ENABLE_MPS_FALLBACK='1')
        # Temporary files go in the exercise folder, which is deleted after the run.
        env.update(TMPDIR=directory,TEMP=directory,TMP=directory)
        run_id=secrets.token_hex(16);env[RUN_MARKER]=run_id
        timed_out=False
        with output.open('wb') as out:
            args=[sys.executable,'-I','-X','utf8',str(Path(__file__).resolve())]+(['--javascript',node] if node else [])+[str(request),str(result)]
            options=dict(start_new_session=True)
            if sys.platform == 'win32':
                options=dict(creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
                if node:args=[node,str(Path(__file__).with_name('js_runner.cjs')),str(request),str(result)]
            process=subprocess.Popen(args,cwd=work,env=env,stdout=out,stderr=out,**options)
            try:
                wait_for_result(process,result,timeout)
            except subprocess.TimeoutExpired:
                timed_out=True
            finally:
                # Clean up any exercise-created child processes as well, before reading the result.
                cleanup_process(process,work,f'{RUN_MARKER}={run_id}')
        if timed_out:
            data=dict(error=f'Execution stopped after {timeout} seconds. Check for an infinite loop or reduce the workload.',checks=[],passed=False)
        elif result.exists():
            data=read_result(result)
        else:
            data=dict(error=stopped_message(language,process.returncode),checks=[],passed=False)
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
