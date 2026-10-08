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

add('harness',1,'Control the agent loop',
('An agent harness is the software that runs a model’s proposed actions. It keeps track of '
 'the run and decides which actions may happen next. Start with the rules for changing '
 'state.'),
'current state + event → next state',
('A run starts in "idle". The "start" event moves it to "running". From there, "ask" moves '
 'it to "waiting", and "approve" moves it back. From "running", the "finish" event moves '
 'it to "done". A table lists these four allowed pairs, making a missing rule easy to spot.'),
['Create the four transitions: idle/start→running, running/ask→waiting, '
 'waiting/approve→running, and running/finish→done.',
 'Look up the (state, event) pair in transition(state, event).',
 'Return its next state, or raise ValueError for every other pair.'],
['Use a dictionary keyed by the tuple (state, event).',
 'raise stops the function with an error. For example, if age < 0: raise ValueError("age '
 'must not be negative") rejects a negative age. Raise one when the tuple is absent from '
 'the table.',
 'Return table[(state, event)] after checking membership.'],
'''
def transition(state, event):
    # Return the next state or raise ValueError.
    return None

print(transition("idle", "start"))
''',
'''
def transition(state, event):
    table = {
        ("idle", "start"): "running",
        ("running", "ask"): "waiting",
        ("waiting", "approve"): "running",
        ("running", "finish"): "done",
    }
    if (state, event) not in table:
        raise ValueError('Invalid transition')
    return table[(state, event)]
''',
[('Starts the run', 'transition("idle","start")=="running"'),
 ('Waits and resumes', 'transition(transition("running","ask"),"approve")=="running"'),
 ('Stops at completion', 'transition("running","finish")=="done"'),
 ('Rejects a restart after completion',
  'raises(ValueError,lambda:transition("done","start"))'),
 ('Rejects events in the wrong state',
  'raises(ValueError, lambda: transition("idle", "approve")) and raises(ValueError, '
  'lambda: transition("waiting", "finish")) and raises(ValueError, lambda: '
  'transition("waiting", "start"))')],['Event','Transition rules','New state'],
'Test waiting/finish as well as done/start. Both should raise ValueError.')
add('harness',2,'Give a tool only its allowed inputs',
('When a large language model (LLM) calls a tool, it proposes a tool name and a dictionary '
 'of arguments. The proposal can miss required keys, add extra keys, or name an unknown '
 'tool. Check it before running anything.'),
'tool name and arguments → check keys → accepted arguments',
('Suppose "lookup" expects the argument "id". {"id": 3} is accepted, but {"id": 3, '
 '"shell": "x"} has an extra key. Comparing sets of keys catches that difference '
 'regardless of their order. Return a fresh dictionary so changing the result’s keys '
 'leaves the original dictionary unchanged.'),
['Find the required argument names for name in schemas.',
 'Require args to be a dictionary with exactly those keys. Raise ValueError for an unknown '
 'tool or invalid arguments.',
 'Return a shallow copy of args from validate_call(name, args, schemas).'],
['Find the expected keys for name. Compare sets of argument keys, not the order they '
 'arrived.',
 'raise stops the function with an error. For example, if age < 0: raise ValueError("age '
 'must not be negative") rejects a negative age.',
 'Return dict(args) so callers cannot mutate the original through the returned mapping.'],
'''
def validate_call(name, args, schemas):
    # Return a copy of the validated arguments.
    return None

print(validate_call("lookup", {"id": 3}, {"lookup": ["id"]}))
''',
'''
def validate_call(name, args, schemas):
    if name not in schemas or not isinstance(args, dict) or set(args) != set(schemas[name]):
        raise ValueError('Invalid tool call')
    return dict(args)
''',
[('Accepts a declared call',
  'validate_call("lookup",{"id":3},{"lookup":["id"]})=={"id":3}'),
 ('Rejects hidden extra arguments',
  'raises(ValueError,lambda:validate_call("lookup",{"id":3,"shell":"x"},{"lookup":["id"]}))'),
 ('Rejects unknown tools', 'raises(ValueError,lambda:validate_call("unknown",{},{}))'),
 ('Rejects missing arguments',
  'raises(ValueError,lambda:validate_call("lookup",{},{"lookup":["id"]}))'),
 ('Copies the argument dictionary and rejects other input types',
  '(lambda args: (lambda result: result == args and result is not '
  'args)(validate_call("lookup", args, {"lookup": ["id"]})) )({"id": 3}) and '
  'raises(ValueError, lambda: validate_call("lookup", None, {"lookup": ["id"]}))')],['Tool proposal', 'Check argument keys', 'Accepted arguments'],
'Test both a missing key and an extra key. A subset comparison accepts extra keys.')
add('harness',3,'Stop before the budget is exhausted',
('A run can keep taking valid steps forever unless you give it a stopping rule. Check both '
 'the number of completed steps and the cost of the next step before starting more work.'),
'allow when steps < max_steps and spent + next_cost ≤ budget',
('With 2 of 3 steps used, 8 units spent, and a budget of 10, a step costing 2 fits. A step '
 'costing 3 does not. Once 3 steps are complete, the run must stop even if budget remains. '
 'Counting with integer units keeps these comparisons exact.'),
['Reject negative values in steps, max_steps, spent, next_cost, or budget with ValueError.',
 'Check steps < max_steps and spent + next_cost <= budget.',
 'Return a boolean from can_step(steps, max_steps, spent, next_cost, budget).'],
['Validate all five values first. There must be room for one more step and its full cost.',
 'raise stops the function with an error. For example, if not names: raise '
 'ValueError("names is empty") rejects an empty list.',
 'Return steps < max_steps and spent + next_cost <= budget.'],
'''
def can_step(steps, max_steps, spent, next_cost, budget):
    # Return whether one more step fits both limits.
    return None

print(can_step(2, 3, 8, 2, 10))
''',
'''
def can_step(steps, max_steps, spent, next_cost, budget):
    if min(steps, max_steps, spent, next_cost, budget) < 0:
        raise ValueError('Negative budget value')
    return steps < max_steps and spent + next_cost <= budget
''',
[('Allows exact cost boundary','can_step(2,3,8,2,10) is True'),('Stops at the step boundary','can_step(3,3,0,1,10) is False'),('Rejects unaffordable work','can_step(0,5,8,3,10) is False'),('Rejects invalid accounting','raises(ValueError,lambda:can_step(0,5,0,-1,10))')],['Next step cost', 'Check both limits', 'Run or stop'],
('Test equality at each limit. Equal cost is affordable, while equal step count means the '
 'limit is reached.'))
add('harness',4,'Score a run from its trace',
('A final answer can look correct even when the required tool failed. A trace is a list of '
 'recorded events. Check the successful tool events as well as the last final answer.'),
'success = required successful tools + expected final answer',
('A tool event has "kind", "name", and "ok" fields. A final event has "kind" and "answer". '
 'If "read" succeeded and the last final answer is "ok", a run requiring "read" can pass. '
 'Changing that tool event’s "ok" to False makes the same final answer insufficient.'),
['Collect tool names from events whose kind is "tool" and ok is True.',
 'Find the answer in the last event whose kind is "final".',
 'Return True from score_trace only when every required tool succeeded and the last final '
 'answer equals expected. No final event means False.'],
['Build a set named successful from successful tool events.',
 'Build finals from final-event answers in their original order.',
 'Require bool(finals), finals[-1] == expected, and '
 'set(required_tools).issubset(successful).'],
'''
def score_trace(events, required_tools, expected):
    # Return whether the trace meets both success rules.
    return None

sample = [
    {"kind": "tool", "name": "read", "ok": True},
    {"kind": "final", "answer": "ok"},
]
print(score_trace(sample, ["read"], "ok"))
''',
'''
def score_trace(events, required_tools, expected):
    successful = {e.get('name') for e in events if e.get('kind') == 'tool' and e.get('ok') is True}
    finals = [e.get('answer') for e in events if e.get('kind') == 'final']
    return bool(finals) and finals[-1] == expected and set(required_tools).issubset(successful)
''',
[('Accepts observed success',
  'score_trace([{"kind":"tool","name":"read","ok":True},{"kind":"final","answer":"ok"}],["read"],"ok") '
  'is True'),
 ('Rejects a claim without tool evidence',
  'score_trace([{"kind":"final","answer":"ok"}],["read"],"ok") is False'),
 ('Uses the last final answer',
  'score_trace([{"kind":"final","answer":"ok"},{"kind":"final","answer":"wrong"}],[],"ok") '
  'is False'),
 ('No final event is incomplete', 'score_trace([],[],"ok") is False'),
 ('Failed tools do not count as success',
  'score_trace([{"kind": "tool", "name": "read", "ok": False}, {"kind": "final", "answer": '
  '"ok"}], ["read"], "ok") is False')],['Run trace','Acceptance rules','Evaluation result'],
'Include a failed tool event in a test. Seeing its name alone must not count as success.',20)

