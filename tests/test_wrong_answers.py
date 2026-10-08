"""Plausible wrong implementations must fail a lesson's executable checks.

The first 23 cases reproduce the curriculum audit. Extra cases cover device
transfers, shared memory, missing inputs, checks that used to accept stubs, and
the beginner mistakes that Python from zero must catch.
"""
import ast
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from courses import BY_ID
from runner import execute
from test_curriculum import OFFLINE_PREFIX, JS_OFFLINE_PREFIX, require_lesson_modules, missing_lesson_modules
from parallel_runs import PrefetchedRuns


def reference(lesson_id):
    """Keep imports and definitions so demo calls cannot hide a check failure."""
    source = BY_ID[lesson_id]["solution"]
    if BY_ID[lesson_id].get("language") == "javascript":
        return source
    tree = ast.parse(source)
    tree.body = [node for node in tree.body if isinstance(
        node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef)
    )]
    return ast.unparse(tree)


def changed(lesson_id, old, new):
    source = reference(lesson_id)
    if old not in source:
        raise AssertionError(f"Mutation no longer matches {lesson_id}: {old!r}")
    return source.replace(old, new)


def functions(lesson_id, **replacements):
    tree = ast.parse(reference(lesson_id))
    found = set()
    for index, node in enumerate(tree.body):
        if isinstance(node, ast.FunctionDef) and node.name in replacements:
            tree.body[index] = ast.parse(replacements[node.name]).body[0]
            found.add(node.name)
    if found != set(replacements):
        raise AssertionError(f"Missing functions in {lesson_id}: {set(replacements) - found}")
    return ast.unparse(tree)


# Six audit cases: bypass an empty kernel by doing the work in its wrapper.
CUDA_BYPASSES = {
    "cuda-1": ("fill_indices", "out", "run_indices", "n", "np.arange(n)"),
    "cuda-2": ("add_kernel", "a, b, out", "add_vectors", "a, b", "np.asarray(a) + np.asarray(b)"),
    "cuda-3": ("double_kernel", "data", "doubled", "values", "np.asarray(values, dtype=np.float32) * 2"),
    "cuda-4": ("transpose_kernel", "source, out", "transpose", "values", "np.asarray(values).T"),
    "cuda-5": ("block_sum_kernel", "values, out", "block_sums", "values", "np.array([sum(values[i:i + 8]) for i in range(0, len(values), 8)])"),
    "cuda-6": ("fused_kernel", "a, b, scale, out", "fused", "a, b, scale", "np.maximum(scale * np.asarray(a) + np.asarray(b), 0)"),
}
WRONG_ANSWERS = {
    lesson_id: [("empty kernel hidden by NumPy wrapper", functions(
        lesson_id,
        **{
            kernel: f"@cuda.jit\ndef {kernel}({kernel_args}):\n    pass",
            wrapper: f"def {wrapper}({wrapper_args}):\n    return {result}",
        },
    ))]
    for lesson_id, (kernel, kernel_args, wrapper, wrapper_args, result) in CUDA_BYPASSES.items()
}
WRONG_ANSWERS["cuda-2"].append(("missing guard hidden by exact-size launch", functions(
    "cuda-2",
    add_kernel="""@cuda.jit
def add_kernel(a, b, out):
    i = cuda.grid(1)
    out[i] = a[i] + b[i]
""",
    add_vectors="""def add_vectors(a, b):
    a, b = np.asarray(a, dtype=np.float32), np.asarray(b, dtype=np.float32)
    out = np.zeros_like(a)
    if a.size:
        add_kernel[a.size, 1](a, b, out)
    return out
""",
)))
WRONG_ANSWERS.update({
    "harness-1": [("accepts events in the wrong state", """def transition(state, event):
    if state == "done":
        raise ValueError("Already done")
    return {"start": "running", "ask": "waiting", "approve": "running", "finish": "done"}[event]
""")],
    "harness-4": [("counts failed tools as successes", changed(
        "harness-4", " and e.get('ok') is True", ""))],
    "backend-1": [("ignores the priority range", changed(
        "backend-1", " or (not 1 <= priority <= 5)", ""))],
    "backend-3": [
        ("cursor points to an empty next page", changed("backend-3", "len(remaining) > limit", "len(remaining) >= limit")),
        ("sorts the caller's rows", functions("backend-3", page_after="""def page_after(rows, after, limit):
    if limit <= 0:
        raise ValueError("Positive limit required")
    rows.sort(key=lambda row: row["id"])
    remaining = [row for row in rows if row["id"] > after]
    selected = remaining[:limit]
    cursor = selected[-1]["id"] if len(remaining) > limit else None
    return selected, cursor
""")),
    ],
    "backend-4": [("omits optional failures and sorting", """def readiness(dependencies):
    return {
        "ready": all(d["healthy"] for d in dependencies if d["required"]),
        "degraded": [d["name"] for d in dependencies if d["required"] and not d["healthy"]],
    }
""")],
    "web-4": [("trusts arbitrary themes and future versions", changed(
        "web-4", "  return {version: 2, theme};",
        '  if (p && typeof p.theme === "string") { theme = p.theme; }\n  return {version: 2, theme};'))],
    "pytorch-3": [("places ReLU after both Linear layers", changed(
        "pytorch-3", "nn.Linear(2, 4), nn.ReLU(), nn.Linear(4, 1)", "nn.Linear(2, 4), nn.Linear(4, 1), nn.ReLU()"))],
    "tensorflow-3": [("clamps the regression output with ReLU", changed(
        "tensorflow-3", "tf.keras.layers.Dense(1)", "tf.keras.layers.Dense(1, activation='relu')"))],
    "foundations-6": [("recomputes the bias gradient after updating weight", """def train(xs, ys, epochs=400, lr=0.05):
    weight, bias = 0.0, 0.0
    for _ in range(epochs):
        errors = [weight * x + bias - y for x, y in zip(xs, ys)]
        dw = sum(2 * error * x for error, x in zip(errors, xs)) / len(xs)
        weight -= lr * dw
        errors = [weight * x + bias - y for x, y in zip(xs, ys)]
        db = sum(2 * error for error in errors) / len(xs)
        bias -= lr * db
    return weight, bias
""")],
    "rl-4": [("uses the first next value instead of the best", changed("rl-4", "max(next_values)", "next_values[0]"))],
    "pytorch-4": [("shuffles an ordered loader", changed("pytorch-4", "shuffle=False", "shuffle=True"))],
    "modern-2": [("uses BERT's default twelve layers", changed("modern-2", "num_hidden_layers=1, ", ""))],
    "harness-2": [("returns the argument dictionary without copying", changed("harness-2", "return dict(args)", "return args"))],
    "rl-1": [("does not validate environment inputs", functions("rl-1", env_step="""def env_step(position, action, steps, max_steps):
    if position == 4:
        return 4, 0, True, False
    next_position = max(0, min(4, position + action))
    terminated = next_position == 4
    reward = 1 if terminated else -0.1
    truncated = not terminated and steps + 1 >= max_steps
    return next_position, reward, terminated, truncated
"""))],
    "interactive-1": [("cannot close an active app", changed("interactive-1", "('active', 'close'): 'stopped', ", ""))],
})
AUDIT_CASE_COUNT = sum(len(cases) for cases in WRONG_ANSWERS.values())
assert AUDIT_CASE_COUNT == 23

