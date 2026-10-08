# Contributing

Engineering Workshop is a personal project. Small lesson improvements, clearer explanations, better checks, and reproducible bug reports are welcome. Discuss larger features in an issue first. See [the roadmap](ROADMAP.md) for direction.

Everyone who takes part follows the [code of conduct](CODE_OF_CONDUCT.md).

## Report a problem

Use the [issue forms](https://github.com/ShmalexM/ml-workshop/issues/new/choose):

- **Bug report** for something in the app or the installer that does not work.
- **Problem with a lesson** for a wrong or unclear explanation, a check that accepts a wrong answer or rejects a correct one, or a broken example.
- **Feature or lesson idea** for something you want to learn or see in the app.

Remove personal notes, local paths and secrets from logs and screenshots before you post them. Report security problems privately, as [SECURITY.md](SECURITY.md) describes.

## Set up a clone

Install [Node.js](https://nodejs.org/en/download) 22.13 or newer (24 recommended), including npm, and [Python](https://www.python.org/downloads/) 3.12 or newer. CI uses Python 3.12. [uv](https://docs.astral.sh/uv/getting-started/installation/) is optional; setup uses it when available and otherwise uses Python's built-in `venv` and pip. On Linux, your distribution may also require its `python3-venv` package.

Clone this repository, then use the setup wrapper for your OS. Allow several GB for a full ML install. Internet is needed for installation; installed lessons run offline. Setup creates `.venv`, installs packages, builds the interface, and opens your browser. It does not install Python packages globally. Rerun setup after updating or to repair dependencies; your saved progress is kept.

To update a clone, export your progress, stop the app, run `git pull --ff-only`, then rerun setup. If you are developing on a branch, commit or stash your source edits before integrating updates. Setup preserves `data/`.

### macOS

On Apple silicon, setup uses the pinned `requirements.lock` snapshot. On Intel Macs, run setup with `--no-ml`: current PyTorch and TensorFlow releases no longer ship Intel macOS packages. With Homebrew, `brew install node uv` provides the prerequisites; the macOS wrapper can use uv to obtain Python 3.12.

```sh
git clone https://github.com/ShmalexM/ml-workshop.git
cd ml-workshop
./"Setup ML Workshop.command"
```

On future visits, double-click **Open ML Workshop.command**. Double-click **Stop ML Workshop.command** to stop the server. The existing filenames are kept for compatibility.

### Linux

```sh
git clone https://github.com/ShmalexM/ml-workshop.git
cd ml-workshop
./setup.sh
```

Use `./start.sh` to open Engineering Workshop and `./stop.sh` to stop it. Use `./start.sh --no-open` to start the server without opening a browser.

### Windows 10 or 11

Install Python with its launcher or add Python to PATH, and install Node.js including npm. Reopen your terminal after installation. Clone or extract the repository, then double-click **Setup Engineering Workshop.cmd**. On future visits, use **Open Engineering Workshop.cmd** and **Stop Engineering Workshop.cmd**.

The `.cmd` files call the accompanying PowerShell scripts with `-ExecutionPolicy Bypass -File`; they do not change the machine's execution policy. From PowerShell you can also run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\start.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\stop.ps1
```

### Light install and local settings

Pass `--no-ml` to setup to skip PyTorch, TensorFlow, Transformers, tokenizers, LangChain, LlamaIndex, and Numba. Engineering lessons and book imports remain available. Lessons that need an omitted module explain how to install it. Rerun setup without `--no-ml` to add those packages. A light setup does not remove packages already installed. Pass `--no-launch` to install and build without starting the server:

```sh
./setup.sh --no-ml --no-launch                     # Linux
./"Setup ML Workshop.command" --no-ml --no-launch  # macOS
```

```powershell
.\"Setup Engineering Workshop.cmd" --no-ml --no-launch
```

Once running, open http://127.0.0.1:7318. Closing the browser leaves the local server running. Set `ML_WORKSHOP_PORT` to use another port and `ML_WORKSHOP_DATA_DIR` to keep progress, logs, and the PID file in another directory. Use the same settings when starting and stopping. Relative data paths are resolved against the checkout directory. These settings apply to the browser launchers; the native Mac window uses the default configuration.

### Native Mac window

After setup, double-click **Install Mac App.command** once. It builds **Engineering Workshop.app** in your user Applications folder and adds a Desktop shortcut. Open it like any other Mac app; it starts the local server automatically and uses your existing lessons, books and progress. Right-click its Dock icon → **Options → Keep in Dock** for permanent access.

The native window supports code exercises, book reading, normal copy/paste shortcuts, **⌘R** to reload, and **⌘Q** to quit. Closing the window keeps the app available in the Dock; click its icon to reopen. External references open in your default browser. Quitting the app leaves the shared local server running, so an open browser session continues to work.

**Install Mac App.command** needs macOS 13 or newer and the Apple command-line tools (`xcode-select --install`). It uses a local ad-hoc signature. No paid Apple developer membership is needed for this local build. Keep the project folder in place; if you move it, run **Install Mac App.command** again. The native window and its installer are macOS-only.

### Platform support

| Platform | Verification | Exercise limits |
| --- | --- | --- |
| macOS, Apple silicon | By hand, and in CI: build, the full suite including ML lessons, and the one-line installer | 50-second wall timeout, 40/45-second CPU limits, 1 MiB file-size limit |
| Linux | CI: build, all non-ML tests, and the one-line installer | Same limits as macOS |
| Windows 10/11 | CI (`windows-latest`): build, all non-ML tests, and the one-line installer | 50-second wall timeout; **no CPU or file-size limit** |

All platforms cap returned output at 24,000 bytes and clean up exercise process trees. Windows CI uses GitHub's hosted Windows image, not separate Windows 10 and 11 desktop machines. CI installs the ML libraries only on Apple silicon macOS; on Linux, Windows and Intel Macs, package availability depends on the Python version and architecture.

### Troubleshooting a clone

- **Setup cannot find Python or Node/npm:** install the prerequisites, reopen your terminal, and rerun setup. uv is optional.
- **Frontend not built or packages missing:** rerun setup from the checkout directory.
- **Port 7318 is in use:** stop the program that uses it, or set `ML_WORKSHOP_PORT` to an unused port. If it is another Engineering Workshop server, the launcher opens that server.

## Develop locally

Work on a branch. The interface uses React, TypeScript, Vite, and CodeMirror. The backend uses Python's HTTP server and SQLite. JavaScript lessons use the already-required Node runtime and its built-in modules. ML packages load only inside exercise processes.

```sh
npm run build     # Type-check and build the frontend
npm test          # Test every lesson, runner behavior, and the local API
npm run dev       # Rebuild on edits; refresh the running app in your browser
```

To edit the frontend, start the app and run `npm run dev`. It watches and rebuilds `dist/`. Refresh http://127.0.0.1:7318 after a change. Serving the UI and API from one origin preserves the local server's request checks. For backend edits, stop and restart with your OS wrappers: `stop.sh`/`start.sh` on Linux, `stop.ps1`/`start.ps1` on Windows, or the Stop/Open `.command` files on macOS. `npm start -- --no-open` starts the browser server without opening a browser. Use the same `ML_WORKSHOP_PORT` and `ML_WORKSHOP_DATA_DIR` values for launch and stop.

## Add a lesson

Lessons live in `backend/python_course.py`, `backend/courses.py`, `backend/extra_lessons.py` and `backend/engineering_courses.py`. The public schema is described by `src/types.ts`; start from a nearby lesson.

1. Give the lesson a stable, unique ID. Progress is keyed by ID, so preserve existing IDs.
2. Explain one concept with a worked case, three diagram steps, three tasks, and three hints that go from a nudge to nearly the answer. Define each term where it is first used. Link to primary documentation.
3. Include starter code with a runnable demo call and a reference solution that uses the starter's names. The starter must run without an error and fail the checks; the solution must pass.
4. Add three to five checks that exercise behavior across inputs. Include a boundary case and reject plausible wrong implementations; avoid checking source spelling. Add those wrong implementations to `tests/test_wrong_answers.py`.
5. Keep exercises small, deterministic, offline, and within the runner's limits. No downloads, API credentials, telemetry, or paid services. Label synthetic data and simulated hardware accurately.
6. Add a small worked example, exact expected output, two value-tracing steps and a three-choice prediction question in `backend/lesson_guides.py`. Teach a smaller case before asking the learner to generalize. The question asks what the example prints after one small change: add that change to `PREDICTIONS` in `tests/test_guides.py`, and vary which choice (A, B or C) is correct.
7. If you add or remove lessons, update the lesson-count assertions in `tests/test_curriculum.py` and `tests/test_api.py`. Also update the counts in the README (the opening paragraph and the table in What's inside), `ROADMAP.md`, and `docs/architecture.md`.

For JavaScript, set `language="javascript"`; checks are JavaScript expressions and the runner exposes `equal(a,b)` for JSON-compatible values. Python remains the default. Node.js must be available for API tests that run web lessons. Keep public exercises reusable; store personal project mappings in the ignored catalog described in [project learning](docs/project-learning.md).

## Add a public project

Edit `backend/public_projects.json` with a public repository, verified starting-file URL, prerequisites, preparation lesson and a few walkthrough steps. Start with a source slice instead of requiring an entire stack. See [project learning](docs/project-learning.md). Keep your own project list in the ignored `data/portfolio.json`.

## Add a reading guide

`backend/book_study.py` contains the reading guides, linked to stable lesson IDs and local book locations. EPUB locations resolve by section key; PDF locations count physical pages. Keep source book text and images out of commits. Use synthetic documents in tests. See [local library documentation](docs/local-library.md) for storage, import, and quality boundaries.

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

The suite checks solutions and starters, plausible wrong answers, worked examples and prediction questions, persistence, runner limits, process cleanup, and API guards. Launcher/API integration tests choose unused loopback ports and disposable databases. POSIX-only checks skip on Windows. Lessons whose required Python modules are absent skip using `importlib.util.find_spec`; setup with `--no-ml` lets you run all other tests. Set `ML_WORKSHOP_REQUIRE_ML=1` for a full-install check that fails on missing lesson modules.

`npm test` and `npm start` use the checkout's `.venv` on every OS. For a quick API-only check, run `node scripts/py.mjs -m unittest discover -s tests -p test_api.py -v`.

CI runs on every pull request and every push to `main`. The macOS job builds the frontend and runs the full suite, including every ML lesson, on Apple silicon with Python 3.12. The Linux and Windows jobs run light setup, build, and all non-ML tests. An installer job packages a release with `scripts/package_release.py` and installs it on macOS, Linux and Windows without the ML libraries. It then runs `tests/check_install.py`, updates the copy and uninstalls it. To try the installer locally, package a release, then run `EW_ARCHIVE=release/engineering-workshop.tar.gz EW_HOME=<temporary folder> EW_LIGHT=1 EW_NO_LAUNCH=1 EW_NO_SHORTCUTS=1 sh install.sh`. CI does not install the ML libraries with the installer, or on Linux and Windows. It does not test desktop browser integration or NVIDIA hardware. Windows exercises have a wall timeout and returned-output cap, but no CPU or file-size limit. For UI changes, check both desktop and narrow layouts and each lesson stage: Understand, See an example, and Try it yourself.

## Publish a release

Raise `version` in `package.json`, add the changes to [CHANGELOG.md](CHANGELOG.md), and merge to `main`. The release workflow then publishes `v<version>` with the archives the install command downloads, and installs it on macOS, Linux and Windows with the public command as a final check. Pushing a tag such as `v1.2.0` also works; a tag with a hyphen makes a prerelease.

`docs/social-preview.png` (1280×640) is the image that link previews show. It is set in the repository's GitHub settings, so replace it there when it changes.

## Pull requests

Keep generated files, learner progress, notes, logs, and credentials out of commits. The [pull request template](.github/PULL_REQUEST_TEMPLATE.md) lists what to include: what changed, why, and what you tested. Contributions are provided under the project's MIT license.
