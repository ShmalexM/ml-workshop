"""Original, reusable engineering exercises with deterministic local checks."""
from textwrap import dedent

COURSES_ENGINEERING = [
    dict(id='harness',title='Agent harness engineering',subtitle='State, tools, budgets and evaluation',icon='workflow',color='green'),
    dict(id='backend',title='Backend & API engineering',subtitle='Contracts, idempotency and pagination',icon='server',color='blue'),
    dict(id='web',title='Web app engineering',subtitle='JavaScript state, async results and data flow',icon='code',color='orange'),
    dict(id='rl',title='Reinforcement learning',subtitle='Environment steps, returns and value updates',icon='gamepad',color='green'),
    dict(id='data',title='Data & retrieval engineering',subtitle='Ingestion, chunks, graphs and evaluation',icon='database',color='blue'),
    dict(id='reliability',title='Shipping & reliability',subtitle='Retries, telemetry and release decisions',icon='activity',color='orange'),
    dict(id='interactive',title='Interactive & native systems',subtitle='Lifecycle, time, coordinates and media',icon='monitor',color='green'),
]
LESSONS_ENGINEERING=[]
REFS={
 'harness':('Python state machines and enums','https://docs.python.org/3/library/enum.html'),
 'backend':('HTTP request semantics','https://www.rfc-editor.org/rfc/rfc9110.html'),
 'web':('React: extracting state logic into a reducer','https://react.dev/learn/extracting-state-logic-into-a-reducer'),
 'rl':('Gymnasium: handling time limits','https://gymnasium.farama.org/tutorials/gymnasium_basics/handling_time_limits/'),
 'data':('Python collections','https://docs.python.org/3/library/collections.html'),
 'reliability':('OpenTelemetry concepts','https://opentelemetry.io/docs/concepts/'),
 'interactive':('MDN: animation frames','https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame'),
}
def add(course,n,title,intro,concept,explanation,tasks,hints,starter,solution,checks,diagram,tip,minutes=15):
    name,url=REFS[course]
    LESSONS_ENGINEERING.append(dict(id=f'{course}-{n}',course=course,title=title,intro=intro,concept=concept,explanation=explanation,tasks=tasks,tip=tip,hints=hints,starter=dedent(starter).strip()+'\n',solution=dedent(solution).strip()+'\n',checks=[dict(label=l,expr=e) for l,e in checks],diagram=diagram,minutes=minutes,xp=150 if n==4 else 100,language='javascript' if course=='web' else 'python',reference=dict(title=name,url=url)))

add('harness',1,'Make the agent loop explicit',
'An agent harness decides what may happen next. A model proposes actions; the harness owns state transitions, stopping rules and execution.\n\nModel a small run before connecting any model or tool.',
'current state + event → next state',
'Our run starts idle, becomes running after start, and can wait for approval. Only approve resumes a waiting run. A completed run cannot restart through an accidental event. A transition table makes these rules reviewable and testable without an LLM.',
['Implement transition(state, event).','Support idle/start→running; running/ask→waiting; waiting/approve→running; running/finish→done.','Reject every other pair with ValueError.'],
['Use a dictionary keyed by (state, event).','Check that the pair is present before returning a value.','Terminal states have no outgoing transitions in this exercise.'],
'def transition(state, event):\n    return None\n\nprint(transition("idle", "start"))',
'''def transition(state, event):
    table={('idle','start'):'running',('running','ask'):'waiting',('waiting','approve'):'running',('running','finish'):'done'}
    if (state,event) not in table: raise ValueError('Invalid transition')
    return table[state,event]
''',
[('Starts the run','transition("idle","start")=="running"'),('Waits and resumes','transition(transition("running","ask"),"approve")=="running"'),('Stops at completion','transition("running","finish")=="done"'),('Rejects a restart after completion','raises(ValueError,lambda:transition("done","start"))')],['Event','Transition rules','New state'],
'Keep orchestration state outside the model response.')
add('harness',2,'Give a tool only its allowed inputs',
'A tool call is an API boundary. A model-generated dictionary may contain unsupported fields, miss required fields, or name a tool that does not exist. Validate that boundary before dispatch.',
'proposal → schema validation → dispatch',
'The schema in this exercise maps each tool to its required argument names. We deliberately support exact keys only. Real systems also validate value types, identity, authorization and quotas; an argument allowlist does not establish permission by itself.',
['Implement validate_call(name, args, schemas).','Accept only known tools with exactly the declared argument keys.','Return a copy of args; reject everything else with ValueError.'],
['Find the expected keys for name.','Compare sets of argument keys, not the order they arrived.','Return dict(args) so callers cannot mutate the original through the returned mapping.'],
'def validate_call(name, args, schemas):\n    return None',
'''def validate_call(name, args, schemas):
    if name not in schemas or not isinstance(args,dict) or set(args)!=set(schemas[name]):
        raise ValueError('Invalid tool call')
    return dict(args)
''',
[('Accepts a declared call','validate_call("lookup",{"id":3},{"lookup":["id"]})=={"id":3}'),('Rejects hidden extra arguments','raises(ValueError,lambda:validate_call("lookup",{"id":3,"shell":"x"},{"lookup":["id"]}))'),('Rejects unknown tools','raises(ValueError,lambda:validate_call("unknown",{},{}))'),('Rejects missing arguments','raises(ValueError,lambda:validate_call("lookup",{},{"lookup":["id"]}))')],['Tool proposal','Check contract','Allowed arguments'],
'Validation is separate from authorization. Test both boundaries in a real harness.')
add('harness',3,'Stop before the budget is exhausted',
'An agent loop needs a finite budget even when each individual step works. Reserve enough capacity for the next operation before starting it.',
'allow when steps < max_steps and spent + next_cost ≤ budget',
'This toy budget uses integer units to avoid floating-point accounting. The step limit counts completed steps, so a run with steps equal to max_steps must stop. An exactly affordable operation is allowed. Negative accounting values are invalid rather than free credit.',
['Implement can_step(steps, max_steps, spent, next_cost, budget).','Return whether both the step and cost constraints allow the next operation.','Reject negative values with ValueError.'],
['Validate all five values before comparing them.','The step comparison is strict; the cost comparison is inclusive.','Combine the two comparisons with and.'],
'def can_step(steps, max_steps, spent, next_cost, budget):\n    return None',
'''def can_step(steps, max_steps, spent, next_cost, budget):
    if min(steps,max_steps,spent,next_cost,budget)<0: raise ValueError('Negative budget value')
    return steps<max_steps and spent+next_cost<=budget
''',
[('Allows exact cost boundary','can_step(2,3,8,2,10) is True'),('Stops at the step boundary','can_step(3,3,0,1,10) is False'),('Rejects unaffordable work','can_step(0,5,8,3,10) is False'),('Rejects invalid accounting','raises(ValueError,lambda:can_step(0,5,0,-1,10))')],['Remaining budget','Reserve next step','Run or stop'],
'A timeout, a step limit and a spend limit protect different resources.')
add('harness',4,'Score a run from its trace',
'Final text can claim success even when a required tool was never called. Evaluate observed behavior from the run trace and an independent expected outcome.',
'success = required successful tools + expected final answer',
'Events have kind tool or final. Tool events include name and ok. Final events include answer. Use the last final event and require every named tool to have at least one successful result. This is an offline acceptance rule, not a universal measure of reasoning quality.',
['Implement score_trace(events, required_tools, expected).','Require successful tool events for all required tools.','Return True only if the last final answer also equals expected.'],
['Collect names of events whose kind is tool and ok is True.','Gather final answers in event order.','Use set(required_tools).issubset(successes) and check the last final.'],
'def score_trace(events, required_tools, expected):\n    return None',
'''def score_trace(events, required_tools, expected):
    successful={e.get('name') for e in events if e.get('kind')=='tool' and e.get('ok') is True}
    finals=[e.get('answer') for e in events if e.get('kind')=='final']
    return bool(finals) and finals[-1]==expected and set(required_tools)<=successful
''',
[('Accepts observed success','score_trace([{"kind":"tool","name":"read","ok":True},{"kind":"final","answer":"ok"}],["read"],"ok") is True'),('Rejects a claim without tool evidence','score_trace([{"kind":"final","answer":"ok"}],["read"],"ok") is False'),('Uses the last final answer','score_trace([{"kind":"final","answer":"ok"},{"kind":"final","answer":"wrong"}],[],"ok") is False'),('No final event is incomplete','score_trace([],[],"ok") is False')],['Run trace','Acceptance rules','Evaluation result'],
'Keep evaluation cases independent from the instructions used to generate the run.',20)

