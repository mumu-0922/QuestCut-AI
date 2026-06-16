# Repository Guidelines

## Project Structure & Module Organization
QuestCut-AI is a Python/PySide6 desktop app for AI background removal. `run.py` is the launcher. Main code lives in `src/`: `core/` handles model loading, GPU/memory helpers, portrait mode, and background removal; `processing/` contains image transforms, masks, cache, export, and batch queue logic; `ui/` contains Qt windows, widgets, dialogs, and controls; `utils/` contains constants, settings, validation, licensing, and image helpers; `resources/` stores generated resource helpers such as icons. `requirements.txt` pins runtime dependencies. `install_script.iss` is the Windows Inno Setup installer script. Treat `.venv/`, `__pycache__/`, and `_decompiled_stdlib_backup/` as local/generated artifacts, not primary source.

## Build, Test, and Development Commands
```bash
python -m pip install -r requirements.txt   # install runtime dependencies
python run.py                               # launch the desktop app locally
python -m compileall run.py src             # syntax/import smoke check
python -m pytest                            # run tests once tests/ exists
```
For Windows packaging, use Inno Setup against `install_script.iss` only after the expected `QuestCut-AI.exe` and `_internal/` build outputs exist.

## Coding Style & Naming Conventions
Use Python 3.10/3.11, 4-space indentation, and PEP 8 naming: `snake_case` for functions and methods, `PascalCase` for Qt classes/dataclasses, and `UPPER_CASE` for constants. Keep Qt signal definitions as class attributes. Keep UI-only behavior in `src/ui`, image algorithms in `src/processing`, and model/session lifecycle in `src/core`. Prefer type hints on new public functions and avoid broad `except Exception` unless errors are converted into user-facing UI signals.

## Testing Guidelines
No committed `tests/` tree is present yet. Add tests under `tests/` mirroring `src/` paths, for example `tests/processing/test_mask_ops.py`. Use small fixture images in `tests/fixtures/`. Mock `rembg`, network downloads, and model-manager sessions so tests do not fetch models or require GPU access. Prioritize deterministic tests for `utils/` and pure `processing/` functions; use `pytest-qt` for signal/widget behavior when needed.

## Commit & Pull Request Guidelines
Git history is unavailable in this workspace, so use Conventional Commits such as `fix: repair batch export mask handling` or `feat: add portrait preview cache`. PRs should include a concise summary, linked issue if any, test command output, and screenshots/GIFs for visible UI changes. Note any model, dependency, or installer impact explicitly.

## Security & Configuration Tips
Do not commit personal images, license keys, downloaded model binaries, or machine-specific paths. Keep model URLs and app defaults centralized in `src/utils/constants.py`; document any new external endpoint or file-write location in the PR.