add('backend',1,'Validate a request at the boundary',
('A request can contain missing fields, wrong types, or extra fields. Validate it before '
 'creating a task. This request needs a nonempty title and an integer priority from 1 to '
 '5.'),
'untrusted JSON → validated command',
('A title of "  test  " becomes "test", and a missing priority defaults to 3. Python '
 'treats bool as a kind of int, so isinstance(True, int) is True. Checking type(priority) '
 'is int rejects that boolean. Build a new result with only the two accepted fields.'),
['Require payload to be a dictionary with a string title that remains nonempty after '
 'stripping whitespace.',
 'Use priority 3 when absent. Otherwise require an integer from 1 to 5, excluding '
 'booleans.',
 'Return {"title": title, "priority": priority} from parse_task(payload). Raise ValueError '
 'for invalid input.'],
['Check the payload and title types before calling strip(). Read priority with '
 'payload.get("priority", 3), then check its exact type and range.',
 'raise stops the function with an error. For example, if age < 0: raise ValueError("age '
 'must not be negative") rejects a negative age.',
 'Return a new dictionary with the stripped title and checked priority.'],
'''
def parse_task(payload):
    # Return a normalized title and priority, or raise ValueError.
    return None

print(parse_task({"title": "  test  "}))
''',
'''
def parse_task(payload):
    if not isinstance(payload, dict):
        raise ValueError('Expected object')
    title = payload.get('title')
    priority = payload.get('priority', 3)
    if (
        not isinstance(title, str)
        or not title.strip()
        or type(priority) is not int
        or not 1 <= priority <= 5
    ):
        raise ValueError('Invalid task')
    return {'title': title.strip(), 'priority': priority}
''',
[('Normalizes and defaults',
  'parse_task({"title":"  test  "})=={"title":"test","priority":3}'),
 ('Rejects blank titles', 'raises(ValueError,lambda:parse_task({"title":" "}))'),
 ('Rejects bool as integer',
  'raises(ValueError,lambda:parse_task({"title":"x","priority":True}))'),
 ('Drops unrelated fields',
  'parse_task({"title":"x","priority":5,"admin":True})=={"title":"x","priority":5}'),
 ('Rejects missing fields and out-of-range priorities',
  'all(raises(ValueError, lambda payload=payload: parse_task(payload)) for payload in '
  '[None, {}, {"title": 7}, {"title": "x", "priority": 0}, {"title": "x", "priority": '
  '6}])')],['Request','Validate & normalize','Command'],
'Test a missing title, a numeric title, and priority True. Each should raise ValueError.')
add('backend',2,'Make retries idempotent',
('A client may retry after a response is lost, even though the server already did the '
 'work. An idempotency key is a unique request ID. Saving the request and result under '
 'that key lets a retry return the same result.'),
'same key + same payload → same result',
('Suppose key "a" stores payload {"x": 1} and result 7. A retry with the same payload '
 'returns 7 even if a new result was supplied. Reusing "a" with {"x": 2} is a conflict. '
 'Deep copies keep later edits to nested input or result objects from changing the saved '
 'record.'),
['Look for key in store before saving anything.',
 'For a matching payload, return a copy of the saved result. Raise ValueError when the '
 'same key has a different payload.',
 'On first use, save deep copies of payload and result, then return a copy of result from '
 'remember(store, key, payload, result).'],
['If key already exists, compare store[key]["payload"] with payload.',
 'For a matching retry, copy store[key]["result"]. A conflict stops the function with '
 'raise. For example, if age < 0: raise ValueError("age must not be negative") rejects a '
 'negative age.',
 'Use copy.deepcopy for the new stored record and every returned result.'],
'''
import copy

def remember(store, key, payload, result):
    # Save or reuse a request and return a copy of its result.
    return None

store = {}
print(remember(store, "a", {"x": 1}, 7))
''',
'''
import copy

def remember(store, key, payload, result):
    if key in store:
        if store[key]['payload'] != payload:
            raise ValueError('Conflicting idempotency key')
        return copy.deepcopy(store[key]['result'])
    store[key] = copy.deepcopy({'payload': payload, 'result': result})
    return copy.deepcopy(result)
''',
[('Stores the first result','(lambda s: remember(s,"a",{"x":1},7)==7 and "a" in s)({})'),('Retry returns old result','remember({"a":{"payload":{"x":1},"result":7}},"a",{"x":1},99)==7'),('Conflicting request is rejected','raises(ValueError,lambda:remember({"a":{"payload":1,"result":7}},"a",2,9))'),('Nested request is copied','(lambda s,p: (remember(s,"a",p,7),p["x"].append(2),s["a"]["payload"]["x"]==[1])[-1])({}, {"x":[1]})')],['Request key','Find or claim','Stable result'],
('Try appending to a nested list after saving it. The list inside store should stay '
 'unchanged.'))