WRONG_ANSWERS["cuda-3"].extend([
    ("correct kernel but wrapper skips transfers", functions("cuda-3", doubled="""def doubled(values):
    return np.asarray(values, dtype=np.float32) * 2
""")),
    ("launches on a host copy instead of a device array", functions("cuda-3", doubled="""def doubled(values):
    host = np.array(values, dtype=np.float32, copy=True)
    if host.size:
        double_kernel[(host.size + 3) // 4, 4](host)
    return host
""")),
])
WRONG_ANSWERS["cuda-5"].extend([
    ("serial block sum skips shared memory and the barrier", functions("cuda-5", block_sum_kernel="""@cuda.jit
def block_sum_kernel(values, out):
    if cuda.threadIdx.x == 0:
        total = 0.0
        for i in range(cuda.blockIdx.x * 8, min(values.size, (cuda.blockIdx.x + 1) * 8)):
            total += values[i]
        out[cuda.blockIdx.x] = total
""")),
    ("shared writes have no barrier", changed("cuda-5", "    cuda.syncthreads()\n", "")),
])
WRONG_ANSWERS["backend-1"].append(("accepts a missing title", changed("backend-1", "payload.get('title')", "payload.get('title', 'untitled')")))
WRONG_ANSWERS["web-4"].append(("accepts a missing v2 theme", changed("web-4", '["light", "dark"].includes(p.theme)', 'true')))
WRONG_ANSWERS["data-3"] = [("accepts negative depth", changed("data-3", "    if depth < 0:\n        raise ValueError('Negative depth')\n", ""))]
WRONG_ANSWERS["foundations-5"] = [("accepts missing training statistics", changed("foundations-5", "raise ValueError('Training data cannot be empty')", "return [0 for value in values]"))]
WRONG_ANSWERS["reliability-2"] = [("unimplemented redaction", "def redact(value):\n    return None")]
WRONG_ANSWERS["interactive-4"] = [("unimplemented progress merge", "def merge_progress(state, events):\n    return None")]
WRONG_ANSWERS["web-3"] = [("always returns an empty view", "function visibleRows(rows, query) { return []; }")]
# The JavaScript bridge lesson: the Python habits that JavaScript treats differently.
WRONG_ANSWERS["web-0"] = [
    ("compares with == instead of ===", changed("web-0", "result.name === name", "result.name == name")),
    ("matches part of a name", changed("web-0", "result.name === name", "result.name.includes(name)")),
    ("returns the matching results instead of their scores", changed(
        "web-0", ".map(result => result.score)", "")),
    ("restarts the sum on each pass", changed("web-0", "    sum += score;", "    sum = score;")),
]
# The task asks for `return train, validation, test`; a list of the three lists is a different value.
WRONG_ANSWERS["foundations-4"] = [("returns a list instead of a tuple", changed(
    "foundations-4", "return (rows[:train_end], rows[train_end:val_end], rows[val_end:])",
    "return [rows[:train_end], rows[train_end:val_end], rows[val_end:]]"))]

