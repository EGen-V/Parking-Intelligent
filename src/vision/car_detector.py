"""Local YOLOv4-tiny car, bus and truck detection."""

from __future__ import annotations

from dataclasses import dataclass
import threading

import cv2
import numpy as np

from src import config

_INFERENCE_LOCK = threading.Lock()
_DETECTOR_LOCK = threading.Lock()
_DETECTOR_INSTANCE: CarDetector | None = None


@dataclass(frozen=True)
class CarDetection:
    """A detected vehicle box in frame coordinates."""

    box: tuple[int, int, int, int]
    class_id: int
    confidence: float


class CarDetector:
    """Load one local OpenCV DNN model and reuse it for each frame."""

    def __init__(self) -> None:
        if not config.CAR_MODEL_CONFIG_PATH.is_file() or not config.CAR_MODEL_WEIGHTS_PATH.is_file():
            raise FileNotFoundError(
                "Modèle YOLO absent. Exécutez « python -m src.vision.download_models »."
            )
        network = cv2.dnn.readNetFromDarknet(
            str(config.CAR_MODEL_CONFIG_PATH),
            str(config.CAR_MODEL_WEIGHTS_PATH),
        )
        self._model = cv2.dnn_DetectionModel(network)
        self._model.setInputParams(
            scale=1 / 255.0,
            size=config.DETECTION_INPUT_SIZE,
            swapRB=True,
        )

    def detect(self, frame) -> list[CarDetection]:
        """Return confident COCO car, bus and truck detections."""
        with _INFERENCE_LOCK:
            class_ids, confidences, boxes = self._model.detect(
                frame,
                confThreshold=config.CAR_DETECT_CONFIDENCE,
                nmsThreshold=config.CAR_DETECT_NMS_THRESHOLD,
            )
        if class_ids is None or confidences is None or boxes is None:
            return []
        class_values = np.asarray(class_ids).reshape(-1)
        confidence_values = np.asarray(confidences).reshape(-1)
        box_values = np.asarray(boxes)
        if box_values.size == 0:
            return []
        box_values = box_values.reshape(-1, 4)
        detections = []
        for class_id, confidence, box in zip(
            class_values,
            confidence_values,
            box_values,
        ):
            class_number = int(class_id)
            if class_number not in config.CAR_CLASS_IDS:
                continue
            x, y, width, height = (int(value) for value in box)
            if width <= 0 or height <= 0:
                continue
            detections.append(
                CarDetection(
                    (x, y, width, height),
                    class_number,
                    float(confidence),
                )
            )
        return detections


def get_car_detector() -> CarDetector:
    """Return the process-wide detector so the model loads only once."""
    global _DETECTOR_INSTANCE
    with _DETECTOR_LOCK:
        if _DETECTOR_INSTANCE is None:
            _DETECTOR_INSTANCE = CarDetector()
        return _DETECTOR_INSTANCE
