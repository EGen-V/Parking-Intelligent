"""Tests for safe crops, plate validation, voting and capture persistence."""

from __future__ import annotations

import queue
from pathlib import Path
import threading
import time

import numpy as np
import pytest

import cv2

from src.vision.capture_store import CaptureStore
from src.vision.car_detector import CarDetector
from src.vision.crop import crop_with_margin
from src.vision.ocr_reader import OCRReader, normalize_plate, validate_plate
from src.vision.plate_detector import PlateDetection, PlateDetector
from src.vision.pipeline import VisionWorker
from src.vision.preprocess import preprocess_variants
from src.vision.voting import PlateDebouncer, PlateVoter


def test_crop_clamps_to_bounds_and_adds_margin() -> None:
    image = np.zeros((40, 60, 3), dtype=np.uint8)
    result = crop_with_margin(image, (-4, -2, 20, 12), 0.25, (10, 8))
    assert result is not None
    crop, clamped_box = result
    assert clamped_box == (0, 0, 21, 13)
    assert crop.shape[:2] == (13, 21)


def test_crop_skips_too_small_regions() -> None:
    image = np.zeros((20, 20, 3), dtype=np.uint8)
    assert crop_with_margin(image, (3, 3, 5, 5), 0, (8, 8)) is None


def test_car_detector_accepts_tuple_shaped_opencv_results() -> None:
    class TupleResultModel:
        def detect(self, _frame, **_kwargs):
            return (2, 1), (0.9, 0.8), ((10, 20, 30, 40), (1, 2, 3, 4))

    detector = object.__new__(CarDetector)
    detector._model = TupleResultModel()

    detections = detector.detect(np.zeros((80, 100, 3), dtype=np.uint8))

    assert len(detections) == 1
    assert detections[0].class_id == 2
    assert detections[0].box == (10, 20, 30, 40)


def test_plate_voter_requires_repeated_reads_for_same_car() -> None:
    now = [0.0]
    voter = PlateVoter(required_votes=3, clock=lambda: now[0])
    box = (10, 10, 100, 60)
    assert voter.add("123 تونس 4567", 0.7, box) is None
    now[0] += 0.1
    assert voter.add("123 تونس 4567", 0.8, (12, 10, 100, 60)) is None
    now[0] += 0.1
    result = voter.add("123 تونس 4567", 0.9, (11, 12, 100, 60))
    assert result is not None
    assert result.plate_key == "123TN4567"
    assert result.confidence == pytest.approx(0.8)
    now[0] += 0.1
    assert voter.add("123 تونس 4567", 0.9, box) is None


def test_plate_voter_resets_for_another_car() -> None:
    voter = PlateVoter(required_votes=2, clock=lambda: 1.0)
    assert voter.add("123 تونس 4567", 0.9, (0, 0, 100, 50)) is None
    assert voter.add("123 تونس 4567", 0.9, (500, 300, 100, 50)) is None


def test_debouncer_suppresses_repeats() -> None:
    now = [10.0]
    debouncer = PlateDebouncer(seconds=10, clock=lambda: now[0])
    assert debouncer.accept("123TN4567")
    now[0] += 9.9
    assert not debouncer.accept("123TN4567")
    now[0] += 0.2
    assert debouncer.accept("123TN4567")


def test_normalization_accepts_known_alternate_plate_formats() -> None:
    assert validate_plate("RS 1234") == "RS 1234"
    assert normalize_plate("CD 1234") == "CD1234"
    assert normalize_plate("123 حكومة 45") == "GOV12345"


def test_preprocessing_generates_multiple_scaled_variants() -> None:
    plate = np.full((24, 80, 3), 255, dtype=np.uint8)
    variants = preprocess_variants(plate)
    assert len(variants) >= 3
    assert all(variant.shape[0] >= 48 and variant.shape[1] >= 160 for variant in variants)


def test_plate_detector_returns_a_clamped_candidate_for_vehicle_crop() -> None:
    crop = np.zeros((100, 180, 3), dtype=np.uint8)
    detection = PlateDetector().detect(crop)
    assert detection is not None
    assert detection.box[1] + detection.box[3] <= crop.shape[0]
    assert detection.box[2] >= 24


