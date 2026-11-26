"""Shared Tkinter styling helpers for a consistent, modern look.

Tkinter has no native rounded corners or shadows, so the "modern" feel comes
from a disciplined palette, generous padding, flat surfaces and a single accent
color. These helpers centralise that styling so every widget stays consistent.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from src import config
from src.ui.icons import get_icon


def make_button(
    parent: tk.Misc,
    text: str,
    command,
    *,
    icon: str | None = None,
    bg: str = config.COLOR_BLUE,
    fg: str = "#ffffff",
    hover: str | None = None,
    font_size: int = 10,
    padx: int = 12,
    pady: int = 8,
) -> tk.Button:
    """Create a flat, hand-cursor button with optional icon and hover color."""
    hover = hover or _darken(bg)
    button = tk.Button(
        parent,
        text=text,
        command=command,
        image=get_icon(icon, 16, fg) if icon else None,
        compound="left" if icon else "none",
        bg=bg,
        fg=fg,
        activebackground=hover,
        activeforeground=fg,
        relief="flat",
        bd=0,
        highlightthickness=0,
        font=(config.FONT_FAMILY, font_size, "bold"),
        cursor="hand2",
        padx=padx,
        pady=pady,
    )
    return button


def make_card(parent: tk.Misc, *, bg: str = config.COLOR_CARD) -> tk.Frame:
    """A bordered white surface used as a card/panel container."""
    return tk.Frame(parent, bg=bg, highlightbackground=config.COLOR_BORDER, highlightthickness=1)


def section_title(parent: tk.Misc, text: str, *, icon: str | None = None, color: str = config.COLOR_TEXT) -> tk.Frame:
    """A title row with an optional accent icon; returns the row frame."""
    row = tk.Frame(parent, bg=parent["bg"])
    tk.Label(
        row,
        text=text,
        image=get_icon(icon, 20, config.COLOR_BLUE) if icon else None,
        compound="left",
        fg=color,
        bg=parent["bg"],
        font=(config.FONT_FAMILY, 13, "bold"),
    ).pack(side="left")
    return row


def make_badge(parent: tk.Misc, text: str, *, fg: str, bg: str) -> tk.Label:
    """A small pill-style status badge."""
    return tk.Label(
        parent,
        text=text,
        fg=fg,
        bg=bg,
        font=(config.FONT_FAMILY, 9, "bold"),
        padx=10,
        pady=3,
    )


def _darken(hex_color: str, factor: float = 0.85) -> str:
    """Return a darker shade of a #rrggbb color for hover states."""
    value = hex_color.lstrip("#")
    if len(value) != 6:
        return hex_color
    r, g, b = (int(value[i : i + 2], 16) for i in (0, 2, 4))
    r, g, b = (max(0, int(channel * factor)) for channel in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def configure_treeview_style(root: tk.Misc) -> ttk.Style:
    """Configure a flat, modern ttk style for Treeview and Progressbar."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure(
        "Treeview",
        background=config.COLOR_CARD,
        fieldbackground=config.COLOR_CARD,
        foreground=config.COLOR_TEXT,
        rowheight=34,
        borderwidth=0,
        font=(config.FONT_FAMILY, 10),
    )
    style.configure(
        "Treeview.Heading",
        background=config.COLOR_CARD_ALT,
        foreground=config.COLOR_TEXT_MUTED,
        font=(config.FONT_FAMILY, 10, "bold"),
        borderwidth=0,
        relief="flat",
    )
    style.map("Treeview.Heading", background=[("active", config.COLOR_BORDER)])
    style.configure(
        "Horizontal.TProgressbar",
        troughcolor=config.COLOR_BORDER,
        background=config.COLOR_ACCENT,
        bordercolor=config.COLOR_BORDER,
        lightcolor=config.COLOR_ACCENT,
        darkcolor=config.COLOR_ACCENT,
        borderwidth=0,
        thickness=8,
    )
    return style