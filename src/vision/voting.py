"""Temporal voting and same-vehicle association for plate reads."""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
import time

from src import config
from src.vision.ocr_reader import normalize_plate

Box = tuple[int, int, int, int]


@dataclass(frozen=True)
class PlateVote:
    """A plate read accepted after repeated matching OCR results."""

    plate_display: str
    plate_key: str
    confidence: float
    box: Box


def intersection_over_union(first: Box, second: Box) -> float:
    """Compute intersection-over-union for two xywh boxes."""
    x1, y1, width1, height1 = first
    x2, y2, width2, height2 = second
    left, top = max(x1, x2), max(y1, y2)
    right = min(x1 + width1, x2 + width2)
    bottom = min(y1 + height1, y2 + height2)
    intersection = max(0, right - left) * max(0, bottom - top)
    union = width1 * height1 + width2 * height2 - intersection
    return intersection / union if union > 0 else 0.0


class PlateVoter:
    """Accept an OCR result only after repeated reads of the same tracked car."""

    def __init__(
        self,
        required_votes: int = config.PLATE_VOTE_COUNT,
        track_iou: float = config.PLATE_TRACK_IOU,
        window_seconds: float = config.PLATE_VOTE_WINDOW_SECONDS,
        clock=time.monotonic,
    ) -> None:
        self.required_votes = required_votes
        self.track_iou = track_iou
        self.window_seconds = window_seconds
        self.clock = clock
        self._reads: deque[tuple[str, str, float, float]] = deque()
        self._box: Box | None = None
        self._last_seen = 0.0
        self._emitted_keys: set[str] = set()

    def add(
        self,
        plate_display: str | None,
        confidence: float,
        box: Box,
    ) -> PlateVote | None:
        """Add a candidate read and return the first sufficiently voted plate."""
        now = self.clock()
        if (
            self._box is None
            or intersection_over_union(self._box, box) < self.track_iou
            or now - self._last_seen > self.window_seconds
        ):
            self._reads.clear()
            self._emitted_keys.clear()
        self._box = box
        self._last_seen = now
        if not plate_display:
            return None
        try:
            plate_key = normalize_plate(plate_display)
        except ValueError:
            return None
        self._reads.append((plate_key, plate_display, confidence, now))
        while self._reads and now - self._reads[0][3] > self.window_seconds:
            self._reads.popleft()
        counts = Counter(item[0] for item in self._reads)
        winning_key, votes = counts.most_common(1)[0]
        if votes < self.required_votes or winning_key in self._emitted_keys:
            return None
        matching = [item for item in self._reads if item[0] == winning_key]
        self._emitted_keys.add(winning_key)
        return PlateVote(
            matching[-1][1],
            winning_key,
            sum(item[2] for item in matching) / len(matching),
            box,
        )


class PlateDebouncer:
    """Suppress repeated plate events during the configured debounce window."""

    def __init__(self, seconds: float = config.DEBOUNCE_SECONDS, clock=time.monotonic) -> None:
        self.seconds = seconds
        self.clock = clock
        self._last_emitted: dict[str, float] = {}

    def accept(self, plate_key: str) -> bool:
        """Return true for the first event and after the debounce interval."""
        now = self.clock()
        previous = self._last_emitted.get(plate_key)
        if previous is not None and now - previous < self.seconds:
            return False
        self._last_emitted[plate_key] = now
        return True
