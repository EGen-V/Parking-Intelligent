"""Path handling for the frozen one-file Windows build."""

from __future__ import annotations

import importlib
from pathlib import Path
import sys

import src.config as config


def test_frozen_resources_and_writable_data_use_separate_roots(
    monkeypatch,
    tmp_path: Path,
) -> None:
    bundle_dir = tmp_path / "bundle"
    executable_dir = tmp_path / "release"
    bundled_videos = bundle_dir / "test-video"
    bundled_videos.mkdir(parents=True)
    executable_dir.mkdir()
    (bundled_videos / "bundled.mp4").write_bytes(b"")

    try:
        with monkeypatch.context() as patch:
            patch.setattr(sys, "frozen", True, raising=False)
            patch.setattr(sys, "_MEIPASS", str(bundle_dir), raising=False)
            patch.setattr(sys, "executable", str(executable_dir / "ParkingIntelligent.exe"))
            importlib.reload(config)

            assert config.BASE_DIR == executable_dir
            assert config.RESOURCE_DIR == bundle_dir
            assert config.DATA_DIR == executable_dir / "data"
            assert config.MODELS_DIR == bundle_dir / "models"
            assert config.TEST_VIDEO_DIR == bundled_videos

            external_videos = executable_dir / "test-video"
            external_videos.mkdir()
            (external_videos / "custom.avi").write_bytes(b"")
            importlib.reload(config)
            assert config.TEST_VIDEO_DIR == external_videos
    finally:
        importlib.reload(config)
