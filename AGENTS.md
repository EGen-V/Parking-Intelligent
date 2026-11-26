# AGENTS.md — Instructions for AI coding agents

Project: **Parking Intelligent** — Tkinter app for automatic entry/exit clocking using Tunisian license plate recognition.

## 0. Read first

1. `context.md` — what the project is, requirements, data model, business rules.
2. `docs/interface_example.png` — **the UI reference image.** Open and look at it before writing or changing any GUI code. The interface you build must follow its layout, colors, French labels and behavior.

If something here conflicts with `context.md`, `context.md` wins for requirements; this file wins for how to work.

## 1. Stack and constraints

- Python 3.10+, **Tkinter/ttk** for the GUI (mandatory), OpenCV, Pillow, EasyOCR, SQLite.
- 100% local. **Do not add cloud/AI API calls** (no NVIDIA NIM, OpenAI, Google Vision, etc.).
- Prefer existing open-source libraries/models over writing detectors or OCR from scratch.
- Do not add Flask or any web framework to the base deliverable.
- Keep dependencies minimal; every new package must be added to `requirements.txt` with a reason in the PR/commit message.

## 2. Architecture rules

- Layers: `camera/` -> `vision/` -> `services/` -> `db/`, with `ui/` on top.
- `vision/`, `services/`, `db/` **never import `tkinter`**.
- The UI never talks to SQLite or models directly; it calls `services/parking_service.py`.
- Business rules (duplicate entry, exit without entry, duration, free places) live **only** in `parking_service.py`.
- Heavy work (camera read, detection, OCR) runs in worker threads; communicate with the UI via `queue.Queue` and `root.after()` polling. **Never** call `time.sleep()` or run OCR on the Tk main thread. Only the main thread touches widgets.
- Models are loaded once at startup (or lazily once), never per frame.

## 3. UI guidelines (match `docs/interface_example.png`)

- Window: sidebar (dark navy) + header + main area (two camera panels, summary cards, history table).
- All visible text in **French**, exactly as in the mockup (e.g. "Démarrer Caméra", "Capturer", "Pointer Entrée", "Pointer Sortie", "Historique des Pointages", "Places Disponibles", "Terminé", "En cours").
- Status badges: Terminé = green, En cours = yellow/orange. Buttons: blue (start), grey (capture), green (entry), red (exit).
- Use `ttk.Treeview` for the history table with tag colors; keep columns `# | Date | Immatriculations | Entrée | Sortie | Durée | Statut | Actions`.
- Arabic plate text (`تونس`) must display correctly; pick a font with Arabic support and test it.
- Keep widgets in small modules (`sidebar.py`, `camera_panel.py`, `summary_cards.py`, `history_table.py`) instead of one giant file.
- Sidebar entries other than "Pointages" can be placeholders, but must not crash when clicked.

## 4. Vision and OCR rules

- Pipeline: frame -> car detection (rectangle) -> plate localization -> crop -> preprocessing -> OCR -> regex validation -> normalization.
- Preprocessing steps to try (keep them configurable): grayscale, resize x2–x3, bilateral/Gaussian denoise, CLAHE, adaptive threshold, deskew.
- EasyOCR with languages `['ar', 'en']`; restrict to digits + the word تونس where possible (allowlist) and validate with a regex such as `^\d{1,3}\s*تونس\s*\d{1,4}$`.
- Convert Arabic-Indic digits to Western digits before validation.
- Always save: `plate_display`, `plate_key` (normalized), confidence, plate crop image.
- Never write a low-confidence read silently to the DB: ask the operator to confirm/edit.
- Debounce repeated reads of the same plate (default 10 s).

## 5. Database rules

- SQLite file at `data/parking.db`; schema defined in `db/database.py` and created automatically on first run.
- Use parameterized queries only (never string-format SQL).
- Timestamps stored as ISO 8601 strings in local time (Africa/Tunis); format for display in the UI layer only (`17/11/2026`, `08:15:25`, `2h 15min`).
- Never delete records from the UI without an explicit confirmation dialog.

## 6. Code style

- PEP 8, type hints on public functions, docstrings on modules and classes.
- Identifiers, comments and commit messages in English; user-facing strings in French.
- Constants and thresholds go in `config.py`, not inline.
- Use `logging` instead of `print`.
- Handle failures gracefully: camera not found, model missing, OCR returns nothing -> show a message in the UI, do not crash.

## 7. Testing and verification

Before saying a task is done:

1. `pytest` passes. Minimum tests: plate normalization/regex, entry/exit logic (including duplicate entry and exit without entry), duration formatting, free-places calculation.
2. The app launches with `python -m src.main` without a camera (falls back to the sample video/image folder mode).
3. If the GUI changed, compare against `docs/interface_example.png` and mention any deviation.
4. Do not claim OCR accuracy you did not measure; report results on the sample images in `tests/data/` if you ran them.

## 8. Workflow for agents

- Make small, focused changes; one feature or fix per commit.
- Implement in this order unless told otherwise: DB + services (with tests) -> car detection -> plate detection + OCR -> Tkinter UI wiring -> polish.
- Do not rename or move the folders in `context.md` section 6 without updating that document.
- Do not commit large model weights, `data/captures/`, or `data/parking.db`; update `.gitignore`.
- If requirements are ambiguous, make the simplest reasonable choice, write it down in `context.md` under a "Decisions" section, and continue.
- Update `README.md` when installation or run steps change.

## 9. Do NOT

- Do not hardcode camera indexes, thresholds, paths or capacity; use `config.py`.
- Do not block the UI thread.
- Do not invent entries/exits to "fix" data inconsistencies.
- Do not add face recognition, brand recognition or web features unless the user asks (they are optional extensions listed in `context.md` section 10).
- Do not expose or log personal data beyond what the app needs (plates, timestamps, captures).
