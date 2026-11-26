# context.md — Parking Intelligent (Pointage avec reconnaissance des plaques tunisiennes)

> Source of truth for WHAT the project is. For HOW agents must work on it, see `AGENTS.md`.

## 1. Project summary

A Python desktop application that manages a smart parking lot. A camera at the **entrance** and a camera at the **exit** capture each car. The app must:

1. Detect that a car is present.
2. Locate and read its **Tunisian license plate**.
3. Record the **entry** date/time automatically.
4. Record the **exit** date/time automatically.
5. Compute the **parking duration**.

The GUI is built with **Tkinter** (mandatory, part of the assignment).
Everything runs **locally**: no cloud AI API, no paid service.

## 2. UI reference (IMPORTANT)

The target interface mockup is in:

```
docs/referance.png
```

Agents MUST open and follow this image when building the GUI. It is a visual target, not a pixel-perfect spec; reproduce its layout, labels (in French) and behavior with Tkinter/ttk.

### Layout described from the mockup

**Left sidebar (dark navy, fixed width)**

- Logo + title: "Parking Intelligent / Smart Parking"
- Menu: Tableau de bord, Caméras, Historique, **Pointages** (active, highlighted blue), Rapports, Paramètres (expandable), À propos (expandable)
- Bottom: status box "En ligne" (green dot) + current date/time; red "Se déconnecter" button

**Top bar**

- Page title: "Monitoring / Gestion du Parking"
- Right side: organization logo ("Genio" in the mockup, replaceable), notification bell with badge count, "Admin" user menu

**Main area, top row — two live camera panels**

- "Caméra Entrée" (blue header, green "En direct" indicator): live video, green rectangle around the detected car, overlay label `Plaque détectée : 123 تونس 4567`
  - Buttons: **Démarrer Caméra** (blue), **Capturer** (grey), **Pointer Entrée** (green)
- "Caméra Sortie" (same style): live video
  - Button: **Pointer Sortie** (red)

**Main area, top right — "Résumé du Parking" cards**

- Véhicules en Entrée (count + delta, e.g. 12 / +1)
- Véhicules en Sortie (count + delta, e.g. 10 / +0)
- Places Disponibles (e.g. 18 / 30) with a progress bar

**Main area, bottom — "Historique des Pointages" table**

- Search field "Rechercher une plaque..." and "Filtrer par date" dropdown
- Columns: `#`, `Date`, `Immatriculations`, `Entrée`, `Sortie`, `Durée`, `Statut`, `Actions`
- Status badges: **Terminé** (green) when exit recorded, **En cours** (yellow/orange) while the car is inside
- Actions column: eye button to view details (captured images, plate crop, times)
- Sample row: `1 | 17/11/2026 | 123 تونس 4567 | 08:15:25 | 10:30:17 | 2h 15min | Terminé`
- Open rows show `—` for exit and an empty duration.

### Tkinter implementation notes

- Use `tkinter` + `ttk` (optionally `customtkinter` only if allowed by the teacher; default is plain Tkinter/ttk).
- Video frames: OpenCV BGR -> RGB -> `PIL.Image` -> `ImageTk.PhotoImage`, refreshed with `after()` (never `time.sleep` in the UI thread).
- Table: `ttk.Treeview` with tag colors for statuses.
- Cards and sidebar: `tk.Frame` / `tk.Label` with custom colors; progress bar: `ttk.Progressbar`.
- Arabic text (تونس) must render correctly: use a font with Arabic support (e.g. Segoe UI, Tahoma, Noto Sans Arabic).

## 3. Functional requirements

### F1 — Car detection

- Open the camera (OpenCV `VideoCapture`).
- Capture an image / read a live stream.
- Detect the presence of a car.
- Draw a rectangle around the detected car.

### F2 — Plate reading

- Locate the license plate.
- Crop the plate region.
- Enhance image quality (grayscale, resize, denoise, contrast/CLAHE, threshold, deskew).
- Run OCR to read the characters.
- Display the detected plate number.

