"""Threaded vehicle detection, plate reading, voting and automatic capture."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import queue
import threading

import cv2

from src import config
from src.camera.camera_stream import CameraStream
from src.vision.capture_store import CaptureStore
from src.vision.car_detector import get_car_detector
from src.vision.crop import crop_with_margin
from src.vision.ocr_reader import OCRReader, get_ocr_reader, normalize_plate
from src.vision.plate_detector import PlateDetection, PlateDetector
from src.vision.voting import PlateDebouncer, PlateVoter, intersection_over_union

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VisionUpdate:
    """A UI-safe result from one processed camera frame."""

    frame: object
    car_box: tuple[int, int, int, int] | None = None
    plate_display: str | None = None
    confidence: float = 0.0
    car_image: str | None = None
    plate_image: str | None = None
    error: str | None = None


class VisionWorker:
    """Run model inference and OCR away from Tk's event thread."""

    def __init__(
        self,
        stream: CameraStream,
        camera_role: str,
        captures_dir: Path | None = None,
        detector=None,
        plate_detector: PlateDetector | None = None,
        ocr_reader: OCRReader | None = None,
    ) -> None:
        if camera_role not in {"entry", "exit"}:
            raise ValueError(f"Unknown camera role: {camera_role}")
        self.stream = stream
        self.camera_role = camera_role
        self.detector = detector
        self.plate_detector = plate_detector or PlateDetector()
        self.ocr_reader = ocr_reader or get_ocr_reader()
        self.capture_store = CaptureStore(captures_dir)
        self.updates: queue.Queue[VisionUpdate] = queue.Queue(maxsize=2)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._voter = PlateVoter()
        self._debouncer = PlateDebouncer()

    def start(self) -> bool:
        """Start the camera and pipeline worker."""
        if self._thread is not None and self._thread.is_alive():
            return True
        if not self.stream.start():
            self._publish(VisionUpdate(None, error=self.stream.error or "Caméra indisponible."))
            return False
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name=f"vision-{self.camera_role}", daemon=True)
        self._thread.start()
        return True

    def _run(self) -> None:
        try:
            detector = self.detector or get_car_detector()
        except (FileNotFoundError, cv2.error, OSError) as exc:
            logger.exception("Unable to initialize the local car detector")
            self._publish(VisionUpdate(None, error=str(exc)))
            return

        last_frame_number = -1
        processed_frames = 0
        last_box: tuple[int, int, int, int] | None = None
        stable_frames = 0
        failed_ocr_reads = 0
        last_ocr_frame = 0
        current_paths: dict[str, str] | None = None
        current_plate: str | None = None
        current_confidence = 0.0

        while not self._stop_event.is_set():
            snapshot = self.stream.get_frame_snapshot()
            if snapshot is None or snapshot[0] == last_frame_number:
                if self.stream.error:
                    self._publish(VisionUpdate(None, error=self.stream.error))
                    return
                self._stop_event.wait(0.02)
                continue
            frame_number, frame = snapshot
            last_frame_number = frame_number
            processed_frames += 1
            if processed_frames % config.VISION_FRAME_SKIP:
                continue
            try:
                detections = detector.detect(frame)
            except (cv2.error, RuntimeError, ValueError) as exc:
                logger.exception("Vehicle detection failed")
                self._publish(VisionUpdate(frame, error=f"Détection impossible : {exc}"))
                self._stop_event.wait(0.2)
                continue

            if not detections:
                last_box = None
                stable_frames = 0
                failed_ocr_reads = 0
                current_paths = None
                current_plate = None
                self._voter.add(None, 0.0, (0, 0, 0, 0))
                self._publish(VisionUpdate(frame))
                continue

            detection = max(
                detections,
                key=lambda item: item.box[2] * item.box[3],
            )
            box = detection.box
            if last_box and intersection_over_union(last_box, box) >= config.PLATE_TRACK_IOU:
                stable_frames += 1
            else:
                stable_frames = 1
                failed_ocr_reads = 0
                current_paths = None
                current_plate = None
                current_confidence = 0.0
            last_box = box

            car_result = crop_with_margin(
                frame,
                box,
                config.CAR_CROP_MARGIN,
                config.MIN_CAR_CROP_SIZE,
            )
            plate_detection: PlateDetection | None = None
            plate_crop = None
            if car_result is not None:
                car_crop, _ = car_result
                plate_detection = self.plate_detector.detect(car_crop)
                if plate_detection is not None:
                    plate_crop_result = crop_with_margin(
                        car_crop,
                        plate_detection.box,
                        config.PLATE_CROP_MARGIN,
                        config.MIN_PLATE_CROP_SIZE,
                    )
                    if plate_crop_result is not None:
                        plate_crop = plate_crop_result[0]

            vote = None
            if (
                plate_crop is not None
                and stable_frames >= config.CAR_STABILITY_FRAMES
                and processed_frames - last_ocr_frame >= config.OCR_FRAME_INTERVAL * config.VISION_FRAME_SKIP
            ):
                last_ocr_frame = processed_frames
                try:
                    plate_display, confidence = self.ocr_reader.read(plate_crop)
                except (RuntimeError, OSError, ValueError, cv2.error) as exc:
                    failed_ocr_reads += 1
                    logger.exception("Plate OCR failed")
                    self._publish(VisionUpdate(frame, box, error=f"OCR indisponible : {exc}"))
                else:
                    if plate_display:
                        vote = self._voter.add(plate_display, confidence, box)
                        current_plate = plate_display
                        current_confidence = confidence
                        failed_ocr_reads = 0
                    else:
                        self._voter.add(None, 0.0, box)
                        failed_ocr_reads += 1

            event_accepted = vote is not None and self._debouncer.accept(vote.plate_key)
            capture_without_vote = (
                vote is None
                and (
                    failed_ocr_reads >= config.OCR_FAILURE_LIMIT
                    or (
                        stable_frames >= config.CAR_CAPTURE_MAX_WAIT_FRAMES
                        and current_paths is None
                    )
                )
            )
            if (
                car_result is not None
                and plate_detection is not None
                and plate_crop is not None
                and stable_frames >= config.CAR_STABILITY_FRAMES
                and (event_accepted or capture_without_vote)
            ):
                plate_key = (
                    vote.plate_key
                    if event_accepted
                    else normalize_plate(current_plate)
                    if current_plate
                    else config.CAPTURE_UNKNOWN_PLATE_KEY
                )
                if current_paths is None or (vote is not None and current_plate == vote.plate_display):
                    saved = self.capture_store.save(
                        frame,
                        box,
                        plate_detection,
                        plate_key,
                        self.camera_role,
                    )
                    if saved:
                        current_paths = saved

            self._publish(
                VisionUpdate(
                    frame=frame,
                    car_box=box,
                    plate_display=current_plate,
                    confidence=current_confidence,
                    car_image=current_paths["car_image"] if current_paths else None,
                    plate_image=current_paths["plate_image"] if current_paths else None,
                )
            )

    def _publish(self, update: VisionUpdate) -> None:
        """Keep only recent frames/results so a slow UI cannot build a backlog."""
        try:
            self.updates.put_nowait(update)
        except queue.Full:
            try:
                self.updates.get_nowait()
            except queue.Empty:
                pass
            self.updates.put_nowait(update)

    def stop(self) -> None:
        """Stop the worker and release the camera."""
        self._stop_event.set()
        self.stream.stop()