# Python from zero. Lessons 1 and 2 check top-level variables, so their
# mistakes are whole programs; the others replace the reference functions.
WRONG_ANSWERS.update({
    "python-1": [
        ("forgets delivery", "items = 3\nprice = 2\ndelivery = 1\ntotal = items * price\n"),
        ("adds instead of multiplying", "items = 3\nprice = 2\ndelivery = 1\ntotal = items + price + delivery\n"),
        ("works out total before setting price and delivery",
         "items = 3\nprice = 0\ndelivery = 0\ntotal = items * price + delivery\nprice = 2\ndelivery = 1\n"),
    ],
    "python-2": [
        ("leaves out the brackets before squaring",
         "error = 5 - 2 ** 2\naverage = (1 + 4) / 2\nrate = (9 - 3) / (4 - 1)\n"),
        ("doubles instead of squaring",
         "error = (5 - 2) * 2\naverage = (1 + 4) / 2\nrate = (9 - 3) / (4 - 1)\n"),
        ("divides only the 4", "error = (5 - 2) ** 2\naverage = 1 + 4 / 2\nrate = (9 - 3) / (4 - 1)\n"),
    ],
    "python-3": [
        ("prints instead of returning", functions("python-3", area="""def area(width, height):
    print(width * height)
""")),
        ("adds instead of multiplying", changed("python-3", "width * height", "width + height")),
        ("squares the width", changed("python-3", "width * height", "width * width")),
    ],
    "python-4": [
        ("forgets the high side", functions("python-4", clamp="""def clamp(value, low, high):
    if value < low:
        return low
    return value
""")),
        ("returns the wrong edge", functions("python-4", clamp="""def clamp(value, low, high):
    if value < low:
        return high
    elif value > high:
        return low
    else:
        return value
""")),
        ("has no return for values inside the range", functions("python-4", clamp="""def clamp(value, low, high):
    if value < low:
        return low
    if value > high:
        return high
""")),
    ],
    "python-5": [
        ("counts positions from 1", changed("python-5", "values[-1]", "values[len(values)]")),
        ("keeps the last item", changed("python-5", "values[1:-1]", "values[1:]")),
        ("drops only the last item", changed("python-5", "values[1:-1]", "values[:-1]")),
    ],
    "python-6": [
        ("resets the total inside the loop", functions("python-6", total="""def total(values):
    for value in values:
        result = 0
        result += value
    return result
""")),
        ("returns inside the loop", functions("python-6", total="""def total(values):
    result = 0
    for value in values:
        result += value
        return result
    return result
""")),
        ("always divides by 2", functions("python-6", mean="""def mean(values):
    return total(values) / 2
""")),
    ],
    "python-7": [
        ("subtracts in the wrong order", changed("python-7", "[p - t for", "[t - p for")),
        ("keeps only the last difference", functions("python-7", differences="""def differences(predictions, targets):
    result = []
    for p, t in zip(predictions, targets):
        result = [p - t]
    return result
""")),
        ("pairs every prediction with every target", changed(
            "python-7", "for p, t in zip(predictions, targets)", "for p in predictions for t in targets")),
    ],
    "python-8": [
        ("returns a list instead of a tuple", functions("python-8", low_high="""def low_high(values):
    return [min(values), max(values)]
""")),
        ("ignores fraction", functions("python-8", split_at="""def split_at(values, fraction=0.5):
    cut = int(len(values) * 0.5)
    return values[:cut], values[cut:]
""")),
        ("loses the item at the cut", functions("python-8", split_at="""def split_at(values, fraction=0.5):
    cut = int(len(values) * fraction)
    return values[:cut], values[cut + 1:]
""")),
    ],
    "python-9": [
        ("sets every count to 1", changed("python-9", "counts.get(word, 0) + 1", "1")),
        ("skips words it has not seen yet", functions("python-9", count_words="""def count_words(words):
    counts = {}
    for word in words:
        if word in counts:
            counts[word] += 1
    return counts
""")),
        ("starts a new word at 1 before adding 1", changed("python-9", "counts.get(word, 0)", "counts.get(word, 1)")),
    ],
    "python-10": [
        ("returns the error instead of raising it", functions("python-10", safe_mean="""def safe_mean(values):
    if not values:
        return ValueError("values is empty")
    return sum(values) / len(values)
""")),
        ("returns 0 for an empty list", functions("python-10", safe_mean="""def safe_mean(values):
    if not values:
        return 0
    return sum(values) / len(values)
""")),
        ("raises a general Exception", functions("python-10", safe_mean="""def safe_mean(values):
    if not values:
        raise Exception("values is empty")
    return sum(values) / len(values)
""")),
    ],
    "python-11": [
        ("forgets the square root", functions("python-11", distance="""def distance(x, y):
    return x ** 2 + y ** 2
""")),
        ("leaves out the f before the quote", functions("python-11", describe="""def describe(name, value):
    return "{name} = {value:.2f}"
""")),
        ("rounds instead of showing 2 decimal places", functions("python-11", describe="""def describe(name, value):
    return f"{name} = {round(value, 2)}"
""")),
    ],
    "python-12": [
        ("divides the change in x by the change in y", functions("python-12", slope="""def slope(x1, y1, x2, y2):
    if x1 == x2:
        raise ValueError("x1 and x2 must differ")
    return (x2 - x1) / (y2 - y1)
""")),
        ("does not reject equal x values", functions("python-12", slope="""def slope(x1, y1, x2, y2):
    return (y2 - y1) / (x2 - x1)
""")),
        ("subtracts the x values in the other order", functions("python-12", slope="""def slope(x1, y1, x2, y2):
    if x1 == x2:
        raise ValueError("x1 and x2 must differ")
    return (y2 - y1) / (x1 - x2)
""")),
    ],
    "python-13": [
        ("fixes only the return", functions("python-13", mse="""def mse(a, b):
    total = 0
    for i in range(len(a) - 1):
        total = (a[i] - b[i]) ** 2
    return total / len(a)
""")),
        ("still skips the last position", functions("python-13", mse="""def mse(a, b):
    total = 0
    for i in range(len(a) - 1):
        total += (a[i] - b[i]) ** 2
    return total / len(a)
""")),
        ("still replaces the total", functions("python-13", mse="""def mse(a, b):
    total = 0
    for i in range(len(a)):
        total = (a[i] - b[i]) ** 2
    return total / len(a)
""")),
    ],
})