### F3 — Automatic clocking (pointage)

**At entry**

- Read the plate.
- Check whether the vehicle is already registered as inside the parking (open entry with no exit).
- Record the entry date and time.

**At exit**

- Read the plate.
- Find the latest open entry record for that plate.
- Record the exit date and time.
- Compute the parking duration.

### F4 — Graphical interface

- Tkinter application matching `docs/interface_example.png`.

### F5 — Isolated test mode

- The **Mode Test** toggle uses local video files instead of live cameras.
- Entry and exit videos loop independently; when several videos are available,
  each panel has its own selector. Playback can be paused and resumed.
- Test mode uses a separate database and capture directory; test data never
  appears in the normal parking history.
- A confirmed reset clears only test records and test captures.

## 4. Tunisian plate knowledge

- Standard format: `NNN تونس NNNN` — 1 to 3 digits, the Arabic word **تونس** (Tunis), then 1 to 4 digits. Example: `123 تونس 4567`.
- Other formats to tolerate: `RS` (régime suspensif) plates, government/administration plates (`حكومة`), diplomatic (`CD`), and Latin-letter variants.
- OCR language packs: Arabic + English digits. Digits can be Western (0-9) or Arabic-Indic; normalize to Western.
- Store two forms:
  - `plate_display`: `123 تونس 4567` (for the UI)
  - `plate_key`: normalized, no spaces, e.g. `123TN4567` (for matching/search)
- Validate with a regex after OCR; reject or flag low-confidence reads instead of saving garbage.

## 5. Technical stack

| Area            | Choice                                                                                     |
| --------------- | ------------------------------------------------------------------------------------------ |
| Language        | Python 3.10+                                                                               |
| GUI             | Tkinter / ttk (+ Pillow for images)                                                        |
| Vision          | OpenCV                                                                                     |
| Car detection   | Local YOLOv4-tiny COCO model through OpenCV DNN (car, bus, truck classes) |
| Plate detection | OpenCV contour localization with a lower-car-region fallback |
| OCR             | EasyOCR (`['ar','en']`)                                                                    |
| Storage         | SQLite (`sqlite3` from the standard library)                                               |
| Config          | `config.py` or `config.json`                                                               |
| Tests           | `pytest`                                                                                   |

No cloud APIs. Weights are downloaded once and stored under `models/`.

## 6. Proposed architecture

```
parking/
├── AGENTS.md
├── context.md
├── README.md
├── requirements.txt
├── docs/
│   ├── interface_example.png      <- UI target
│   └── conception/                <- UML / MCD / presentation material
├── models/                        <- local model weights (git-ignored if large)
├── data/
│   ├── parking.db                 <- live SQLite database
│   ├── captures/                  <- live car + plate images
│   ├── parking_test.db            <- isolated test-mode database
│   └── captures_test/             <- isolated test-mode crops
├── test-video/                    <- local videos for test mode
├── src/
│   ├── main.py                    <- entry point
│   ├── config.py
│   ├── camera/
│   │   └── camera_stream.py       <- threaded VideoCapture wrapper
│   ├── vision/
│   │   ├── car_detector.py        <- F1
│   │   ├── plate_detector.py      <- F2 locate + crop
│   │   ├── preprocess.py          <- F2 enhancement
│   │   └── ocr_reader.py          <- F2 OCR + plate regex/normalization
│   ├── services/
│   │   └── parking_service.py     <- F3 business rules (entry/exit/duration)
│   ├── db/
│   │   ├── database.py
│   │   └── repository.py
│   └── ui/
│       ├── app.py                 <- main window
│       ├── sidebar.py
│       ├── camera_panel.py
│       ├── summary_cards.py
│       └── history_table.py
└── tests/
```

Rule: **vision, services and db must not import tkinter.** The UI calls services, never the reverse.

## 7. Data model (SQLite)

Table `pointages`:

