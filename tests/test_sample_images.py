"""Measured local vision checks against extracted traffic-video frames."""

from __future__ import annotations

import cv2
import pytest

from src import config
from src.vision.car_detector import get_car_detector
from src.vision.crop import crop_with_margin
from src.vision.ocr_reader import OCRReader, validate_plate
from src.vision.plate_detector import PlateDetector

SAMPLE_IMAGES = sorted(config.TEST_IMAGES_DIR.glob("*.jpg"))
LOCAL_OCR_READY = (
    (config.OCR_MODEL_DIR / "arabic.pth").is_file()
    and (config.OCR_MODEL_DIR / "craft_mlt_25k.pth").is_file()
)


@pytest.mark.skipif(
    not config.CAR_MODEL_WEIGHTS_PATH.is_file()
    or not config.CAR_MODEL_CONFIG_PATH.is_file(),
    reason="Download the local YOLOv4-tiny files to run model-backed sample checks.",
)
def test_car_detector_finds_a_vehicle_in_each_sample_image() -> None:
    assert SAMPLE_IMAGES, "tests/data must contain extracted sample frames"
    detector = get_car_detector()
    for path in SAMPLE_IMAGES:
        image = cv2.imread(str(path))
        assert image is not None, f"Could not read {path.name}"
        assert detector.detect(image), f"No vehicle detected in {path.name}"


@pytest.mark.skipif(
    not config.CAR_MODEL_WEIGHTS_PATH.is_file()
    or not config.CAR_MODEL_CONFIG_PATH.is_file()
    or not LOCAL_OCR_READY,
    reason="Download the local car and EasyOCR models to run OCR sample checks.",
)
def test_sample_plate_ocr_only_returns_validated_formats() -> None:
    assert SAMPLE_IMAGES, "tests/data must contain extracted sample frames"
    detector = get_car_detector()
    plate_detector = PlateDetector()
    reader = OCRReader()
    for path in SAMPLE_IMAGES:
        image = cv2.imread(str(path))
        assert image is not None, f"Could not read {path.name}"
        detections = detector.detect(image)
        assert detections, f"No vehicle detected in {path.name}"
        largest = max(detections, key=lambda item: item.box[2] * item.box[3])
        car_result = crop_with_margin(
            image,
            largest.box,
            config.CAR_CROP_MARGIN,
            config.MIN_CAR_CROP_SIZE,
        )
        assert car_result is not None, f"Car crop too small in {path.name}"
        plate_candidate = plate_detector.detect(car_result[0])
        assert plate_candidate is not None, f"No plate candidate in {path.name}"
        plate_result = crop_with_margin(
            car_result[0],
            plate_candidate.box,
            config.PLATE_CROP_MARGIN,
            config.MIN_PLATE_CROP_SIZE,
        )
        assert plate_result is not None, f"Plate crop too small in {path.name}"
        display, confidence = reader.read(plate_result[0])
        assert 0.0 <= confidence <= 1.0
        assert display is None or validate_plate(display) == display
