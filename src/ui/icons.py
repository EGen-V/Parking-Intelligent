"""Lucide icon access for the Tkinter interface."""

from __future__ import annotations

import tkinter as tk

from tkinter_icons import LucideIcon

_ICON_NAMES = {
    "parking": "square-parking",
    "dashboard": "layout-dashboard",
    "cameras": "video",
    "history": "history",
    "pointages": "clipboard-list",
    "reports": "chart-no-axes-column-increasing",
    "settings": "settings",
    "about": "info",
    "logout": "log-out",
    "live": "circle",
    "camera": "video",
    "start": "play",
    "pause": "pause",
    "capture": "camera",
    "entry": "log-in",
    "exit": "log-out",
    "vehicles": "car-front",
    "available": "square-parking",
    "search": "search",
    "calendar": "calendar-days",
    "notification": "bell",
    "user": "user-round",
    "dropdown": "chevron-down",
    "list": "list",
    "view": "eye",
}


# PhotoImage objects belong to one Tk interpreter, so the cache must be reset
# when the default root changes (for example when the app is rebuilt in tests).
_ICON_CACHE: dict[tuple[str, int, str], tk.PhotoImage] = {}
_ICON_CACHE_ROOT: tk.Misc | None = None


def clear_icon_cache() -> None:
    """Drop cached images, e.g. after their Tk interpreter was destroyed."""
    _ICON_CACHE.clear()


def get_icon(name: str, size: int, color: str) -> tk.PhotoImage:
    """Return a cached Tk image for a named Lucide icon."""
    global _ICON_CACHE_ROOT
    root = getattr(tk, "_default_root", None)
    if root is not _ICON_CACHE_ROOT:
        _ICON_CACHE.clear()
        _ICON_CACHE_ROOT = root
    key = (name, size, color)
    image = _ICON_CACHE.get(key)
    if image is not None:
        return image
    try:
        glyph = _ICON_NAMES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown UI icon: {name}") from exc
    image = LucideIcon(glyph, size=size, color=color).image
    _ICON_CACHE[key] = image
    return image
