"""Parking history table — searchable, date-filterable, with status badges."""

from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import simpledialog, ttk

from src import config
from src.services.parking_service import format_duration
from src.ui.icons import get_icon
from src.ui.theme import configure_treeview_style, make_button, make_card, section_title


class HistoryTable(tk.Frame):
    """Searchable, filterable pointage history with per-row view buttons."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, bg=config.COLOR_BG)
        self.records: list[dict] = []
        self.search_var = tk.StringVar()
        self.date_filter = ""
        self.view_record_id: int | None = None
        self._action_buttons: dict[str, tk.Button] = {}
        self._build()

    def _build(self) -> None:
        card = make_card(self)
        card.pack(fill="both", expand=True)
        configure_treeview_style(self)

        toolbar = tk.Frame(card, bg=config.COLOR_CARD, height=60)
        toolbar.pack(fill="x", padx=16)
        toolbar.pack_propagate(False)
        section_title(toolbar, "Historique des Pointages", icon="list").pack(side="left")

        make_button(
            toolbar, "Filtrer par date", self.choose_date, icon="calendar",
            bg=config.COLOR_CARD_ALT, fg=config.COLOR_TEXT, hover=config.COLOR_BORDER,
            font_size=9,
        ).pack(side="right", padx=(12, 0))

        search = tk.Frame(toolbar, bg=config.COLOR_CARD)
        search.pack(side="right", padx=(8, 0))
        entry_wrap = tk.Frame(
            search,
            bg=config.COLOR_CARD,
            highlightbackground=config.COLOR_BORDER,
            highlightthickness=1,
        )
        entry_wrap.pack(side="left")
        tk.Label(
            entry_wrap, image=get_icon("search", 16, config.COLOR_TEXT_MUTED),
            bg=config.COLOR_CARD,
        ).pack(side="left", padx=(6, 0))
        self._search_entry = tk.Entry(
            entry_wrap, textvariable=self.search_var, width=24, relief="flat", bd=0,
            highlightthickness=0, bg=config.COLOR_CARD,
            font=(config.FONT_FAMILY, 10),
        )
        self._search_entry.pack(side="left", ipady=6, padx=(4, 6))
        self._search_placeholder = tk.Label(
            entry_wrap,
            text="Rechercher une plaque…",
            fg=config.COLOR_TEXT_MUTED,
            bg=config.COLOR_CARD,
            font=(config.FONT_FAMILY, 10),
        )
        self._search_placeholder.place(x=30, rely=0.5, anchor="w")
        self._search_placeholder.bind("<Button-1>", lambda _event: self._search_entry.focus_set())
        self._search_entry.bind("<FocusIn>", lambda _event: self._sync_search_placeholder())
        self._search_entry.bind("<FocusOut>", lambda _event: self._sync_search_placeholder())
        self.search_var.trace_add("write", lambda *_: self._sync_search_placeholder())

        table_frame = tk.Frame(card, bg=config.COLOR_CARD)
        table_frame.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        columns = ("number", "date", "plate", "entry", "exit", "duration", "status", "actions")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=7)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self._scroll)
        self.tree.configure(yscrollcommand=scrollbar.set)
        headings = ["#", "Date", "Immatriculations", "Entrée", "Sortie", "Durée", "Statut", "Actions"]
        # Only the plate column grows with the window; the rest keep readable widths.
        widths = [48, 110, 230, 100, 100, 100, 110, 84]
        stretch = [False, False, True, False, False, False, False, False]
        anchors = ["center", "center", "w", "center", "center", "center", "center", "center"]
        for column, heading, width, can_stretch, anchor in zip(
            columns, headings, widths, stretch, anchors
        ):
            self.tree.heading(column, text=heading)
            self.tree.column(
                column, width=width, minwidth=width, anchor=anchor, stretch=can_stretch
            )
        self.tree.tag_configure("done", background=config.COLOR_GREEN_BG)
        self.tree.tag_configure("open", background=config.COLOR_YELLOW_BG)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._empty_label = tk.Label(
            table_frame,
            text="Aucun pointage enregistré",
            fg=config.COLOR_TEXT_MUTED,
            bg=config.COLOR_CARD,
            font=(config.FONT_FAMILY, 11),
        )
        self.tree.bind("<Configure>", self._position_action_buttons)
        self.tree.bind("<MouseWheel>", self._position_action_buttons)

    def _sync_search_placeholder(self) -> None:
        """Show the hint only while the search field is empty and unfocused."""
        has_text = bool(self.search_var.get())
        focused = self.focus_get() is self._search_entry
        if has_text or focused:
            self._search_placeholder.place_forget()
        else:
            self._search_placeholder.place(x=30, rely=0.5, anchor="w")

    def update_records(self, records: list[dict]) -> None:
        self.records = records
        for button in self._action_buttons.values():
            button.destroy()
        self._action_buttons.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
        search = self.search_var.get().strip().lower()
        inserted = 0
        for number, record in enumerate(records, start=1):
            plate = str(record["plate_display"])
            if search and search not in plate.lower() and search not in str(record["plate_key"]).lower():
                continue
            inserted += 1
            entry = self._format_datetime(record["entry_time"])
            exit_value = self._format_datetime(record["exit_time"]) if record["exit_time"] else "—"
            duration = format_duration(record["duration_seconds"]) if record["duration_seconds"] is not None else ""
            status = "Terminé" if record["status"] == "TERMINE" else "En cours"
            tag = "done" if record["status"] == "TERMINE" else "open"
            self.tree.insert(
                "",
                "end",
                iid=str(record["id"]),
                values=(number, entry["date"], plate, entry["time"],
                        exit_value["time"] if isinstance(exit_value, dict) else exit_value,
                        duration, status, ""),
                tags=(tag,),
            )
            button = tk.Button(
                self.tree,
                image=get_icon("view", 16, "white"),
                command=lambda current_id=int(record["id"]): self._view_record(current_id),
                bg=config.COLOR_BLUE,
                activebackground=config.COLOR_BLUE_DARK,
                relief="flat",
                bd=0,
                highlightthickness=0,
                cursor="hand2",
            )
            self._action_buttons[str(record["id"])] = button
        if inserted:
            self._empty_label.place_forget()
        else:
            self._empty_label.configure(
                text="Aucun résultat pour cette recherche"
                if search
                else "Aucun pointage enregistré"
            )
            self._empty_label.place(relx=0.5, rely=0.55, anchor="center")
            self._empty_label.lift()
        self.after_idle(self._position_action_buttons)

    def _view_record(self, record_id: int) -> None:
        self.view_record_id = record_id
        self.event_generate("<<ViewPointage>>")

    def _scroll(self, *args) -> None:
        self.tree.yview(*args)
        self._position_action_buttons()

    def _position_action_buttons(self, _event=None) -> None:
        for record_id, button in self._action_buttons.items():
            bounds = self.tree.bbox(record_id, "actions")
            if not bounds:
                button.place_forget()
                continue
            x, y, width, height = bounds
            button.place(x=x + (width - 26) // 2, y=y + (height - 22) // 2, width=26, height=22)

    def choose_date(self) -> None:
        value = simpledialog.askstring("Filtrer par date", "Date (JJ/MM/AAAA) :", parent=self)
        if value is None:
            return
        value = value.strip()
        if not value:
            self.date_filter = ""
        else:
            try:
                parsed = datetime.strptime(value, "%d/%m/%Y")
            except ValueError:
                return
            self.date_filter = parsed.strftime("%Y-%m-%d")
        self.event_generate("<<HistoryRefresh>>")

    @staticmethod
    def _format_datetime(value: str) -> dict:
        try:
            dt = datetime.fromisoformat(str(value))
            return {"date": dt.strftime("%d/%m/%Y"), "time": dt.strftime("%H:%M:%S")}
        except Exception:
            return {"date": str(value), "time": "—"}