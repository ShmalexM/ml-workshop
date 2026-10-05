"""Plausible wrong implementations must fail a lesson's executable checks.

The first 23 cases reproduce the curriculum audit. Extra cases cover device
transfers, shared memory, missing inputs, and checks that used to accept stubs.
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