add('backend',3,'Page through a stable cursor',
('Offset paging means "skip 20 rows, take 10". An inserted row before that offset can '
 'cause repeats, while a deleted row can cause skips. A cursor instead asks for rows after '
 'a known ID.'),
'filter id > cursor → sort → take limit',
('For IDs [4, 2, 3], cursor 1, and limit 2, sorting matching rows gives [2, 3, 4]. Return '
 'rows 2 and 3 with next cursor 3 because row 4 remains. If only [2, 3] matched, the same '
 'page would have next cursor None. Copying before sorting preserves the caller’s row '
 'order.'),
['Select rows with id greater than after, then sort a new list by ascending id. IDs are '
 'unique integers.',
 'Return at most limit rows and the last returned ID only if another matching row remains. '
 'Otherwise use None.',
 'Return (items, next_cursor) from page_after(rows, after, limit). Raise ValueError for '
 'limit <= 0 and leave rows unchanged.'],
['Use sorted on the matching rows to leave rows unchanged. Take remaining[:limit].',
 'raise stops the function with an error. For example, if not names: raise '
 'ValueError("names is empty") rejects an empty list.',
 'Compare len(remaining) > limit to see whether another page exists. Set next_cursor to '
 'selected[-1]["id"] only when more rows remain, then return selected, next_cursor.'],
'''
def page_after(rows, after, limit):
    # Return (items, next_cursor).
    return None

print(page_after([{"id": 4}, {"id": 2}, {"id": 3}], after=1, limit=2))
''',
'''
def page_after(rows, after, limit):
    if limit <= 0:
        raise ValueError('Positive limit required')
    remaining = sorted((row for row in rows if row['id'] > after), key=lambda row: row['id'])
    selected = remaining[:limit]
    next_cursor = selected[-1]['id'] if len(remaining) > limit else None
    return (selected, next_cursor)
''',
[('Sorts and exposes next cursor',
  'page_after([{"id":4},{"id":2},{"id":3}],1,2)==([{"id":2},{"id":3}],3)'),
 ('Excludes the prior cursor', 'page_after([{"id":2},{"id":3}],2,9)==([{"id":3}],None)'),
 ('Empty end page', 'page_after([],0,2)==([],None)'),
 ('Rejects zero page size', 'raises(ValueError,lambda:page_after([],0,0))'),
 ('A full last page ends without reordering the input',
  '(lambda rows: page_after(rows, 0, 2) == ([{"id": 1}, {"id": 2}], None) and rows == '
  '[{"id": 2}, {"id": 1}])([{"id": 2}, {"id": 1}])')],['Cursor','Ordered query','Page + next cursor'],
'Test exactly limit matching rows. A full final page should still have next cursor None.')
add('backend',4,'Separate live from ready',
('A process can be running, or "live", while its database is down. Readiness asks whether '
 'it can take traffic now. A failed required dependency blocks traffic. A failed optional '
 'one is reported while traffic continues.'),
'ready = every required dependency is healthy',
('If a required database is healthy and optional search is down, ready is True and '
 'degraded is ["search"]. If the database also fails, ready becomes False and degraded '
 'lists both names. Sorting those names makes the report predictable. With no '
 'dependencies, there is nothing to block readiness.'),
['Read name, required, and healthy from each dependency record.',
 'Set ready to False if any required dependency is unhealthy.',
 'Return {"ready": ready, "degraded": sorted_names} from readiness(dependencies), '
 'including every unhealthy name.'],
['Compute readiness with all over required dependencies only.',
 'Separately collect the names of every unhealthy dependency and sort them.',
 'Return the two keys "ready" and "degraded". all([]) is True.'],
'''
def readiness(dependencies):
    # Return ready and the sorted degraded names.
    return None

print(readiness([{"name": "search", "required": False, "healthy": False}]))
''',
'''
def readiness(dependencies):
    ready = all(item["healthy"] for item in dependencies if item["required"])
    degraded = sorted(item["name"] for item in dependencies if not item["healthy"])
    return {"ready": ready, "degraded": degraded}
''',
[('No dependencies is ready', 'readiness([])=={"ready":True,"degraded":[]}'),
 ('Required failure blocks readiness',
  'readiness([{"name":"db","required":True,"healthy":False}])=={"ready":False,"degraded":["db"]}'),
 ('Optional failure is degraded',
  'readiness([{"name":"search","required":False,"healthy":False}])["ready"] is True'),
 ('Healthy dependencies are not degraded',
  'readiness([{"name":"db","required":True,"healthy":True}])["degraded"]==[]'),
 ('Lists required and optional failures in sorted order',
  'readiness([{"name": "z-db", "required": True, "healthy": False}, {"name": "a-search", '
  '"required": False, "healthy": False}]) == {"ready": False, "degraded": ["a-search", '
  '"z-db"]}')],['Dependency probes','Readiness policy','Status response'],
('Build the failure-name list from all dependencies. Filtering to required dependencies '
 'would hide optional failures.'),18)

add('web',1,'Update UI state without mutation',
('A reducer takes the current state and an action, then returns the next state. A pure '
 'function produces the same result for the same inputs and leaves its inputs unchanged. '
 'Returning new objects lets React detect state changes.'),
'nextState = reducer(previousState, action)',
('From {count: 1, label: "runs"}, an increment action with amount 2 produces {count: 3, '
 'label: "runs"}. Spreading state copies its fields, then overriding count changes just '
 'that value. For an unknown action, return the original object so callers can tell that '
 'nothing changed.'),
['Handle action.type "increment" by adding action.amount to count, and "reset" by setting '
 'count to zero.',
 'Preserve the other fields and leave the input state unchanged.',
 'Return the new state from counter(state, action). For unknown actions, return state '
 'itself.'],
['Use {...state} to copy existing fields.',
 'For increment, return {...state, count: state.count + action.amount}. Reset uses count: '
 '0.',
 'Return state for any action type you did not handle.'],
'''
function counter(state, action) {
  // Return the next state without changing state.
  return null;
}

console.log(counter({count: 1, label: "runs"}, {type: "increment", amount: 2}));
''',
'''
function counter(state, action) {
  if (action.type === "increment") {
    return {...state, count: state.count + action.amount};
  }
  if (action.type === "reset") {
    return {...state, count: 0};
  }
  return state;
}
''',
[('Increments while preserving fields','equal(counter({count:1,label:"runs"},{type:"increment",amount:2}),{count:3,label:"runs"})'),('Resets','counter({count:8},{type:"reset"}).count===0'),('Does not mutate input','(()=>{const s=Object.freeze({count:2});return counter(s,{type:"increment",amount:1}).count===3&&s.count===2})()'),('Unknown action preserves identity','(()=>{const s={count:4};return counter(s,{type:"other"})===s})()')],['User action','Pure reducer','Render next state'],
('Spread state before setting count. Spreading it afterward would overwrite the updated '
 'count.'))
add('web',2,'Ignore an out-of-order response',
'A slow response for an old search can arrive after the result for the current search. Tie each response to the request that produced it.',
'apply result only when response.requestId = state.requestId',
('Suppose the current request ID is 3, but response 2 arrives next. Returning state '
 'unchanged keeps the current search visible. Response 3 can update status to "ready" and '
 'supply new items. Copy its items array so editing the response later cannot edit the '
 'saved state.'),
['Compare response.requestId with state.requestId before changing anything.',
 'For a matching ID, return a new state with status "ready" and a copy of response.items. '
 'Preserve the other fields.',
 'For a different ID, return the original state from applyResponse(state, response).'],
['Check the IDs before copying anything.',
 'If they differ, return state immediately.',
 'For a match, return {...state, status: "ready", items: [...response.items]}.'],
'''
function applyResponse(state, response) {
  // Return the current state or a copy containing the matching response.
  return null;
}

const state = {requestId: 3, status: "loading"};
const response = {requestId: 3, items: ["GPU notes"]};
console.log(applyResponse(state, response));
''',
'''
function applyResponse(state, response) {
  if (state.requestId !== response.requestId) {
    return state;
  }
  return {...state, status: "ready", items: [...response.items]};
}
''',
[('Accepts current response','equal(applyResponse({requestId:2,status:"loading",query:"a"},{requestId:2,items:[1]}),{requestId:2,status:"ready",query:"a",items:[1]})'),('Ignores an older response','(()=>{const s={requestId:3};return applyResponse(s,{requestId:2,items:[]})===s})()'),('Copies items','(()=>{const r={requestId:1,items:[1]};const n=applyResponse({requestId:1},r);r.items.push(2);return n.items.length===1})()')],['Start request','Receive response','Check identity'],
'Never treat arrival order as request order.')
add('web',3,'Derive a filtered view',
('A filtered list should reflect the current search and sort controls. Keep one source '
 'array, then calculate a new visible array when those controls change.'),
'source rows + filters → visible rows',
('For titles "GPU work" and "API", query " gpu " matches only the first after trimming and '
 'lowercasing. Among matches, priority 3 comes before priority 1. Equal priorities use '
 'ascending numeric IDs. filter creates a new array, so sorting it leaves the source order '
 'intact.'),
['Trim and lowercase query, then match it against each lowercased title.',
 'Sort the matches by priority, highest first, then numeric id, lowest first.',
 'Return a new array from visibleRows(rows, query). Do not reorder the rows array you were '
 'given.'],
['Normalize query with trim().toLowerCase().',
 'Use filter with row.title.toLowerCase().includes(q).',
 'Sort matches with (a, b) => b.priority - a.priority || a.id - b.id.'],
'''
function visibleRows(rows, query) {
  // Return a new array of filtered and sorted rows.
  return [];
}

console.log(visibleRows([{id: 1, title: "GPU work", priority: 1}], " gpu "));
''',
'''
function visibleRows(rows, query) {
  const q = query.trim().toLowerCase();
  const matches = rows.filter(row => row.title.toLowerCase().includes(q));
  // filter returned a new array, so sorting it leaves rows untouched.
  return matches.sort((a, b) => b.priority - a.priority || a.id - b.id);
}
''',
[('Matches case and whitespace',
  'visibleRows([{id:1,title:"GPU work",priority:1},{id:2,title:"API",priority:2}]," gpu '
  '").length===1'),
 ('Breaks ties by ID',
  'equal(visibleRows([{id:2,title:"a",priority:1},{id:1,title:"b",priority:1}],"").map(r=>r.id),[1,2])'),
 ('Sorts by priority first',
  'equal(visibleRows([{id:1,title:"a",priority:1},{id:2,title:"a",priority:3}],"").map(r=>r.id),[2,1])'),
 ('Sorts a copy while leaving the source order unchanged',
  '(() => { const rows = [{id: 2, title: "b", priority: 1}, {id: 1, title: "a", priority: '
  '1}]; const result = visibleRows(rows, ""); return equal(result.map(row => row.id), [1, '
  '2]) && rows[0].id === 2 && result !== rows; })()')],['Canonical data','Filter + stable order','Visible list'],
('sort() changes the array it runs on. Call it on the result of filter(), which is a new '
 'array.'))