def test_capture_store_saves_both_images_and_uses_layout(tmp_path: Path) -> None:
    frame = np.full((140, 200, 3), 180, dtype=np.uint8)
    store = CaptureStore(tmp_path)
    result = store.save(
        frame,
        (20, 20, 150, 100),
        PlateDetection((25, 60, 90, 25), localized=False),
        "123TN4567",
        "entry",
    )
    assert result is not None
    car_path = Path(result["car_image"])
    plate_path = Path(result["plate_image"])
    assert car_path.is_file()
    assert plate_path.is_file()
    assert car_path.parent.parent.name == "entry"
    assert car_path.name.endswith("_123TN4567_car.jpg")
    assert plate_path.name.endswith("_123TN4567_plate.jpg")


def test_ocr_chooses_highest_confidence_validated_variant(monkeypatch) -> None:
    class FakeReader:
        def __init__(self) -> None:
            self.index = 0

        def readtext(self, _image, allowlist: str):
            self.index += 1
            assert "تونس" in allowlist
            if self.index == 1:
                return [(None, "123 تونس 4567", 0.4)]
            return [(None, "123 تونس 4567", 0.9)]

    reader = OCRReader()
    reader._reader = FakeReader()
    monkeypatch.setattr(
        "src.vision.ocr_reader.preprocess_variants",
        lambda _image: [np.zeros((20, 40), dtype=np.uint8) for _ in range(2)],
    )
    assert reader.read(np.zeros((10, 20, 3), dtype=np.uint8)) == (
        "123 تونس 4567",
        0.9,
    )


def test_ocr_orders_tokens_left_to_right_before_parsing(monkeypatch) -> None:
    """RTL output must be reordered by bounding box before validation."""

    class FakeReader:
        def readtext(self, _image, allowlist: str):
            # Right group + garbled band first (RTL), left group last.
            return [
                ([[300, 0], [400, 0], [400, 50], [300, 50]], "4567 سنوت", 0.9),
                ([[10, 0], [120, 0], [120, 50], [10, 50]], "123", 0.9),
            ]

    reader = OCRReader()
    reader._reader = FakeReader()
    monkeypatch.setattr(
        "src.vision.ocr_reader.preprocess_variants",
        lambda _image: [np.zeros((20, 40), dtype=np.uint8)],
    )
    assert reader.read(np.zeros((10, 20, 3), dtype=np.uint8)) == ("123 تونس 4567", 0.9)


def test_plate_detector_rejects_tiny_contour_and_uses_fallback() -> None:
    """A tiny contour hit must not win over the plausible fallback region."""
    # A large car crop with a small bright blob (noise) in the lower region.
    crop = np.zeros((200, 360, 3), dtype=np.uint8)
    cv2.rectangle(crop, (150, 150), (170, 165), (255, 255, 255), -1)
    detection = PlateDetector().detect(crop)
    assert detection is not None
    # Fallback spans ~84% of the car width; a noise blob would be ~20px.
    assert detection.box[2] >= 360 * 0.5


def test_vision_worker_votes_and_saves_car_and_plate_automatically(tmp_path: Path) -> None:
    frame = np.full((160, 220, 3), 180, dtype=np.uint8)

    class FakeStream:
        def __init__(self) -> None:
            self.frame_number = 0

        def start(self) -> bool:
            return True

        def get_frame_snapshot(self):
            self.frame_number += 1
            return self.frame_number, frame.copy()

        def stop(self) -> None:
            return None

    class FakeDetector:
        def detect(self, _frame):
            from src.vision.car_detector import CarDetection

            return [CarDetection((20, 20, 160, 120), 2, 0.95)]

    class FakePlateReader:
        def read(self, _crop):
            return "123 تونس 4567", 0.95

    worker = VisionWorker(
        FakeStream(),
        "entry",
        tmp_path,
        detector=FakeDetector(),
        plate_detector=type(
            "FixedPlateDetector",
            (),
            {"detect": lambda _self, _crop: PlateDetection((25, 70, 90, 22), True)},
        )(),
        ocr_reader=FakePlateReader(),
    )
    assert worker.start()
    ready = threading.Event()
    observation = None
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        try:
            observation = worker.updates.get(timeout=0.05)
        except queue.Empty:
            continue
        if observation.car_image and observation.plate_image:
            ready.set()
            break
    worker.stop()
    assert ready.is_set()
    assert observation.plate_display == "123 تونس 4567"
    assert Path(observation.car_image).is_file()
    assert Path(observation.plate_image).is_file()