# Adversarial QA of 2026-10-08: each program is the exact submission that used to pass.
QA_WRONG_ANSWERS = {
    "python-1": [("skip printing", "items=3\nprice=2\ndelivery=1\ntotal=items*price+delivery\n")],
    "python-4": [
        ("hardcoded range", """def clamp(value, low, high):
    if value < low:
        return 0
    elif value > high:
        return high
    else:
        return value

print(clamp(15, 0, 10))
"""),
        ("hardcoded upper", """def clamp(value, low, high):
    if value < low:
        return low
    elif value > high:
        return 10
    else:
        return value

print(clamp(15, 0, 10))
"""),
    ],
    "python-5": [("pop last mutates", """def last(values):
    return values.pop()

def middle(values):
    return values[1:-1]

print(last([4, 5, 6]))
print(middle([1, 2, 3, 4]))
""")],
    "python-6": [("use forbidden sum", """def total(values):
    return sum(values)

def mean(values):
    return total(values) / len(values)

print(total([1, 2, 3]))
print(mean([2, 4]))
""")],
    "python-7": [("assume same lengths", """def differences(predictions, targets):
    return [predictions[i] - targets[i] for i in range(len(predictions))]

print(differences([3, 5], [1, 5]))
""")],
    "python-9": [
        ("normalize case", """def count_words(words):
    counts = {}
    for word in words:
        word = word.lower()
        counts[word] = counts.get(word, 0) + 1
    return counts

print(count_words(["red", "blue", "red"]))
"""),
        ("count only adjacent", """def count_words(words):
    counts = {}
    for word in words:
        counts[word] = 1 + (counts.get(word, 0) if word == words[0] else 0)
    return counts

print(count_words(["red", "blue", "red"]))
"""),
    ],
    "python-10": [("floor mean", """def safe_mean(values):
    if not values:
        raise ValueError("values is empty")
    return sum(values) // len(values)

print(safe_mean([2, 4]))
""")],
    "python-11": [("negative distance sign", """import math


def distance(x, y):
    return math.sqrt(x ** 2 + y ** 2) if x >= 0 else -math.sqrt(x ** 2 + y ** 2)

def describe(name, value):
    return f"{name} = {value:.2f}"

print(distance(3, 4))
print(describe("loss", 0.12345))
""")],
    "python-12": [
        ("floor division", """def slope(x1, y1, x2, y2):
    if x1 == x2:
        raise ValueError("x1 and x2 must differ")
    return (y2 - y1) // (x2 - x1)

print(slope(0, 1, 1, 3))
"""),
        ("reject all equal y", """def slope(x1, y1, x2, y2):
    if x1 == x2 or y1 == y2:
        raise ValueError("x1 and x2 must differ")
    return (y2 - y1) / (x2 - x1)

print(slope(0, 1, 1, 3))
"""),
    ],
    "foundations-2": [("only reject longer targets", """def mse(predictions, targets):
    if not predictions or len(predictions) < len(targets):
        raise ValueError('Expected nonempty, matching lists')
    return sum((p - t) ** 2 for p, t in zip(predictions, targets)) / len(targets)

print(mse([2, 4], [1, 6]))
""")],
    "pytorch-1": [("absolute output", """import torch

def linear_batch(x, weights, bias):
    return (x @ weights + bias).abs()

x = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
print(linear_batch(x, torch.tensor([[2.0], [1.0]]), 0.5))
""")],
    "pytorch-2": [("no PyTorch at all", "def derivative(value):\n    return 2.0 * value + 3.0\n")],
    "backend-1": [("reject valid low priority", """def parse_task(payload):
    if not isinstance(payload, dict):
        raise ValueError('Expected object')
    title = payload.get('title')
    priority = payload.get('priority', 3)
    if (
        not isinstance(title, str)
        or not title.strip()
        or type(priority) is not int
        or priority != 3 and priority != 5
    ):
        raise ValueError('Invalid task')
    return {'title': title.strip(), 'priority': priority}
""")],
    "backend-3": [("allow negative limit", """def page_after(rows, after, limit):
    if limit == 0:
        raise ValueError('Positive limit required')
    remaining = sorted((row for row in rows if row['id'] > after), key=lambda row: row['id'])
    selected = remaining[:limit]
    next_cursor = selected[-1]['id'] if len(remaining) > limit else None
    return (selected, next_cursor)
""")],
    "data-2": [
        ("allow boolean size", """def chunks(tokens, size, overlap):
    if not isinstance(size, int) or type(overlap) is not int or size <= 0 or (not 0 <= overlap < size):
        raise ValueError('Invalid chunk settings')
    result = []
    start = 0
    while start < len(tokens):
        result.append(tokens[start:start + size])
        if start + size >= len(tokens):
            break
        start += size - overlap
    return result
"""),
        ("drop partial chunk", """def chunks(tokens, size, overlap):
    if type(size) is not int or type(overlap) is not int or size <= 0 or (not 0 <= overlap < size):
        raise ValueError('Invalid chunk settings')
    result = []
    start = 0
    while start < len(tokens):
        if start + size <= len(tokens):
            result.append(tokens[start:start + size])
        if start + size >= len(tokens):
            break
        start += size - overlap
    return result
"""),
    ],
    "data-4": [("wrong denominator", """def recall_at_k(ranked, relevant, k):
    if k < 0:
        raise ValueError('Negative cutoff')
    relevant = set(relevant)
    return len(set(ranked[:k]) & relevant) / max(1,k) if relevant else 0.0
""")],
    "rl-2": [("no lower bound", """def returns(rewards, gamma):
    if gamma > 1:
        raise ValueError('Invalid discount')
    values = []
    total = 0
    for reward in reversed(rewards):
        total = reward + gamma * total
        values.append(total)
    return list(reversed(values))
""")],
    "reliability-1": [
        ("uncapped first", """def retry_delays(base, cap, attempts, budget):
    if base <= 0 or cap <= 0 or attempts < 0 or budget < 0:
        raise ValueError('Invalid retry settings')
    delays = []
    spent = 0
    delay = base
    for _ in range(attempts):
        if spent + delay > budget:
            break
        delays.append(delay)
        spent += delay
        delay = min(cap, delay * 2)
    return delays
"""),
        ("no negative base rejection", """def retry_delays(base, cap, attempts, budget):
    if base == 0 or cap <= 0 or attempts < 0 or budget < 0:
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
"""),
    ],
    "web-1": [("reset discards fields", """function counter(state, action) {
  if (action.type === "increment") {
    return {...state, count: state.count + action.amount};
  }
  if (action.type === "reset") {
    return {count: 0};
  }
  return state;
}
""")],
    "web-3": [
        ("startsWith not includes", """function visibleRows(rows, query) {
  const q = query.trim().toLowerCase();
  const matches = rows.filter(row => row.title.toLowerCase().startsWith(q));
  // filter returned a new array, so sorting it leaves rows untouched.
  return matches.sort((a, b) => b.priority - a.priority || a.id - b.id);
}
"""),
        ("lowercase query omitted", """function visibleRows(rows, query) {
  const q = query.trim();
  const matches = rows.filter(row => row.title.toLowerCase().includes(q));
  // filter returned a new array, so sorting it leaves rows untouched.
  return matches.sort((a, b) => b.priority - a.priority || a.id - b.id);
}
"""),
    ],
}
# QA suspicion: python-8 now says the input list stays unchanged.
QA_WRONG_ANSWERS["python-8"] = [("sorts the input in place", functions("python-8", low_high="""def low_high(values):
    values.sort()
    return values[0], values[-1]
"""))]
# Learner code that redefines a name the checks use must not pass wrong work.
QA_WRONG_ANSWERS["python-10"].append(("returns 0 and redefines raises", functions("python-10", safe_mean="""def safe_mean(values):
    if not values:
        return 0
    return sum(values) / len(values)
""") + "\ndef raises(*args):\n    return True\n"))
QA_WRONG_ANSWERS["web-1"].append(("fixed increment and its own equal", changed(
    "web-1", "state.count + action.amount", "state.count + 1") + "\nfunction equal() { return true; }\n"))
