"""Threaded OpenCV camera and demo-source wrapper."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

try:
    import cv2
except Exception:  # pragma: no cover - handled as a no-camera fallback
    cv2 = None

from src import config

logger = logging.getLogger(__name__)


def list_test_videos(directory: Path = config.TEST_VIDEO_DIR) -> list[Path]:
    """Return supported video files in a test-video directory."""
    if not directory.is_dir():
        return []
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in config.TEST_VIDEO_EXTENSIONS
    )


class CameraStream:
    """Read frames in a worker thread and expose the latest frame."""

    def __init__(self, source: int | str = 0) -> None:
        self.source = source
        self._capture = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._frame_lock = threading.Lock()
        self._frame = None
        self._frame_number = 0
        self.error: str | None = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()

    def start(self) -> bool:
        if cv2 is None:
            self.error = "OpenCV n'est pas installé."
            return False
        if self._thread is not None and self._thread.is_alive():
            return True
        self.error = None
        self._stop_event.clear()
        self._pause_event.clear()
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, name="camera-stream", daemon=True)
        self._thread.start()
        return True

    def _read_loop(self) -> None:
        capture = None
        frames_read = 0
        try:
            capture = cv2.VideoCapture(self.source)
            self._capture = capture
            if not capture.isOpened():
                self.error = (
                    f"Vidéo illisible : {Path(self.source).name}"
                    if isinstance(self.source, (str, Path))
                    else f"Caméra indisponible (index {self.source})."
                )
                return
            while not self._stop_event.is_set():
                if self._pause_event.is_set():
                    self._stop_event.wait(0.05)
                    continue
                success, frame = capture.read()
                if not success:
                    if isinstance(self.source, (str, Path)):
                        if frames_read == 0:
                            self.error = f"Vidéo illisible : {Path(self.source).name}"
                            return
                        capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        self._stop_event.wait(0.02)
                    else:
                        self._stop_event.wait(0.05)
                    continue
                with self._frame_lock:
                    self._frame = frame
                    self._frame_number += 1
                frames_read += 1
                self._stop_event.wait(0.025)
        except cv2.error as exc:
            logger.warning("Camera source failed: %s", exc)
            self.error = f"Impossible de lire la caméra ou la vidéo : {exc}"
        finally:
            if capture is not None:
                capture.release()
            self._capture = None
            self._running = False

    def get_frame(self):
        with self._frame_lock:
            if self._frame is None:
                return None
            return self._frame.copy()

    def get_frame_snapshot(self):
        """Return the most recent frame and its sequence number."""
        with self._frame_lock:
            if self._frame is None:
                return None
            return self._frame_number, self._frame.copy()

    @property
    def paused(self) -> bool:
        """Whether frame reading is paused."""
        return self._pause_event.is_set()

    def pause(self) -> None:
        """Pause the stream without stopping or releasing its source."""
        self._pause_event.set()

    def resume(self) -> None:
        """Resume reading from the current source position."""
        self._pause_event.clear()

    def stop(self) -> None:
        self._stop_event.set()
        self._running = False
