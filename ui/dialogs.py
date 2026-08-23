import tkinter as tk
from tkinter import ttk

from .theme import COLORS, SPACING, SIZES
from .widgets import SquareCheckbutton


class AdvancedAudioDialog(tk.Toplevel):
    FIELD_GROUPS = (
        (
            "equalizer",
            (
                ("bass_gain", "bass_gain_var", -12, 12, 0.5),
                ("mid_gain", "mid_gain_var", -12, 12, 0.5),
                ("treble_gain", "treble_gain_var", -12, 12, 0.5),
                ("highpass_hz", "highpass_hz_var", 10, 500, 5),
                ("lowpass_hz", "lowpass_hz_var", 4000, 24000, 100),
                ("stereo_width", "stereo_width_var", 0, 2, 0.05),
            ),
        ),
        (
            "compressor",
            (
                ("compressor_threshold", "compressor_threshold_var", -60, 0, 1),
                ("compressor_ratio", "compressor_ratio_var", 1, 20, 0.5),
                ("compressor_attack", "compressor_attack_var", 1, 200, 1),
                ("compressor_release", "compressor_release_var", 20, 2000, 10),
                ("compressor_makeup", "compressor_makeup_var", 0, 18, 0.5),
            ),
        ),
        (
            "effects",
            (
                ("pitch_semitones", "pitch_semitones_var", -12, 12, 0.5),
                ("playback_speed", "playback_speed_var", 0.5, 2, 0.05),
                ("reverb_mix", "reverb_mix_var", 0, 1, 0.05),
                ("fade_in", "fade_in_var", 0, 30, 0.5),
                ("fade_out", "fade_out_var", 0, 30, 0.5),
            ),
        ),
    )

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.localized = []
        self.title(app.t("advanced_title"))
        self.configure(bg=COLORS["bg"])
        self.geometry("720x650")
        self.minsize(680, 610)
        self.transient(app)
        self.grab_set()
        self._build()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<Escape>", lambda _event: self.destroy())

    def _text(self, widget, key):
        widget.configure(text=self.app.t(key))
        self.localized.append((widget, key))
        return widget

    def _build(self):
        body = ttk.Frame(self, padding=SPACING["lg"])
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(0, weight=1)
        row = 0
        for group_key, fields in self.FIELD_GROUPS:
            frame = ttk.Labelframe(
                body,
                text=self.app.t(group_key),
                style="Surface.TLabelframe",
                padding=SPACING["md"],
            )
            self.localized.append((frame, group_key))
            frame.grid(row=row, column=0, sticky="ew", pady=(0, SPACING["md"]))
            frame.columnconfigure(0, weight=1)
            frame.columnconfigure(1, weight=1)
            start_row = 0
            if group_key == "compressor":
                check = SquareCheckbutton(
                    frame,
                    app_var(self.app, "compressor_var"),
                    self.app.t("compressor"),
                    fixed_width=190,
                )
                self.localized.append((check, "compressor"))
                check.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, SPACING["sm"]))
                start_row = 1
            for index, (key, var_name, minimum, maximum, step) in enumerate(fields):
                column = index % 2
                field_row = start_row + (index // 2) * 2
                label = ttk.Label(frame, text=self.app.t(key), style="SurfaceSecondary.TLabel")
                self.localized.append((label, key))
                label.grid(
                    row=field_row,
                    column=column,
                    sticky="w",
                    padx=(0 if column == 0 else SPACING["sm"], SPACING["sm"]),
                )
                spin = ttk.Spinbox(
                    frame,
                    textvariable=app_var(self.app, var_name),
                    from_=minimum,
                    to=maximum,
                    increment=step,
                    width=14,
                )
                spin.grid(
                    row=field_row + 1,
                    column=column,
                    sticky="ew",
                    padx=(0 if column == 0 else SPACING["sm"], SPACING["sm"] if column == 0 else 0),
                    pady=(SPACING["xs"], SPACING["sm"]),
                )
            row += 1
        close = ttk.Button(
            body,
            text=self.app.t("close"),
            width=SIZES["button_width"],
            command=self.destroy,
        )
        self.localized.append((close, "close"))
        close.grid(row=row, column=0, sticky="e")


def app_var(app, name):
    return getattr(app, name)


class AdditionalMetadataDialog(tk.Toplevel):
    FIELDS = (
        ("disc", "disc_var"),
        ("publisher", "publisher_var"),
        ("copyright", "copyright_var"),
        ("lyrics", "lyrics_var"),
    )

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title(app.t("additional_metadata_title"))
        self.configure(bg=COLORS["bg"])
        self.geometry("680x330")
        self.resizable(False, False)
        self.transient(app)
        self.grab_set()
        self._build()
        self.bind("<Escape>", lambda _event: self.destroy())

    def _build(self):
        body = ttk.Labelframe(
            self,
            text=self.app.t("additional_metadata_title"),
            style="Surface.TLabelframe",
            padding=SPACING["lg"],
        )
        body.pack(fill=tk.BOTH, expand=True, padx=SPACING["lg"], pady=SPACING["lg"])
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        for index, (key, var_name) in enumerate(self.FIELDS):
            column = index % 2
            row = (index // 2) * 2
            ttk.Label(
                body,
                text=self.app.t(key),
                style="SurfaceSecondary.TLabel",
            ).grid(
                row=row,
                column=column,
                sticky="w",
                padx=(0 if column == 0 else SPACING["sm"], SPACING["sm"] if column == 0 else 0),
            )
            ttk.Entry(body, textvariable=getattr(self.app, var_name)).grid(
                row=row + 1,
                column=column,
                sticky="ew",
                padx=(0 if column == 0 else SPACING["sm"], SPACING["sm"] if column == 0 else 0),
                pady=(SPACING["xs"], SPACING["md"]),
            )
        ttk.Button(
            body,
            text=self.app.t("close"),
            width=SIZES["button_width"],
            command=self.destroy,
        ).grid(row=4, column=0, columnspan=2, sticky="e", pady=(SPACING["sm"], 0))