add('backend',1,'Validate a request at the boundary',
'An API should reject malformed input before business logic sees it. Here a task-creation request needs a nonempty title and an integer priority from one to five.',
'untrusted JSON → validated command',
'Python considers bool a subclass of int. A strict API must therefore use type(value) is int when booleans are not valid priorities. Normalize the title by stripping whitespace; return only fields the endpoint accepts.',
['Implement parse_task(payload).','Require a string title that is nonempty after stripping and priority 1–5 (default 3).','Return title and priority; reject invalid payloads with ValueError.'],
['Check that payload is a dict and title is a string.','Use type(priority) is int to reject True.','Build a fresh result instead of returning the unvalidated request.'],
'def parse_task(payload):\n    return None',
'''def parse_task(payload):
    if not isinstance(payload,dict): raise ValueError('Expected object')
    title=payload.get('title');priority=payload.get('priority',3)
    if not isinstance(title,str) or not title.strip() or type(priority) is not int or not 1<=priority<=5:
        raise ValueError('Invalid task')
    return {'title':title.strip(),'priority':priority}
''',
[('Normalizes and defaults','parse_task({"title":"  test  "})=={"title":"test","priority":3}'),('Rejects blank titles','raises(ValueError,lambda:parse_task({"title":" "}))'),('Rejects bool as integer','raises(ValueError,lambda:parse_task({"title":"x","priority":True}))'),('Drops unrelated fields','parse_task({"title":"x","priority":5,"admin":True})=={"title":"x","priority":5}')],['Request','Validate & normalize','Command'],
'A successful parse does not grant access to someone else’s task.')
add('backend',2,'Make retries idempotent',
'A client may retry after a response is lost. If the server already handled the request, running it again can duplicate a job or charge. Bind an idempotency key to both the request and its result.',
'same key + same payload → same result',
'Implement an in-memory model: store[key] contains payload and result. Repeating a matching payload returns the original result, while reusing a key for a different payload raises ValueError. A production database also needs an atomic claim and a defined retention policy.',
['Implement remember(store, key, payload, result).','Return the original result for a matching retry; reject conflicting payloads.','Save a deep copy on first use so later caller mutation cannot change the record.'],
['Check for an existing record before writing.','Compare the stored payload to the new payload.','Use copy.deepcopy when storing a new request and result.'],
'import copy\n\ndef remember(store, key, payload, result):\n    return None',
'''import copy

def remember(store, key, payload, result):
    if key in store:
        if store[key]['payload']!=payload: raise ValueError('Conflicting idempotency key')
        return copy.deepcopy(store[key]['result'])
    store[key]=copy.deepcopy({'payload':payload,'result':result})
    return copy.deepcopy(result)
''',
[('Stores the first result','(lambda s: remember(s,"a",{"x":1},7)==7 and "a" in s)({})'),('Retry returns old result','remember({"a":{"payload":{"x":1},"result":7}},"a",{"x":1},99)==7'),('Conflicting request is rejected','raises(ValueError,lambda:remember({"a":{"payload":1,"result":7}},"a",2,9))'),('Nested request is copied','(lambda s,p: (remember(s,"a",p,7),p["x"].append(2),s["a"]["payload"]["x"]==[1])[-1])({}, {"x":[1]})')],['Request key','Find or claim','Stable result'],
'This in-memory exercise models the contract; it does not implement distributed locking.')
add('backend',3,'Page through a stable cursor',
'Offset pagination can skip or repeat rows when new rows arrive before the current offset. A cursor based on a stable unique ordering can avoid that class of shift.',
'filter id > cursor → sort → take limit',
'Rows have unique integer IDs. Return the rows whose IDs are greater than after, ordered ascending and limited to limit. The next cursor is the last returned ID only when more matching rows remain. None means there is no further page.',
['Implement page_after(rows, after, limit), returning (items, next_cursor).','Use ascending unique IDs and do not mutate rows.','Reject nonpositive limits with ValueError.'],
['Filter and sort into a new list.','Compare the total matching count to limit.','Only return the last selected ID as cursor if another row remains.'],
'def page_after(rows, after, limit):\n    return None',
'''def page_after(rows, after, limit):
    if limit<=0: raise ValueError('Positive limit required')
    remaining=sorted((r for r in rows if r['id']>after),key=lambda r:r['id'])
    selected=remaining[:limit]
    return selected,selected[-1]['id'] if len(remaining)>limit else None
''',
[('Sorts and exposes next cursor','page_after([{"id":4},{"id":2},{"id":3}],1,2)==([{"id":2},{"id":3}],3)'),('Excludes the prior cursor','page_after([{"id":2},{"id":3}],2,9)==([{"id":3}],None)'),('Empty end page','page_after([],0,2)==([],None)'),('Rejects zero page size','raises(ValueError,lambda:page_after([],0,0))')],['Cursor','Ordered query','Page + next cursor'],
'Timestamps alone are often not unique enough: real cursors may need a tie-breaker.')
add('backend',4,'Separate live from ready',
'A process can be alive while unable to serve requests. Readiness should express whether required dependencies are usable; optional failures should be visible without necessarily taking the service offline.',
'ready = every required dependency is healthy',
'Dependency records contain name, required and healthy. Return ready plus a sorted degraded list containing all unhealthy dependencies. An empty dependency list is ready. The result can power an HTTP readiness endpoint and a human-readable status panel.',
['Implement readiness(dependencies).','Set ready False if any required dependency is unhealthy.','Return all unhealthy names sorted under degraded.'],
['Use all over required dependencies.','Collect failures independently of whether they are required.','Return exactly the two keys ready and degraded.'],
'def readiness(dependencies):\n    return None',
'''def readiness(dependencies):
    return {'ready':all(d['healthy'] for d in dependencies if d['required']),
            'degraded':sorted(d['name'] for d in dependencies if not d['healthy'])}
''',
[('No dependencies is ready','readiness([])=={"ready":True,"degraded":[]}'),('Required failure blocks readiness','readiness([{"name":"db","required":True,"healthy":False}])=={"ready":False,"degraded":["db"]}'),('Optional failure is degraded','readiness([{"name":"search","required":False,"healthy":False}])["ready"] is True'),('Healthy dependencies are not degraded','readiness([{"name":"db","required":True,"healthy":True}])["degraded"]==[]')],['Dependency probes','Readiness policy','Status response'],
'Probe actual dependencies in a real service; this exercise tests the aggregation policy.',18)

