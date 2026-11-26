"""Regression tests for RTL-tolerant Tunisian plate parsing.

These lock in the fix for the real-world OCR failure where EasyOCR reads
right-to-left and misreads the Arabic band (e.g. ``"4567 سنوت"``). The parser
must rebuild the plate from its two digit groups while still rejecting free
text.
"""

from __future__ import annotations

import pytest

from src.vision.ocr_reader import normalize_plate, validate_plate


@pytest.mark.parametrize(
    "raw,display,key",
    [
        ("123 تونس 4567", "123 تونس 4567", "123TN4567"),
        ("123 4567 سنوت", "123 تونس 4567", "123TN4567"),      # RTL glue + misread band
        ("4567سنوت 123", "123 تونس 4567", "123TN4567"),      # reversed digit order
        ("45 89 رنوت", "45 تونس 89", "45TN89"),
        ("١٢٣ تونس ٤٥٦٧", "123 تونس 4567", "123TN4567"),     # Arabic-Indic digits
        ("12 3456", "12 تونس 3456", "12TN3456"),             # band missing entirely
    ],
)
def test_tolerant_parser_rebuilds_standard_plate(raw: str, display: str, key: str) -> None:
    assert validate_plate(raw) == display
    assert normalize_plate(raw) == key


@pytest.mark.parametrize("bad", ["garbage", "hello world", "abc", ""])
def test_free_text_is_still_rejected(bad: str) -> None:
    assert validate_plate(bad) is None
    with pytest.raises(ValueError):
        normalize_plate(bad)


def test_alternate_formats_still_validate() -> None:
    assert validate_plate("RS 1234") == "RS 1234"
    assert normalize_plate("CD 1234") == "CD1234"
    assert normalize_plate("123 حكومة 45") == "GOV12345"