add('web',4,'Migrate saved browser state',
('Saved browser data can outlive the code that wrote it. A new app version needs to read '
 'older formats and choose a default when saved data is malformed.'),
'parse → recognize version → migrate → validate',
('Version 1 uses {version: 1, darkMode: true}. Version 2 represents that choice as '
 '{version: 2, theme: "dark"}. Convert the old boolean into the new string. Unknown '
 'versions, invalid fields, and broken JSON use the light theme so startup can continue.'),
['Parse raw inside try/catch. For version 1, accept only a boolean darkMode.',
 'For version 2, accept only theme "light" or "dark". Use "light" for all other input.',
 'Return {version: 2, theme} from normalizePrefs(raw).'],
['Start with a light default and catch JSON.parse errors.',
 'For version 1 with a boolean darkMode, choose dark or light from that boolean.',
 'For version 2, keep the theme only if ["light", "dark"].includes(p.theme). Return the '
 'version 2 object.'],
'''
function normalizePrefs(raw) {
  // Return version 2 preferences with a valid theme.
  return null;
}

console.log(normalizePrefs('{"version":1,"darkMode":true}'));
''',
'''
function normalizePrefs(raw) {
  let p;
  try {
    p = JSON.parse(raw);
  } catch {
    p = null;
  }
  let theme = "light";
  if (p && p.version === 1 && typeof p.darkMode === "boolean") {
    theme = p.darkMode ? "dark" : "light";
  }
  if (p && p.version === 2 && ["light", "dark"].includes(p.theme)) {
    theme = p.theme;
  }
  return {version: 2, theme};
}
''',
[('Migrates v1',
  'equal(normalizePrefs(\'{"version":1,"darkMode":true}\'),{version:2,theme:"dark"})'),
 ('Reads v2', 'normalizePrefs(\'{"version":2,"theme":"dark"}\').theme==="dark"'),
 ('Handles broken storage', 'normalizePrefs("{broken").theme==="light"'),
 ('Rejects unknown and mistyped fields',
  'normalizePrefs(\'{"version":1,"darkMode":"false"}\').theme==="light" && '
  'normalizePrefs("null").version===2'),
 ('Rejects unsupported themes, versions, and missing fields',
  '[\'{"version":2,"theme":"blue"}\', \'{"version":9,"theme":"dark"}\', \'{"version":2}\', '
  '\'{}\'].every(raw => equal(normalizePrefs(raw), {version:2, theme:"light"}))')],['Stored JSON','Versioned migration','Valid UI preferences'],
('JSON.parse("null") succeeds and returns null. Check the parsed value before reading its '
 'fields.'),18)

add('rl',1,'Model an environment step',
('In reinforcement learning, an environment takes an action and returns a new observation, '
 'a reward, and stopping signals. Here the observation is the agent’s position in a '
 'five-cell corridor.'),
'(position, action) → (next_position, reward, terminated, truncated)',
('Moving right from position 3 reaches the goal at 4, earns reward 1, and sets terminated '
 'to True. A time limit sets truncated instead when the goal has not been reached. '
 'Reaching the goal on the last allowed step still counts as terminated. The two signals '
 'distinguish a finished task from an interrupted one.'),
['In env_step, accept positions 0–4, actions -1 or 1, steps >= 0, and max_steps >= 1. '
 'Raise ValueError otherwise.',
 'Clamp movement to 0–4. Reaching 4 earns 1 and terminates. Other moves earn -0.1 and '
 'truncate when steps + 1 >= max_steps.',
 'Return (next_position, reward, terminated, truncated). If already at 4, return (4, 0, '
 'True, False).'],
['Validate the inputs first. Then handle position 4 before moving. Otherwise clamp '
 'position + action with min and max.',
 'raise stops the function with an error. For example, if not names: raise '
 'ValueError("names is empty") rejects an empty list.',
 'Set terminated when next_position == 4. The current move is step number steps + 1, so '
 'truncated = not terminated and steps + 1 >= max_steps. Return all four values.'],
'''
def env_step(position, action, steps, max_steps):
    # Return the next position, reward, and both ending flags.
    return None

print(env_step(3, 1, 9, 10))
''',
'''
def env_step(position, action, steps, max_steps):
    if not 0 <= position <= 4 or action not in (-1, 1) or steps < 0 or max_steps < 1:
        raise ValueError('Invalid environment input')
    if position == 4:
        return (4, 0, True, False)
    next_position = max(0, min(4, position + action))
    terminated = next_position == 4
    reward = 1 if terminated else -0.1
    truncated = not terminated and steps + 1 >= max_steps
    return (next_position, reward, terminated, truncated)
''',
[('Moves and rewards', 'env_step(1,1,0,10)==(2,-.1,False,False)'),
 ('Goal terminates, not truncates', 'env_step(3,1,9,10)==(4,1,True,False)'),
 ('External limit truncates', 'env_step(1,-1,9,10)==(0,-.1,False,True)'),
 ('Clamps movement and keeps the goal terminal',
  'env_step(0, -1, 0, 10) == (0, -0.1, False, False) and env_step(4, -1, 10, 10) == (4, 0, '
  'True, False)'),
 ('Rejects invalid position, action, and step limits',
  'all(raises(ValueError, lambda args=args: env_step(*args)) for args in [(-1, 1, 0, 10), '
  '(5, 1, 0, 10), (1, 0, 0, 10), (1, 1, -1, 10), (1, 1, 0, 0)])')],['Action','Environment transition','Reward + observation'],
('Test position 3, action 1, steps 9, max_steps 10. The goal takes precedence over the '
 'cutoff.'))
add('rl',2,'Compute discounted returns',
('An action may lead to rewards several steps later. A return combines the current and '
 'future rewards, discounting later ones by a factor called gamma. These returns help a '
 'policy, the rule for choosing actions, learn from delayed outcomes.'),
'G[t] = reward[t] + gamma × G[t+1]',
('For rewards [1, 2, 3] and gamma 0.5, work backward. The last return is 3. The previous '
 'one is 2 + 0.5 × 3 = 3.5. The first is 1 + 0.5 × 3.5 = 2.75. The return after the last '
 'reward is zero because this episode is complete.'),
['Check that gamma is between 0 and 1 inclusive, raising ValueError otherwise.',
 'Work backward through rewards, accumulating each discounted return.',
 'Return a list in the original time order from returns(rewards, gamma), leaving rewards '
 'unchanged. Empty input returns [].'],
['Check gamma first. Then start with total = 0 at the end of the sequence.',
 'raise stops the function with an error. For example, if not names: raise '
 'ValueError("names is empty") rejects an empty list.',
 'Walk rewards in reverse and update total = reward + gamma * total. Reverse the collected '
 'results before returning.'],
'''
def returns(rewards, gamma):
    # Return one discounted return per reward.
    return None

print(returns([1, 2, 3], 0.5))
''',
'''
def returns(rewards, gamma):
    if not 0 <= gamma <= 1:
        raise ValueError('Invalid discount')
    values = []
    total = 0
    for reward in reversed(rewards):
        total = reward + gamma * total
        values.append(total)
    return list(reversed(values))
''',
[('Propagates delayed rewards','returns([1,2,3],.5)==[2.75,3.5,3]'),('Zero discount is immediate reward','returns([1,-2,3],0)==[1,-2,3]'),('Empty rollout','returns([],1)==[]'),('Rejects invalid gamma','raises(ValueError,lambda:returns([1],1.1))')],['Episode rewards', 'Work backward', 'Discounted returns'],
('Compute from the end, then reverse the result. Otherwise the returned values will '
 'describe the wrong time steps.'))
