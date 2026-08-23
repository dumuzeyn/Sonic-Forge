import tkinter as tk
from tkinter import ttk

from .theme import COLORS, FONTS, SPACING, SIZES
from .widgets import SquareCheckbutton, ToolTip


class SonicForgeView(ttk.Frame):
    METADATA_FIELDS = (
        ("title", "title_var", "tip_title"),
        ("artist", "artist_var", None),
        ("album", "album_var", None),
        ("album_artist", "album_artist_var", None),
        ("composer", "composer_var", None),
        ("date", "date_var", None),
        ("track", "track_var", None),
        ("genre", "genre_var", "tip_genre"),
        ("comment", "comment_var", None),
    )

    def __init__(self, parent, app, header_image):
        super().__init__(parent, padding=(SPACING["lg"], SPACING["sm"], SPACING["lg"], SPACING["md"]))
        self.app = app
        self.header_image = header_image
        self.localized = []
        self.cover_controls = []
        self.tooltips = []
        self.busy = False
        self.active_tab = "metadata"
        self.tab_buttons = {}
        self.tab_pages = {}
        self._build()

    def _localize(self, widget, key):
        widget.configure(text=self.app.t(key))
        self.localized.append((widget, key))
        return widget

    def _tip(self, widget, key):
        self.tooltips.append(ToolTip(widget, lambda: self.app.t(key)))
        return widget

    def _section(self, parent, key, row, column, **grid_options):
        frame = ttk.Labelframe(
            parent,
            text=self.app.t(key),
            style="Surface.TLabelframe",
            padding=SPACING["sm"],
        )
        self.localized.append((frame, key))
        frame.grid(row=row, column=column, **grid_options)
        return frame

    def _build(self):
        self.pack(fill=tk.BOTH, expand=True)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)
        self._build_header()
        ttk.Separator(self, orient="horizontal").grid(row=1, column=0, sticky="ew", pady=(0, SPACING["md"]))
        self._build_paths()
        self._build_tabs()

    def _build_header(self):
        header = ttk.Frame(self, height=SIZES["header_height"])
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.columnconfigure(1, weight=1)
        icon = ttk.Label(header, image=self.header_image)
        icon.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, SPACING["md"]))
        self.title_label = ttk.Label(header, text=self.app.app_name(), style="Title.TLabel")
        self.title_label.grid(row=0, column=1, sticky="sw", pady=(6, 0))
        self.description_label = self._localize(
            ttk.Label(header, style="Secondary.TLabel"), "description"
        )
        self.description_label.grid(row=1, column=1, sticky="nw", pady=(2, 5))
        self.language_button = self._localize(
            ttk.Button(
                header,
                width=SIZES["language_width"],
                command=self.app.toggle_language,
            ),
            "language_button",
        )
        self.language_button.grid(row=0, column=2, rowspan=2, sticky="e")

    def _build_paths(self):
        frame = self._section(self, "paths", 2, 0, sticky="ew", pady=(0, SPACING["md"]))
        frame.columnconfigure(1, weight=1)
        self._path_row(frame, 0, "source", self.app.source_var, "tip_source", True)
        self._path_row(frame, 1, "output", self.app.output_var, "tip_output", False)

    def _path_row(self, parent, row, key, variable, tip_key, source):
        label = self._localize(ttk.Label(parent, style="Surface.TLabel"), key)
        label.grid(row=row, column=0, sticky="w", padx=(0, SPACING["md"]), pady=SPACING["xs"])
        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(row=row, column=1, sticky="ew", pady=SPACING["xs"])
        self._tip(label, tip_key)
        self._tip(entry, tip_key)
        buttons = ttk.Frame(parent, style="Surface.TFrame")
        buttons.grid(row=row, column=2, sticky="e", padx=(SPACING["sm"], 0))
        if source:
            file_button = self._localize(
                ttk.Button(buttons, width=SIZES["button_width"], command=self.app.choose_source_file),
                "choose_file",
            )
            folder_button = self._localize(
                ttk.Button(buttons, width=SIZES["button_width"], command=self.app.choose_source_folder),
                "choose_folder",
            )
            file_button.grid(row=0, column=0, padx=(0, SPACING["sm"]))
            folder_button.grid(row=0, column=1)
        else:
            choose_button = self._localize(
                ttk.Button(buttons, width=SIZES["button_width"], command=self.app.choose_output_folder),
                "choose",
            )
            choose_button.grid(row=0, column=1)

    def _build_tabs(self):
        tabs = ttk.Frame(self)
        tabs.grid(row=3, column=0, sticky="nsew")
        tabs.columnconfigure(0, weight=1)
        tabs.rowconfigure(1, weight=1)

        tab_bar = ttk.Frame(tabs, style="TabBar.TFrame", height=SIZES["tab_height"])
        tab_bar.grid(row=0, column=0, sticky="ew")
        tab_bar.grid_propagate(False)
        for column, (name, key) in enumerate(
            (
                ("metadata", "tab_metadata"),
                ("audio", "tab_audio"),
                ("cover", "tab_cover"),
                ("processing", "tab_processing"),
            )
        ):
            tab_bar.columnconfigure(column, weight=1, uniform="tabs")
            button = self._localize(
                ttk.Button(
                    tab_bar,
                    style="Tab.TButton",
                    command=lambda selected=name: self.show_tab(selected),
                ),
                key,
            )
            button.grid(row=0, column=column, sticky="nsew")
            self.tab_buttons[name] = button

        page_holder = ttk.Frame(tabs, style="Surface.TFrame")
        page_holder.grid(row=1, column=0, sticky="nsew")
        page_holder.columnconfigure(0, weight=1)
        page_holder.rowconfigure(0, weight=1)
        for name in ("metadata", "audio", "cover", "processing"):
            page = ttk.Frame(page_holder, style="Surface.TFrame", padding=SPACING["md"])
            page.grid(row=0, column=0, sticky="nsew")
            page.columnconfigure(0, weight=1)
            page.rowconfigure(0, weight=1)
            self.tab_pages[name] = page

        self._build_metadata(self.tab_pages["metadata"])
        self._build_audio(self.tab_pages["audio"])
        self._build_cover(self.tab_pages["cover"])
        processing_page = self.tab_pages["processing"]
        processing_page.rowconfigure(0, weight=0)
        processing_page.rowconfigure(1, weight=1)
        self._build_processing(processing_page)
        self._build_log(processing_page)
        self.show_tab(self.active_tab)

    def show_tab(self, name):
        self.active_tab = name
        self.tab_pages[name].tkraise()
        for tab_name, button in self.tab_buttons.items():
            style = "Selected.Tab.TButton" if tab_name == name else "Tab.TButton"
            button.configure(style=style)

    def _build_metadata(self, parent):
        frame = self._section(parent, "metadata", 0, 0, sticky="nsew")
        frame.configure(padding=(SPACING["sm"], SPACING["xs"]))
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        for index, (key, var_name, tip_key) in enumerate(self.METADATA_FIELDS):
            if key == "comment":
                column, pair_row, span = 0, 4, 2
            else:
                column, pair_row, span = index % 2, index // 2, 1
            base_row = pair_row * 2
            label = self._localize(ttk.Label(frame, style="SurfaceSecondary.TLabel"), key)
            label.grid(
                row=base_row,
                column=column,
                columnspan=span,
                sticky="w",
                padx=(0 if column == 0 else SPACING["sm"], SPACING["sm"] if column == 0 else 0),
            )
            entry = ttk.Entry(frame, textvariable=getattr(self.app, var_name))
            entry.grid(
                row=base_row + 1,
                column=column,
                columnspan=span,
                sticky="ew",
                padx=(0 if column == 0 else SPACING["sm"], SPACING["sm"] if column == 0 else 0),
                pady=(1, 2),
            )
            if tip_key:
                self._tip(label, tip_key)
                self._tip(entry, tip_key)
        checks = ttk.Frame(frame, style="Surface.TFrame")
        checks.grid(row=10, column=0, columnspan=2, sticky="ew", pady=(SPACING["xs"], 0))
        self.overwrite_genre_check = self._localize(
            SquareCheckbutton(checks, self.app.overwrite_genre_var, fixed_width=230), "overwrite_genre"
        )
        self.overwrite_genre_check.pack(side=tk.LEFT, padx=(0, SPACING["lg"]))
        self._tip(self.overwrite_genre_check, "tip_overwrite_genre")
        self.overwrite_all_check = self._localize(
            SquareCheckbutton(checks, self.app.overwrite_all_metadata_var, fixed_width=230), "overwrite_all_metadata"
        )
        self.overwrite_all_check.pack(side=tk.LEFT)
        self._tip(self.overwrite_all_check, "tip_overwrite_all_metadata")
        self.metadata_actions = self._localize(
            ttk.Menubutton(checks, width=SIZES["button_width"]), "metadata_actions"
        )
        self.metadata_actions.pack(side=tk.RIGHT)
        self.metadata_menu = tk.Menu(self.metadata_actions, tearoff=False)
        self.metadata_actions.configure(menu=self.metadata_menu)
        self._rebuild_metadata_menu()

    def _build_audio(self, parent):
        frame = self._section(parent, "audio", 0, 0, sticky="nsew")
        frame.columnconfigure(0, minsize=145)
        frame.columnconfigure(1, weight=1, minsize=70)
        frame.columnconfigure(2, minsize=135)
        frame.columnconfigure(3, weight=1, minsize=65)
        subtitle = self._localize(ttk.Label(frame, style="SurfaceSecondary.TLabel"), "normalization")
        subtitle.grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, SPACING["xs"]))
        fields = (
            ("integrated_lufs", self.app.integrated_lufs_var, -30, -5, 0.5, "tip_integrated_lufs"),
            ("true_peak", self.app.true_peak_var, -9, 0, 0.1, "tip_true_peak"),
            ("lra", self.app.lra_var, 1, 20, 0.5, "tip_lra"),
            ("final_gain", self.app.final_gain_var, 0.5, 2, 0.05, "tip_final_gain"),
        )
        for index, (key, variable, minimum, maximum, step, tip_key) in enumerate(fields):
            pair = index % 2
            base_row = 1 + index // 2
            label_column = pair * 2
            control_column = label_column + 1
            label = self._localize(ttk.Label(frame, style="SurfaceSecondary.TLabel"), key)
            label.grid(
                row=base_row,
                column=label_column,
                sticky="w",
                padx=(0 if pair == 0 else SPACING["md"], SPACING["sm"]),
                pady=SPACING["xs"],
            )
            spin = ttk.Spinbox(frame, textvariable=variable, from_=minimum, to=maximum, increment=step, width=12)
            spin.grid(
                row=base_row,
                column=control_column,
                sticky="ew",
                pady=SPACING["xs"],
            )
            self._tip(label, tip_key)
            self._tip(spin, tip_key)
        cleanup = self._localize(ttk.Label(frame, style="SurfaceSecondary.TLabel"), "cleanup")
        cleanup.grid(row=3, column=0, columnspan=2, sticky="w", pady=(SPACING["xs"], SPACING["xs"]))
        advanced_holder = tk.Frame(
            frame,
            width=200,
            height=SIZES["control_height"],
            bg=COLORS["surface"],
        )
        advanced_holder.grid(
            row=3,
            column=2,
            columnspan=2,
            sticky="e",
            pady=(SPACING["xs"], SPACING["xs"]),
        )
        advanced_holder.pack_propagate(False)
        advanced = self._localize(
            ttk.Button(advanced_holder, command=self.app.show_advanced_audio),
            "advanced_audio",
        )
        advanced.pack(fill=tk.BOTH, expand=True)
        checks = ttk.Frame(frame, style="Surface.TFrame")
        checks.grid(row=4, column=0, columnspan=4, sticky="ew")
        self.denoise_check = self._localize(
            SquareCheckbutton(
                checks,
                self.app.denoise_var,
                command=self.update_dependencies,
                fixed_width=150,
            ),
            "denoise",
        )
        self.denoise_check.pack(side=tk.LEFT)
        strength_label = self._localize(ttk.Label(checks, style="SurfaceSecondary.TLabel"), "denoise_strength")
        strength_label.pack(side=tk.LEFT, padx=(SPACING["lg"], SPACING["sm"]))
        self.denoise_strength = ttk.Spinbox(
            checks, textvariable=self.app.denoise_strength_var, from_=0, to=20, increment=0.5, width=7
        )
        self.denoise_strength.pack(side=tk.LEFT)
        self.limiter_check = self._localize(
            SquareCheckbutton(checks, self.app.limiter_var, fixed_width=90), "limiter"
        )
        self.limiter_check.pack(side=tk.RIGHT)
        self._tip(self.denoise_check, "tip_denoise")
        self._tip(strength_label, "tip_denoise_strength")
        self._tip(self.denoise_strength, "tip_denoise_strength")
        self._tip(self.limiter_check, "tip_limiter")
    def _build_cover(self, parent):
        header = ttk.Frame(parent, style="Surface.TFrame")
        title = self._localize(ttk.Label(header, style="Surface.TLabel", font=FONTS["section"]), "cover")
        title.pack(side=tk.LEFT, padx=(0, SPACING["lg"]))
        self.no_change_cover_check = self._localize(
            SquareCheckbutton(
                header,
                self.app.no_change_cover_var,
                command=self.update_dependencies,
                fixed_width=190,
            ),
            "no_change_cover",
        )
        self.no_change_cover_check.pack(side=tk.LEFT)
        self._tip(self.no_change_cover_check, "tip_no_change_cover")
        frame = ttk.Labelframe(
            parent,
            labelwidget=header,
            style="Surface.TLabelframe",
            padding=SPACING["sm"],
        )
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)
        fields = (
            ("color_mode", self.app.color_var, "combo"),
            ("seed", self.app.seed_var, "entry"),
            ("cover_size", self.app.cover_size_var, "size"),
            ("cover_patterns", self.app.cover_patterns_var, "detail"),
        )
        for index, (key, variable, kind) in enumerate(fields):
            pair = index % 2
            base_row = index // 2
            label_column = pair * 2
            control_column = label_column + 1
            label = self._localize(ttk.Label(frame, style="SurfaceSecondary.TLabel"), key)
            label.grid(
                row=base_row,
                column=label_column,
                sticky="w",
                padx=(0 if pair == 0 else SPACING["md"], SPACING["sm"]),
                pady=SPACING["xs"],
            )
            if kind == "combo":
                control = ttk.Combobox(
                    frame,
                    textvariable=variable,
                    values=("ocean", "plasma", "fusion", "aurora"),
                    state="readonly",
                )
                tip_key = "tip_color_mode"
            elif kind == "size":
                control = ttk.Spinbox(frame, textvariable=variable, from_=300, to=3000, increment=100)
                tip_key = "tip_cover_size"
            elif kind == "detail":
                control = ttk.Combobox(frame, textvariable=variable, values=(1, 2), state="readonly")
                tip_key = "tip_cover_patterns"
            else:
                control = ttk.Entry(frame, textvariable=variable)
                tip_key = "tip_seed"
            control.grid(
                row=base_row,
                column=control_column,
                sticky="ew",
                pady=SPACING["xs"],
            )
            self.cover_controls.extend((label, control))
            self._tip(label, tip_key)
            self._tip(control, tip_key)
        options = ttk.Frame(frame, style="Surface.TFrame")
        options.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(SPACING["xs"], 0))
        self.center_title_check = self._localize(
            SquareCheckbutton(options, self.app.center_title_var, fixed_width=170), "center_title"
        )
        self.embed_cover_check = self._localize(
            SquareCheckbutton(options, self.app.embed_cover_var, fixed_width=170), "embed_cover"
        )
        self.center_title_check.grid(row=0, column=0, sticky="w", padx=(0, SPACING["lg"]))
        self.embed_cover_check.grid(row=0, column=1, sticky="w")
        self.cover_controls.extend((self.center_title_check, self.embed_cover_check))

    def _build_processing(self, parent):
        frame = self._section(parent, "processing", 0, 0, sticky="ew", pady=(0, SPACING["md"]))
        frame.columnconfigure(1, weight=1)
        stages = ttk.Frame(frame, style="Surface.TFrame")
        stages.grid(row=0, column=0, sticky="w")
        stage_label = self._localize(ttk.Label(stages, style="SurfaceSecondary.TLabel"), "stages")
        stage_label.pack(side=tk.LEFT, padx=(0, SPACING["md"]))
        for key, variable in (
            ("stage_audio", self.app.process_audio_var),
            ("stage_metadata", self.app.process_metadata_var),
            ("stage_cover", self.app.process_cover_var),
        ):
            check = self._localize(
                SquareCheckbutton(stages, variable, fixed_width=105), key
            )
            check.pack(side=tk.LEFT, padx=(0, SPACING["md"]))
        actions = ttk.Frame(frame, style="Surface.TFrame")
        actions.grid(row=0, column=2, sticky="e")
        self.run_button = self._localize(
            ttk.Button(
                actions,
                style="Primary.TButton",
                width=SIZES["primary_width"],
                command=self.app.run_selected_steps,
            ),
            "run",
        )
        self.run_button.pack(side=tk.LEFT, padx=(0, SPACING["sm"]))
        self.stop_button = self._localize(
            ttk.Button(
                actions,
                style="Danger.TButton",
                width=SIZES["button_width"],
                command=self.app.stop_processing,
                state=tk.DISABLED,
            ),
            "stop",
        )
        self.stop_button.pack(side=tk.LEFT)
        self._tip(self.run_button, "tip_run")
        self._tip(self.stop_button, "tip_stop")
        self.progress = ttk.Progressbar(frame, mode="indeterminate", style="Thin.Horizontal.TProgressbar")
        self.progress.grid(row=0, column=1, sticky="ew", padx=SPACING["lg"])

    def _build_log(self, parent):
        frame = self._section(parent, "log", 1, 0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self.clear_log_button = self._localize(
            ttk.Button(frame, width=SIZES["button_width"], command=self.app.clear_log), "clear_log"
        )
        self.clear_log_button.grid(row=0, column=1, sticky="ne", padx=(SPACING["sm"], 0))
        log_wrap = tk.Frame(
            frame,
            bg=COLORS["log"],
            highlightthickness=1,
            highlightbackground=COLORS["border"],
        )
        log_wrap.grid(row=0, column=0, sticky="nsew")
        log_wrap.columnconfigure(0, weight=1)
        log_wrap.rowconfigure(0, weight=1)
        self.log = tk.Text(
            log_wrap,
            height=6,
            wrap="word",
            undo=True,
            bg=COLORS["log"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            selectbackground=COLORS["accent_pressed"],
            selectforeground=COLORS["white"],
            relief="flat",
            borderwidth=0,
            padx=12,
            pady=10,
            font=FONTS["mono"],
        )
        scrollbar = ttk.Scrollbar(log_wrap, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)
        self.log.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

    def update_dependencies(self):
        self.denoise_strength.configure(state="normal" if self.app.denoise_var.get() else "disabled")
        cover_enabled = not self.app.no_change_cover_var.get()
        state = "normal" if cover_enabled else "disabled"
        for control in self.cover_controls:
            if isinstance(control, SquareCheckbutton):
                control.configure(state=state)
            elif isinstance(control, ttk.Label):
                control.configure(foreground=COLORS["secondary"] if cover_enabled else COLORS["disabled"])
            elif isinstance(control, ttk.Combobox):
                control.configure(state="readonly" if cover_enabled else "disabled")
            else:
                control.configure(state=state)

    def apply_language(self):
        self.title_label.configure(text=self.app.app_name())
        for widget, key in self.localized:
            widget.configure(text=self.app.t(key))
        self._rebuild_metadata_menu()
        self.update_dependencies()
        if self.busy:
            self.run_button.configure(text=self.app.t("processing_busy"))

    def _rebuild_metadata_menu(self):
        self.metadata_menu.delete(0, tk.END)
        self.metadata_menu.add_command(
            label=self.app.t("read_metadata"), command=self.app.load_metadata
        )
        self.metadata_menu.add_command(
            label=self.app.t("additional_metadata"),
            command=self.app.show_additional_metadata,
        )
        self.metadata_menu.add_separator()
        self.metadata_menu.add_command(
            label=self.app.t("clear_metadata"), command=self.app.clear_metadata
        )

    def set_busy(self, busy):
        self.busy = busy
        self.run_button.configure(
            state=tk.DISABLED if busy else tk.NORMAL,
            text=self.app.t("processing_busy") if busy else self.app.t("run"),
        )
        self.stop_button.configure(state=tk.NORMAL if busy else tk.DISABLED)
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()
