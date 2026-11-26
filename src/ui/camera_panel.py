"""Camera panel widget — live feed, detection overlay and clock controls."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from queue import Empty

from PIL import Image, ImageDraw, ImageTk

try:
    import cv2
except Exception:
    cv2 = None

from src import config
from src.camera.camera_stream import CameraStream
from src.ui.icons import get_icon
from src.ui.theme import make_button
from src.vision.pipeline import VisionUpdate, VisionWorker


class CameraPanel(tk.Frame):
    """One live camera panel with controls and an optional detected plate."""

    def __init__(
        self,
        parent: tk.Misc,
        title: str,
        stream: CameraStream,
        accent: str,
        on_capture,
        on_clock,
        clock_label: str,
        clock_color: str,
        camera_role: str,
        captures_dir=None,
    ) -> None:
        super().__init__(
            parent,
            bg=config.COLOR_CARD,
            highlightbackground=config.COLOR_BORDER,
            highlightthickness=1,
        )
        self.stream = stream
        self.on_capture = on_capture
        self.on_clock = on_clock
        self.worker = VisionWorker(stream, camera_role, captures_dir)
        self.current_observation: VisionUpdate | None = None
        self._photo = None
        self._poll_after_id = None
        self._test_mode = False
        self.start_button = None
        self.capture_button = None
        self._build(title, accent, clock_label, clock_color)

    def _build(self, title: str, accent: str, clock_label: str, clock_color: str) -> None:
        header = tk.Frame(self, bg=accent, height=42)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(
            header,
            text=title,
            image=get_icon("camera", 18, "white"),
            compound="left",
            fg="white",
            bg=accent,
            font=(config.FONT_FAMILY, 12, "bold"),
        ).pack(side="left", padx=14)
        live = tk.Label(
            header,
            text="● En direct",
            fg="#bbf7d0",
            bg=accent,
            font=(config.FONT_FAMILY, 9, "bold"),
        )
        live.pack(side="right", padx=14)

        self.video = tk.Label(
            self,
            text="Aucun flux caméra",
            fg=config.COLOR_TEXT_MUTED,
            bg="#0f172a",
            font=(config.FONT_FAMILY, 11),
        )
        self.video.pack(fill="both", expand=True, padx=10, pady=10)
        self.plate_overlay = tk.Label(
            self.video,
            text="",
            fg="white",
            bg="#15803d",
            font=(config.FONT_ARABIC, 11, "bold"),
            padx=10,
            pady=5,
        )

        controls = tk.Frame(self, bg=config.COLOR_CARD, height=56)
        controls.pack(fill="x", padx=10, pady=(0, 10))
        controls.pack_propagate(False)
        self._controls = controls
        # Six equal columns let one row hold 3/2/1 buttons without dead space.
        for column in range(6):
            controls.columnconfigure(column, weight=1, uniform="control")
        self._controls_signature = None
        if "Entrée" in title:
            self.start_button = make_button(
                controls, "Démarrer Caméra", self.start, icon="start",
                bg=config.COLOR_BLUE, font_size=9, padx=8,
            )
            self.capture_button = make_button(
                controls, "Capturer", self.on_capture, icon="capture",
                bg=config.COLOR_CARD_ALT, fg=config.COLOR_TEXT, hover=config.COLOR_BORDER,
                font_size=9, padx=8,
            )
        self.pause_button = make_button(
            controls, "Pause", self.toggle_play_pause, icon="pause",
            bg=config.COLOR_CARD_ALT, fg=config.COLOR_TEXT, hover=config.COLOR_BORDER,
            font_size=9, padx=8,
        )
        self.clock_button = make_button(
            controls, clock_label, self.on_clock,
            icon="entry" if "Entrée" in clock_label else "exit",
            bg=clock_color, font_size=9, padx=8,
        )
        controls.bind("<Configure>", self._reflow_controls)
        self._reflow_controls()

    def _control_buttons(self) -> list[tk.Button]:
        """Return the buttons visible in the current mode, left to right."""
        buttons: list[tk.Button] = []
        if self.start_button is not None:
            # Pause takes the start button's slot while a test video plays.
            buttons.append(self.pause_button if self._test_mode else self.start_button)
        elif self._test_mode:
            buttons.append(self.pause_button)
        if self.capture_button is not None:
            buttons.append(self.capture_button)
        buttons.append(self.clock_button)
        return buttons

    def _reflow_controls(self, _event=None, *, force: bool = False) -> None:
        """Keep the control row readable, wrapping the clock button when narrow."""
        controls = getattr(self, "_controls", None)
        if controls is None:
            return
        buttons = self._control_buttons()
        gap = 8
        needed = sum(button.winfo_reqwidth() for button in buttons) + gap * (len(buttons) - 1)
        width = controls.winfo_width()
        rows = [buttons]
        if width > 1 and needed > width and len(buttons) > 1:
            rows = [buttons[:-1], buttons[-1:]]
        signature = (tuple(id(button) for button in buttons), len(rows))
        if not force and signature == self._controls_signature:
            return
        self._controls_signature = signature
        for button in (self.start_button, self.capture_button, self.pause_button, self.clock_button):
            if button is not None:
                button.grid_forget()
        controls.configure(height=56 if len(rows) == 1 else 98)
        for row_index, row in enumerate(rows):
            span = 6 // len(row)
            for column_index, button in enumerate(row):
                button.grid(
                    row=row_index,
                    column=column_index * span,
                    columnspan=span,
                    sticky="ew",
                    padx=(0 if column_index == 0 else gap, 0),
                    pady=(0 if row_index == 0 else 6, 0),
                )

    def start(self) -> None:
        if not self.worker.start():
            try:
                update = self.worker.updates.get_nowait()
            except Empty:
                update = VisionUpdate(None, error="Aucun flux disponible")
            self.video.configure(text=update.error or "Aucun flux disponible", image="", compound="center")
        if self._poll_after_id is None:
            self._poll_frame()

    def _poll_frame(self) -> None:
        while True:
            try:
                self.current_observation = self.worker.updates.get_nowait()
            except Empty:
                break
        update = self.current_observation
        frame = update.frame if update is not None else None
        if frame is not None and cv2 is not None:
            original_height, original_width = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb)
            image = self._fit_image(image)
            if update and update.car_box:
                draw = ImageDraw.Draw(image)
                scale_x = image.width / original_width
                scale_y = image.height / original_height
                x, y, width, height = update.car_box
                bounds = (
                    int(x * scale_x),
                    int(y * scale_y),
                    int((x + width) * scale_x),
                    int((y + height) * scale_y),
                )
                draw.rectangle(bounds, outline="#22c55e", width=3)
            self._photo = ImageTk.PhotoImage(image)
            self.video.configure(image=self._photo, text="")
            if update and update.plate_display:
                self.plate_overlay.configure(text=f"Plaque détectée : {update.plate_display}")
                self.plate_overlay.place(relx=0.5, rely=0.95, anchor="s")
            else:
                self.plate_overlay.place_forget()
        elif update is not None and update.error:
            self.video.configure(text=update.error, image="", compound="center")
        elif self.stream.error:
            self.video.configure(text=self.stream.error, image="", compound="center")
        elif not self.stream._running:
            self._show_placeholder()
        self._poll_after_id = self.after(config.UI_POLL_MS, self._poll_frame)

    def _fit_image(self, image: Image.Image) -> Image.Image:
        width = max(240, self.video.winfo_width())
        height = max(180, self.video.winfo_height())
        image.thumbnail((width, height), Image.Resampling.LANCZOS)
        return image

    def _show_placeholder(self) -> None:
        self.video.configure(text="Démarrez la caméra pour afficher le flux.", image="", compound="center")

    def set_test_mode(self, enabled: bool) -> None:
        """Swap between the live start action and test-video playback control."""
        self._test_mode = enabled
        if enabled:
            self._update_pause_button()
        self._reflow_controls(force=True)

    def _update_pause_button(self) -> None:
        paused = self.stream.paused
        self.pause_button.configure(
            text="Reprendre" if paused else "Pause",
            image=get_icon("start" if paused else "pause", 16, config.COLOR_TEXT),
        )

    def toggle_play_pause(self) -> None:
        """Pause or resume the active test video."""
        if self.stream.paused:
            self.stream.resume()
        else:
            self.stream.pause()
        self._update_pause_button()

    def set_stream(
        self,
        stream: CameraStream,
        captures_dir: Path,
        test_mode: bool,
        auto_start: bool = True,
    ) -> None:
        """Replace the source and worker without blocking the Tk thread."""
        if self._poll_after_id is not None:
            self.after_cancel(self._poll_after_id)
            self._poll_after_id = None
        self.worker.stop()
        self.stream = stream
        self.worker = VisionWorker(stream, "entry" if self.start_button is not None else "exit", captures_dir)
        self.current_observation = None
        self._photo = None
        self.plate_overlay.place_forget()
        self.video.configure(text="Chargement du flux…", image="", compound="center")
        self.set_test_mode(test_mode)
        if auto_start:
            self.start()