add('rl',3,'Balance exploration and exploitation',
('Always choosing the current best action can hide a better one. Epsilon-greedy is a '
 'policy that explores with probability epsilon and otherwise takes the action with the '
 'highest estimated value.'),
'with probability epsilon: explore; otherwise: choose the highest value',
('For values [1, 5, 2], the best action is index 1. Each value, often called Q, estimates '
 'how good that action is. With epsilon 0.2, draw 0.1 triggers exploration using the '
 'supplied explore_index. Draw 0.8 uses the best action. Passing the random draw as input '
 'makes both branches easy to test.'),
['Require nonempty values, epsilon in [0, 1], draw in [0, 1), and explore_index within '
 'values. Raise ValueError otherwise.',
 'If draw < epsilon, return explore_index.',
 'Otherwise return the index of the first maximum from choose_action(values, epsilon, '
 'draw, explore_index).'],
['Validate every range before choosing an action. If draw < epsilon, return explore_index; '
 'equality takes the greedy branch.',
 'raise stops the function with an error. For example, if age < 0: raise ValueError("age '
 'must not be negative") rejects a negative age.',
 'Use values.index(max(values)) to choose the first largest value.'],
'''
def choose_action(values, epsilon, draw, explore_index):
    # Return the selected action index.
    return None

print(choose_action([1, 5, 2], 0.2, 0.1, 2))
''',
'''
def choose_action(values, epsilon, draw, explore_index):
    if (
        not values
        or not 0 <= epsilon <= 1
        or not 0 <= draw < 1
        or not 0 <= explore_index < len(values)
    ):
        raise ValueError('Invalid policy input')
    return explore_index if draw < epsilon else values.index(max(values))
''',
[('Greedy action', 'choose_action([1,5,2],.1,.5,0)==1'),
 ('Exploration action', 'choose_action([1,5,2],.5,.1,2)==2'),
 ('Stable tie-breaking', 'choose_action([4,4,1],0,.9,2)==0'),
 ('Boundary is greedy', 'choose_action([1,5],.5,.5,0)==1'),
 ('Rejects empty values and invalid selection inputs',
  'all(raises(ValueError, lambda args=args: choose_action(*args)) for args in [([], 0, '
  '0.5, 0), ([1], -0.1, 0.5, 0), ([1], 1.1, 0.5, 0), ([1], 0.5, 1, 0), ([1], 0.5, -0.1, '
  '0), ([1], 0.5, 0.2, 1)])')],['Estimated action values', 'Explore or choose best', 'Action index'],
'Return an index, not the largest value. For [1, 5, 2], greedy choice is 1.')
add('rl',4,'Bootstrap only when the task continues',
('Q-learning updates an action’s estimated value toward reward plus a discounted estimate '
 'of what comes next. Using that future estimate is called bootstrapping. A terminated '
 'task has no future rewards. A truncated task was interrupted and can still have future '
 'rewards.'),
'Q_new = Q + alpha × (reward + gamma × next_value × not_terminated − Q)',
('With reward 1, next values [3, 4], and gamma 0.9, a continuing task has target 1 + 0.9 × '
 '4 = 4.6. Starting from old value 2, alpha 0.5 moves halfway to that target: 3.3. If '
 'terminated is True, the target is only 1 and the update gives 1.5.'),
['Require alpha and gamma in [0, 1]. Require nonempty next_values when terminated is '
 'False. Raise ValueError otherwise.',
 'Set the target to reward for a terminated task, or reward + gamma * max(next_values) for '
 'a continuing task, including truncation.',
 'Return old + alpha * (target - old) from q_update.'],
['Validate the inputs first. Then choose the target before applying alpha.',
 'raise stops the function with an error. For example, if age < 0: raise ValueError("age '
 'must not be negative") rejects a negative age.',
 'Check terminated, rather than terminated or truncated, when deciding whether to include '
 'a future value. Return old + alpha * (target - old).'],
'''
def q_update(old, reward, next_values, alpha, gamma, terminated, truncated):
    # Return the updated action value.
    return None

print(q_update(2, 1, [3, 4], 0.5, 0.9, False, True))
''',
'''
def q_update(old, reward, next_values, alpha, gamma, terminated, truncated):
    if not 0 <= alpha <= 1 or not 0 <= gamma <= 1 or (not terminated and not next_values):
        raise ValueError('Invalid update')
    target = reward if terminated else reward + gamma * max(next_values)
    return old + alpha * (target - old)
''',
[('Bootstraps a normal step', 'abs(q_update(2,1,[3,4],.5,.9,False,False)-3.3)<1e-9'),
 ('Truncation retains bootstrap', 'abs(q_update(2,1,[4],.5,.9,False,True)-3.3)<1e-9'),
 ('Termination removes bootstrap', 'q_update(2,1,[],.5,.9,True,False)==1.5'),
 ('No learning when alpha zero', 'q_update(8,1,[3],0,.9,False,False)==8'),
 ('Rejects missing continuation values and invalid rates',
  'raises(ValueError, lambda: q_update(0, 1, [], .5, .9, False, True)) and '
  'raises(ValueError, lambda: q_update(0, 1, [2], -0.1, .9, False, False)) and '
  'raises(ValueError, lambda: q_update(0, 1, [2], .5, 1.1, False, False))')],['Transition','Bootstrap decision','Q update'],
('Try next_values=[3, 4]. Taking the first value instead of the maximum gives the wrong '
 'target.'),20)

add('data',1,'Deduplicate an event stream',
('Ingestion means receiving data for a system to store or process. The same event may '
 'arrive more than once, and versions can arrive out of order. Use an event ID and '
 'revision to choose which copy to keep.'),
'one event ID → highest revision',
('For ID "a", revision 3 replaces revision 1 even if revision 1 arrives later. If two '
 'events have revision 3, keep the first one seen. A dictionary stores one chosen event '
 'per ID. Sorting its keys gives a predictable output order.'),
['Group events by their id using a dictionary.',
 'Keep the greatest revision for each ID. On a tie, keep the first event seen.',
 'Return a list sorted by ID from latest_events(events), leaving the input unchanged.'],
['Maintain a dictionary from ID to the chosen event.','Replace only when revision is strictly greater.','Return chosen records for sorted dictionary keys.'],
'''
def latest_events(events):
    # Return one event per ID, sorted by ID.
    return None

print(latest_events([{"id": "a", "revision": 1}, {"id": "a", "revision": 3}]))
''',
'''
def latest_events(events):
    selected = {}
    for event in events:
        key = event['id']
        if key not in selected or event['revision'] > selected[key]['revision']:
            selected[key] = event
    return [selected[key] for key in sorted(selected)]
''',
[('Keeps latest revision','latest_events([{"id":"a","revision":2},{"id":"a","revision":1}])==[{"id":"a","revision":2}]'),('Keeps first equal revision','latest_events([{"id":"a","revision":1,"x":1},{"id":"a","revision":1,"x":2}])[0]["x"]==1'),('Orders identities','[e["id"] for e in latest_events([{"id":"z","revision":1},{"id":"a","revision":0}])]==["a","z"]'),('Empty input','latest_events([])==[]')],['Incoming events', 'Choose highest revision', 'One record per ID'],
'Use > rather than >= when comparing revisions. Equality must keep the earlier event.')
add('data',2,'Chunk text with bounded overlap',
('A retrieval system splits long documents into chunks, smaller pieces it can search and '
 'return. Overlap keeps some words at the boundary in both neighboring chunks.'),
'stride = chunk size − overlap',
('For tokens [a, b, c, d, e], size 3, and overlap 1, return [a, b, c] and [c, d, e]. Each '
 'start advances by 3 − 1 = 2. Stop when a chunk reaches the end. Another chunk starting '
 'at e would contain only text already covered.'),
['Require integer size > 0 and integer overlap with 0 <= overlap < size. Raise ValueError '
 'otherwise.',
 'Slice tokens into lists of at most size elements, advancing by size - overlap.',
 'Return the chunks from chunks(tokens, size, overlap). Stop when a chunk reaches the end, '
 'and return [] for empty input.'],
['Validate size and overlap first. Then track a start index, beginning at zero.',
 'raise stops the function with an error. For example, if not names: raise '
 'ValueError("names is empty") rejects an empty list.',
 'Append tokens[start:start + size]. Stop if start + size >= len(tokens); otherwise add '
 'size - overlap to start and repeat.'],
'''
def chunks(tokens, size, overlap):
    # Return a list of overlapping token lists.
    return None

print(chunks(["a", "b", "c", "d", "e"], 3, 1))
''',
'''
def chunks(tokens, size, overlap):
    if type(size) is not int or type(overlap) is not int or size <= 0 or (not 0 <= overlap < size):
        raise ValueError('Invalid chunk settings')
    result = []
    start = 0
    while start < len(tokens):
        result.append(tokens[start:start + size])
        if start + size >= len(tokens):
            break
        start += size - overlap
    return result
''',
[('Overlaps adjacent chunks', 'chunks(list(range(7)),4,1)==[[0,1,2,3],[3,4,5,6]]'),
 ('Preserves final partial chunk', 'chunks([1,2,3,4,5],3,1)==[[1,2,3],[3,4,5]]'),
 ('Empty document', 'chunks([],3,1)==[]'),
 ('Rejects nonprogressing stride', 'raises(ValueError,lambda:chunks([1],3,3))'),
 ('Rejects zero size and noninteger settings',
  'raises(ValueError, lambda: chunks([1], 0, 0)) and raises(ValueError, lambda: '
  'chunks([1], 2.5, 0)) and raises(ValueError, lambda: chunks([1], 3, -1))')],['Token sequence','Bounded overlap','Retrievable chunks'],
('An overlap equal to size would give stride zero and an endless loop. Validate before '
 'starting.'))
