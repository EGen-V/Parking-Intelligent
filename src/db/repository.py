"""SQLite repository for parking records."""

from __future__ import annotations

import sqlite3

from src.db.database import get_connection


class ParkingRepository:
    """Provide parameterized queries for the pointages table."""

    def __init__(self, db_path=None) -> None:
        self.db_path = db_path

    def find_open_by_plate(self, plate_key: str) -> sqlite3.Row | None:
        conn = get_connection(self.db_path)
        try:
            return conn.execute(
                """
                SELECT * FROM pointages
                WHERE plate_key = ? AND exit_time IS NULL
                ORDER BY entry_time DESC, id DESC
                LIMIT 1
                """,
                (plate_key,),
            ).fetchone()
        finally:
            conn.close()

    def create_entry(
        self,
        plate_display: str,
        plate_key: str,
        entry_time: str,
        entry_image: str | None = None,
        plate_image: str | None = None,
        confidence: float = 0.0,
    ) -> int:
        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(
                """
                INSERT INTO pointages (
                    plate_display, plate_key, entry_time, exit_time,
                    duration_seconds, status, entry_image, exit_image,
                    plate_image, confidence
                ) VALUES (?, ?, ?, NULL, NULL, 'EN_COURS', ?, NULL, ?, ?)
                """,
                (
                    plate_display,
                    plate_key,
                    entry_time,
                    entry_image,
                    plate_image,
                    confidence,
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)
        finally:
            conn.close()

    def close_entry(
        self,
        record_id: int,
        exit_time: str,
        duration_seconds: int,
        exit_image: str | None = None,
        exit_plate_image: str | None = None,
    ) -> None:
        conn = get_connection(self.db_path)
        try:
            conn.execute(
                """
                UPDATE pointages
                SET exit_time = ?, duration_seconds = ?, status = 'TERMINE',
                    exit_image = COALESCE(?, exit_image),
                    exit_plate_image = COALESCE(?, exit_plate_image)
                WHERE id = ?
                """,
                (exit_time, duration_seconds, exit_image, exit_plate_image, record_id),
            )
            conn.commit()
        finally:
            conn.close()

    def list_records(self, search: str = "", date: str = "") -> list[sqlite3.Row]:
        conn = get_connection(self.db_path)
        try:
            clauses: list[str] = []
            parameters: list[str] = []
            if search:
                clauses.append("(plate_display LIKE ? OR plate_key LIKE ?)")
                term = f"%{search}%"
                parameters.extend((term, term))
            if date:
                clauses.append("substr(entry_time, 1, 10) = ?")
                parameters.append(date)
            where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
            return conn.execute(
                f"SELECT * FROM pointages{where} ORDER BY entry_time DESC, id DESC",
                parameters,
            ).fetchall()
        finally:
            conn.close()

    def count_open(self) -> int:
        conn = get_connection(self.db_path)
        try:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM pointages WHERE exit_time IS NULL"
            ).fetchone()
            return int(row["n"])
        finally:
            conn.close()

    def clear_all(self) -> None:
        """Delete every pointage in this repository's database."""
        conn = get_connection(self.db_path)
        try:
            conn.execute("DELETE FROM pointages")
            conn.commit()
        finally:
            conn.close()

