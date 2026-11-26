"""Contour-based license-plate localization inside a detected vehicle."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from src import config


@dataclass(frozen=True)
class PlateDetection:
    """A plate candidate and whether its outline was localized."""

    box: tuple[int, int, int, int]
    localized: bool


class PlateDetector:
    """Find a plate-shaped contour; fall back to the lower vehicle region."""

    def detect(self, car_crop: np.ndarray) -> PlateDetection | None:
        if car_crop is None or car_crop.size == 0:
            return None
        height, width = car_crop.shape[:2]
        if width < config.MIN_CAR_CROP_SIZE[0] or height < config.MIN_CAR_CROP_SIZE[1]:
            return None
        roi_y = int(height * config.PLATE_REGION_TOP_FRACTION)
        roi = car_crop[roi_y:, :]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        enhanced = cv2.createCLAHE(
            clipLimit=config.PREPROCESS_CLAHE_CLIP_LIMIT,
            tileGridSize=config.PREPROCESS_CLAHE_GRID_SIZE,
        ).apply(gray)
        filtered = cv2.bilateralFilter(
            enhanced,
            config.PREPROCESS_DENOISE_DIAMETER,
            config.PREPROCESS_DENOISE_SIGMA_COLOR,
            config.PREPROCESS_DENOISE_SIGMA_SPACE,
        )
        threshold = cv2.adaptiveThreshold(
            filtered,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            config.PLATE_ADAPTIVE_BLOCK_SIZE,
            config.PLATE_ADAPTIVE_C,
        )
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, config.PLATE_MORPH_KERNEL)
        threshold = cv2.morphologyEx(threshold, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(
            threshold,
            cv2.RETR_LIST,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        candidates: list[tuple[float, tuple[int, int, int, int]]] = []
        for contour in contours:
            x, y, box_width, box_height = cv2.boundingRect(contour)
            area = box_width * box_height
            ratio = box_width / max(1, box_height)
            area_fraction = area / max(1, width * height)
            if (
                box_width < config.MIN_PLATE_CROP_SIZE[0]
                or box_height < config.MIN_PLATE_CROP_SIZE[1]
                or not config.PLATE_ASPECT_RATIO_MIN <= ratio <= config.PLATE_ASPECT_RATIO_MAX
                or not config.PLATE_AREA_FRACTION_MIN <= area_fraction <= config.PLATE_AREA_FRACTION_MAX
            ):
                continue
            global_y = y + roi_y
            centrality = 1.0 - abs((x + box_width / 2) - width / 2) / max(1, width)
            lower_position = global_y / max(1, height)
            score = area_fraction * centrality * (0.5 + lower_position)
            candidates.append((score, (x, global_y, box_width, box_height)))

        if candidates:
            _, best_box = max(candidates, key=lambda candidate: candidate[0])
            # Reject a "localized" box that is implausibly small next to the car:
            # a real plate spans a meaningful fraction of the vehicle width. Tiny
            # contour hits (13x52 etc.) are noise and lead to blank OCR crops.
            plate_width = best_box[2]
            if plate_width >= width * config.PLATE_MIN_WIDTH_FRACTION:
                return PlateDetection(best_box, True)

        fallback_box = (
            int(width * config.PLATE_FALLBACK_X),
            int(height * config.PLATE_FALLBACK_Y),
            max(1, int(width * config.PLATE_FALLBACK_WIDTH)),
            max(1, int(height * config.PLATE_FALLBACK_HEIGHT)),
        )
        if (
            fallback_box[2] < config.MIN_PLATE_CROP_SIZE[0]
            or fallback_box[3] < config.MIN_PLATE_CROP_SIZE[1]
        ):
            return None
        return PlateDetection(fallback_box, False)