add('data',3,'Traverse a graph without looping',
('A graph links nodes to other nodes. To find everything within a given number of links, '
 'walk outward one step at a time. Track visited nodes so a loop such as a → b → a cannot '
 'send you around forever.'),
'frontier → unseen neighbors → next frontier',
('For a → b → c, depth 0 returns only a, depth 1 includes b, and depth 2 includes c. This '
 'is a breadth-first walk: visit all nodes one link away before moving farther. The '
 'frontier is the set to expand next. Subtract already-seen nodes before building the next '
 'frontier.'),
['Put start in both the seen set and the frontier.',
 'Expand outgoing neighbors at most depth times. Missing graph keys have no outgoing '
 'neighbors.',
 'Return sorted unique node IDs from neighborhood(graph, start, depth), including start. '
 'Raise ValueError for negative depth.'],
['Reject a negative depth first. Keep seen and frontier as separate sets, each initially '
 'containing start.',
 'raise stops the function with an error. For example, if not names: raise '
 'ValueError("names is empty") rejects an empty list.',
 'Collect neighbors of each frontier node, then subtract seen. Set frontier = neighbors - '
 'seen, update seen with that frontier, and return sorted(seen) after the loop.'],
'''
def neighborhood(graph, start, depth):
    # Return the sorted node IDs within the depth limit.
    return None

print(neighborhood({"a": ["b"], "b": ["a", "c"]}, "a", 2))
''',
'''
def neighborhood(graph, start, depth):
    if depth < 0:
        raise ValueError('Negative depth')
    seen = {start}
    frontier = {start}
    for _ in range(depth):
        neighbors = set()
        for node in frontier:
            neighbors.update(graph.get(node, []))
        frontier = neighbors - seen
        seen.update(frontier)
    return sorted(seen)
''',
[('Respects one-hop boundary', 'neighborhood({"a":["b"],"b":["c"]},"a",1)==["a","b"]'),
 ('Terminates cycles', 'neighborhood({"a":["b"],"b":["a","c"]},"a",9)==["a","b","c"]'),
 ('Zero depth includes only start', 'neighborhood({"a":["b"]},"a",0)==["a"]'),
 ('Start node not in the graph returns itself', 'neighborhood({},"x",3)==["x"]'),
 ('Rejects negative depth', 'raises(ValueError, lambda: neighborhood({}, "a", -1))')],['Starting node','Bounded graph walk','Relevant neighborhood'],
('Try a graph containing a cycle and a branch. You should include the branch once without '
 'revisiting the cycle.'))
add('data',4,'Measure retrieval coverage',
'A retrieval system needs an evaluation set, not just convincing examples. Recall at k asks what fraction of known relevant documents appear in the first k results.',
'recall@k = unique relevant hits in top k / all relevant IDs',
('For ranked IDs ["a", "x", "b"] and relevant IDs {"a", "b"}, recall at 2 is 1 / 2 = 0.5. '
 'The first two positions include only one relevant ID. Repeated results use up positions '
 'but count once as hits, so ["a", "a", "b"] also scores 0.5 at 2.'),
['Take the first k positions from ranked before removing duplicate IDs.',
 'Count the unique relevant IDs in those positions and divide by the number of relevant '
 'IDs.',
 'Return 0 for no relevant IDs from recall_at_k(ranked, relevant, k). Raise ValueError for '
 'negative k.'],
['Reject a negative k first. Then build set(ranked[:k]).',
 'raise stops the function with an error. For example, if not names: raise '
 'ValueError("names is empty") rejects an empty list.',
 'Intersect that set with set(relevant). Divide the intersection size by len(relevant), '
 'returning 0 when relevant is empty.'],
'''
def recall_at_k(ranked, relevant, k):
    # Return the fraction of relevant IDs retrieved in the first k positions.
    return None

print(recall_at_k(["a", "x", "b"], {"a", "b"}, 2))
''',
'''
def recall_at_k(ranked, relevant, k):
    if k < 0:
        raise ValueError('Negative cutoff')
    relevant = set(relevant)
    return len(set(ranked[:k]) & relevant) / len(relevant) if relevant else 0.0
''',
[('Counts top-k relevant hits', 'recall_at_k(["a","x","b"],{"a","b"},2)==.5'),
 ('Duplicates do not inflate recall', 'recall_at_k(["a","a","b"],{"a","b"},2)==.5'),
 ('No relevant IDs returns 0', 'recall_at_k(["a"],set(),3)==0'),
 ('Zero cutoff', 'recall_at_k(["a"],{"a"},0)==0'),
 ('Rejects negative cutoff', 'raises(ValueError, lambda: recall_at_k(["a"], {"a"}, -1))')],['Ranked results','Ground-truth relevance','Recall at k'],
('Slice before converting to a set. Removing duplicates first would move later results '
 'into the first k positions.'),18)

add('reliability',1,'Bound exponential retries',
('A brief failure may clear before a retry, but repeated requests can also overload a '
 'struggling service. Exponential backoff increases the wait after each failure. Cap each '
 'wait and the total time spent waiting.'),
'delay[n] = min(cap, base × 2ⁿ)',
('With base 2 and cap 5, the candidate delays are 2, 4, 5, 5. A total budget of 10 allows '
 'only [2, 4], since adding 5 would cost 11. A delay that reaches the budget exactly is '
 'allowed. The function returns the schedule for a caller to use.'),
['Start with min(base, cap), doubling each later delay up to cap.',
 'Return at most attempts delays from retry_delays(base, cap, attempts, budget), stopping '
 'before their sum exceeds budget.',
 'Raise ValueError if base or cap is zero or negative, or if attempts or budget is '
 'negative. Zero attempts or budget returns [].'],
['Validate the inputs first. Then track a delays list, spent time, and the next delay.',
 'raise stops the function with an error. For example, if not names: raise '
 'ValueError("names is empty") rejects an empty list.',
 'Break when spent + delay > budget; otherwise append delay and add it to spent. Set delay '
 '= min(cap, delay * 2) for the next iteration, then return delays.'],
'''
def retry_delays(base, cap, attempts, budget):
    # Return the delays that fit both limits.
    return None

print(retry_delays(2, 5, 4, 10))
''',
'''
def retry_delays(base, cap, attempts, budget):
    if base <= 0 or cap <= 0 or attempts < 0 or budget < 0:
        raise ValueError('Invalid retry settings')
    delays = []
    spent = 0
    delay = min(base, cap)
    for _ in range(attempts):
        if spent + delay > budget:
            break
        delays.append(delay)
        spent += delay
        delay = min(cap, delay * 2)
    return delays
''',
[('Exponential with cap', 'retry_delays(1,4,5,20)==[1,2,4,4,4]'),
 ('Stops at total budget', 'retry_delays(1,9,5,6)==[1,2]'),
 ('Exact boundary allowed', 'retry_delays(2,8,3,6)==[2,4]'),
 ('Zero attempts', 'retry_delays(1,8,0,9)==[]'),
 ('Handles zero budget and rejects invalid settings',
  'retry_delays(1, 8, 3, 0) == [] and all(raises(ValueError, lambda args=args: '
  'retry_delays(*args)) for args in [(0, 4, 2, 10), (1, 0, 2, 10), (1, 4, -1, 10), (1, 4, '
  '2, -1)])')],['Transient failure','Retry budget','Delay or stop'],
('Check spent + delay before appending. Checking afterward would include a wait that '
 'exceeds the budget.'))
