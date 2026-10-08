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
from test_curriculum import OFFLINE_PREFIX, JS_OFFLINE_PREFIX, require_lesson_modules


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


class WrongAnswerTests(unittest.TestCase):
    def test_plausible_wrong_answers_fail_a_check(self):
        for lesson_id, cases in WRONG_ANSWERS.items():
            lesson = BY_ID[lesson_id]
            language = lesson.get("language", "python")
            prefix = JS_OFFLINE_PREFIX if language == "javascript" else OFFLINE_PREFIX
            for name, source in cases:
                with self.subTest(lesson=lesson_id, mistake=name):
                    require_lesson_modules(self, lesson)
                    result = execute(prefix + source, lesson["checks"],
                                     simulator=lesson["course"] == "cuda", language=language)
                    self.assertIsNone(result["error"], result)
                    self.assertFalse(result["passed"], result)
                    self.assertTrue(any(not c["passed"] for c in result["checks"]), result)

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
