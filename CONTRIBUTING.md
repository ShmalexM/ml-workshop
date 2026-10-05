# Contributing

ML Workshop is a personal learning project that grows through use. Small lesson improvements, clearer explanations, better checks, and reproducible bug reports are welcome. Discuss larger features in an issue first. See [the roadmap](ROADMAP.md) for direction.

## Develop locally

Follow the [setup instructions](README.md#quick-start-macos-with-apple-silicon). Work on a branch. To edit the frontend, start the app and run:

```sh
npm run dev
```

This watches and rebuilds `dist/`. Refresh `http://127.0.0.1:7318` after a change. Serving the UI and API from one origin preserves the local server's request checks. For backend edits, stop the app with `./"Stop ML Workshop.command"` and restart it with `./"Open ML Workshop.command"`.

## Add a lesson

Lessons live in `backend/courses.py`, `backend/courses_extra.py`, and `backend/extra_lessons.py`. The public schema is described by `src/types.ts`; start from a nearby lesson.

1. Give the lesson a stable, unique ID. Progress is keyed by ID, so preserve existing IDs.
2. Explain one concept with a concrete example, three diagram steps, three tasks, and three graduated hints. Link to primary documentation.
3. Include runnable starter code and a worked solution. The starter should fail the checks, and the solution should pass.
4. Add three to five checks that exercise behavior across inputs. Include a boundary case and reject plausible wrong implementations; avoid checking source spelling.
5. Keep exercises small, deterministic, offline, and within the runner's limits. No downloads, API credentials, telemetry, or paid services. Label synthetic data and simulated hardware accurately.
6. Update lesson-count assertions in `tests/test_curriculum.py` and `tests/test_api.py`, plus the README's curriculum table, if adding/removing lessons.

## Verify

```sh
npm run build
npm test
```

The full suite runs every solution and starter, denies network access in curriculum checks, and exercises persistence, execution limits, and API guards using a disposable database. A quick backend check without ML packages is:

```sh
python3 -m unittest discover -s tests -p test_api.py -v
```

CI builds the frontend and runs the full suite on an Apple Silicon macOS runner with Python 3.12. It also runs the dependency-free API suite on Linux. This does not qualify the complete application on Linux or on NVIDIA hardware. For UI changes, check both desktop and narrow layouts and the read → edit → run → check flow.

Keep generated files, learner progress, notes, logs, and credentials out of commits. Include what changed, why, and what you tested in your pull request. Contributions are provided under the project's MIT license.
