"""Automatic car and plate crop persistence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import cv2
import numpy as np

from src import config
from src.vision.crop import crop_with_margin
from src.vision.plate_detector import PlateDetection


class CaptureStore:
    """Crop, clamp, and persist a vehicle and its plate candidate."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or config.CAPTURES_DIR

    def save(
        self,
        frame: np.ndarray,
        car_box: tuple[int, int, int, int],
        plate: PlateDetection,
        plate_key: str,
        camera_role: str,
    ) -> dict[str, str] | None:
        """Save automatic vehicle and plate crops under role/date folders."""
        if camera_role not in {"entry", "exit"}:
            raise ValueError(f"Unknown camera role: {camera_role}")
        car_result = crop_with_margin(
            frame,
            car_box,
            config.CAR_CROP_MARGIN,
            config.MIN_CAR_CROP_SIZE,
        )
        if car_result is None:
            return None
        car_crop, car_frame_box = car_result
        local_plate = crop_with_margin(
            car_crop,
            plate.box,
            config.PLATE_CROP_MARGIN,
            config.MIN_PLATE_CROP_SIZE,
        )
        if local_plate is None:
            return None
        plate_crop, _ = local_plate

        try:
            now = datetime.now(ZoneInfo(config.TIMEZONE))
        except ZoneInfoNotFoundError:
            now = datetime.now(timezone(timedelta(hours=1)))
        folder = self.base_dir / camera_role / now.date().isoformat()
        folder.mkdir(parents=True, exist_ok=True)
        safe_key = re.sub(r"[^A-Za-z0-9]+", "", plate_key) or config.CAPTURE_UNKNOWN_PLATE_KEY
        timestamp = now.strftime("%Y%m%d_%H%M%S_%f")
        car_path = folder / f"{timestamp}_{safe_key}_car.jpg"
        plate_path = folder / f"{timestamp}_{safe_key}_plate.jpg"
        if not cv2.imwrite(str(car_path), car_crop) or not cv2.imwrite(str(plate_path), plate_crop):
            car_path.unlink(missing_ok=True)
            plate_path.unlink(missing_ok=True)
            raise OSError(f"Impossible d'enregistrer les captures dans {folder}")
        return {
            "car_image": str(car_path),
            "plate_image": str(plate_path),
            "car_box": car_frame_box,
        }
