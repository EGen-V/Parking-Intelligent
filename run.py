"""Parking Intelligent — root launcher.

Run from source with ``python run.py``. The same file is the PyInstaller entry
point, so the frozen executable follows exactly the same startup path.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_project_on_path() -> None:
    """Make ``import src`` work when the script is started from another folder."""
    if getattr(sys, "frozen", False):
        return
    project_root = Path(__file__).resolve().parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


def main() -> None:
    _ensure_project_on_path()
    from src.main import main as run_application

    run_application()


if __name__ == "__main__":
    main()
