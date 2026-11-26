"""SQLite schema creation and connection management.

The schema is defined here and created automatically on first run. All
queries elsewhere use parameterized statements (see AGENTS.md section 5).
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from src import config

logger = logging.getLogger(__name__)

# Status constants stored in the ``status`` column.
STATUS_OPEN = "EN_COURS"
STATUS_CLOSED = "TERMINE"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pointages (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    plate_display    TEXT    NOT NULL,
    plate_key        TEXT    NOT NULL,
    entry_time       TEXT    NOT NULL,          -- ISO 8601 local (Africa/Tunis)
    exit_time        TEXT,                       -- NULL while inside
    duration_seconds INTEGER,                     -- NULL while inside
    status           TEXT    NOT NULL,            -- EN_COURS | TERMINE
    entry_image      TEXT,
    exit_image       TEXT,
    plate_image      TEXT,
    exit_plate_image TEXT,
    confidence       REAL
);

CREATE INDEX IF NOT EXISTS idx_pointages_plate_key
    ON pointages (plate_key);
CREATE INDEX IF NOT EXISTS idx_pointages_status
    ON pointages (status);
CREATE INDEX IF NOT EXISTS idx_pointages_entry_time
    ON pointages (entry_time);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def ensure_parent_dir(path: Path) -> None:
    """Create the parent directory of ``path`` if it does not exist."""
    path.parent.mkdir(parents=True, exist_ok=True)


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Open a SQLite connection with row factory and foreign keys enabled.

    The connection is configured so callers can use ``conn.execute(...)``
    with parameterized queries and get ``sqlite3.Row`` objects back.
    """
    path = Path(db_path) if db_path is not None else config.DB_PATH
    ensure_parent_dir(path)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Path | None = None) -> None:
    """Create the schema (tables + indexes) if it does not yet exist."""
    conn = get_connection(db_path)
    try:
        conn.executescript(_SCHEMA)
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(pointages)").fetchall()
        }
        if "exit_plate_image" not in columns:
            conn.execute("ALTER TABLE pointages ADD COLUMN exit_plate_image TEXT;")
        conn.commit()
        logger.info("Database initialized at %s", db_path or config.DB_PATH)
    finally:
        conn.close()


def init_default_settings(db_path: Path | None = None) -> None:
    """Insert default settings (capacity) if the settings table is empty."""
    conn = get_connection(db_path)
    try:
        cur = conn.execute("SELECT COUNT(*) AS n FROM settings;")
        count = cur.fetchone()["n"]
        if count == 0:
            conn.executemany(
                "INSERT INTO settings (key, value) VALUES (?, ?);",
                [
                    ("capacity", str(config.PARKING_CAPACITY)),
                    ("timezone", config.TIMEZONE),
                    ("debounce_seconds", str(config.DEBOUNCE_SECONDS)),
                ],
            )
            conn.commit()
            logger.info("Default settings inserted.")
    finally:
        conn.close()


def initialize(db_path: Path | None = None) -> None:
    """Convenience: create schema and default settings in one call."""
    init_db(db_path)
    init_default_settings(db_path)