for lesson_id, cases in QA_WRONG_ANSWERS.items():
    WRONG_ANSWERS.setdefault(lesson_id, []).extend(cases)

# Final QA of 2026-10-08: the exact submissions that passed before the checks were tightened.
FINAL_QA_WRONG_ANSWERS = {
    "foundations-2": [("divides by the number of nonzero errors", """def mse(predictions, targets):
    if not predictions or len(predictions) != len(targets):
        raise ValueError('Expected nonempty, matching lists')
    return sum((p - t) ** 2 for p, t in zip(predictions, targets)) / sum(p != t for p,t in zip(predictions,targets))

print(mse([2, 4], [1, 6]))
""")],
    "python-8": [("starts the bounds from the first two items", """def low_high(values):
    lo, hi = values[0], values[1]
    for value in values:
        lo, hi = min(lo, value), max(hi, value)
    return lo, hi

def split_at(values, fraction=0.5):
    cut = int(len(values) * fraction)
    return values[:cut], values[cut:]

low, high = low_high([3, 1, 2])
print(low, high)
print(split_at([1, 2, 3, 4]))
""")],
    "python-3": [("truncates the area to a whole number", "def area(width,height): return int(width*height)")],
    "python-4": [("rounds the clamped value", "def clamp(value,low,high): return round(max(low,min(high,value)))")],
    "python-6": [
        ("adds the absolute values", """def total(values):
    result = 0
    for value in values:
        result += abs(value)
    return result

def mean(values):
    return total(values) / len(values)

print(total([1, 2, 3]))
print(mean([2, 4]))
"""),
        ("calls sum under another name", """from builtins import sum as add_all
def total(values): return add_all(values)
def mean(values): return total(values)/len(values)"""),
    ],
    "python-10": [("returns the absolute mean", """def safe_mean(values):
    if not values:
        raise ValueError("values is empty")
    return abs(sum(values) / len(values))

print(safe_mean([2, 4]))
""")],
    "foundations-3": [("uses a fixed learning rate of 0.1", "def step(weight,target,learning_rate): return weight if learning_rate==0 else weight-0.2*(weight-target)")],
    "tensorflow-2": [("works out the derivative without TensorFlow", "def derivative(value): return 2.0*value+3.0")],
    "cuda-2": [("wrapper never launches the kernel", """import numpy as np
from numba import cuda

@cuda.jit
def add_kernel(a, b, out):
    i = cuda.grid(1)
    if i < out.size:
        out[i] = a[i] + b[i]

def add_vectors(a, b):
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    out = np.zeros_like(a)
    if a.size:
        threads = 4
        blocks = (a.size + threads - 1) // threads
        pass
    return out
""")],
    "rl-2": [("overwrites the caller's rewards", """def returns(rewards, gamma):
    if not 0 <= gamma <= 1:
        raise ValueError('Invalid discount')
    values = []
    total = 0
    for reward in reversed(rewards):
        total = reward + gamma * total
        values.append(total)
    rewards[:] = reversed(values)
    return rewards
""")],
}
# A wrapper that launches too few blocks leaves the last elements at zero.
FINAL_QA_WRONG_ANSWERS["cuda-2"].append(("rounds the block count down", changed(
    "cuda-2", "(a.size + threads - 1) // threads", "a.size // threads")))
