"""Application sidebar — deep slate, collapsible groups, live status footer."""

from __future__ import annotations

import tkinter as tk
from datetime import datetime

from src import config
from src.ui.icons import get_icon
from src.ui.theme import make_button


class Sidebar(tk.Frame):
    """Dark navigation sidebar matching the redesigned layout."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, width=248, bg=config.COLOR_SIDEBAR)
        self.pack_propagate(False)
        self._build()

    def _build(self) -> None:
        brand = tk.Frame(self, bg=config.COLOR_SIDEBAR, height=84)
        brand.pack(fill="x")
        brand.pack_propagate(False)
        logo = tk.Label(brand, image=get_icon("parking", 30, "#ffffff"), bg=config.COLOR_BLUE, padx=8, pady=8)
        logo.place(x=18, y=22)
        tk.Label(
            brand,
            text="Parking Intelligent",
            fg="#ffffff",
            bg=config.COLOR_SIDEBAR,
            font=(config.FONT_FAMILY, 13, "bold"),
            anchor="w",
        ).place(x=64, y=24)
        tk.Label(
            brand,
            text="Smart Parking",
            fg=config.COLOR_SIDEBAR_TEXT,
            bg=config.COLOR_SIDEBAR,
            font=(config.FONT_FAMILY, 10),
            anchor="w",
        ).place(x=64, y=46)

        # Groups: (title, items) where each item is (icon, label).
        groups = [
            ("MAIN", [
                ("dashboard", "Tableau de bord"),
                ("cameras", "Caméras"),
                ("history", "Historique"),
                ("pointages", "Pointages"),
                ("reports", "Rapports"),
            ]),
            ("SYSTÈME", [
                ("settings", "Paramètres"),
                ("about", "À propos"),
            ]),
        ]
        for title, items in groups:
            tk.Label(
                self,
                text=title,
                fg="#64748b",
                bg=config.COLOR_SIDEBAR,
                font=(config.FONT_FAMILY, 8, "bold"),
                anchor="w",
            ).pack(fill="x", padx=26, pady=(18, 6))
            for icon_name, label in items:
                self._add_menu_item(icon_name, label)

        self._build_footer()

    def _add_menu_item(self, icon_name: str, label: str) -> None:
        active = label == "Pointages"
        row = tk.Frame(
            self,
            bg=config.COLOR_SIDEBAR_ACTIVE if active else config.COLOR_SIDEBAR,
            height=46,
        )
        row.pack(fill="x", padx=14, pady=1)
        row.pack_propagate(False)
        # Left accent bar for the active item.
        if active:
            tk.Frame(row, bg="#93c5fd", width=3).pack(side="left", fill="y")
        tk.Label(
            row,
            image=get_icon(icon_name, 19, "#ffffff" if active else config.COLOR_SIDEBAR_TEXT),
            bg=row["bg"],
        ).pack(side="left", padx=(14, 12))
        tk.Label(
            row,
            text=label,
            fg="#ffffff" if active else config.COLOR_SIDEBAR_TEXT,
            bg=row["bg"],
            font=(config.FONT_FAMILY, 11, "bold" if active else "normal"),
            anchor="w",
        ).pack(side="left", fill="x", expand=True)
        # Clicking a placeholder must not crash (AGENTS.md §3).
        for widget in (row, *row.winfo_children()):
            widget.bind("<Button-1>", lambda _event: None)

    def _build_footer(self) -> None:
        bottom = tk.Frame(self, bg=config.COLOR_SIDEBAR)
        bottom.pack(side="bottom", fill="x", padx=14, pady=14)

        status = tk.Frame(bottom, bg=config.COLOR_SIDEBAR_ALT, height=76)
        status.pack(fill="x")
        status.pack_propagate(False)
        tk.Label(status, image=get_icon("live", 13, "#22c55e"), bg=config.COLOR_SIDEBAR_ALT).place(x=14, y=14)
        tk.Label(
            status,
            text="En ligne",
            fg="#4ade80",
            bg=config.COLOR_SIDEBAR_ALT,
            font=(config.FONT_FAMILY, 11, "bold"),
        ).place(x=34, y=12)
        self.time_label = tk.Label(
            status,
            text="",
            fg="#94a3b8",
            bg=config.COLOR_SIDEBAR_ALT,
            font=(config.FONT_FAMILY, 9),
        )
        self.time_label.place(x=14, y=44)

        make_button(
            bottom,
            "Se déconnecter",
            lambda: None,
            icon="logout",
            bg=config.COLOR_RED,
            hover=config.COLOR_RED_DARK,
            font_size=11,
            pady=10,
        ).pack(fill="x", pady=(12, 0))
        self._update_time()

    def _update_time(self) -> None:
        now = datetime.now().strftime("%d/%m/%Y  %H:%M:%S")
        self.time_label.configure(text=now)
        self.after(1000, self._update_time)