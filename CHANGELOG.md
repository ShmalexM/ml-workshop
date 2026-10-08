# Changelog

This file lists the notable changes in each release. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and version numbers follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- An optional AI assistant, off by default. You bring the model: Ollama or LM Studio on this computer, or OpenRouter, OpenAI or another OpenAI-compatible service with your own API key. Set it up in **Settings → AI assistant**, then open it with **Ask** in the header or ⌘J (Ctrl+J). In a lesson, chips show what is sent with a question: the lesson and stage, the worked example without its answer, your code, the last run and the hints you opened. Notes are off by default, and other pages send only the page name. **Explain this error** next to an error or a failed check opens the assistant with a question ready to send. Tutor mode gives one hint at a time and no full solution unless **Allow full solutions** is on. The local server forwards the request and streams the answer, and **Stop** ends it. The API key is saved in `data/assistant.json` (`0600`), is never shown again or exported, and uninstall deletes it.
- Python from zero, a new first path of 13 lessons for people who have never written code. It starts with `print` and variables, then covers arithmetic, functions, `if`, lists and slices, `for` loops, `zip` and list comprehensions, tuples, dictionaries, tracebacks and `raise ValueError`, f-strings and `import`, the slope between two points, and fixing a broken function. It ends where ML foundations lesson 1 begins.
- From Python to JavaScript, a new first lesson in Web app engineering. It shows the JavaScript forms of the Python from zero basics: `let` and `const`, functions and arrow functions, arrays, objects, `===`, `map` and `filter`, and `console.log`. Web app engineering now lists Python from zero as its suggested first path. The app now has 72 lessons in 13 paths.
- A glossary of 143 terms: the three each path introduces, the Python words the lessons use (variable, function, parameter, list, dictionary, loop, exception, class and more), the JavaScript basics, and ML and engineering terms such as tensor, gradient, loss, batch, epoch, embedding, idempotency and latency. Each definition is one or two sentences. In the lesson text, a term is a dotted-underline button where it first appears; it opens the definition and a link to the lesson that teaches it, and Escape closes it. The lesson drawer has a **Glossary** view with a search box, also opened by the **Glossary** button next to **Lessons**.
- **You’ll use** at the top of Understand, closed at first. It lists the Python constructs the lesson's starter and solution use, such as `def`, `zip`, list comprehensions, slicing and `raise`, each linked to the Python from zero lesson that teaches it and marked when that lesson is done. Constructs that no lesson teaches, such as `class`, `lambda` and `with`, link to the Python documentation. Web lessons list their JavaScript, linked to From Python to JavaScript or to MDN. The server finds the constructs with Python's `ast` module and builds the list once.
- A question on the Paths page for new learners: "Have you written Python before?" **No** opens Python from zero, and **Yes** hides the question. The answer is saved in the browser. It shows only when you have no saved work.
- A line on the Paths page, under the opening text, that says most paths assume the basics from Python from zero and links to it. It stays after the first-run question is answered.

### Changed

- ML foundations and the other Python paths list Python from zero as a suggested first path, and the ML & GPU engineer order starts with it.
- ML foundations lesson 2 explains the Python in its code: the worked example pairs the lists with `zip` in one step and squares the errors in a second, and the explanation names `zip`, unpacking, `**` and `raise`. Lessons 3 and 6 show where their gradient formulas come from.
- The Terms box on each path's first lesson takes its definitions from the glossary. Python from zero lesson 13 says "They do not stop the program" instead of "None of them stops the program", so that None links only to the Python value.
- In the Hero game, Python from zero lessons earn the smallest chests: the first seven earn a Worn Footlocker.
- The lesson list is a drawer, opened with **Lessons** next to the back link. From 1440px it sits beside the lesson and remembers when you close it; on smaller screens it opens over the lesson.
- The right panel follows the lesson stage: none in Understand, the worked example in See an example, and the editor in Try it yourself. The line between the lesson text and the editor can be dragged.
- Try it yourself starts with the tasks and hints. The formula and explanation from Understand are in **Recap of the idea**, closed at first.
- **Show solution** is no longer at the top of every lesson. It is the last step after the hints and stays at the end of the exercise.
- The code editor, worked examples and solutions are light by default. **Settings → Editor** has a dark background option.
- Code suggestions in the editor are off by default, so Enter always starts a new line. Turn them on in **Settings → Editor**.
- **All lessons** is a tab in **Progress**.
- Settings starts with the Hero game, backup and editor options. Versions and the CUDA note are in **About this install**.
- The header says "Code runs on this computer" instead of "Local runtime".
- The chest earned for a lesson is a line under the lesson buttons instead of a pop-up over **Next lesson**.
- **Projects** has 12 hands-on projects, each pinned to one commit. A project gives setup and run commands, 3 to 5 tasks that link to the lines to change, and a command to check each task. Tasks can be ticked and have their own notes. Pasted output is checked in the browser and not saved. A project's chest tier follows its level, and is one tier higher when every check passed. Notes and ticks on the earlier walkthroughs are kept under **Retired projects**.

### Fixed

- Text and button colors meet WCAG AA contrast, the focus ring is darker, and text is at least 12px.
- A locked **Next lesson** says why in visible text.
- Checks in 20 lessons reject the wrong answers that used to pass, and learner code that reuses a name such as `abs` or `raises` no longer breaks grading. A far-future draft revision no longer blocks later saves, results are marked out of date after the code changes, and a draft the server refuses shows the reason.
- The editor shows "Esc, then Tab, leaves the editor". Key hints are hidden on touch screens.
- Keyboard use: a skip link, `aria-current` on the active page, page titles, focus that stays in place after stage changes and returns after dialogs close, and Escape to close the lesson list.

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
