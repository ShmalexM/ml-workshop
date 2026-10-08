# Roadmap

These are planned areas of work, with no dates. Suggest improvements in [GitHub Issues](https://github.com/ShmalexM/ml-workshop/issues).

## Available now

- 72 coding lessons in 13 paths: Python from zero for people who have never coded, then ML, GPUs, agents, backend, web, RL, data, reliability and interactive systems.
- Python and JavaScript exercises that run locally, with checks, hints, solutions, notes and XP.
- Every lesson has an explanation, a runnable example, a prediction question and a solution you can open at any time.
- A glossary of the terms the lessons use, linked where each term first appears, and a list of the Python or JavaScript each exercise needs, linked to the lessons that teach it.
- Tests that make sure plausible wrong answers fail the lesson checks.
- Offline exercises using small synthetic inputs, including CUDA CPU simulation.
- Local progress storage and JSON export.
- A one-line install for macOS, Linux and Windows. Running it again updates the app and keeps your progress.
- Setup and launch scripts for clones on macOS, Linux and Windows, and an optional native Mac window.
- A list of 12 public projects, each with a starting file, a preparation lesson and walkthrough steps with notes saved locally.
- PDF and EPUB reading, with reading guides linked to lessons.
- An optional Hero game: finished lessons, paths, project walkthroughs and reading guides earn chests of gear and arena battles.

## Next improvements

- [ ] Import a progress backup with validation and a preview before replacing data.
- [ ] Add spaced review and a practice queue based on concepts that need revisiting.
- [ ] Add guided framework projects beyond the introductory invariants: train/evaluate a classifier, compare frameworks, and build an offline retrieval pipeline.
- [ ] Make lesson authoring less repetitive while preserving stable lesson IDs.
- [ ] Add CPU and file-size limits for exercises on Windows.
- [ ] Add browser-rendered component exercises and Swift/Flutter-specific labs.
- [ ] Add richer RL experiments, policy evaluation and opt-in emulator integration with user-provided assets.
- [ ] Add a catalog editor and project-specific progress history.

## CUDA progression

- [ ] Add an opt-in Linux/NVIDIA runtime with capability detection and device compilation checks.
- [ ] Teach memory coalescing, reductions, CUDA events, streams, and profiler interpretation on actual hardware.
- [ ] Add CUDA C++ exercises after validating toolchain setup and cleanup.

No GPU, cloud account, or API key should become a prerequisite for the core learning path. Actual hardware exercises must remain clearly separate from CPU simulation.
