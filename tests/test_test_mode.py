"""Tests for test-video discovery and threaded playback controls."""

from __future__ import annotations

from pathlib import Path
import time

from src.camera.camera_stream import CameraStream, list_test_videos


def test_video_discovery_handles_missing_and_empty_directories(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    empty = tmp_path / "empty"
    empty.mkdir()
    assert list_test_videos(missing) == []
    assert list_test_videos(empty) == []


def test_video_discovery_filters_extensions_and_sorts(tmp_path: Path) -> None:
    (tmp_path / "zeta.mp4").write_bytes(b"")
    (tmp_path / "alpha.MKV").write_bytes(b"")
    (tmp_path / "notes.txt").write_text("not a video")
    assert [path.name for path in list_test_videos(tmp_path)] == [
        "alpha.MKV",
        "zeta.mp4",
    ]


def test_camera_stream_reports_unreadable_video(tmp_path: Path) -> None:
    source = tmp_path / "broken.mp4"
    source.write_bytes(b"not a video")
    stream = CameraStream(str(source))
    assert stream.start()
    deadline = time.monotonic() + 2.0
    while stream.error is None and time.monotonic() < deadline:
        time.sleep(0.01)
    stream.stop()
    if stream._thread:
        stream._thread.join(timeout=2.0)
    assert stream.error == f"Vidéo illisible : {source.name}"


def test_camera_stream_can_pause_resume_and_loop() -> None:
    videos = list_test_videos()
    assert videos, "The project test-video directory must include a sample"
    stream = CameraStream(str(videos[0]))
    assert stream.start()
    deadline = time.monotonic() + 3.0
    first = None
    while time.monotonic() < deadline:
        first = stream.get_frame_snapshot()
        if first is not None:
            break
        time.sleep(0.01)
    assert first is not None

    stream.pause()
    paused_frame = stream.get_frame_snapshot()
    time.sleep(0.1)
    assert stream.paused
    assert stream.get_frame_snapshot()[0] == paused_frame[0]

    stream.resume()
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        if stream.get_frame_snapshot()[0] > paused_frame[0]:
            break
        time.sleep(0.01)
    stream.stop()
    if stream._thread:
        stream._thread.join(timeout=2.0)
    assert not stream.paused
    assert stream.get_frame_snapshot()[0] > paused_frame[0]