add('web',1,'Update UI state without mutation',
'A reducer turns an event into a new UI state. Keeping the update pure makes it easier to replay events, test interactions, and avoid stale references in React.',
'nextState = reducer(previousState, action)',
'The state contains count and label. increment adds action.amount to count. reset makes count zero. Unknown actions return the original object unchanged. Preserve unrelated fields and never mutate the input object. This JavaScript runs in Node; browser rendering is a separate project exercise.',
['Implement counter(state, action).','Handle increment and reset while preserving other fields.','Keep state immutable and return the same reference for unknown actions.'],
['Use object spread to copy state.','Override count after spreading the original fields.','For an unknown type, return state.'],
'function counter(state, action) {\n  return null;\n}\n\nconsole.log(counter({count: 1, label: "runs"}, {type: "increment", amount: 2}));',
'''function counter(state, action) {
  if (action.type === 'increment') return {...state, count: state.count + action.amount};
  if (action.type === 'reset') return {...state, count: 0};
  return state;
}''',
[('Increments while preserving fields','equal(counter({count:1,label:"runs"},{type:"increment",amount:2}),{count:3,label:"runs"})'),('Resets','counter({count:8},{type:"reset"}).count===0'),('Does not mutate input','(()=>{const s=Object.freeze({count:2});return counter(s,{type:"increment",amount:1}).count===3&&s.count===2})()'),('Unknown action preserves identity','(()=>{const s={count:4};return counter(s,{type:"other"})===s})()')],['User action','Pure reducer','Render next state'],
'Practice the data transition here, then inspect how your project connects it to components.')
add('web',2,'Ignore an out-of-order response',
'A slow response for an old search can arrive after the result for the current search. Tie each response to the request that produced it.',
'apply result only when response.requestId = state.requestId',
'State contains requestId, status and items. A matching response changes status to ready and copies its items. An older or unrelated response returns state unchanged. In a browser, aborting obsolete fetches saves work, but an identity check still protects state.',
['Implement applyResponse(state, response).','Only apply matching request IDs, and preserve other state fields.','Copy the response items array so external mutation cannot alter saved state.'],
['Check IDs before copying anything.','Return {...state, status: "ready", items: [...response.items]}.','Mismatch must return the original state reference.'],
'function applyResponse(state, response) {\n  return null;\n}',
'''function applyResponse(state, response) {
  if (state.requestId !== response.requestId) return state;
  return {...state, status:'ready', items:[...response.items]};
}''',
[('Accepts current response','equal(applyResponse({requestId:2,status:"loading",query:"a"},{requestId:2,items:[1]}),{requestId:2,status:"ready",query:"a",items:[1]})'),('Ignores an older response','(()=>{const s={requestId:3};return applyResponse(s,{requestId:2,items:[]})===s})()'),('Copies items','(()=>{const r={requestId:1,items:[1]};const n=applyResponse({requestId:1},r);r.items.push(2);return n.items.length===1})()')],['Start request','Receive response','Check identity'],
'Never treat arrival order as request order.')
add('web',3,'Derive a filtered view',
'A dashboard often needs a filtered, sorted list derived from one canonical collection. Store the source data once and derive the visible view from current controls.',
'source rows + filters → visible rows',
'Each row has id, title and priority. Filter titles with a case-insensitive substring query, sort priority descending, then id ascending to make ties deterministic. Return a new array without rearranging the original.',
['Implement visibleRows(rows, query).','Match titles case-insensitively after trimming query.','Sort priority descending and numeric id ascending; preserve the input order.'],
['filter returns a new array.','Normalize query and each title with toLowerCase.','Comparator: b.priority - a.priority || a.id - b.id.'],
'function visibleRows(rows, query) {\n  return [];\n}',
'''function visibleRows(rows, query) {
  const q=query.trim().toLowerCase();
  return rows.filter(r=>r.title.toLowerCase().includes(q)).sort((a,b)=>b.priority-a.priority || a.id-b.id);
}''',
[('Matches case and whitespace','visibleRows([{id:1,title:"GPU work",priority:1},{id:2,title:"API",priority:2}]," gpu ").length===1'),('Breaks ties by ID','equal(visibleRows([{id:2,title:"a",priority:1},{id:1,title:"b",priority:1}],"").map(r=>r.id),[1,2])'),('Sorts by priority first','equal(visibleRows([{id:1,title:"a",priority:1},{id:2,title:"a",priority:3}],"").map(r=>r.id),[2,1])'),('Does not sort the source','(()=>{const rows=[{id:2,title:"b",priority:1},{id:1,title:"a",priority:1}];visibleRows(rows,"");return rows[0].id===2})()')],['Canonical data','Filter + stable order','Visible list'],
'Derived lists should not become a second, drifting source of truth.')
add('web',4,'Migrate saved browser state',
'Local storage outlives deployments. A new UI must understand older saved data and reject malformed data without crashing its startup.',
'parse → recognize version → migrate → validate',
'Version 1 stores a theme under darkMode (boolean). Version 2 stores theme as light or dark. normalizePrefs receives a JSON string and must always return {version:2,theme:...}. Malformed JSON, unknown versions and invalid fields fall back to light. This is a pure function; it does not access browser storage.',
['Implement normalizePrefs(raw).','Convert valid v1 darkMode or valid v2 theme into the v2 shape.','Use the light default for all other input.'],
['Wrap JSON.parse in try/catch.','Check the exact field type before migrating v1.','Do not assume parsed JSON is an object rather than null.'],
'function normalizePrefs(raw) {\n  return null;\n}',
'''function normalizePrefs(raw) {
  let p; try { p=JSON.parse(raw); } catch { p=null; }
  let theme='light';
  if (p && p.version===1 && typeof p.darkMode==='boolean') theme=p.darkMode?'dark':'light';
  if (p && p.version===2 && ['light','dark'].includes(p.theme)) theme=p.theme;
  return {version:2,theme};
}''',
[('Migrates v1','equal(normalizePrefs(\'{"version":1,"darkMode":true}\'),{version:2,theme:"dark"})'),('Reads v2','normalizePrefs(\'{"version":2,"theme":"dark"}\').theme==="dark"'),('Handles broken storage','normalizePrefs("{broken").theme==="light"'),('Rejects unknown and mistyped fields','normalizePrefs(\'{"version":1,"darkMode":"false"}\').theme==="light" && normalizePrefs("null").version===2')],['Stored JSON','Versioned migration','Valid UI preferences'],
'Migration should preserve valid user choices while providing a safe default.',18)

