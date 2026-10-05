# Contributing

Engineering Workshop is a personal learning project that grows through use. Small lesson improvements, clearer explanations, better checks, and reproducible bug reports are welcome. Discuss larger features in an issue first. See [the roadmap](ROADMAP.md) for direction.

## Develop locally

Follow the [setup instructions](README.md#install). Work on a branch. To edit the frontend, start the app and run:

```sh
npm run dev
```

This watches and rebuilds `dist/`. Refresh `http://127.0.0.1:7318` after a change. Serving the UI and API from one origin preserves the local server's request checks. For backend edits, stop and restart with your OS wrappers: `stop.sh`/`start.sh` on Linux, `stop.ps1`/`start.ps1` on Windows, or the existing Stop/Open `.command` files on macOS. `npm start -- --no-open` starts the browser server without opening a browser. Use the same `ML_WORKSHOP_PORT` and `ML_WORKSHOP_DATA_DIR` values for launch and stop.

## Add a lesson

Lessons live in `backend/courses.py`, `backend/courses_extra.py`, `backend/extra_lessons.py`, and `backend/engineering_courses.py`. The public schema is described by `src/types.ts`; start from a nearby lesson.

1. Give the lesson a stable, unique ID. Progress is keyed by ID, so preserve existing IDs.
2. Explain one concept with a concrete example, three diagram steps, three tasks, and three graduated hints. Link to primary documentation.
3. Include runnable starter code and a worked solution. The starter should fail the checks, and the solution should pass.
4. Add three to five checks that exercise behavior across inputs. Include a boundary case and reject plausible wrong implementations; avoid checking source spelling.
5. Keep exercises small, deterministic, offline, and within the runner's limits. No downloads, API credentials, telemetry, or paid services. Label synthetic data and simulated hardware accurately.
6. Add a small worked example, exact expected output, two value-tracing steps and a three-choice prediction question in `backend/lesson_guides.py`. Teach a smaller case before asking the learner to generalize; test the output with the real runner.
7. Update lesson-count assertions in `tests/test_curriculum.py` and `tests/test_api.py`, plus the README's curriculum table, if adding/removing lessons.

For JavaScript, set `language="javascript"`; checks are JavaScript expressions and the runner exposes `equal(a,b)` for JSON-compatible values. Python remains the default. Node.js must be available for API tests that run web lessons. Keep public exercises reusable; store personal project mappings in the ignored catalog described in [project learning](docs/project-learning.md).

## Add a public project

Edit `backend/public_projects.json` with a public repository, verified starting-file URL, prerequisites, preparation lesson and a focused walkthrough. Start with a source slice instead of requiring an entire stack. See [project learning](docs/project-learning.md). Private inventories belong only in ignored local overrides.

## Add a reading guide

`backend/book_study.py` contains original study prompts linked to stable lesson IDs and local book locations. EPUB locations resolve by section key; PDF locations count physical pages. Keep source book text and images out of commits. Use synthetic documents in tests. See [local library documentation](docs/local-library.md) for storage, import, and quality boundaries.

`npm run build` and `npm run dev` copy the installed PDF.js fonts, character maps, and decoders into ignored build assets; no CDN is required.

## Verify

Run tests with disposable storage. On macOS/Linux:

```sh
TEST_DATA=$(mktemp -d "${TMPDIR:-/tmp}/workshop-tests.XXXXXX")
export ML_WORKSHOP_DATA_DIR="$TEST_DATA"
npm run build
npm test
```

On Windows (PowerShell):

```powershell
$env:ML_WORKSHOP_DATA_DIR = Join-Path ([System.IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString())
New-Item -ItemType Directory $env:ML_WORKSHOP_DATA_DIR | Out-Null
npm run build
npm test
```

The suite checks solutions and starters, worked examples, persistence, runner limits, process cleanup, and API guards. Launcher/API integration tests choose unused loopback ports and disposable databases. POSIX-only checks skip on Windows. Lessons whose required Python modules are absent skip using `importlib.util.find_spec`; setup with `--no-ml` lets you run all other tests. Set `ML_WORKSHOP_REQUIRE_ML=1` for a full-install check that fails on missing lesson modules.

`npm test` and `npm start` use the checkout's `.venv` on every OS. For a quick API-only check, run `node scripts/py.mjs -m unittest discover -s tests -p test_api.py -v`.

CI builds the frontend and runs the full suite on Apple Silicon macOS with Python 3.12. Linux and Windows jobs run light setup, build, and all non-ML tests; their first run with these changes is pending. This does not qualify full framework installs, desktop browser integration on those platforms, or NVIDIA hardware. Windows exercises have a wall timeout and returned-output cap, but no CPU or file-size limit. For UI changes, check both desktop and narrow layouts and the read → edit → run → check flow.

Keep generated files, learner progress, notes, logs, and credentials out of commits. Include what changed, why, and what you tested in your pull request. Contributions are provided under the project's MIT license.
