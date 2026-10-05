# ML Workshop

[![CI](https://github.com/ShmalexM/ml-workshop/actions/workflows/ci.yml/badge.svg)](https://github.com/ShmalexM/ml-workshop/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Learn ML engineering by writing and running Python. **30 hands-on lessons** take you from ML fundamentals through PyTorch, TensorFlow, modern AI frameworks, and CUDA Python—with hints, worked solutions, notes, practice, and saved progress.

Built for an experienced programmer learning ML. Inspired by the learn-by-doing format of Boot.dev, with original curriculum and interface. This is an independent project with no affiliation with Boot.dev or the framework authors.

![ML Workshop lesson workspace](docs/desktop-screenshot.jpg)

## Quick start: macOS with Apple Silicon

The full application is tested on Apple Silicon Macs with Python 3.12. Windows is not supported yet; full Linux setup is on the [roadmap](ROADMAP.md). Allow several GB of disk space for ML packages. Internet is needed for the first installation; installed lessons run offline.

1. Install [Node.js](https://nodejs.org/en/download) (22.13 or newer; 24 recommended) and [uv](https://docs.astral.sh/uv/getting-started/installation/). If you already use Homebrew: `brew install node uv`.
2. Clone and set up:

   ```sh
   git clone https://github.com/ShmalexM/ml-workshop.git
   cd ml-workshop
   ./"Setup ML Workshop.command"
   ```

   Setup installs Python 3.12 if needed, creates a project virtual environment, installs pinned dependencies, builds the interface, and opens your browser. It does not install Python packages globally.

3. On future visits, double-click **Open ML Workshop.command** in Finder. To add a native app in your user Applications folder and a Desktop shortcut, run once:

   ```sh
   .venv/bin/python scripts/install-launcher.py
   ```

   Then double-click **ML Workshop** to learn. The optional launcher points to this checkout; keep it in the same location. The installer preserves any existing launcher. If you move the checkout, move the old launcher aside before reinstalling.

Once running, open **http://127.0.0.1:7318**. No account, API key, Docker, or cloud service is needed. Closing the browser leaves the local server running; double-click **Stop ML Workshop.command** to stop it. The `.command` files can also be run from Terminal as shown above. Rerun Setup to repair dependencies or rebuild after updating.

## What you'll learn

| Track | Lessons | Topics |
| --- | ---: | --- |
| ML foundations | 6 | Predictions, loss, gradients, data splitting, and training |
| PyTorch | 6 | Tensors, broadcasting, autograd, modules, optimization, and inference |
| TensorFlow | 6 | Tensors, GradientTape, Keras, training, datasets, and inference |
| Modern AI stack | 6 | Hugging Face, tokenization, LangChain, LlamaIndex, and retrieval |
| CUDA Python | 6 | Thread/block indexing, bounds, transfers, 2D kernels, and shared memory |

```mermaid
flowchart LR
  A[Read a concept] --> B[Edit Python]
  B --> C[Run and inspect]
  C --> D[Check assertions]
  D -->|Needs work| E[Reveal a hint]
  E --> B
  D -->|Pass| F[Save progress and continue]
```

Use **Run code** (⌘ Enter) to inspect output, then **Check answer** (⌘ Shift Enter) for feedback and XP. XP is awarded once per lesson. You can browse any lesson, reveal hints gradually, inspect solutions, and revisit completed work in Practice. See the [learning guide](docs/learning-plan.md).

## Read alongside your exercises

The **Books** area imports your own PDF and EPUB files with search, chapter navigation, bookmarks, notes, and saved reading position. Modal’s *GPU Glossary* and Philip Kiely’s *Inference Engineering* have 15 guided reading stops connected to the exercises. EPUB images keep their original bytes; PDFs retain their vectors, fonts, and images, with zoom rendered from the source.

Books stay local and are not bundled with this repository. See [local library setup and quality notes](docs/local-library.md).

## Your progress stays local

Drafts and notes are cached in the browser and synchronized to SQLite. Completions are saved by the server after checks pass. Your durable state lives in `data/workshop.sqlite3`.

**Settings → Export progress & notes** writes JSON to `data/backups/` and offers a download, including book notes, bookmarks, and reading positions. The JSON does not include imported book files. Keep this backup somewhere safe. JSON import is planned; for a full current restore, stop the app and restore a copy of the entire `data/` folder made while the server was stopped. Git ignores your data, notes, exports, logs, and environment files.

To update, export progress, stop the app, run `git pull --ff-only`, then rerun Setup. If you are developing on a branch, commit or stash your source edits before integrating updates. Setup preserves `data/`.

## CUDA without an NVIDIA GPU

CUDA Python exercises use **Numba's CPU simulator**. They teach kernel structure and indexing on a Mac. They do not run on an NVIDIA GPU or qualify device compilation, races, warp behavior, occupancy, or performance. Real GPU execution and CUDA C++ are future additions. See [CUDA notes and limitations](docs/cuda-notes.md).

Framework lessons execute real libraries with small local inputs. They do not download pretrained models, call an LLM API, or claim that a tiny exercise establishes production model quality.

## Execution model

**This is a trusted personal-code runner, not a security sandbox.** Python runs with your account's filesystem and network permissions. Run code you trust and keep the service local.

The server binds to `127.0.0.1`, checks Host/Origin, and requires a per-session token for writes. Each exercise runs in a fresh Python process and temporary directory with a 50-second wall timeout, CPU/output limits, and process-group cleanup. Only one exercise runs at a time. See [architecture](docs/architecture.md) and [security](SECURITY.md).

## Develop and contribute

The interface uses React, TypeScript, Vite, and CodeMirror. The backend uses Python's HTTP server and SQLite. ML packages load only inside exercise processes.

```sh
npm run build     # Type-check and build the frontend
npm test          # Test every lesson, runner behavior, and the local API
npm run dev       # Rebuild on edits; refresh the running app in your browser
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development workflow, lesson authoring, and verification. The [roadmap](ROADMAP.md) tracks areas to grow. Bug reports and ideas are welcome in [Issues](https://github.com/ShmalexM/ml-workshop/issues).

## Troubleshooting

- **Setup cannot find uv/npm:** install the prerequisites, reopen Terminal, and rerun Setup.
- **Frontend not built or packages missing:** rerun Setup from the checkout directory.
- **Port 7318 is occupied:** stop the other process using that port or the other ML Workshop instance. The launcher reuses an existing ML Workshop server.
- **Session expired after restart:** reload the browser to get a fresh session token.
- **Unexpected failure:** inspect `data/server.log`. Remove personal information before sharing logs.

## License

[MIT](LICENSE). Dependencies retain their respective licenses. The curriculum and interface are original, AI-assisted work, with links to official documentation for deeper study.