for lesson_id, cases in FINAL_QA_WRONG_ANSWERS.items():
    WRONG_ANSWERS.setdefault(lesson_id, []).extend(cases)

# Correct answers that a check must not reject: names that match a check helper or a
# builtin, and other ways to write a correct answer than the reference solution.
CORRECT_ANSWERS = {
    "python-1": [("prints a value before the total",
                  "items = 3\nprice = 2\ndelivery = 1\nprint(items)\ntotal = items * price + delivery\nprint(total)\n")],
    "python-5": [("copies before reading", reference("python-5").replace("values[-1]", "list(values)[-1]"))],
    "python-6": [("adds with a while loop", """def total(numbers):
    result = 0
    i = 0
    while i < len(numbers):
        result = result + numbers[i]
        i += 1
    return result

def mean(numbers):
    return total(numbers) / len(numbers)
""")],
    "python-7": [("appends in a loop", """def differences(predictions, targets):
    result = []
    for p, t in zip(predictions, targets):
        result.append(p - t)
    return result
""")],
    "python-8": [("sorts a copy", functions("python-8", low_high="""def low_high(values):
    ordered = sorted(values)
    return ordered[0], ordered[-1]
"""))],
    "python-9": [("tests membership first", """def count_words(words):
    counts = {}
    for word in words:
        if word in counts:
            counts[word] += 1
        else:
            counts[word] = 1
    return counts
""")],
    "python-10": [("correct with raises variable", """def safe_mean(values):
    if not values:
        raise ValueError("values is empty")
    return sum(values) / len(values)

print(safe_mean([2, 4]))

raises = 123
""")],
    "python-11": [("correct with abs variable", """import math


def distance(x, y):
    return math.sqrt(x ** 2 + y ** 2)

def describe(name, value):
    return f"{name} = {value:.2f}"

print(distance(3, 4))
print(describe("loss", 0.12345))

abs = 123
""")],
    "python-12": [("renamed parameters and float division", """def slope(a, b, c, d):
    if c == a:
        raise ValueError("same x")
    rise = d - b
    run = c - a
    return float(rise) / run
""")],
    "data-2": [("for loop over starts", """def chunks(tokens, size, overlap):
    if type(size) is not int or type(overlap) is not int or size < 1 or not 0 <= overlap < size:
        raise ValueError("bad settings")
    out = []
    for start in range(0, len(tokens), size - overlap):
        out.append(tokens[start:start + size])
        if start + size >= len(tokens):
            break
    return out
""")],
    "reliability-1": [("caps inside the loop", """def retry_delays(base, cap, attempts, budget):
    if base <= 0 or cap <= 0 or attempts < 0 or budget < 0:
        raise ValueError("bad settings")
    delays = []
    for n in range(attempts):
        delay = min(cap, base * 2 ** n)
        if sum(delays) + delay > budget:
            break
        delays.append(delay)
    return delays
""")],
    "web-1": [("correct with its own equal constant", reference("web-1") + "\nconst equal = 1;\n")],
    # Final QA of 2026-10-08: correct answers that reach the same function through another name.
    "pytorch-2": [("calls backward through a saved name", """import torch
backward = torch.Tensor.backward

def derivative(value):
    x = torch.tensor(float(value), requires_grad=True)
    y = x * x + 3 * x
    backward(y)
    return x.grad.item()

print(derivative(2))
""")],
    "tensorflow-2": [
        ("watches a constant and saves gradient under another name", """import tensorflow as tf
gradient = tf.GradientTape.gradient

def derivative(value):
    x = tf.constant(float(value))
    with tf.GradientTape() as tape:
        tape.watch(x)
        y = x ** 2 + 3.0 * x
    return float(gradient(tape, y, x))
"""),
    ],
    "cuda-2": [("launches through a saved configuration with 32 threads", functions("cuda-2", add_vectors="""def add_vectors(a, b):
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    out = np.zeros_like(a)
    if a.size:
        launch = add_kernel[(a.size + 31) // 32, 32]
        launch(a, b, out)
    return out
"""))],
    "rl-2": [("fills a new list from the end", """def returns(rewards, gamma):
    if gamma < 0 or gamma > 1:
        raise ValueError('gamma must be between 0 and 1')
    out = [0.0] * len(rewards)
    running = 0.0
    for i in range(len(rewards) - 1, -1, -1):
        running = rewards[i] + gamma * running
        out[i] = running
    return out
""")],
    "foundations-2": [("adds the squared errors in a loop", """def mse(predictions, targets):
    if len(predictions) == 0 or len(predictions) != len(targets):
        raise ValueError('bad lists')
    total = 0
    for i in range(len(predictions)):
        total += (predictions[i] - targets[i]) ** 2
    return total / len(predictions)
""")],
    "web-3": [("indexOf and uppercase", """function visibleRows(rows, query) {
  const wanted = query.trim().toUpperCase();
  return rows.filter(row => row.title.toUpperCase().indexOf(wanted) !== -1)
    .sort((a, b) => b.priority - a.priority || a.id - b.id);
}
""")],
}


