"""Parking Intelligent — application configuration.

All tunable constants (paths, thresholds, camera indexes, capacity, OCR
settings, debounce windows, colors) live here instead of being hardcoded
across the codebase. See AGENTS.md section 6.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
# In a one-file build, resources are extracted to _MEIPASS while writable data
# must remain beside the executable.
IS_FROZEN: bool = bool(getattr(sys, "frozen", False))
if IS_FROZEN:
    BASE_DIR: Path = Path(sys.executable).resolve().parent
    RESOURCE_DIR: Path = Path(getattr(sys, "_MEIPASS", BASE_DIR)).resolve()
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
    RESOURCE_DIR = BASE_DIR

DATA_DIR: Path = BASE_DIR / "data"
DB_PATH: Path = DATA_DIR / "parking.db"
CAPTURES_DIR: Path = DATA_DIR / "captures"
TEST_DB_PATH: Path = DATA_DIR / "parking_test.db"
TEST_CAPTURES_DIR: Path = DATA_DIR / "captures_test"
MODELS_DIR: Path = RESOURCE_DIR / "models"
OCR_MODEL_DIR: Path = MODELS_DIR / "easyocr"
SAMPLES_DIR: Path = RESOURCE_DIR / "samples"
TEST_IMAGES_DIR: Path = RESOURCE_DIR / "tests" / "data"
TEST_VIDEO_EXTENSIONS: tuple[str, ...] = (".mp4", ".avi", ".mov", ".mkv")
_external_test_video_dir = BASE_DIR / "test-video"
_bundled_test_video_dir = RESOURCE_DIR / "test-video"
if IS_FROZEN and _external_test_video_dir.is_dir() and any(
    path.is_file() and path.suffix.lower() in TEST_VIDEO_EXTENSIONS
    for path in _external_test_video_dir.iterdir()
):
    TEST_VIDEO_DIR: Path = _external_test_video_dir
else:
    TEST_VIDEO_DIR = _bundled_test_video_dir

# --------------------------------------------------------------------------- #
# Parking / business rules
# --------------------------------------------------------------------------- #
PARKING_CAPACITY: int = 30
TIMEZONE: str = "Africa/Tunis"

# Debounce: the same plate seen again within this many seconds is one event.
DEBOUNCE_SECONDS: int = 10

# OCR confidence below this threshold requires operator confirmation.
OCR_CONFIDENCE_THRESHOLD: float = 0.60

# --------------------------------------------------------------------------- #
# Cameras / video
# --------------------------------------------------------------------------- #
# Entry = camera index 0, exit = camera index 1. Override with env vars so the
# app can fall back to sample video files without touching the code.
CAMERA_ENTRY_INDEX: int = int(os.environ.get("SPMS_ENTRY_CAMERA", "0"))
CAMERA_EXIT_INDEX: int = int(os.environ.get("SPMS_EXIT_CAMERA", "1"))
# Optional sample video/image-folder paths for demo mode (no camera needed).
SAMPLE_ENTRY_SOURCE: str = os.environ.get("SPMS_ENTRY_SOURCE", "")
SAMPLE_EXIT_SOURCE: str = os.environ.get("SPMS_EXIT_SOURCE", "")

# How often (ms) the UI polls the worker queue / redraws a frame.
UI_POLL_MS: int = 30
# Target live display width/height in pixels (aspect kept by the panel).
CAMERA_DISPLAY_WIDTH: int = 480
CAMERA_DISPLAY_HEIGHT: int = 300

# --------------------------------------------------------------------------- #
# Vision / detection
# --------------------------------------------------------------------------- #
# Confidence threshold for the car detector (0-1).
CAR_DETECT_CONFIDENCE: float = 0.35
CAR_DETECT_NMS_THRESHOLD: float = 0.4
# Confidence threshold for the plate detector (0-1).
PLATE_DETECT_CONFIDENCE: float = 0.30
CAR_CLASS_IDS: tuple[int, ...] = (2, 5, 7)  # COCO: car, bus, truck
CAR_MODEL_CONFIG_PATH: Path = MODELS_DIR / "yolov4-tiny.cfg"
CAR_MODEL_WEIGHTS_PATH: Path = MODELS_DIR / "yolov4-tiny.weights"
CAR_MODEL_CONFIG_URL: str = (
    "https://raw.githubusercontent.com/AlexeyAB/darknet/master/cfg/yolov4-tiny.cfg"
)
CAR_MODEL_WEIGHTS_URL: str = (
    "https://github.com/AlexeyAB/darknet/releases/download/yolov4/"
    "yolov4-tiny.weights"
)
DETECTION_INPUT_SIZE: tuple[int, int] = (416, 416)
CAR_CROP_MARGIN: float = 0.08
PLATE_CROP_MARGIN: float = 0.12
MIN_CAR_CROP_SIZE: tuple[int, int] = (48, 32)
MIN_PLATE_CROP_SIZE: tuple[int, int] = (24, 10)
VISION_FRAME_SKIP: int = 4
OCR_FRAME_INTERVAL: int = 2
CAR_STABILITY_FRAMES: int = 3
CAR_CAPTURE_MAX_WAIT_FRAMES: int = 3
PLATE_VOTE_COUNT: int = 3
PLATE_TRACK_IOU: float = 0.30
PLATE_VOTE_WINDOW_SECONDS: float = 8.0
OCR_FAILURE_LIMIT: int = 4
CAPTURE_UNKNOWN_PLATE_KEY: str = "unknown"
PLATE_REGION_TOP_FRACTION: float = 0.30
PLATE_ASPECT_RATIO_MIN: float = 2.0
PLATE_ASPECT_RATIO_MAX: float = 6.5
PLATE_AREA_FRACTION_MIN: float = 0.006
PLATE_AREA_FRACTION_MAX: float = 0.35
PLATE_ADAPTIVE_BLOCK_SIZE: int = 19
PLATE_ADAPTIVE_C: int = 7
PLATE_MORPH_KERNEL: tuple[int, int] = (9, 3)
# A localized contour must span at least this fraction of the car width to be
# trusted; smaller hits are treated as noise and the fallback region is used.
PLATE_MIN_WIDTH_FRACTION: float = 0.35
PLATE_FALLBACK_X: float = 0.08
PLATE_FALLBACK_Y: float = 0.59
PLATE_FALLBACK_WIDTH: float = 0.84
PLATE_FALLBACK_HEIGHT: float = 0.32
PREPROCESS_ADAPTIVE_BLOCK_SIZE: int = 31
PREPROCESS_ADAPTIVE_C: int = 7
DESKEW_MIN_ANGLE: float = 1.0
DESKEW_MAX_ANGLE: float = 25.0

# Preprocessing knobs (kept configurable per AGENTS.md section 4).
PREPROCESS_SCALE: float = 2.5
PREPROCESS_DENOISE: bool = True
PREPROCESS_CLAHE: bool = True
PREPROCESS_THRESHOLD: bool = True

# --------------------------------------------------------------------------- #
# OCR
# --------------------------------------------------------------------------- #
OCR_LANGUAGES: tuple[str, ...] = ("ar", "en")
# Allowlist restricts EasyOCR to digits + the Arabic word تونس.
OCR_ALLOWLIST: str = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZتونسحكومة"
PREPROCESS_DENOISE_DIAMETER: int = 7
PREPROCESS_DENOISE_SIGMA_COLOR: int = 45
PREPROCESS_DENOISE_SIGMA_SPACE: int = 45
PREPROCESS_CLAHE_CLIP_LIMIT: float = 2.0
PREPROCESS_CLAHE_GRID_SIZE: tuple[int, int] = (8, 8)

# --------------------------------------------------------------------------- #
# UI theme — modern slate/indigo palette (bold redesign)
# --------------------------------------------------------------------------- #
COLOR_SIDEBAR: str = "#0f172a"         # deep slate sidebar
COLOR_SIDEBAR_ALT: str = "#1e293b"     # raised sidebar surface
COLOR_SIDEBAR_ACTIVE: str = "#2563eb"  # active menu highlight (blue)
COLOR_SIDEBAR_TEXT: str = "#cbd5e1"    # inactive menu text
COLOR_HEADER: str = "#ffffff"
COLOR_BG: str = "#f1f5f9"              # main background (slate-100)
COLOR_CARD: str = "#ffffff"
COLOR_CARD_ALT: str = "#f8fafc"        # subtle card inner surface
COLOR_TEXT: str = "#0f172a"
COLOR_TEXT_MUTED: str = "#64748b"
COLOR_BLUE: str = "#2563eb"
COLOR_BLUE_DARK: str = "#1d4ed8"
COLOR_GREY: str = "#94a3b8"
COLOR_GREEN: str = "#16a34a"
COLOR_GREEN_DARK: str = "#15803d"
COLOR_RED: str = "#dc2626"
COLOR_RED_DARK: str = "#b91c1c"
COLOR_YELLOW: str = "#d97706"
COLOR_YELLOW_BG: str = "#fef3c7"
COLOR_GREEN_BG: str = "#dcfce7"
COLOR_BORDER: str = "#e2e8f0"
COLOR_ACCENT: str = "#7c3aed"          # purple accent (available places)

# Fonts (Arabic-capable). Segoe UI / Tahoma ship with Windows and cover تونس.
FONT_FAMILY: str = "Segoe UI"
FONT_ARABIC: str = "Tahoma"

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
LOG_LEVEL: str = os.environ.get("SPMS_LOG_LEVEL", "INFO")