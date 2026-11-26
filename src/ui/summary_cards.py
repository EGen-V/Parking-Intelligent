"""Parking summary cards — modern stat cards with deltas and a capacity bar."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from src import config
from src.ui.icons import get_icon
from src.ui.theme import configure_treeview_style, make_card, section_title


class SummaryCards(tk.Frame):
    """Right-side summary panel with three stat cards."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, bg=config.COLOR_BG)
        self.entries_label: tk.Label | None = None
        self.exits_label: tk.Label | None = None
        self.available_label: tk.Label | None = None
        self.progress: ttk.Progressbar | None = None
        self._build()

    def _build(self) -> None:
        card = make_card(self)
        card.pack(fill="both", expand=True)
        configure_treeview_style(self)

        header = tk.Frame(card, bg=config.COLOR_CARD, height=52)
        header.pack(fill="x", padx=16)
        header.pack_propagate(False)
        section_title(header, "Résumé du Parking", icon="reports").pack(side="left")

        self._add_stat(card, "vehicles", config.COLOR_GREEN, "Véhicules en Entrée", "entries")
        self._add_stat(card, "vehicles", config.COLOR_BLUE, "Véhicules en Sortie", "exits")
        self._add_available(card)

    def _add_stat(self, parent: tk.Misc, icon: str, color: str, label: str, kind: str) -> None:
        row = tk.Frame(parent, bg=config.COLOR_CARD)
        row.pack(fill="x", padx=16, pady=10)
        # Coloured glyph on the card surface (a same-colour square would hide it).
        tk.Label(row, image=get_icon(icon, 30, color), bg=config.COLOR_CARD).pack(
            side="left", padx=(2, 14)
        )
        text = tk.Frame(row, bg=config.COLOR_CARD)
        text.pack(side="left", fill="x", expand=True)
        tk.Label(
            text, text=label, fg=config.COLOR_TEXT_MUTED, bg=config.COLOR_CARD,
            font=(config.FONT_FAMILY, 10),
        ).pack(anchor="w")
        value = tk.Label(
            text, text="0", fg=config.COLOR_TEXT, bg=config.COLOR_CARD,
            font=(config.FONT_FAMILY, 22, "bold"),
        )
        value.pack(anchor="w")
        setattr(self, f"{kind}_label", value)
        # Delta pill (filled in update_summary).
        delta = tk.Label(
            row, text="+0", fg=config.COLOR_GREEN, bg=config.COLOR_GREEN_BG,
            font=(config.FONT_FAMILY, 9, "bold"), padx=8, pady=3,
        )
        delta.pack(side="right")
        setattr(self, f"{kind}_delta", delta)

    def _add_available(self, parent: tk.Misc) -> None:
        wrap = tk.Frame(parent, bg=config.COLOR_CARD_ALT)
        wrap.pack(fill="x", padx=16, pady=(8, 16), ipady=10)
        tk.Label(wrap, image=get_icon("available", 26, config.COLOR_ACCENT), bg=config.COLOR_CARD_ALT).pack(side="left", padx=12)
        text = tk.Frame(wrap, bg=config.COLOR_CARD_ALT)
        text.pack(side="left", fill="x", expand=True, padx=(0, 12))
        tk.Label(
            text, text="Places Disponibles", fg=config.COLOR_TEXT_MUTED, bg=config.COLOR_CARD_ALT,
            font=(config.FONT_FAMILY, 10),
        ).pack(anchor="w")
        self.available_label = tk.Label(
            text, text="30 / 30", fg=config.COLOR_TEXT, bg=config.COLOR_CARD_ALT,
            font=(config.FONT_FAMILY, 20, "bold"),
        )
        self.available_label.pack(anchor="w")
        self.progress = ttk.Progressbar(text, maximum=30, value=30)
        self.progress.pack(fill="x", pady=(6, 0))

    def update_summary(self, summary: dict) -> None:
        self.entries_label.configure(text=str(summary["entries_today"]))
        self.exits_label.configure(text=str(summary["exits_today"]))
        self.available_label.configure(text=f"{summary['available']} / {summary['capacity']}")
        self.progress.configure(value=summary["available"], maximum=summary["capacity"])
        self.entries_delta.configure(text=f"+{summary['entries_today']}")
        self.exits_delta.configure(text=f"+{summary['exits_today']}")