def wrong_answer_calls():
    """The execute() calls of test_plausible_wrong_answers_fail_a_check, so they can run side by side."""
    calls = []
    for lesson_id, cases in WRONG_ANSWERS.items():
        lesson = BY_ID[lesson_id]
        if missing_lesson_modules(lesson):
            continue
        language = lesson.get("language", "python")
        prefix = JS_OFFLINE_PREFIX if language == "javascript" else OFFLINE_PREFIX
        calls += [((prefix + source, lesson["checks"]), dict(simulator=lesson["course"] == "cuda", language=language))
                  for _, source in cases]
    return calls


def correct_answer_calls():
    """The execute() calls of test_other_correct_answers_pass, so they can run side by side."""
    calls = []
    for lesson_id, cases in CORRECT_ANSWERS.items():
        lesson = BY_ID[lesson_id]
        if missing_lesson_modules(lesson):
            continue
        language = lesson.get("language", "python")
        prefix = JS_OFFLINE_PREFIX if language == "javascript" else OFFLINE_PREFIX
        calls += [((prefix + source, lesson["checks"]), dict(simulator=lesson["course"] == "cuda", language=language))
                  for _, source in cases]
    return calls


WRONG_ANSWER_RUNS = PrefetchedRuns(wrong_answer_calls)
CORRECT_ANSWER_RUNS = PrefetchedRuns(correct_answer_calls)


