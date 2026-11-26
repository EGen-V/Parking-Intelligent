"""Smoke test: the redesigned UI builds, refreshes and tears down cleanly.

Tk needs a display; skip when none is available (CI / headless).
"""

from __future__ import annotations

import tkinter as tk

import pytest

from src.ui.app import ParkingApp


@pytest.fixture(scope="module")
def app():
    """One Tk root for the module: Tk is unreliable when recreated repeatedly."""
    try:
        instance = ParkingApp()
    except tk.TclError as exc:
        pytest.skip(f"No display available for Tkinter: {exc}")
    # Realise the window so widget mapping/geometry can be asserted.
    instance.update_idletasks()
    instance.update()
    try:
        yield instance
    finally:
        instance.destroy()


def test_ui_builds_and_refreshes(app: ParkingApp) -> None:
    app.update_idletasks()
    app.refresh()
    # Summary labels reflect the service state.
    assert app.summary.available_label is not None
    assert app.history.tree is not None
    # Sidebar and both camera panels exist.
    assert app.sidebar.winfo_exists()
    assert app.entry_panel.winfo_exists()
    assert app.exit_panel.winfo_exists()


def test_camera_controls_fit_inside_the_panel_at_minimum_size(app: ParkingApp) -> None:
    """Regression: the third button used to be clipped by the panel edge."""
    app.geometry("1360x760")
    app.update_idletasks()
    app.update()
    controls = app.entry_panel._controls
    buttons = app.entry_panel._control_buttons()
    assert len(buttons) == 3
    assert controls.winfo_width() > 300
    for button in buttons:
        assert button.winfo_ismapped()
        assert button.winfo_x() + button.winfo_width() <= controls.winfo_width()


def test_history_shows_an_empty_state_and_hides_it_with_rows(app: ParkingApp) -> None:
    history = app.history
    history.update_records([])
    app.update_idletasks()
    assert history._empty_label.winfo_ismapped()
    record = {
        "id": 1,
        "plate_display": "123 تونس 4567",
        "plate_key": "123TN4567",
        "entry_time": "2026-11-17T08:15:25",
        "exit_time": None,
        "duration_seconds": None,
        "status": "EN_COURS",
    }
    history.update_records([record])
    app.update_idletasks()
    assert not history._empty_label.winfo_ismapped()


def test_search_placeholder_hides_while_typing(app: ParkingApp) -> None:
    app.focus_set()
    history = app.history
    history.search_var.set("")
    app.update_idletasks()
    assert history._search_placeholder.winfo_ismapped()
    history.search_var.set("123")
    app.update_idletasks()
    assert not history._search_placeholder.winfo_ismapped()
    history.search_var.set("")
    app.update_idletasks()
    assert history._search_placeholder.winfo_ismapped()