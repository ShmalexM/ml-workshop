# Changelog

This file lists the notable changes in each release. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and version numbers follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.2] - 2026-10-06

### Fixed

- The install download now includes the license texts of the npm packages compiled into the app. The build had stripped some of them, such as the CodeMirror and Lezer notices. `npm run build` now collects them in `dist/THIRD_PARTY_LICENSES.txt`.

### Added

- An **Open-source licenses** link in Settings that opens `THIRD_PARTY_LICENSES.txt`.

### Changed

- The install download no longer includes pdf.js's engine for scripts inside PDFs (QuickJS). The app never ran PDF scripts.

## [1.1.1] - 2026-10-06

### Fixed

- Much less glare in the Hero game. Bright lights and bloom washed out the hero and the arena, most of all with Legendary gear. Lights, bloom and glowing gear are now toned down, and the armory no longer applies bloom to the whole scene.
- `/api/health` reported version 1.0 in every release. It now reports the version in `package.json`.

### Changed

- The hero in the armory no longer turns by itself. Drag to turn it. With reduced motion turned on in your system settings, the hero and the ring under it stay still.
- The install download no longer includes the screenshots in `docs/`, about 540 KB of images.

## [1.1.0] - 2026-10-06

### Added

- Seven new paths: Agent harness engineering, Backend & API engineering, Web app engineering, Reinforcement learning, Data & retrieval engineering, Shipping & reliability, and Interactive & native systems. The app now has 58 lessons in 12 paths.
- JavaScript exercises. The four Web app engineering lessons run in Node.js.
- A worked example in every lesson. Lessons now have three stages: Understand, See an example and Try it yourself. A prediction question asks what the example prints after one small change.
- Projects: 12 public repositories, each with a preparation lesson, a starting file and three walkthrough steps. Notes and finished steps are saved locally.
- Books: a reader for PDF and EPUB files that you import from your own copies with `scripts/import-books.py`. It has search, a table of contents, bookmarks, notes and a saved reading position. 15 reading guides link sections of *GPU Glossary* and *Inference Engineering* to lessons.
- A native Mac window for clones. **Install Mac App.command** builds it on your Mac.
- Windows and Linux support for clones, with setup, start and stop scripts for each system. On Windows, exercises have the time and output limits but no CPU or file-size limit.
- A one-line install for macOS, Linux and Windows. It needs no admin rights and puts everything in one folder. Run it again to update; your progress is kept. The uninstall command removes the app and keeps your progress, unless you add `--purge` (`-Purge` on Windows).
- Release archives with SHA-256 checksums for the installer. A release is published when the version in `package.json` changes on `main`.
- The optional Hero game. Finished lessons, paths, project walkthroughs and reading guides earn chests of gear and arena battles. You can turn it off in Settings.
- Line numbers and Python highlighting in solutions, and **Compare with my code**, which marks the lines that differ from your draft.
- Status filters on **All lessons**: not started, in progress and completed.
- A timer and a small loader while code runs.
- A status dot in the header that turns red when the local server stops responding.
- THIRD_PARTY_NOTICES.md for the components adapted from beautiful-ui (MIT).

### Changed

- The app is now called Engineering Workshop. The repository and the macOS launcher files keep the older ML Workshop name.
- All 58 lessons are rewritten in plain language. Each term is defined where it first appears. Hints go from a nudge to nearly the answer, and every starter has a demo call that runs.
- Stronger checks: 235 checks in 58 lessons, up from 103 in 30. The CUDA checks launch the learner's own kernel. Tests make sure that 34 plausible wrong answers across 26 lessons each fail a check.
- Plain-language text in the app shell, Settings and error messages.
- Progress exports (version 3) also include project notes, the project catalog, reading state and Hero game data.
- CI builds the app and runs the tests on macOS, Linux and Windows, and tests the one-line installer on all three.

### Fixed

- After a server restart, saves failed until you reloaded the page. The app now gets a new session token and retries the save.
- An error in the interface left a blank window. The app now shows a message with a reload button.

## [1.0.0] - 2026-10-05

First public release.

### Added

- 30 Python lessons in five paths: ML foundations, PyTorch, TensorFlow, Modern AI stack and CUDA & GPU programming. Each lesson has hints, a solution, notes and XP.
- A local runner. Each exercise runs in a new Python process in a temporary folder, with a 50-second time limit and CPU and output limits. The runner also stops any child processes.
- CUDA exercises that run in Numba's CPU simulator, so you do not need an NVIDIA GPU.
- Progress, drafts and notes saved in a local SQLite database, with a JSON export.
- Setup and launch scripts for Apple silicon Macs, and an optional launcher in your Applications folder.
- CI that runs every lesson on macOS and the API tests on Linux.

[1.1.2]: https://github.com/ShmalexM/ml-workshop/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/ShmalexM/ml-workshop/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/ShmalexM/ml-workshop/compare/a493fba...v1.1.0
[1.0.0]: https://github.com/ShmalexM/ml-workshop/tree/a493fba31f2016f17edeb1bc551db9e0d46b498d
