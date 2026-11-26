"""Safe image cropping for detected vehicles and plates."""

from __future__ import annotations

from typing import TypeAlias

import numpy as np

Box: TypeAlias = tuple[int, int, int, int]


def crop_with_margin(
    image: np.ndarray,
    box: Box,
    margin: float,
    minimum_size: tuple[int, int],
) -> tuple[np.ndarray, Box] | None:
    """Crop a box with proportional margin, clamped to image bounds."""
    if image is None or image.size == 0:
        return None
    height, width = image.shape[:2]
    x, y, box_width, box_height = (int(value) for value in box)
    if box_width <= 0 or box_height <= 0:
        return None
    margin_x = int(round(box_width * max(0.0, margin)))
    margin_y = int(round(box_height * max(0.0, margin)))
    left = max(0, x - margin_x)
    top = max(0, y - margin_y)
    right = min(width, x + box_width + margin_x)
    bottom = min(height, y + box_height + margin_y)
    if right - left < minimum_size[0] or bottom - top < minimum_size[1]:
        return None
    return image[top:bottom, left:right].copy(), (left, top, right - left, bottom - top)
