"""Plate image preprocessing variants for local OCR.

Each variant is deliberately *different* so the OCR voter sees distinct
candidates instead of near-identical copies (the previous deskew/threshold
variants collapsed to the same image). The variants cover the common failure
modes of Tunisian plates: low contrast, uneven lighting and a dark-on-light or
light-on-dark band.
"""

from __future__ import annotations

import cv2
import numpy as np

from src import config


def deskew(image: np.ndarray) -> np.ndarray:
    """Rotate a plate crop to level its strongest text-like component."""
    gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, threshold = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
    )
    points = cv2.findNonZero(threshold)
    if points is None or len(points) < 8:
        return image
    angle = cv2.minAreaRect(points)[-1]
    if angle < -45:
        angle += 90
    if abs(angle) < config.DESKEW_MIN_ANGLE or abs(angle) > config.DESKEW_MAX_ANGLE:
        return image
    height, width = gray.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
    return cv2.warpAffine(
        image,
        matrix,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def _upscale(gray: np.ndarray) -> np.ndarray:
    scale = max(2.0, min(3.0, config.PREPROCESS_SCALE))
    return cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)


def preprocess_variants(image: np.ndarray) -> list[np.ndarray]:
    """Create distinct grayscale, denoised, contrast and threshold variants.

    The variants are intentionally different from one another so the OCR voter
    can pick the one that reads best for a given crop.
    """
    if image is None or image.size == 0:
        return []
    gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    resized = _upscale(gray)

    denoised = (
        cv2.bilateralFilter(
            resized,
            config.PREPROCESS_DENOISE_DIAMETER,
            config.PREPROCESS_DENOISE_SIGMA_COLOR,
            config.PREPROCESS_DENOISE_SIGMA_SPACE,
        )
        if config.PREPROCESS_DENOISE
        else resized
    )

    enhanced = denoised
    if config.PREPROCESS_CLAHE:
        enhanced = cv2.createCLAHE(
            clipLimit=config.PREPROCESS_CLAHE_CLIP_LIMIT,
            tileGridSize=config.PREPROCESS_CLAHE_GRID_SIZE,
        ).apply(denoised)

    leveled = deskew(enhanced)

    variants: list[np.ndarray] = [resized, enhanced, leveled]

    if config.PREPROCESS_THRESHOLD:
        # Global Otsu (robust for a bright plate on a dark car).
        _, otsu = cv2.threshold(leveled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants.append(otsu)
        # Adaptive Gaussian (robust for uneven lighting).
        variants.append(
            cv2.adaptiveThreshold(
                leveled,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                config.PREPROCESS_ADAPTIVE_BLOCK_SIZE,
                config.PREPROCESS_ADAPTIVE_C,
            )
        )
    return variants