add('reliability',2,'Redact structured telemetry',
('Structured logs can contain passwords inside nested dictionaries and lists. Redaction '
 'replaces those values before the log is written. Walk the whole object so a nested '
 'secret is handled like a top-level one.'),
'structured data → recursive redaction → loggable copy',
('For {"nested": [{"TOKEN": "secret"}]}, the output keeps the same dictionary and list '
 'structure but replaces "secret" with "[REDACTED]". Lowercase each key only for '
 'comparison, preserving its spelling in the output. Create new containers while copying '
 'ordinary scalar values such as numbers and booleans.'),
['Replace values under token, password, or api_key keys, ignoring key case, with '
 '"[REDACTED]".',
 'Recursively process other dictionary values and list items in redact(value).',
 'Return new dictionaries and lists, preserve scalar values, and leave the input '
 'unchanged.'],
['Use separate branches for dictionaries, lists, and scalars.',
 'Compare str(key).lower() with the three sensitive names. Keep key unchanged in the '
 'result.',
 'Recursively redact ordinary dictionary values and list items. Return scalar values '
 'directly.'],
'''
def redact(value):
    # Return a redacted copy, preserving ordinary values.
    return None

print(redact({"nested": [{"TOKEN": "example-only"}], "count": 3}))
''',
'''
def redact(value):
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if str(key).lower() in {'token', 'password', 'api_key'}:
                result[key] = '[REDACTED]'
            else:
                result[key] = redact(item)
        return result
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value
''',
[('Redacts nested credentials',
  'redact({"nested":[{"TOKEN":"secret"}]})=={"nested":[{"TOKEN":"[REDACTED]"}]}'),
 ('Preserves ordinary data', 'redact({"count":3,"ok":True})=={"count":3,"ok":True}'),
 ('Redacts a copy and leaves the source unchanged',
  '(lambda value: (lambda result: result == {"password": "[REDACTED]"} and result is not '
  'value and value["password"] == "secret")(redact(value)))({"password": "secret"})'),
 ('Preserves scalar values and redacts all named keys',
  'redact(None) is None and redact(7) == 7 and redact("plain") == "plain" and '
  'redact({"API_KEY": "x", "password": "y"}) == {"API_KEY": "[REDACTED]", "password": '
  '"[REDACTED]"}')],['Telemetry object','Redaction rules','Diagnostic event'],
('A list can contain another dictionary. Apply redact to each list item as well as each '
 'ordinary dictionary value.'))
add('reliability',3,'Plan a deployment as a diff',
('Before changing a deployment, compare what is running with what you want to run. A diff '
 'groups service names into additions, version changes, and removals.'),
'desired state − observed state → change plan',
('If current has api version 1 and old version 1, while desired has api version 2 and '
 'worker version 1, create worker. Update api because its version changed. Remove old '
 'because it is absent from desired. Equal versions produce no update, so repeating the '
 'comparison after applying the plan gives empty lists.'),
['Compare the service-name keys in current and desired.',
 'Classify new names as create, missing names as remove, and shared names with changed '
 'versions as update.',
 'Return sorted lists under those three keys from deploy_plan(current, desired), '
 'preserving both inputs.'],
['Use set(current) and set(desired) to compare names.',
 'Set differences give create and remove. Intersect the sets before comparing versions.',
 'Sort each group before returning {"create": ..., "update": ..., "remove": ...}.'],
'''
def deploy_plan(current, desired):
    # Return the sorted create, update, and remove lists.
    return None

print(deploy_plan({"api": "1", "old": "1"}, {"api": "2", "worker": "1"}))
''',
'''
def deploy_plan(current, desired):
    old = set(current)
    new = set(desired)
    return {
        "create": sorted(new - old),
        "update": sorted(name for name in old & new if current[name] != desired[name]),
        "remove": sorted(old - new),
    }
''',
[('Classifies differences','deploy_plan({"api":"1","old":"1"},{"api":"2","worker":"1"})=={"create":["worker"],"update":["api"],"remove":["old"]}'),('No-op on identical state','deploy_plan({"api":"1"},{"api":"1"})=={"create":[],"update":[],"remove":[]}'),('Sorted additions','deploy_plan({},{"z":"1","a":"1"})["create"]==["a","z"]')],['Observed + desired','Compute diff','Reviewable plan'],
'A service present in both mappings belongs in update only if its version changed.')
add('reliability',4,'Gate a release on measured signals',
('A release passes when measurements meet targets set in advance. Here the targets are '
 'success rate and p95 latency: at least 95% of successful requests were that fast or '
 'faster. Missing measurements mean the release fails.'),
'pass = success_rate ≥ target and nearest-rank p95 ≤ latency budget',
('If nine of ten requests succeed, success rate is 0.9. For successful latencies [10, 20, '
 '30, 40], nearest-rank p95 selects ceil(0.95 × 4) − 1 = index 3, or 40. The ceiling '
 'function rounds up. Calculate latency from successful requests, but keep failures in the '
 'success-rate denominator.'),
['Compute success rate using all samples. Each sample contains ok and latency_ms.',
 'Sort successful latencies and choose index math.ceil(0.95 * count) - 1 for p95.',
 'Return whether both inclusive thresholds pass from release_passes. Return False for no '
 'samples or no successful samples.'],
['Return False if samples is empty, then collect and sort successful latencies.',
 'Return False if that list is empty. Select its p95 using math.ceil.',
 'Compare len(successful) / len(samples) >= min_success_rate and p95 <= max_p95.'],
'''
import math

def release_passes(samples, min_success_rate, max_p95):
    # Return whether the measured success rate and p95 pass.
    return None

print(release_passes([{"ok": True, "latency_ms": 100}], 1, 100))
''',
'''
import math

def release_passes(samples, min_success_rate, max_p95):
    if not samples:
        return False
    successful = sorted(s['latency_ms'] for s in samples if s['ok'])
    if not successful:
        return False
    p95 = successful[math.ceil(0.95 * len(successful)) - 1]
    return len(successful) / len(samples) >= min_success_rate and p95 <= max_p95
''',
[('Passes inclusive thresholds',
  'release_passes([{"ok":True,"latency_ms":100}],1,100) is True'),
 ('Rejects too many failures',
  'release_passes([{"ok":True,"latency_ms":10},{"ok":False,"latency_ms":1}],.9,100) is '
  'False'),
 ('Rejects tail regression',
  'release_passes([{"ok":True,"latency_ms":10},{"ok":True,"latency_ms":500}],1,100) is '
  'False'),
 ('No samples: release fails', 'release_passes([],1,100) is False'),
 ('All failed samples: release fails',
  'release_passes([{"ok":False,"latency_ms":1}],0,100) is False')],['Test samples','Success + tail latency','Release decision'],
('Use all attempts in the success-rate denominator. Dividing by only successes would '
 'always give 1.'),20)