add('rl',1,'Model an environment step',
'An RL environment turns an action into a next observation, reward and stopping signals. Start with a five-cell corridor instead of an emulator so every transition is inspectable.',
'(state, action) → (next_state, reward, terminated, truncated)',
'States are 0–4 and actions are -1 or +1. Movement is clamped to the corridor. Reaching state 4 terminates with reward +1; every other step gives -0.1. An external max_steps cutoff truncates only if the goal was not reached. If already at 4, return (4,0,True,False). steps is the number of moves already taken.',
['Implement env_step(position, action, steps, max_steps).','Move within 0–4, reward the goal, and distinguish termination from truncation.','Return the four-tuple; reject invalid state, action or step bounds.'],
['Compute next_position with min and max.','The current action uses step number steps + 1.','A terminal goal takes precedence over the external cutoff.'],
'def env_step(position, action, steps, max_steps):\n    return None',
'''def env_step(position, action, steps, max_steps):
    if not 0<=position<=4 or action not in (-1,1) or steps<0 or max_steps<1: raise ValueError('Invalid environment input')
    if position==4: return 4,0,True,False
    next_position=max(0,min(4,position+action));terminal=next_position==4
    return next_position,1 if terminal else -.1,terminal,steps+1>=max_steps and not terminal
''',
[('Moves and rewards','env_step(1,1,0,10)==(2,-.1,False,False)'),('Goal terminates, not truncates','env_step(3,1,9,10)==(4,1,True,False)'),('External limit truncates','env_step(1,-1,9,10)==(0,-.1,False,True)'),('Clamps at boundary','env_step(0,-1,0,10)[0]==0'),('Terminal state stays terminal','env_step(4,-1,10,10)==(4,0,True,False)')],['Action','Environment transition','Reward + observation'],
'This toy environment teaches the contract; it does not launch a game or train PPO.')
add('rl',2,'Compute discounted returns',
'An action may lead to rewards much later. A return combines future rewards with a discount factor so a policy can learn from delayed outcomes.',
'G[t] = reward[t] + gamma × G[t+1]',
'For rewards [1,2,3] with gamma=0.5, returns are [2.75,3.5,3]. Work backward so each suffix is computed once. Here the final bootstrap value is zero, appropriate for a complete terminal trajectory; a truncated rollout may need a value estimate instead.',
['Implement returns(rewards, gamma).','Return one discounted return for each reward without mutating rewards.','Accept gamma from 0 through 1; reject values outside that range.'],
['Start with total=0 at the end of the sequence.','Walk rewards in reverse and update total=reward+gamma*total.','Reverse the collected results before returning.'],
'def returns(rewards, gamma):\n    return None',
'''def returns(rewards, gamma):
    if not 0<=gamma<=1: raise ValueError('Invalid discount')
    values=[];total=0
    for reward in reversed(rewards):
        total=reward+gamma*total;values.append(total)
    return list(reversed(values))
''',
[('Propagates delayed rewards','returns([1,2,3],.5)==[2.75,3.5,3]'),('Zero discount is immediate reward','returns([1,-2,3],0)==[1,-2,3]'),('Empty rollout','returns([],1)==[]'),('Rejects invalid gamma','raises(ValueError,lambda:returns([1],1.1))')],['Reward trajectory','Backward accumulation','Training targets'],
'Do not silently use a terminal bootstrap value for an externally truncated rollout.')
add('rl',3,'Balance exploration and exploitation',
'A policy that always chooses its current best action may never discover a better one. Epsilon-greedy chooses a random available action with probability epsilon and the best action otherwise.',
'epsilon chance: explore; otherwise: argmax Q',
'Pass randomness in explicitly so tests remain deterministic: draw is a number in [0,1), and explore_index is a valid action index selected by the caller. Explore when draw < epsilon. Break greedy ties using the first index. This is tabular exploration, not a PPO update.',
['Implement choose_action(values, epsilon, draw, explore_index).','Use the supplied exploration index when draw < epsilon; otherwise choose the first maximum.','Reject empty values or invalid epsilon, draw, and index.'],
['Validate ranges before selecting an action.','Use values.index(max(values)) for deterministic ties.','At draw == epsilon, choose greedily.'],
'def choose_action(values, epsilon, draw, explore_index):\n    return None',
'''def choose_action(values, epsilon, draw, explore_index):
    if not values or not 0<=epsilon<=1 or not 0<=draw<1 or not 0<=explore_index<len(values): raise ValueError('Invalid policy input')
    return explore_index if draw<epsilon else values.index(max(values))
''',
[('Greedy action','choose_action([1,5,2],.1,.5,0)==1'),('Exploration action','choose_action([1,5,2],.5,.1,2)==2'),('Stable tie-breaking','choose_action([4,4,1],0,.9,2)==0'),('Boundary is greedy','choose_action([1,5],.5,.5,0)==1'),('Rejects an empty action space','raises(ValueError,lambda:choose_action([],0,.5,0))')],['Q estimates','Explore or exploit','Selected action'],
'Use independent evaluation runs to assess performance, rather than exploration rewards alone.')
add('rl',4,'Bootstrap only when the task continues',
'A value update should not imagine future reward beyond a true terminal state. An external time limit, however, does not necessarily end the underlying task.',
'Q_new = Q + alpha × (reward + gamma × next_value × not_terminated − Q)',
'Use max(next_values) when not terminated, including a transition marked truncated. When terminated, the target is reward alone and next_values may be empty. The truncated argument documents why a rollout stopped; it does not independently zero the bootstrap. Gymnasium makes this distinction explicit.',
['Implement q_update(old, reward, next_values, alpha, gamma, terminated, truncated).','Use a reward-only target for terminated transitions; bootstrap all others.','Reject alpha/gamma outside [0,1] and missing next values for nonterminal transitions.'],
['Compute target before applying the learning rate.','Check terminated rather than terminated or truncated.','A zero alpha must return old unchanged.'],
'def q_update(old, reward, next_values, alpha, gamma, terminated, truncated):\n    return None',
'''def q_update(old, reward, next_values, alpha, gamma, terminated, truncated):
    if not 0<=alpha<=1 or not 0<=gamma<=1 or (not terminated and not next_values): raise ValueError('Invalid update')
    target=reward if terminated else reward+gamma*max(next_values)
    return old+alpha*(target-old)
''',
[('Bootstraps a normal step','abs(q_update(2,1,[4,3],.5,.9,False,False)-3.3)<1e-9'),('Truncation retains bootstrap','abs(q_update(2,1,[4],.5,.9,False,True)-3.3)<1e-9'),('Termination removes bootstrap','q_update(2,1,[],.5,.9,True,False)==1.5'),('No learning when alpha zero','q_update(8,1,[3],0,.9,False,False)==8'),('Missing continuation value is invalid','raises(ValueError,lambda:q_update(0,1,[],.5,.9,False,True))')],['Transition','Bootstrap decision','Q update'],
'The correct cutoff treatment depends on the task definition, not just wall-clock time.',20)