| Column           | Type                     | Notes                   |
| ---------------- | ------------------------ | ----------------------- |
| id               | INTEGER PK AUTOINCREMENT | shown as `#`            |
| plate_display    | TEXT                     | `123 تونس 4567`         |
| plate_key        | TEXT, indexed            | normalized              |
| entry_time       | TEXT (ISO 8601)          | required                |
| exit_time        | TEXT (ISO 8601)          | NULL while inside       |
| duration_seconds | INTEGER                  | NULL while inside       |
| status           | TEXT                     | `EN_COURS` or `TERMINE` |
| entry_image      | TEXT                     | path to capture         |
| exit_image       | TEXT                     | path to capture         |
| plate_image      | TEXT                     | path to plate crop      |
| exit_plate_image | TEXT                     | exit plate crop         |
| confidence       | REAL                     | OCR confidence          |

Optional table `settings` (capacity, camera indexes, thresholds). Parking capacity default: **30** (matches the mockup).

## 8. Business rules

1. **Entry**: if an open record (`exit_time IS NULL`) already exists for `plate_key`, do NOT create a duplicate; warn "Véhicule déjà dans le parking".
2. **Exit**: find the most recent open record for `plate_key`; if none, warn "Aucune entrée trouvée" and do not invent one.
3. **Duration** = `exit_time - entry_time`, displayed as `2h 15min` / `34 min`; stored in seconds.
4. **Places disponibles** = capacity − number of open records.
5. **Véhicules en Entrée / Sortie** = counts of entries / exits for the current day, with delta vs. the previous period.
6. Same plate seen repeatedly by the camera within a short window (e.g. 10 s) counts as ONE event (debounce).
7. OCR confidence below the threshold: show the read, ask the operator to confirm or edit before saving.
8. All timestamps use local time (Africa/Tunis).

## 9. Non-functional requirements

- Responsive UI: camera and OCR run in worker threads; the UI thread only draws.
- Near real-time feedback: detection overlay updates smoothly; OCR runs only on a cropped plate and not on every frame.
- Works offline and on a laptop webcam; camera indexes configurable (entry = 0, exit = 1 or a video file for demos).
- A video file / image folder mode for testing without a camera.
- Clear French UI text; code identifiers and comments in English.

## 10. Scope

**In scope:** F1–F4 above, SQLite persistence, history table with search/date filter, summary cards, saved captures.

**Out of scope for the base deliverable (optional extensions later):** face recognition of the driver, car brand/logo recognition, Flask web interface, remote cameras, billing/tariffs, user authentication beyond a simple "Admin" label.

## 11. Deliverables

- Working Python application (Tkinter).
- `requirements.txt` and a README with install/run instructions.
- Conception documents (use cases, class/sequence diagrams, data model) in `docs/conception/`.
- Short presentation / demo.

## 12. Definition of done

- Opening the app shows a UI visually matching `docs/interface_example.png`.
- A car in front of the entry camera gets a rectangle; the plate is read and displayed.
- "Pointer Entrée" creates an `EN_COURS` row; "Pointer Sortie" closes it, sets `TERMINE` and fills `Durée`.
- Duplicate entry and exit-without-entry cases are handled with clear messages.
- The summary cards and the history table update immediately after each action.
- Tests for plate normalization, entry/exit logic and duration pass.

## 13. Test mode and capture storage

The test-video folder is configured by `TEST_VIDEO_DIR` in `src/config.py`.
Supported extensions are configured by `TEST_VIDEO_EXTENSIONS`. The app shows
an error instead of crashing if the folder is missing, empty, or contains an
unreadable video. Both entry and exit panels use the first video by default;
with multiple files, the operator can choose a source for each panel.

Live and test captures use the same role/date naming structure:

```
data/captures/{entry|exit}/{YYYY-MM-DD}/{timestamp}_{plate_key}_{car|plate}.jpg
data/captures_test/{entry|exit}/{YYYY-MM-DD}/{timestamp}_{plate_key}_{car|plate}.jpg
```

