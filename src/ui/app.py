"""Main Tkinter application — modern card-based layout."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

from src import config
from src.camera.camera_stream import CameraStream, list_test_videos
from src.services.parking_service import ParkingService, ServiceError
from src.ui.camera_panel import CameraPanel
from src.ui.history_table import HistoryTable
from src.ui.icons import get_icon
from src.ui.sidebar import Sidebar
from src.ui.summary_cards import SummaryCards
from src.ui.theme import make_button


class ParkingApp(tk.Tk):
    """Parking Intelligent main window."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Parking Intelligent")
        self.geometry("1560x920")
        self.minsize(1360, 760)
        self.configure(bg=config.COLOR_BG)
        self.service = ParkingService()
        self.test_mode_var = tk.BooleanVar(self, value=False)
        self.is_test_mode = False
        self.test_videos: list[Path] = []

        self._build()
        self.refresh()

    def _build(self) -> None:
        self.sidebar = Sidebar(self)
        self.sidebar.pack(side="left", fill="y")

        shell = tk.Frame(self, bg=config.COLOR_BG)
        shell.pack(side="left", fill="both", expand=True)

        self._build_header(shell)

        content = tk.Frame(shell, bg=config.COLOR_BG)
        content.pack(fill="both", expand=True, padx=16, pady=16)
        self.content = content

        top = tk.Frame(content, bg=config.COLOR_BG)
        top.pack(fill="x")
        # Both camera panels share one uniform width; the summary keeps a minimum.
        top.columnconfigure(0, weight=3, uniform="cameras")
        top.columnconfigure(1, weight=3, uniform="cameras")
        top.columnconfigure(2, weight=2, minsize=280)

        entry_source = config.SAMPLE_ENTRY_SOURCE or config.CAMERA_ENTRY_INDEX
        exit_source = config.SAMPLE_EXIT_SOURCE or config.CAMERA_EXIT_INDEX
        self.entry_panel = CameraPanel(
            top, "Caméra Entrée", CameraStream(entry_source), config.COLOR_BLUE,
            self.capture_entry, self.pointer_entry, "Pointer Entrée",
            config.COLOR_GREEN, "entry", config.CAPTURES_DIR,
        )
        self.entry_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        self.exit_panel = CameraPanel(
            top, "Caméra Sortie", CameraStream(exit_source), config.COLOR_BLUE,
            lambda: None, self.pointer_exit, "Pointer Sortie",
            config.COLOR_RED, "exit", config.CAPTURES_DIR,
        )
        self.exit_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=(0, 10))
        self.summary = SummaryCards(top)
        self.summary.grid(row=0, column=2, sticky="nsew", pady=(0, 10))
        top.rowconfigure(0, weight=1)

        self.history = HistoryTable(content)
        self.history.pack(fill="both", expand=True, pady=(6, 0))
        self.history.search_var.trace_add("write", lambda *_: self.refresh_history())
        self.history.bind("<<HistoryRefresh>>", lambda _event: self.refresh_history())
        self.history.bind("<<ViewPointage>>", self.show_record_detail)
        self.protocol("WM_DELETE_WINDOW", self.close)

    def _build_header(self, shell: tk.Frame) -> None:
        header = tk.Frame(shell, bg=config.COLOR_HEADER, height=68)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(
            header,
            text="Monitoring / Gestion du Parking",
            image=get_icon("parking", 26, config.COLOR_BLUE),
            compound="left",
            fg=config.COLOR_TEXT,
            bg=config.COLOR_HEADER,
            font=(config.FONT_FAMILY, 17, "bold"),
        ).pack(side="left", padx=20)

        right = tk.Frame(header, bg=config.COLOR_HEADER)
        right.pack(side="right", padx=20)
        tk.Label(
            right, text="Genio", fg=config.COLOR_BLUE, bg=config.COLOR_HEADER,
            font=(config.FONT_FAMILY, 12, "bold"),
        ).pack(side="right", padx=(0, 8))
        notif = tk.Frame(right, bg=config.COLOR_HEADER)
        notif.pack(side="right", padx=10)
        tk.Label(notif, image=get_icon("notification", 20, config.COLOR_TEXT), bg=config.COLOR_HEADER).pack(side="left")
        tk.Label(
            notif, text="2", fg="white", bg=config.COLOR_RED,
            font=(config.FONT_FAMILY, 8, "bold"), width=2,
        ).pack(side="left", padx=(2, 0), pady=(0, 10))
        tk.Label(
            right, text="Admin", image=get_icon("user", 20, config.COLOR_TEXT),
            compound="left", fg=config.COLOR_TEXT, bg=config.COLOR_HEADER,
            font=(config.FONT_FAMILY, 11, "bold"),
        ).pack(side="right", padx=(10, 4))
        tk.Label(right, image=get_icon("dropdown", 14, config.COLOR_TEXT), bg=config.COLOR_HEADER).pack(side="right")

        self.test_badge = tk.Label(
            header, text="MODE TEST", fg="white", bg=config.COLOR_RED,
            font=(config.FONT_FAMILY, 9, "bold"), padx=8, pady=5,
        )
        tk.Checkbutton(
            header, text="Mode Test", variable=self.test_mode_var,
            command=self._toggle_test_mode, fg=config.COLOR_TEXT, bg=config.COLOR_HEADER,
            activebackground=config.COLOR_HEADER, selectcolor=config.COLOR_HEADER,
            font=(config.FONT_FAMILY, 10, "bold"), cursor="hand2",
        ).pack(side="right", padx=14)

        self.test_toolbar = tk.Frame(shell, bg=config.COLOR_CARD_ALT, height=50)
        self.test_toolbar.pack_propagate(False)
        tk.Label(
            self.test_toolbar, text="Vidéo Entrée", bg=config.COLOR_CARD_ALT,
            fg=config.COLOR_TEXT, font=(config.FONT_FAMILY, 9, "bold"),
        ).pack(side="left", padx=(14, 4))
        self.entry_video_var = tk.StringVar()
        self.entry_video_combo = ttk.Combobox(self.test_toolbar, textvariable=self.entry_video_var, width=22, state="readonly")
        self.entry_video_combo.pack(side="left", padx=4)
        self.entry_video_combo.bind("<<ComboboxSelected>>", lambda _event: self._change_test_video("entry"))
        tk.Label(
            self.test_toolbar, text="Vidéo Sortie", bg=config.COLOR_CARD_ALT,
            fg=config.COLOR_TEXT, font=(config.FONT_FAMILY, 9, "bold"),
        ).pack(side="left", padx=(14, 4))
        self.exit_video_var = tk.StringVar()
        self.exit_video_combo = ttk.Combobox(self.test_toolbar, textvariable=self.exit_video_var, width=22, state="readonly")
        self.exit_video_combo.pack(side="left", padx=4)
        self.exit_video_combo.bind("<<ComboboxSelected>>", lambda _event: self._change_test_video("exit"))
        make_button(
            self.test_toolbar, "Réinitialiser les données de test", self.reset_test_data,
            bg=config.COLOR_RED, hover=config.COLOR_RED_DARK, font_size=9,
        ).pack(side="right", padx=14)

    def capture_entry(self) -> None:
        observation = self.entry_panel.current_observation
        if observation is None or not observation.car_image or not observation.plate_image:
            messagebox.showwarning(
                "Capture indisponible",
                "Aucun véhicule stable à capturer pour le moment.",
                parent=self,
            )
            return
        messagebox.showinfo(
            "Capture enregistrée",
            f"Véhicule : {observation.car_image}\nPlaque : {observation.plate_image}",
            parent=self,
        )

    def pointer_entry(self) -> None:
        observation = self.entry_panel.current_observation
        initial_plate = observation.plate_display if observation else ""
        low_confidence = (
            observation is not None
            and initial_plate is not None
            and observation.confidence < config.OCR_CONFIDENCE_THRESHOLD
        )
        plate = simpledialog.askstring(
            "Confirmer ou corriger la plaque" if low_confidence else "Pointer Entrée",
            "Lecture faible : vérifiez ou corrigez l'immatriculation :" if low_confidence else "Immatriculation :",
            initialvalue=initial_plate or "",
            parent=self,
        )
        if not plate:
            return
        try:
            self.service.record_entry(
                plate,
                entry_image=observation.car_image if observation else None,
                plate_image=observation.plate_image if observation else None,
                confidence=observation.confidence if observation else 0.0,
            )
        except (ServiceError, ValueError) as exc:
            messagebox.showerror("Entrée refusée", str(exc))
            return
        messagebox.showinfo("Entrée enregistrée", f"Entrée enregistrée pour {plate}.")
        self.refresh()

    def pointer_exit(self) -> None:
        observation = self.exit_panel.current_observation
        initial_plate = observation.plate_display if observation else ""
        low_confidence = (
            observation is not None
            and initial_plate is not None
            and observation.confidence < config.OCR_CONFIDENCE_THRESHOLD
        )
        plate = simpledialog.askstring(
            "Confirmer ou corriger la plaque" if low_confidence else "Pointer Sortie",
            "Lecture faible : vérifiez ou corrigez l'immatriculation :" if low_confidence else "Immatriculation :",
            initialvalue=initial_plate or "",
            parent=self,
        )
        if not plate:
            return
        try:
            self.service.record_exit(
                plate,
                exit_image=observation.car_image if observation else None,
                plate_image=observation.plate_image if observation else None,
            )
        except (ServiceError, ValueError) as exc:
            messagebox.showerror("Sortie refusée", str(exc))
            return
        messagebox.showinfo("Sortie enregistrée", f"Sortie enregistrée pour {plate}.")
        self.refresh()

    def refresh_history(self) -> None:
        records = self.service.get_records(
            search=self.history.search_var.get(),
            date=self.history.date_filter,
        )
        self.history.update_records(records)

    def refresh(self) -> None:
        self.refresh_history()
        self.summary.update_summary(self.service.get_summary())

    def show_record_detail(self, _event=None) -> None:
        record_id = self.history.view_record_id
        record = next((row for row in self.service.get_records() if row["id"] == record_id), None)
        if record is None:
            return
        details = [
            f"Immatriculation : {record['plate_display']}",
            f"Entrée : {record['entry_time']}",
            f"Sortie : {record['exit_time'] or '—'}",
            f"Image du véhicule : {record['entry_image'] or 'Non disponible'}",
            f"Plaque capturée : {record['plate_image'] or 'Non disponible'}",
            f"Véhicule à la sortie : {record['exit_image'] or 'Non disponible'}",
            f"Plaque à la sortie : {record['exit_plate_image'] or 'Non disponible'}",
        ]
        messagebox.showinfo("Détail du pointage", "\n".join(details), parent=self)

    def _toggle_test_mode(self) -> None:
        if self.test_mode_var.get():
            if not self._enable_test_mode():
                self.test_mode_var.set(False)
        elif self.is_test_mode:
            self._disable_test_mode()

    def _enable_test_mode(self) -> bool:
        videos = list_test_videos(config.TEST_VIDEO_DIR)
        if not videos:
            messagebox.showerror(
                "Mode Test indisponible",
                f"Aucune vidéo compatible dans : {config.TEST_VIDEO_DIR}",
                parent=self,
            )
            return False

        self.test_videos = videos
        names = [path.name for path in videos]
        self.entry_video_combo.configure(values=names, state="readonly" if len(names) > 1 else "disabled")
        self.exit_video_combo.configure(values=names, state="readonly" if len(names) > 1 else "disabled")
        self.entry_video_var.set(names[0])
        self.exit_video_var.set(names[1] if len(names) > 1 else names[0])

        self.service = ParkingService(db_path=config.TEST_DB_PATH)
        self.is_test_mode = True
        self.test_toolbar.pack(fill="x", before=self.content)
        self.test_badge.pack(side="right", padx=8)
        self.entry_panel.set_stream(CameraStream(str(videos[0])), config.TEST_CAPTURES_DIR, test_mode=True)
        exit_video = videos[1] if len(videos) > 1 else videos[0]
        self.exit_panel.set_stream(CameraStream(str(exit_video)), config.TEST_CAPTURES_DIR, test_mode=True)
        self.refresh()
        return True

    def _disable_test_mode(self) -> None:
        self.is_test_mode = False
        self.test_toolbar.pack_forget()
        self.test_badge.pack_forget()
        self.service = ParkingService(db_path=config.DB_PATH)
        entry_source = config.SAMPLE_ENTRY_SOURCE or config.CAMERA_ENTRY_INDEX
        exit_source = config.SAMPLE_EXIT_SOURCE or config.CAMERA_EXIT_INDEX
        self.entry_panel.set_stream(CameraStream(entry_source), config.CAPTURES_DIR, test_mode=False)
        self.exit_panel.set_stream(CameraStream(exit_source), config.CAPTURES_DIR, test_mode=False)
        self.refresh()

    def _change_test_video(self, camera_role: str) -> None:
        if not self.is_test_mode:
            return
        variable = self.entry_video_var if camera_role == "entry" else self.exit_video_var
        video = next((path for path in self.test_videos if path.name == variable.get()), None)
        if video is None:
            return
        panel = self.entry_panel if camera_role == "entry" else self.exit_panel
        panel.set_stream(CameraStream(str(video)), config.TEST_CAPTURES_DIR, test_mode=True)

    def reset_test_data(self) -> None:
        if not self.is_test_mode:
            return
        confirmed = messagebox.askyesno(
            "Réinitialiser les données de test",
            "Supprimer tous les pointages et les captures du mode test ?",
            parent=self,
        )
        if not confirmed:
            return
        try:
            self.service.reset_test_data()
        except (OSError, ServiceError) as exc:
            messagebox.showerror("Réinitialisation impossible", str(exc), parent=self)
            return
        self.refresh()

    def close(self) -> None:
        self.entry_panel.worker.stop()
        self.exit_panel.worker.stop()
        self.destroy()