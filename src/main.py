"""Application entry point."""

from __future__ import annotations

import logging

from src import config
from src.ui.app import ParkingApp


def main() -> None:
    logging.basicConfig(level=config.LOG_LEVEL)
    app = ParkingApp()
    app.mainloop()


if __name__ == "__main__":
    main()