The car and plate crops are written automatically once a vehicle is stable.
If the plate has not been confidently identified, the filename uses `unknown`.
The corresponding entry and exit image paths are stored in `pointages`.

## 14. Decisions

- Test mode uses `data/parking_test.db` and `data/captures_test/` rather than
  tagging rows in the live database. The reset action is available only in test
  mode and is confirmed before deleting those records and captures.
- The same local detection, crop, OCR, and plate-voting pipeline runs in both
  modes. Entry/exit records still require the operator's pointage action, and
  uncertain OCR readings must be confirmed or edited.
- The supplied traffic video is a demonstration source, not a representative
  Tunisian plate dataset. On the three included sample frames, the local
  detector found 5, 8, and 7 vehicles respectively; none of the three plate
  crops produced a validated plate. These measurements are not an OCR accuracy
  claim.

### OCR fix (RTL-tolerant parsing)

- Root cause of "OCR doesn't work": EasyOCR reads right-to-left, so the right
  digit group glued onto the Arabic band (e.g. `"4567 سنوت"`), and the band was
  frequently misread (`سنوت` / `رذوت` / `رنوت`). The previous strict regex
  `^\d{1,3}\s*تونس\s*\d{1,4}$` rejected every real read.
- `validate_plate()` now rebuilds the plate from its **two digit groups** (1-3
  then 1-4 digits), tolerating a garbled or reordered band, while still
  rejecting free text. `normalize_plate()` routes through it, so messy OCR text
  yields the same key as a clean plate.
- `OCRReader.read()` sorts OCR tokens **left-to-right by bounding box** before
  parsing, undoing the RTL scramble.
- The contour plate detector now rejects implausibly small contour hits
  (`PLATE_MIN_WIDTH_FRACTION`) and falls back to a plausible region instead of
  cropping a 13 px noise blob.
- Preprocessing now produces genuinely distinct variants (grayscale, CLAHE,
  deskew, global Otsu, adaptive threshold) so the voter sees different inputs.
- Measured on synthetic Tunisian plates: the OCR stage reads 2 of 3 plates
  correctly (including 3-digit and 2-digit left groups) with real EasyOCR,
  versus 0 of 3 before. The remaining failure is a single thin digit that
  EasyOCR's text detector does not see at all; the operator confirms
  low-confidence reads. This is an OCR measurement on rendered images, not an
  accuracy claim for real photographs.
- `tests/test_plate_parsing.py` locks in RTL/misread-band/reversed-order cases.

### UI redesign

- The Tkinter UI was rebuilt on a shared `ui/theme.py` (palette, buttons,
  cards, treeview style) with a slate/indigo palette, grouped sidebar, stat
  cards with delta pills, and status-tinted history rows. All French labels and
  the `# | Date | Immatriculations | Entrée | Sortie | Durée | Statut | Actions`
  columns are unchanged. `tests/test_ui_smoke.py` builds and tears the UI down.
- The layout was compared with `docs/referance.png` on screen and corrected:
  the two camera panels share a uniform width, the entry panel's third button
  no longer clips (it wraps to a second row on very narrow windows), summary
  icons use the accent colour on the card instead of a same-colour square, the
  history columns only stretch the plate column, the search field has a
  placeholder, and an empty table shows "Aucun pointage enregistré".
- The window minimum is 1360x760: below that the two camera panels plus the
  summary cannot keep readable widths.
- Icon images are cached per Tk interpreter (`ui/icons.py`), so the UI can be
  rebuilt in one process without reusing images from a destroyed root.

### Dependencies added in this pass

- `opencv-python-headless` replaces `opencv-python`: the app only uses OpenCV
  through NumPy arrays, and the headless build avoids Qt/Tk plugin conflicts and
  trims the PyInstaller bundle.
- `tkinter-icons[lucide]` provides the font-based icons used by the sidebar,
  cards and buttons; `parking_intelligent.spec` bundles its data files.
- `tzdata` supplies the IANA database on Windows, where `ZoneInfo` has no
  system copy, so `Africa/Tunis` timestamps resolve.