add('interactive',1,'Track app lifecycle states',
('When an app goes to the background, it may need to stop timers or release the camera. '
 'Its lifecycle is the set of states it moves through, such as active and paused. A plain '
 'transition function makes those changes easy to test.'),
'app state + lifecycle event → new app state',
('Opening a stopped app makes it active. Sending it to the background pauses it, and '
 'resuming makes it active again. Closing either an active or paused app stops it. A '
 'second background event leaves a paused app paused because that pair has no transition.'),
['Define stopped/open→active, active/background→paused, and paused/resume→active.',
 'Define active/close→stopped and paused/close→stopped.',
 'Return the next state from lifecycle(state, event), or the original state for an unknown '
 'pair.'],
['Use (state, event) tuples as dictionary keys.',
 'Put all five transitions in the dictionary.',
 'Return table.get((state, event), state) to keep unknown pairs unchanged.'],
'''
def lifecycle(state, event):
    # Return the next lifecycle state.
    return None

print(lifecycle("active", "close"))
''',
'''
def lifecycle(state, event):
    table = {
        ("stopped", "open"): "active",
        ("active", "background"): "paused",
        ("paused", "resume"): "active",
        ("active", "close"): "stopped",
        ("paused", "close"): "stopped",
    }
    return table.get((state, event), state)
''',
[('Launches active', 'lifecycle("stopped","open")=="active"'),
 ('Pauses and resumes', 'lifecycle(lifecycle("active","background"),"resume")=="active"'),
 ('Closes from background', 'lifecycle("paused","close")=="stopped"'),
 ('Repeated events are harmless', 'lifecycle("paused","background")=="paused"'),
 ('Closes from active', 'lifecycle("active", "close") == "stopped"')],['Platform event','Lifecycle transition','Resource effects'],
('Check both ways to close the app. Closing from active should work just like closing from '
 'paused.'))
add('interactive',2,'Use time, not frame count',
'Animation and simulation speed should not depend on display refresh rate. Advance position using elapsed seconds and clamp unexpectedly large frame gaps.',
'position_next = position + velocity × min(delta_time, max_delta)',
('At position 10 with velocity 4 units per second, a 0.5-second gap would move to 12. '
 'Capping that gap at 0.1 seconds moves to 10.4 instead. Then clamp the new position to '
 'the allowed range. This prevents a long pause from causing one large jump.'),
['Reject negative delta_time, negative max_delta, or low > high with ValueError.',
 'Multiply velocity by min(delta_time, max_delta) and add it to position.',
 'Clamp the result to [low, high] and return it from advance(position, velocity, '
 'delta_time, max_delta, low, high).'],
['Validate the input first, then set step = min(delta_time, max_delta).',
 'raise stops the function with an error. For example, if not names: raise '
 'ValueError("names is empty") rejects an empty list.',
 'Compute candidate = position + velocity * step. Return min(high, max(low, candidate)).'],
'''
def advance(position, velocity, delta_time, max_delta, low, high):
    # Return the position after applying time and position limits.
    return None

print(advance(10, 4, 0.5, 0.1, 0, 100))
''',
'''
def advance(position, velocity, delta_time, max_delta, low, high):
    if delta_time < 0 or max_delta < 0 or low > high:
        raise ValueError('Invalid time or bounds')
    step = min(delta_time, max_delta)
    candidate = position + velocity * step
    return min(high, max(low, candidate))
''',
[('Time-scaled movement','advance(0,10,.1,.2,0,100)==1'),('Caps long resume gaps','advance(0,10,5,.2,0,100)==2'),('Clamps at both edges','advance(9,20,1,1,0,10)==10 and advance(1,-20,1,1,0,10)==0'),('Rejects negative elapsed time','raises(ValueError,lambda:advance(0,1,-1,1,0,10))')],['Elapsed time','Bounded update','Next position'],
('Clamp the time before multiplying by velocity, then clamp the position. These are two '
 'different limits.'))
add('interactive',3,'Fit media without changing its shape',
('An image’s aspect ratio is its width divided by its height. Scaling both dimensions by '
 'the same factor preserves that shape. Choose the smaller factor needed to fit inside a '
 'box, then center the remaining space.'),
'scale = min(box_width / width, box_height / height)',
('A 200-by-100 image in a 100-by-100 box needs scale 0.5 to fit its width. Its displayed '
 'size becomes 100 by 50. The box has 50 unused vertical units, so an offset of 25 above '
 'and below centers the image. Using separate width and height scales would stretch it.'),
['Require positive width, height, box_width, and box_height, raising ValueError otherwise.',
 'Use one scale, min(box_width / width, box_height / height), for both image dimensions.',
 'Return (display_width, display_height, offset_x, offset_y) from fit_media, using half '
 'the unused space as each offset.'],
['Check that all four sizes are positive. Then compute both possible scale factors and '
 'take their minimum.',
 'raise stops the function with an error. For example, if not names: raise '
 'ValueError("names is empty") rejects an empty list.',
 'Multiply both original dimensions by that same scale. Offsets are half the remaining '
 'width and height.'],
'''
def fit_media(width, height, box_width, box_height):
    # Return the display size and centered offsets.
    return None

print(fit_media(200, 100, 100, 100))
''',
'''
def fit_media(width, height, box_width, box_height):
    if min(width, height, box_width, box_height) <= 0:
        raise ValueError('Positive dimensions required')
    scale = min(box_width / width, box_height / height)
    display_width = width * scale
    display_height = height * scale
    offset_x = (box_width - display_width) / 2
    offset_y = (box_height - display_height) / 2
    return (display_width, display_height, offset_x, offset_y)
''',
[('Landscape letterbox','fit_media(200,100,100,100)==(100,50,0,25)'),('Portrait pillarbox','fit_media(100,200,100,100)==(50,100,25,0)'),('Matching aspect ratio','fit_media(200,100,400,200)==(400,200,0,0)'),('Rejects impossible dimensions','raises(ValueError,lambda:fit_media(0,100,100,100))')],['Source dimensions','Uniform scale','Centered preview'],
'Test a portrait image as well as a landscape image. The unused space switches axes.')
add('interactive',4,'Merge progress without duplicate rewards',
('An offline app may send the same completion again when it reconnects. Give each event an '
 'ID so merging repeated events awards its points once.'),
'new state = prior event IDs ∪ incoming event IDs',
('Start with {"a": 10} and receive [("a", 99), ("b", 5)]. Keep the saved value 10 for "a" '
 'and add 5 for "b", giving a total of 15. The first value also wins for repeated IDs '
 'within one incoming batch. Copy the starting dictionary so the old state stays '
 'available.'),
['Copy state, then read incoming (id, points) tuples in order.',
 'Add points only for IDs absent from the copied mapping, preserving the first value for '
 'each ID.',
 'Return (merged, total) from merge_progress(state, events), calculating total from the '
 'merged mapping and leaving state unchanged.'],
['Start from dict(state).','Use setdefault to preserve the first value.','Compute total from the final mapping rather than from the incoming batch.'],
'''
def merge_progress(state, events):
    # Return a new progress mapping and its total points.
    return None

print(merge_progress({"a": 10}, [("a", 99), ("b", 5)]))
''',
'''
def merge_progress(state, events):
    merged = dict(state)
    for ident, points in events:
        merged.setdefault(ident, points)
    return (merged, sum(merged.values()))
''',
[('Awards new completions', 'merge_progress({},[("a",10),("b",20)])==({"a":10,"b":20},30)'),
 ('Replay does not duplicate', 'merge_progress({"a":10},[("a",10)])==({"a":10},10)'),
 ('First value wins', 'merge_progress({},[("a",10),("a",99)])[1]==10'),
 ('Merges a copy and leaves the original unchanged',
  '(lambda state: (lambda result: result == ({"a": 10, "b": 5}, 15) and result[0] is not '
  'state and state == {"a": 10})(merge_progress(state, [("b", 5)])))({"a": 10})')],['Offline events','Deduplicate by identity','Saved progress'],
('Sum merged.values() after processing every event. Summing incoming points would count '
 'replays twice.'),18)