class WrongAnswerTests(unittest.TestCase):
    def test_plausible_wrong_answers_fail_a_check(self):
        for lesson_id, cases in WRONG_ANSWERS.items():
            lesson = BY_ID[lesson_id]
            language = lesson.get("language", "python")
            prefix = JS_OFFLINE_PREFIX if language == "javascript" else OFFLINE_PREFIX
            for name, source in cases:
                with self.subTest(lesson=lesson_id, mistake=name):
                    require_lesson_modules(self, lesson)
                    result = WRONG_ANSWER_RUNS.execute(prefix + source, lesson["checks"],
                                                       simulator=lesson["course"] == "cuda", language=language)
                    self.assertIsNone(result["error"], result)
                    self.assertFalse(result["passed"], result)
                    self.assertTrue(any(not c["passed"] for c in result["checks"]), result)

    def test_other_correct_answers_pass(self):
        for lesson_id, cases in CORRECT_ANSWERS.items():
            lesson = BY_ID[lesson_id]
            language = lesson.get("language", "python")
            prefix = JS_OFFLINE_PREFIX if language == "javascript" else OFFLINE_PREFIX
            for name, source in cases:
                with self.subTest(lesson=lesson_id, answer=name):
                    require_lesson_modules(self, lesson)
                    result = CORRECT_ANSWER_RUNS.execute(prefix + source, lesson["checks"],
                                                         simulator=lesson["course"] == "cuda", language=language)
                    self.assertIsNone(result["error"], result)
                    self.assertTrue(result["passed"], [c for c in result["checks"] if not c["passed"]])

    def test_unimplemented_work_does_not_pass_the_reported_stub_checks(self):
        cases = {
            "cuda-2": "Empty wrapper input and a working kernel",
            "cuda-3": "Doubles values and leaves host input unchanged",
            "cuda-5": "Empty wrapper input and a working block kernel",
            "cuda-6": "Empty wrapper input and a working fused kernel",
            "reliability-2": "Redacts a copy and leaves the source unchanged",
            "interactive-4": "Merges a copy and leaves the original unchanged",
            "web-3": "Sorts a copy while leaving the source order unchanged",
        }
        for lesson_id, label in cases.items():
            with self.subTest(lesson=lesson_id):
                lesson = BY_ID[lesson_id]
                require_lesson_modules(self, lesson)
                selected = [c for c in lesson["checks"] if c["label"] == label]
                self.assertEqual(len(selected), 1)
                result = execute(lesson["starter"], selected,
                                 simulator=lesson["course"] == "cuda",
                                 language=lesson.get("language", "python"))
                self.assertIsNone(result["error"], result)
                self.assertFalse(result["checks"][0]["passed"], result)


if __name__ == "__main__":
    unittest.main()
