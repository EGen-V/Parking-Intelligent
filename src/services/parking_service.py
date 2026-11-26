"""Parking business rules."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src import config
from src.db.database import initialize
from src.db.repository import ParkingRepository
from src.vision.ocr_reader import normalize_plate, validate_plate


class ServiceError(Exception):
    """A user-readable parking operation error."""


class ParkingService:
    """Enforce entry, exit and summary rules."""

    def __init__(
        self,
        repository: ParkingRepository | None = None,
        db_path: Path | None = None,
    ) -> None:
        if repository is not None and db_path is not None:
            raise ValueError("Provide either a repository or a database path")
        if repository is None:
            initialize(db_path)
            repository = ParkingRepository(db_path)
        self.repository = repository

    @staticmethod
    def now_iso() -> str:
        try:
            local_zone = ZoneInfo(config.TIMEZONE)
        except ZoneInfoNotFoundError:
            local_zone = timezone(timedelta(hours=1))
        return datetime.now(local_zone).isoformat(timespec="seconds")

    def record_entry(
        self,
        plate_text: str,
        entry_image: str | None = None,
        plate_image: str | None = None,
        confidence: float = 0.0,
    ) -> dict:
        display = validate_plate(plate_text)
        if display is None:
            raise ValueError("Format de plaque non reconnu")
        plate_key = normalize_plate(display)
        open_record = self.repository.find_open_by_plate(plate_key)
        if open_record:
            raise ServiceError("Véhicule déjà dans le parking")
        record_id = self.repository.create_entry(
            display,
            plate_key,
            self.now_iso(),
            entry_image,
            plate_image,
            confidence,
        )
        return {"id": record_id, "plate_display": display, "plate_key": plate_key}

    def record_exit(
        self,
        plate_text: str,
        exit_image: str | None = None,
        plate_image: str | None = None,
    ) -> dict:
        display = validate_plate(plate_text)
        if display is None:
            raise ValueError("Format de plaque non reconnu")
        plate_key = normalize_plate(display)
        open_record = self.repository.find_open_by_plate(plate_key)
        if not open_record:
            raise ServiceError("Aucune entrée trouvée")
        exit_time = self.now_iso()
        entry_time = datetime.fromisoformat(str(open_record["entry_time"]))
        exit_dt = datetime.fromisoformat(exit_time)
        duration = max(0, int((exit_dt - entry_time).total_seconds()))
        self.repository.close_entry(
            int(open_record["id"]),
            exit_time,
            duration,
            exit_image,
            plate_image,
        )
        return {
            "id": int(open_record["id"]),
            "plate_display": str(open_record["plate_display"]),
            "duration_seconds": duration,
        }

    def get_records(self, search: str = "", date: str = "") -> list[dict]:
        return [dict(row) for row in self.repository.list_records(search, date)]

    def get_summary(self) -> dict:
        records = self.get_records()
        try:
            local_zone = ZoneInfo(config.TIMEZONE)
        except ZoneInfoNotFoundError:
            local_zone = timezone(timedelta(hours=1))
        today = datetime.now(local_zone).date().isoformat()
        entries_today = sum(
            str(record["entry_time"])[:10] == today for record in records
        )
        exits_today = sum(
            record["exit_time"] is not None
            and str(record["exit_time"])[:10] == today
            for record in records
        )
        open_count = self.repository.count_open()
        return {
            "entries_today": entries_today,
            "exits_today": exits_today,
            "open_count": open_count,
            "available": max(0, config.PARKING_CAPACITY - open_count),
            "capacity": config.PARKING_CAPACITY,
        }

    def reset_test_data(self) -> None:
        """Clear test records and test captures, never touching live data."""
        database_path = self.repository.db_path
        if database_path is None or Path(database_path).resolve() != config.TEST_DB_PATH.resolve():
            raise ServiceError("La réinitialisation est réservée à la base de test")
        capture_dir = config.TEST_CAPTURES_DIR.resolve()
        if capture_dir.parent != config.DATA_DIR.resolve():
            raise ServiceError("Dossier de captures de test hors du répertoire autorisé")
        self.repository.clear_all()
        if capture_dir.exists():
            shutil.rmtree(capture_dir)


def format_duration(seconds: int | None) -> str:
    """Format a duration as French UI text."""
    if seconds is None:
        return ""
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    if hours:
        return f"{hours}h {minutes}min"
    return f"{minutes} min"
