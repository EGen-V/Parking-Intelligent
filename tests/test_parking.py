"""Tests for normalization and parking business rules."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.db.database import initialize
from src.db.repository import ParkingRepository
from src.services.parking_service import ParkingService, ServiceError, format_duration
from src.vision.ocr_reader import normalize_plate, validate_plate


@pytest.fixture
def service(tmp_path: Path) -> ParkingService:
    db_path = tmp_path / "parking.db"
    initialize(db_path)
    return ParkingService(ParkingRepository(db_path))


def test_normalize_and_validate_plate() -> None:
    assert normalize_plate("123 تونس 4567") == "123TN4567"
    assert normalize_plate("١٢٣ تونس ٤٥٦٧") == "123TN4567"
    assert validate_plate("123 تونس 4567") == "123 تونس 4567"
    assert validate_plate("abc") is None


def test_duplicate_entry(service: ParkingService) -> None:
    service.record_entry("123 تونس 4567")
    with pytest.raises(ServiceError, match="déjà dans le parking"):
        service.record_entry("123 تونس 4567")


def test_exit_without_entry(service: ParkingService) -> None:
    with pytest.raises(ServiceError, match="Aucune entrée"):
        service.record_exit("123 تونس 4567")


def test_entry_exit_and_duration(service: ParkingService) -> None:
    service.record_entry(
        "123 تونس 4567",
        entry_image="entry-car.jpg",
        plate_image="entry-plate.jpg",
        confidence=0.92,
    )
    record = service.repository.find_open_by_plate("123TN4567")
    assert record is not None
    result = service.record_exit(
        "123 تونس 4567",
        exit_image="exit-car.jpg",
        plate_image="exit-plate.jpg",
    )
    assert result["duration_seconds"] >= 0
    closed = service.get_records()[0]
    assert closed["entry_image"] == "entry-car.jpg"
    assert closed["plate_image"] == "entry-plate.jpg"
    assert closed["exit_image"] == "exit-car.jpg"
    assert closed["exit_plate_image"] == "exit-plate.jpg"
    assert format_duration(8100) == "2h 15min"
    assert format_duration(2040) == "34 min"


def test_free_places(service: ParkingService) -> None:
    service.record_entry("123 تونس 4567")
    summary = service.get_summary()
    assert summary["available"] == 29


def test_invalid_plate_is_rejected(service: ParkingService) -> None:
    with pytest.raises(ValueError, match="Format de plaque"):
        service.record_entry("garbage")


def test_entry_exit_duration_uses_timestamps_exactly(
    service: ParkingService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timestamps = iter(
        (
            "2026-11-24T08:00:00+01:00",
            "2026-11-24T10:15:00+01:00",
        )
    )
    monkeypatch.setattr(ParkingService, "now_iso", staticmethod(lambda: next(timestamps)))
    service.record_entry("123 تونس 4567")
    result = service.record_exit("123 تونس 4567")
    assert result["duration_seconds"] == 8100


def test_test_database_reset_clears_only_test_records_and_captures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_db = tmp_path / "parking_test.db"
    live_db = tmp_path / "parking.db"
    captures = tmp_path / "captures_test"
    monkeypatch.setattr("src.config.TEST_DB_PATH", test_db)
    monkeypatch.setattr("src.config.DATA_DIR", tmp_path)
    monkeypatch.setattr("src.config.TEST_CAPTURES_DIR", captures)
    initialize(test_db)
    initialize(live_db)
    test_service = ParkingService(ParkingRepository(test_db))
    live_service = ParkingService(ParkingRepository(live_db))
    test_service.record_entry("123 تونس 4567")
    live_service.record_entry("456 تونس 7890")
    captures.mkdir()
    (captures / "sample.jpg").write_bytes(b"test")

    test_service.reset_test_data()

    assert test_service.get_records() == []
    assert len(live_service.get_records()) == 1
    assert not captures.exists()


def test_live_database_cannot_use_test_reset(service: ParkingService) -> None:
    with pytest.raises(ServiceError, match="réservée à la base de test"):
        service.reset_test_data()