add('data',1,'Deduplicate an event stream',
'Ingestion often delivers the same event more than once. Choose a stable identity and a deterministic rule for updates before writing into your data store.',
'one event ID → highest revision',
'Events have id and revision. Keep the highest revision for each ID; if revisions tie, keep the first event seen. Return results sorted by ID without mutating the input. This policy handles repeated delivery, but assumes the source defines comparable revisions.',
['Implement latest_events(events).','Keep the event with the greatest revision for each ID, using first-seen tie-breaking.','Return a list ordered by ID.'],
['Maintain a dictionary from ID to the chosen event.','Replace only when revision is strictly greater.','Return chosen records for sorted dictionary keys.'],
'def latest_events(events):\n    return None',
'''def latest_events(events):
    selected={}
    for event in events:
        key=event['id']
        if key not in selected or event['revision']>selected[key]['revision']: selected[key]=event
    return [selected[key] for key in sorted(selected)]
''',
[('Keeps latest revision','latest_events([{"id":"a","revision":2},{"id":"a","revision":1}])==[{"id":"a","revision":2}]'),('Keeps first equal revision','latest_events([{"id":"a","revision":1,"x":1},{"id":"a","revision":1,"x":2}])[0]["x"]==1'),('Orders identities','[e["id"] for e in latest_events([{"id":"z","revision":1},{"id":"a","revision":0}])]==["a","z"]'),('Empty input','latest_events([])==[]')],['Incoming events','Identity + revision','Canonical records'],
'Arrival time and source revision are different ordering signals.')
add('data',2,'Chunk text with bounded overlap',
'Retrieval systems break documents into pieces that fit the model context. Overlap can preserve context across boundaries, but too much overlap wastes storage and ranking slots.',
'stride = chunk size − overlap',
'This exercise operates on a list of tokens supplied by the caller. Return chunks of at most size tokens, overlap adjacent chunks by overlap tokens, and stop as soon as a chunk reaches the end. Do not add a redundant tail chunk wholly contained in the last chunk.',
['Implement chunks(tokens, size, overlap).','Require integer size > 0 and 0 ≤ overlap < size.','Return slices without dropping tokens or emitting redundant tails.'],
['Use a while loop over a start index.','After appending a chunk, stop if start + size reaches the input length.','Otherwise advance by size - overlap.'],
'def chunks(tokens, size, overlap):\n    return None',
'''def chunks(tokens, size, overlap):
    if type(size) is not int or type(overlap) is not int or size<=0 or not 0<=overlap<size: raise ValueError('Invalid chunk settings')
    result=[];start=0
    while start<len(tokens):
        result.append(tokens[start:start+size])
        if start+size>=len(tokens): break
        start+=size-overlap
    return result
''',
[('Overlaps adjacent chunks','chunks(list(range(7)),4,1)==[[0,1,2,3],[3,4,5,6]]'),('Preserves final partial chunk','chunks([1,2,3,4,5],3,1)==[[1,2,3],[3,4,5]]'),('Empty document','chunks([],3,1)==[]'),('Rejects nonprogressing stride','raises(ValueError,lambda:chunks([1],3,3))')],['Token sequence','Bounded overlap','Retrievable chunks'],
'Keep source IDs and offsets alongside chunks in your project so answers can cite evidence.')
add('data',3,'Traverse a graph without looping',
'Knowledge graphs connect entities, documents and claims. A neighborhood query should have an explicit depth limit and avoid revisiting cycles.',
'frontier → unseen neighbors → next frontier',
'Implement breadth-first reachability from start through at most depth edges. The graph maps each node to a list of outgoing neighbors. Include start and return sorted unique nodes. Missing nodes have no outgoing neighbors; cycles must terminate.',
['Implement neighborhood(graph, start, depth).','Include nodes reachable within depth directed edges, including start.','Reject negative depth and return sorted unique IDs.'],
['Track seen nodes and a frontier set.','Expand the frontier once per depth step.','Subtract seen from newly found neighbors.'],
'def neighborhood(graph, start, depth):\n    return None',
'''def neighborhood(graph, start, depth):
    if depth<0: raise ValueError('Negative depth')
    seen={start};frontier={start}
    for _ in range(depth):
        frontier={n for node in frontier for n in graph.get(node,[])}-seen
        seen.update(frontier)
    return sorted(seen)
''',
[('Respects one-hop boundary','neighborhood({"a":["b"],"b":["c"]},"a",1)==["a","b"]'),('Terminates cycles','neighborhood({"a":["b"],"b":["a","c"]},"a",9)==["a","b","c"]'),('Zero depth includes only start','neighborhood({"a":["b"]},"a",0)==["a"]'),('Missing node is still an observation','neighborhood({},"x",3)==["x"]')],['Starting node','Bounded graph walk','Relevant neighborhood'],
'Reachability is not evidence that an entity or relationship is correct.')
add('data',4,'Measure retrieval coverage',
'A retrieval system needs an evaluation set, not just convincing examples. Recall at k asks what fraction of known relevant documents appear in the first k results.',
'recall@k = unique relevant hits in top k / all relevant IDs',
'Results are ranked document IDs and relevant is a set of expected IDs. Duplicate results consume ranking slots but count only once as hits. Return 0 when no relevant IDs are provided; in real reporting, mark such queries separately so they do not distort aggregate quality.',
['Implement recall_at_k(ranked, relevant, k).','Count unique relevant hits among the first k positions.','Return 0 for empty relevance and reject negative k.'],
['Slice before converting the ranked results into a set.','Intersect top-k IDs with the relevant set.','Divide by the number of unique relevant IDs.'],
'def recall_at_k(ranked, relevant, k):\n    return None',
'''def recall_at_k(ranked, relevant, k):
    if k<0: raise ValueError('Negative cutoff')
    relevant=set(relevant)
    return len(set(ranked[:k]) & relevant)/len(relevant) if relevant else 0.0
''',
[('Counts top-k relevant hits','recall_at_k(["a","x","b"],{"a","b"},2)==.5'),('Duplicates do not inflate recall','recall_at_k(["a","a","b"],{"a","b"},2)==.5'),('No relevance is defined as zero','recall_at_k(["a"],set(),3)==0'),('Zero cutoff','recall_at_k(["a"],{"a"},0)==0')],['Ranked results','Ground-truth relevance','Recall at k'],
'Recall does not measure ordering quality or whether the generated answer is supported.',18)

