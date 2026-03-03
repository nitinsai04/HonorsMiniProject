"""
Gesture Presentation Launcher
Dark-themed tkinter GUI for slide selection, settings, and launch.

Run:  python presentation_app/launcher.py
"""

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox

# Allow importing engine from the same package regardless of cwd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from presentation_app.engine import run_presentation

# ── Catppuccin Mocha palette ─────────────────────────────────────────────────
BG      = "#1e1e2e"
SURFACE = "#313244"
OVERLAY = "#45475a"
TEXT    = "#cdd6f4"
SUBTEXT = "#a6adc8"
MUTED   = "#6c7086"
BLUE    = "#89b4fa"
SKY     = "#74c7ec"
GREEN   = "#a6e3a1"
RED     = "#f38ba8"
PEACH   = "#fab387"
YELLOW  = "#f9e2af"

IMG_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff"}


class PresentationLauncher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Gesture Presentation")
        self.root.geometry("740x620")
        self.root.configure(bg=BG)
        self.root.resizable(True, True)
        self.root.minsize(640, 540)

        self.image_paths: list[str] = []

        self._build_header()
        self._build_body()
        self._build_footer()

    # ── Layout sections ───────────────────────────────────────────────────────

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=SURFACE, pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Gesture-Controlled Presentation",
                 font=("Helvetica", 17, "bold"),
                 bg=SURFACE, fg=TEXT).pack()
        tk.Label(hdr, text="Pick your slides · configure · launch",
                 font=("Helvetica", 10),
                 bg=SURFACE, fg=MUTED).pack()

    def _build_body(self):
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=18, pady=12)

        self._build_slide_panel(body)
        self._build_settings_panel(body)

    def _build_slide_panel(self, parent):
        left = tk.Frame(parent, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        tk.Label(left, text="Slides", font=("Helvetica", 12, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w")

        # Listbox
        box_frame = tk.Frame(left, bg=SURFACE, relief="flat")
        box_frame.pack(fill="both", expand=True, pady=6)

        sb = tk.Scrollbar(box_frame, bg=OVERLAY, troughcolor=SURFACE,
                          relief="flat", bd=0)
        sb.pack(side="right", fill="y")

        self.listbox = tk.Listbox(
            box_frame,
            yscrollcommand=sb.set,
            bg=SURFACE, fg=TEXT,
            selectbackground=BLUE, selectforeground=BG,
            font=("Helvetica", 10), relief="flat",
            activestyle="none", borderwidth=0, highlightthickness=0,
        )
        self.listbox.pack(fill="both", expand=True, padx=6, pady=6)
        sb.config(command=self.listbox.yview)

        # Buttons row 1
        r1 = tk.Frame(left, bg=BG)
        r1.pack(fill="x", pady=(2, 1))
        self._btn(r1, "Add Files",   self._add_files,   BLUE).pack(side="left", padx=2)
        self._btn(r1, "Add Folder",  self._add_folder,  SKY).pack(side="left", padx=2)
        self._btn(r1, "Remove",      self._remove,      RED).pack(side="left", padx=2)

        # Buttons row 2
        r2 = tk.Frame(left, bg=BG)
        r2.pack(fill="x", pady=(1, 2))
        self._btn(r2, "Move Up",     self._move_up,     GREEN).pack(side="left", padx=2)
        self._btn(r2, "Move Down",   self._move_down,   GREEN).pack(side="left", padx=2)
        self._btn(r2, "Clear All",   self._clear,       PEACH).pack(side="left", padx=2)

    def _build_settings_panel(self, parent):
        right = tk.Frame(parent, bg=BG)
        right.pack(side="right", fill="y", padx=(10, 0))

        tk.Label(right, text="Settings", font=("Helvetica", 12, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w")

        self._spotlight_radius_var  = self._slider(right, "Spotlight Radius",   50,  400, 150)
        self._dim_opacity_var       = self._slider(right, "Dim Opacity",          30,   95,  70)
        self._gesture_threshold_var = self._slider(right, "Gesture Threshold",   100,  500, 300)
        self._dimmed_brightness_var = self._slider(right, "Dimmed Brightness",    10,   90,  30)

        # Hardware brightness toggle
        self.hw_var = tk.BooleanVar(value=True)
        hw_row = tk.Frame(right, bg=BG, pady=6)
        hw_row.pack(fill="x")
        tk.Checkbutton(
            hw_row, text="Hardware Brightness (macOS)",
            variable=self.hw_var,
            bg=BG, fg=TEXT, selectcolor=SURFACE,
            activebackground=BG, activeforeground=TEXT,
            font=("Helvetica", 10),
        ).pack(anchor="w")

        # Gesture reference
        sep = tk.Frame(right, bg=OVERLAY, height=1)
        sep.pack(fill="x", pady=(10, 6))
        tk.Label(right, text="Gesture Map", font=("Helvetica", 11, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w")

        gestures = [
            ("Thumb + Index",   "Previous slide",     BLUE),
            ("Thumb + Middle",  "Next slide",          BLUE),
            ("Thumb + Ring",    "Toggle spotlight",    YELLOW),
            ("Index + Middle",  "Pointer mode",        GREEN),
            ("Index only",      "Draw / annotate",     PEACH),
            ("I + M + R up",    "Erase last stroke",   RED),
        ]
        for gesture, action, colour in gestures:
            row = tk.Frame(right, bg=BG)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=gesture, font=("Helvetica", 9, "bold"),
                     bg=BG, fg=colour, width=16, anchor="w").pack(side="left")
            tk.Label(row, text=action, font=("Helvetica", 9),
                     bg=BG, fg=SUBTEXT).pack(side="left")

        # Keyboard shortcuts hint
        sep2 = tk.Frame(right, bg=OVERLAY, height=1)
        sep2.pack(fill="x", pady=(10, 6))
        tk.Label(right, text="Keyboard", font=("Helvetica", 11, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w")
        keys = [
            ("s", "Spotlight on/off"),
            ("h", "HW brightness"),
            ("+ / -", "Radius"),
            ("[ / ]", "Dim level"),
            ("q", "Quit"),
        ]
        for key, desc in keys:
            row = tk.Frame(right, bg=BG)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=key, font=("Helvetica", 9, "bold"),
                     bg=BG, fg=SKY, width=8, anchor="w").pack(side="left")
            tk.Label(row, text=desc, font=("Helvetica", 9),
                     bg=BG, fg=SUBTEXT).pack(side="left")

    def _build_footer(self):
        footer = tk.Frame(self.root, bg=BG, pady=14)
        footer.pack()

        self.launch_btn = tk.Button(
            footer, text="  Launch Presentation  ",
            command=self._launch,
            bg=BLUE, fg=BG, font=("Helvetica", 14, "bold"),
            relief="flat", padx=20, pady=10, cursor="hand2",
            activebackground=SKY, activeforeground=BG,
        )
        self.launch_btn.pack()

        self.status_lbl = tk.Label(
            footer, text="Add slides to get started",
            bg=BG, fg=MUTED, font=("Helvetica", 10),
        )
        self.status_lbl.pack(pady=(6, 0))

    # ── Widget helpers ────────────────────────────────────────────────────────

    def _btn(self, parent, text, cmd, colour):
        return tk.Button(
            parent, text=text, command=cmd,
            bg=colour, fg=BG, font=("Helvetica", 9, "bold"),
            relief="flat", padx=9, pady=5, cursor="hand2",
            activebackground=colour,
        )

    def _slider(self, parent, label: str, lo: int, hi: int, default: int) -> tk.IntVar:
        var = tk.IntVar(value=default)

        frame = tk.Frame(parent, bg=BG, pady=4)
        frame.pack(fill="x")

        top = tk.Frame(frame, bg=BG)
        top.pack(fill="x")
        tk.Label(top, text=label, font=("Helvetica", 9),
                 bg=BG, fg=TEXT).pack(side="left")
        tk.Label(top, textvariable=var, font=("Helvetica", 9, "bold"),
                 bg=BG, fg=BLUE, width=4, anchor="e").pack(side="right")

        tk.Scale(
            frame, from_=lo, to=hi, orient="horizontal",
            variable=var, showvalue=False,
            bg=BG, fg=TEXT, troughcolor=OVERLAY,
            activebackground=BLUE, highlightthickness=0, relief="flat",
            sliderlength=16,
        ).pack(fill="x")

        return var

    # ── File actions ──────────────────────────────────────────────────────────

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title="Select Slide Images",
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.bmp *.webp *.tiff"),
                ("All files", "*.*"),
            ],
        )
        for p in paths:
            if p not in self.image_paths:
                self.image_paths.append(p)
                self.listbox.insert("end", os.path.basename(p))
        self._update_status()

    def _add_folder(self):
        folder = filedialog.askdirectory(title="Select Folder of Slides")
        if not folder:
            return
        added = 0
        candidates = sorted(
            f for f in os.listdir(folder)
            if os.path.splitext(f)[1].lower() in IMG_EXTS
        )
        for fname in candidates:
            full = os.path.join(folder, fname)
            if full not in self.image_paths:
                self.image_paths.append(full)
                self.listbox.insert("end", fname)
                added += 1
        if added == 0:
            messagebox.showinfo("No Images", "No supported image files found in that folder.")
        self._update_status()

    def _remove(self):
        for idx in reversed(self.listbox.curselection()):
            self.listbox.delete(idx)
            self.image_paths.pop(idx)
        self._update_status()

    def _move_up(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] == 0:
            return
        i = sel[0]
        self.image_paths[i], self.image_paths[i - 1] = (
            self.image_paths[i - 1], self.image_paths[i]
        )
        text = self.listbox.get(i)
        self.listbox.delete(i)
        self.listbox.insert(i - 1, text)
        self.listbox.select_set(i - 1)

    def _move_down(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] >= len(self.image_paths) - 1:
            return
        i = sel[0]
        self.image_paths[i], self.image_paths[i + 1] = (
            self.image_paths[i + 1], self.image_paths[i]
        )
        text = self.listbox.get(i)
        self.listbox.delete(i)
        self.listbox.insert(i + 1, text)
        self.listbox.select_set(i + 1)

    def _clear(self):
        self.listbox.delete(0, "end")
        self.image_paths.clear()
        self._update_status()

    def _update_status(self):
        n = len(self.image_paths)
        if n == 0:
            self.status_lbl.config(text="Add slides to get started", fg=MUTED)
        else:
            self.status_lbl.config(
                text=f"{n} slide{'s' if n != 1 else ''} ready",
                fg=GREEN,
            )

    # ── Launch ────────────────────────────────────────────────────────────────

    def _launch(self):
        if not self.image_paths:
            messagebox.showwarning("No Slides", "Add at least one slide image first.")
            return

        settings = {
            "spotlight_radius":  self._spotlight_radius_var.get(),
            "dim_opacity":       self._dim_opacity_var.get() / 100,
            "gesture_threshold": self._gesture_threshold_var.get(),
            "dimmed_brightness": self._dimmed_brightness_var.get() / 100,
            "hardware_dim":      self.hw_var.get(),
        }

        self.launch_btn.config(state="disabled", text="Running…")
        self.root.withdraw()        # hide launcher while presenting
        try:
            run_presentation(self.image_paths, settings)
        finally:
            self.root.deiconify()  # restore launcher when done
            self.launch_btn.config(state="normal", text="  Launch Presentation  ")

    # ── Entry point ───────────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()


def main():
    PresentationLauncher().run()


if __name__ == "__main__":
    main()
