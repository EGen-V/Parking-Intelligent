"""Plate normalization, validation and local EasyOCR.

Tunisian plates read ``NNN تونس NNNN``. Real OCR output is messy:

* EasyOCR reads right-to-left, so the right digit group often glues onto the
  Arabic word (``"4567 سنوت"``) and the word itself is frequently misread
  (``سنوت`` / ``رذوت`` / ``رنوت`` instead of ``تونس``).
* Arabic-Indic digits (``٠١٢٣``) must be converted to Western digits.

Instead of demanding one exact spelling, the parser reconstructs the plate from
its *structure*: two digit groups (1-3 then 1-4 digits) with the Arabic band in
between. This tolerates a garbled band while still rejecting free text. The
caller (voting + operator confirmation) guards against the rare false positive.
"""

from __future__ import annotations

import re
import threading

from src import config
from src.vision.preprocess import preprocess_variants

# Arabic-Indic (U+0660) and Extended (U+06F0) digit sets -> Western digits.
_ARABIC_INDIC = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
_EXTENDED_ARABIC = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")

# Strict standard plate, kept for callers that want the exact spelling.
_STANDARD_PLATE = re.compile(r"^(\d{1,3})\s*تونس\s*(\d{1,4})$")
_ALTERNATE_PLATES = (
    re.compile(r"^RS\s*\d{1,5}$", re.IGNORECASE),
    re.compile(r"^CD\s*\d{1,5}(?:\s*\d{1,4})?$", re.IGNORECASE),
    re.compile(r"^\d{1,4}\s*حكومة\s*\d{1,4}$"),
    re.compile(r"^[A-Z]{1,3}\s*\d{1,5}(?:\s*[A-Z]{1,2}\s*\d{0,4})?$", re.IGNORECASE),
)
_DIGIT_RUN = re.compile(r"\d+")

_OCR_READER_LOCK = threading.Lock()
_OCR_READER_INSTANCE: "OCRReader | None" = None


def normalize_plate_digits(raw_text: str) -> str:
    """Convert Arabic-Indic and Extended Arabic digits to Western digits."""
    return raw_text.translate(_ARABIC_INDIC).translate(_EXTENDED_ARABIC)


def _tolerant_standard(text: str) -> str | None:
    """Reconstruct a standard plate from two digit groups, tolerating the band.

    ``"123 4567 سنوت"`` and ``"123 تونس 4567"`` both yield ``"123 تونس 4567"``.
    Returns ``None`` when the text does not contain exactly two usable groups.
    """
    runs = _DIGIT_RUN.findall(text)
    if len(runs) != 2:
        return None
    left, right = runs
    # The left group is 1-3 digits, the right 1-4. If OCR hands them over in
    # the wrong order (e.g. a 4-digit run first), swap them back.
    if len(left) == 4 and 1 <= len(right) <= 3:
        left, right = right, left
    if not (1 <= len(left) <= 3 and 1 <= len(right) <= 4):
        return None
    return f"{left} تونس {right}"


def validate_plate(raw_text: str) -> str | None:
    """Return a display form for standard and common alternate plates.

    Tolerant of RTL ordering and a misread Arabic band: the plate is rebuilt
    from its two digit groups when the exact ``تونس`` spelling is not matched.
    """
    text = re.sub(r"\s+", " ", normalize_plate_digits(raw_text).strip())
    if not text:
        return None
    match = _STANDARD_PLATE.fullmatch(text)
    if match:
        return f"{match.group(1)} تونس {match.group(2)}"
    if any(pattern.fullmatch(text) for pattern in _ALTERNATE_PLATES):
        return text.upper()
    # ``حكومة`` (government) plates carry their own marker.
    if "حكومة" in text:
        digits = "".join(_DIGIT_RUN.findall(text))
        if digits:
            return f"{digits[:4]} حكومة {digits[4:8]}".strip()
    return _tolerant_standard(text)


def normalize_plate(raw_text: str) -> str:
    """Convert a standard or supported alternate plate to a compact key.

    Tolerant of RTL ordering and a misread band: the text is first rebuilt by
    :func:`validate_plate`, then reduced to a matching key.
    """
    display = validate_plate(raw_text)
    if display is None:
        raise ValueError("Plaque invalide")
    text = normalize_plate_digits(display).strip()
    compact = re.sub(r"[\s-]+", "", text).upper()
    match = re.fullmatch(r"(\d{1,3})تونس(\d{1,4})", compact)
    if match:
        return f"{match.group(1)}TN{match.group(2)}"
    if "حكومة" in compact:
        digits = "".join(_DIGIT_RUN.findall(compact))
        return f"GOV{digits}"
    ascii_key = re.sub(r"[^A-Z0-9]", "", compact)
    if ascii_key:
        return ascii_key
    raise ValueError("Plaque invalide")


def _token_sort_key(result) -> tuple[float, float]:
    """Sort key placing an OCR token left-to-right by its bounding box.

    EasyOCR returns ``[bbox, text, confidence]`` where ``bbox`` is four points.
    ``None`` boxes (test doubles) sort last while keeping their relative order.
    """
    bbox = result[0]
    if not bbox:
        return (float("inf"), 0.0)
    xs = [point[0] for point in bbox]
    ys = [point[1] for point in bbox]
    return (min(xs), min(ys))


def _read_ordered_text(reader, image, allowlist: str) -> tuple[str, float]:
    """Read one image and return text ordered left-to-right plus mean confidence."""
    results = reader.readtext(image, allowlist=allowlist)
    if not results:
        return "", 0.0
    ordered = sorted(results, key=_token_sort_key)
    parts: list[str] = []
    confidences: list[float] = []
    for _bbox, text, confidence in ordered:
        text = str(text).strip()
        if text:
            parts.append(text)
            confidences.append(float(confidence))
    joined = " ".join(parts)
    mean_conf = sum(confidences) / len(confidences) if confidences else 0.0
    return joined, mean_conf


class OCRReader:
    """Load EasyOCR once and choose the best validated preprocessing result."""

    def __init__(self) -> None:
        self._reader = None
        self._read_lock = threading.Lock()

    def _get_reader(self):
        if self._reader is None:
            try:
                import easyocr
            except ImportError as exc:
                raise RuntimeError(
                    "EasyOCR n'est pas installé. Exécutez « pip install -r requirements.txt »."
                ) from exc
            self._reader = easyocr.Reader(
                list(config.OCR_LANGUAGES),
                gpu=False,
                model_storage_directory=str(config.OCR_MODEL_DIR),
                verbose=False,
            )
        return self._reader

    def read(self, plate_crop) -> tuple[str | None, float]:
        """Read a plate crop through several configured image variants.

        Tokens are ordered left-to-right before parsing so RTL output does not
        scramble the two digit groups. The highest-confidence validated variant
        wins.
        """
        with self._read_lock:
            reader = self._get_reader()
            best: tuple[str, float] | None = None
            for variant in preprocess_variants(plate_crop):
                text, confidence = _read_ordered_text(reader, variant, config.OCR_ALLOWLIST)
                display = validate_plate(text)
                if display and (best is None or confidence > best[1]):
                    best = (display, confidence)
            return best if best is not None else (None, 0.0)


def get_ocr_reader() -> "OCRReader":
    """Return one shared OCR engine for both camera workers."""
    global _OCR_READER_INSTANCE
    with _OCR_READER_LOCK:
        if _OCR_READER_INSTANCE is None:
            _OCR_READER_INSTANCE = OCRReader()
        return _OCR_READER_INSTANCE