add('reliability',1,'Bound exponential retries',
'Retrying transient failures can improve availability. Unbounded retries can amplify an outage. Build a bounded schedule before adding jitter and a clock.',
'delay[n] = min(cap, base × 2ⁿ)',
'Return at most attempts delays, but stop before their cumulative sum would exceed budget. Values are nonnegative integer time units; base and cap must be positive. An exactly affordable delay is allowed. Production callers should also honor retryability, cancellation and server Retry-After signals.',
['Implement retry_delays(base, cap, attempts, budget).','Use exponential delay with a per-delay cap and total budget.','Stop before exceeding budget and reject invalid negative or zero settings.'],
['Track spent time and the next delay.','Append only if spent + delay <= budget.','Double the delay with a cap for the next iteration.'],
'def retry_delays(base, cap, attempts, budget):\n    return None',
'''def retry_delays(base, cap, attempts, budget):
    if base<=0 or cap<=0 or attempts<0 or budget<0: raise ValueError('Invalid retry settings')
    result=[];spent=0;delay=min(base,cap)
    for _ in range(attempts):
        if spent+delay>budget: break
        result.append(delay);spent+=delay;delay=min(cap,delay*2)
    return result
''',
[('Exponential with cap','retry_delays(1,4,5,20)==[1,2,4,4,4]'),('Stops at total budget','retry_delays(1,9,5,6)==[1,2]'),('Exact boundary allowed','retry_delays(2,8,3,6)==[2,4]'),('Zero attempts','retry_delays(1,8,0,9)==[]')],['Transient failure','Retry budget','Delay or stop'],
'This tests scheduling arithmetic only; it never sleeps or calls a service.')
add('reliability',2,'Redact structured telemetry',
'Logs are useful only if they are safe to inspect. Sensitive values can appear inside nested lists and dictionaries, not only at the top level.',
'structured data → recursive redaction → loggable copy',
'Replace values whose case-insensitive key is token, password or api_key with [REDACTED]. Recursively preserve all other dictionary and list content. Return new containers and leave input unchanged. This key-based policy is illustrative: arbitrary free text can still contain secrets.',
['Implement redact(value).','Walk nested dictionaries and lists, redacting the three sensitive key names.','Preserve scalar values and avoid modifying the original.'],
['Handle dict, list and scalar cases separately.','Normalize a key only for comparison, preserving its spelling in the result.','Build fresh dicts and lists recursively.'],
'def redact(value):\n    return None',
'''def redact(value):
    if isinstance(value,dict):
        return {k:'[REDACTED]' if str(k).lower() in {'token','password','api_key'} else redact(v) for k,v in value.items()}
    if isinstance(value,list): return [redact(v) for v in value]
    return value
''',
[('Redacts nested credentials','redact({"nested":[{"TOKEN":"secret"}]})=={"nested":[{"TOKEN":"[REDACTED]"}]}'),('Preserves ordinary data','redact({"count":3,"ok":True})=={"count":3,"ok":True}'),('Does not mutate source','(lambda x: (redact(x),x["password"]=="secret")[-1])({"password":"secret"})'),('Preserves scalars','redact(None) is None')],['Telemetry object','Redaction rules','Diagnostic event'],
'Prefer allowlisted telemetry fields; redaction is a second line of defense.')
add('reliability',3,'Plan a deployment as a diff',
'A deployment plan should describe intended changes before applying them. Comparing desired configuration to observed configuration makes repeated runs understandable.',
'desired state − observed state → change plan',
'Both inputs map service names to version strings. Return sorted create, update and remove lists. A service is updated only if present in both and its version differs. This function is read-only: it neither deploys nor deletes anything.',
['Implement deploy_plan(current, desired).','Classify service names into create, update and remove.','Return sorted lists and preserve both inputs.'],
['Compare sets of keys for additions and removals.','Intersect the keys before comparing versions.','Stable ordering makes plans easier to review.'],
'def deploy_plan(current, desired):\n    return None',
'''def deploy_plan(current, desired):
    old=set(current);new=set(desired)
    return {'create':sorted(new-old),'update':sorted(k for k in old&new if current[k]!=desired[k]),'remove':sorted(old-new)}
''',
[('Classifies differences','deploy_plan({"api":"1","old":"1"},{"api":"2","worker":"1"})=={"create":["worker"],"update":["api"],"remove":["old"]}'),('No-op on identical state','deploy_plan({"api":"1"},{"api":"1"})=={"create":[],"update":[],"remove":[]}'),('Sorted additions','deploy_plan({},{"z":"1","a":"1"})["create"]==["a","z"]')],['Observed + desired','Compute diff','Reviewable plan'],
'Applying the plan is a separate, authorized operation with rollback and health checks.')
add('reliability',4,'Gate a release on measured signals',
'A release should satisfy explicit acceptance criteria. Combine success rate and tail latency, and fail closed when no measurements are available.',
'pass = success_rate ≥ target and nearest-rank p95 ≤ latency budget',
'Each sample has ok and latency_ms. Compute success rate across all attempts, and p95 across successful attempts only. Nearest-rank p95 uses sorted_successes[ceil(0.95*n)-1]. Return False for no samples or no successes. These defaults intentionally expose failures rather than inventing latency for them.',
['Implement release_passes(samples, min_success_rate, max_p95).','Measure success rate and successful-request p95 using nearest rank.','Use inclusive thresholds; return False when required measurements are absent.'],
['Use math.ceil to choose the percentile index.','Count success over all samples, not just successful ones.','Check that the success list is nonempty before indexing.'],
'import math\n\ndef release_passes(samples, min_success_rate, max_p95):\n    return None',
'''import math

def release_passes(samples, min_success_rate, max_p95):
    if not samples: return False
    successful=sorted(s['latency_ms'] for s in samples if s['ok'])
    if not successful: return False
    p95=successful[math.ceil(.95*len(successful))-1]
    return len(successful)/len(samples)>=min_success_rate and p95<=max_p95
''',
[('Passes inclusive thresholds','release_passes([{"ok":True,"latency_ms":100}],1,100) is True'),('Rejects too many failures','release_passes([{"ok":True,"latency_ms":10},{"ok":False,"latency_ms":1}],.9,100) is False'),('Rejects tail regression','release_passes([{"ok":True,"latency_ms":10},{"ok":True,"latency_ms":500}],1,100) is False'),('Missing evidence fails closed','release_passes([],1,100) is False'),('All failures fail closed','release_passes([{"ok":False,"latency_ms":1}],0,100) is False')],['Test samples','Success + tail latency','Release decision'],
'This checks a fixture-defined gate; production readiness also needs representative load and recovery tests.',20)

