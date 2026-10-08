"""Runs a test's exercise checks side by side.

Each check runs in its own subprocess, as in the app, so running several at once gives the
same results as running them one after another. The tests still assert on every result in
lesson order.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import os
import threading

from runner import execute


def worker_count():
    # Many lessons import PyTorch or TensorFlow in the child. Leave half the cores free, and stay
    # sequential on small CI runners, where a cold import already takes a long time.
    return max(1, min(6, (os.cpu_count() or 1) // 2))


class PrefetchedRuns:
    """execute() with results computed ahead: the first call starts every call that plan() lists.

    A call that plan() did not list runs directly, so a mismatch costs time, never coverage.
    """

    def __init__(self, plan):
        self.plan = plan
        self.futures = None
        self.lock = threading.Lock()

    @staticmethod
    def key(args, kwargs):
        return json.dumps([list(args), kwargs], sort_keys=True)

    def execute(self, *args, **kwargs):
        if worker_count() == 1:
            return execute(*args, **kwargs)
        with self.lock:
            if self.futures is None:
                pool = ThreadPoolExecutor(worker_count())
                self.futures = {}
                for call_args, call_kwargs in self.plan():
                    key = self.key(call_args, call_kwargs)
                    if key not in self.futures:
                        self.futures[key] = pool.submit(execute, *call_args, **call_kwargs)
                pool.shutdown(wait=False)
            future = self.futures.pop(self.key(args, kwargs), None)
        return future.result() if future else execute(*args, **kwargs)