add('interactive',1,'Make app lifecycle transitions explicit',
'A mobile or desktop app must release activity when it goes to the background and restore it predictably. Model the lifecycle independently from a framework before wiring platform callbacks.',
'app state + lifecycle event → new app state',
'Support stopped/open→active, active/background→paused, paused/resume→active, and active/close or paused/close→stopped. Unknown transitions return the same state. Actual timers, subscriptions and camera sessions belong in the effects attached to these transitions.',
['Implement lifecycle(state, event).','Apply the five specified transitions.','Ignore unknown pairs without modifying external state.'],
['Use (state,event) tuples as dictionary keys.','Dictionary.get can return state as the fallback.','A repeated background event should remain paused.'],
'def lifecycle(state, event):\n    return None',
'''def lifecycle(state, event):
    return {('stopped','open'):'active',('active','background'):'paused',('paused','resume'):'active',('active','close'):'stopped',('paused','close'):'stopped'}.get((state,event),state)
''',
[('Launches active','lifecycle("stopped","open")=="active"'),('Pauses and resumes','lifecycle(lifecycle("active","background"),"resume")=="active"'),('Closes from background','lifecycle("paused","close")=="stopped"'),('Repeated events are harmless','lifecycle("paused","background")=="paused"')],['Platform event','Lifecycle transition','Resource effects'],
'The exercise models the lifecycle in Python; apply it to SwiftUI, Flutter or browser callbacks in your project.')
add('interactive',2,'Use time, not frame count',
'Animation and simulation speed should not depend on display refresh rate. Advance position using elapsed seconds and clamp unexpectedly large frame gaps.',
'position_next = position + velocity × min(delta_time, max_delta)',
'Implement one-dimensional movement inside [low,high]. Negative delta time is invalid. Clamp elapsed time to max_delta, then clamp the resulting position to the bounds. The clamp avoids huge jumps after the app resumes, but deliberately drops elapsed simulation time.',
['Implement advance(position, velocity, delta_time, max_delta, low, high).','Use elapsed time with a maximum step, then clamp position to the range.','Reject negative times, negative max_delta or low > high.'],
['Validate before doing arithmetic.','Compute velocity times the clamped elapsed duration.','Use min(high,max(low,candidate)).'],
'def advance(position, velocity, delta_time, max_delta, low, high):\n    return None',
'''def advance(position, velocity, delta_time, max_delta, low, high):
    if delta_time<0 or max_delta<0 or low>high: raise ValueError('Invalid time or bounds')
    return min(high,max(low,position+velocity*min(delta_time,max_delta)))
''',
[('Time-scaled movement','advance(0,10,.1,.2,0,100)==1'),('Caps long resume gaps','advance(0,10,5,.2,0,100)==2'),('Clamps at both edges','advance(9,20,1,1,0,10)==10 and advance(1,-20,1,1,0,10)==0'),('Rejects negative elapsed time','raises(ValueError,lambda:advance(0,1,-1,1,0,10))')],['Elapsed time','Bounded update','Next position'],
'A fixed-step accumulator is a different policy when preserving every simulated tick matters.')
add('interactive',3,'Fit media without changing its shape',
'An image or video preview should preserve its aspect ratio. Fit it inside the available area and center the unused space rather than stretching its axes independently.',
'scale = min(box_width / width, box_height / height)',
'Return (display_width, display_height, offset_x, offset_y). The offsets center the fitted media inside its container. Positive dimensions are required. This changes display geometry only; the original image bytes and resolution stay untouched.',
['Implement fit_media(width, height, box_width, box_height).','Use one uniform scale for both dimensions.','Return centered geometry and reject zero or negative dimensions.'],
['Compute both possible scale factors and take their minimum.','Multiply both original dimensions by that same scale.','Offsets are half the remaining width and height.'],
'def fit_media(width, height, box_width, box_height):\n    return None',
'''def fit_media(width, height, box_width, box_height):
    if min(width,height,box_width,box_height)<=0: raise ValueError('Positive dimensions required')
    scale=min(box_width/width,box_height/height);w=width*scale;h=height*scale
    return w,h,(box_width-w)/2,(box_height-h)/2
''',
[('Landscape letterbox','fit_media(200,100,100,100)==(100,50,0,25)'),('Portrait pillarbox','fit_media(100,200,100,100)==(50,100,25,0)'),('Matching aspect ratio','fit_media(200,100,400,200)==(400,200,0,0)'),('Rejects impossible dimensions','raises(ValueError,lambda:fit_media(0,100,100,100))')],['Source dimensions','Uniform scale','Centered preview'],
'Enlarging a raster display does not create additional image detail.')
add('interactive',4,'Merge progress without duplicate rewards',
'Offline applications may replay the same completion after reconnecting. Keep an event identity so syncing a repeated session does not award its points twice.',
'new state = prior event IDs ∪ incoming event IDs',
'State maps event IDs to earned points. Merge incoming (id,points) pairs, keeping the first value for an ID already present or repeated within the batch. Return a new mapping and its total points. This is a local merge policy; concurrent server writes require their own atomic enforcement.',
['Implement merge_progress(state, events), returning (merged, total).','Award each event ID only once, preserving the first value.','Do not mutate the prior state.'],
['Start from dict(state).','Use setdefault to preserve the first value.','Compute total from the final mapping rather than from the incoming batch.'],
'def merge_progress(state, events):\n    return None',
'''def merge_progress(state, events):
    merged=dict(state)
    for ident,points in events: merged.setdefault(ident,points)
    return merged,sum(merged.values())
''',
[('Awards new completions','merge_progress({},[("a",10),("b",20)])==({"a":10,"b":20},30)'),('Replay does not duplicate','merge_progress({"a":10},[("a",10)])==({"a":10},10)'),('First value wins','merge_progress({},[("a",10),("a",99)])[1]==10'),('Original is unchanged','(lambda s:(merge_progress(s,[("b",5)]),s=={"a":10})[-1])({"a":10})')],['Offline events','Deduplicate by identity','Saved progress'],
'Point totals measure recorded activity; they do not establish mastery.',18)
