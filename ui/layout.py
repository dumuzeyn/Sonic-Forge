import tkinter as tk
from pathlib import Path
from tkinter import ttk
from PIL import Image, ImageTk

from .theme import COLORS, FONTS, SPACING, SIZES
from .widgets import ModernScale, SquareCheckbutton, ToolTip


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
        self.lyrics_controls = []
        self.tooltips = []
        self.description_records = {}
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
        self.header_icon = ttk.Label(header, image=self.header_image)
        self.header_icon.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, SPACING["md"]))
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
                ("lyrics", "tab_lyrics"),
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
        for name in ("metadata", "audio", "cover", "lyrics", "processing"):
            page = ttk.Frame(page_holder, style="Surface.TFrame", padding=SPACING["md"])
            page.grid(row=0, column=0, sticky="nsew")
            page.columnconfigure(0, weight=1)
            page.rowconfigure(0, weight=1)
            self.tab_pages[name] = page

        self._build_metadata(self.tab_pages["metadata"])
        self._build_audio(self.tab_pages["audio"])
        self._build_cover(self.tab_pages["cover"])
        self._build_lyrics(self.tab_pages["lyrics"])
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
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)

        profile_label = self._localize(ttk.Label(frame, style="SurfaceSecondary.TLabel"), "audio_profile")
        profile_label.grid(row=0, column=0, sticky="w", padx=(0, SPACING["sm"]))
        self.audio_profile_combo = ttk.Combobox(
            frame,
            textvariable=self.app.audio_profile_var,
            values=self.app.audio_profile_values(),
            state="readonly",
        )
        self.audio_profile_combo.grid(row=0, column=1, columnspan=2, sticky="ew")
        self.audio_profile_combo.bind("<<ComboboxSelected>>", lambda _event: self.app.audio_profile_changed())
        self._tip(profile_label, "tip_audio_profile")
        self._tip(self.audio_profile_combo, "tip_audio_profile")
        advanced = self._localize(
            ttk.Button(frame, command=self.app.show_advanced_audio), "advanced_audio"
        )
        advanced.grid(row=0, column=3, sticky="e", padx=(SPACING["md"], 0))

        intensity_label = self._localize(ttk.Label(frame, style="SurfaceSecondary.TLabel"), "audio_intensity")
        intensity_label.grid(row=1, column=0, sticky="w", pady=(SPACING["md"], 0))
        intensity = ModernScale(
            frame, from_=0, to=100, variable=self.app.audio_intensity_var,
            command=lambda value: self.app._apply_audio_macros(),
        )
        intensity.grid(row=1, column=1, columnspan=3, sticky="ew", pady=(SPACING["md"], 0))
        self._tip(intensity_label, "tip_audio_intensity")
        self._tip(intensity, "tip_audio_intensity")

        macros = ttk.Frame(frame, style="Surface.TFrame")
        macros.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(SPACING["md"], 0))
        macros.columnconfigure(1, weight=1)
        macros.columnconfigure(4, weight=1)
        macro_fields = (
            ("audio_loudness", self.app.loudness_macro_var, "audio_quieter", "audio_louder"),
            ("audio_character", self.app.character_macro_var, "audio_softer", "audio_brighter"),
            ("audio_bass_macro", self.app.bass_macro_var, "audio_less", "audio_more"),
            ("audio_space", self.app.space_macro_var, "audio_narrower", "audio_wider"),
        )
        for index, (key, variable, left_key, right_key) in enumerate(macro_fields):
            column = 0 if index % 2 == 0 else 3
            row = (index // 2) * 2
            label = self._localize(ttk.Label(macros, style="Surface.TLabel"), key)
            label.grid(row=row, column=column, columnspan=2, sticky="w", pady=(0, 2))
            scale = ModernScale(
                macros,
                from_=-100,
                to=100,
                variable=variable,
                command=self.app.audio_macro_changed,
            )
            scale.grid(row=row + 1, column=column + 1, sticky="ew", padx=SPACING["xs"])
            left = self._localize(ttk.Label(macros, style="SurfaceSecondary.TLabel"), left_key)
            right = self._localize(ttk.Label(macros, style="SurfaceSecondary.TLabel"), right_key)
            left.grid(row=row + 1, column=column, sticky="w")
            right.grid(row=row + 1, column=column + 2, sticky="e", padx=(SPACING["xs"], SPACING["md"] if column == 0 else 0))

        checks = ttk.Frame(frame, style="Surface.TFrame")
        checks.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(SPACING["md"], 0))
        self.auto_denoise_check = self._localize(
            SquareCheckbutton(
                checks,
                self.app.auto_denoise_var,
                command=self.app.auto_denoise_changed,
                fixed_width=260,
            ),
            "audio_auto_denoise",
        )
        self.auto_denoise_check.pack(side=tk.LEFT)
        self.limiter_check = self._localize(
            SquareCheckbutton(checks, self.app.limiter_var, fixed_width=210), "audio_peak_protection"
        )
        self.limiter_check.pack(side=tk.LEFT, padx=(SPACING["md"], 0))

        actions = ttk.Frame(frame, style="Surface.TFrame")
        actions.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(SPACING["md"], 0))
        for column in range(3):
            actions.columnconfigure(column, weight=1, uniform="audio_actions")
        self.audio_analyze_button = self._localize(
            ttk.Button(actions, command=self.app.analyze_audio_settings), "audio_analyze"
        )
        self.audio_apply_button = self._localize(
            ttk.Button(actions, command=self.app.apply_audio_recommendation, state="disabled"),
            "audio_apply_recommendation",
        )
        self.audio_preview_button = self._localize(
            ttk.Button(actions, command=self.app.create_audio_preview), "audio_preview"
        )
        self.audio_original_button = self._localize(
            ttk.Button(actions, command=lambda: self.app.play_audio_preview(False), state="disabled"), "audio_original"
        )
        self.audio_processed_button = self._localize(
            ttk.Button(actions, command=lambda: self.app.play_audio_preview(True), state="disabled"), "audio_processed"
        )
        self.audio_stop_button = self._localize(
            ttk.Button(actions, command=self.app.stop_audio_preview, state="disabled"), "audio_stop"
        )
        for column, button in enumerate(
            (self.audio_analyze_button, self.audio_apply_button, self.audio_preview_button)
        ):
            button.grid(row=0, column=column, sticky="ew", padx=(0, SPACING["sm"] if column < 2 else 0))
        for column, button in enumerate(
            (self.audio_original_button, self.audio_processed_button, self.audio_stop_button)
        ):
            button.grid(row=1, column=column, sticky="ew", padx=(0, SPACING["sm"] if column < 2 else 0), pady=(SPACING["xs"], 0))

        analysis = ttk.Label(
            frame, textvariable=self.app.audio_analysis_var, style="SurfaceSecondary.TLabel",
            wraplength=760, justify=tk.LEFT,
        )
        analysis.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(SPACING["md"], 0))
        warning = ttk.Label(
            frame, textvariable=self.app.audio_warning_var, style="SurfaceSecondary.TLabel",
            foreground=COLORS["danger"], wraplength=760, justify=tk.LEFT,
        )
        warning.grid(row=6, column=0, columnspan=4, sticky="ew", pady=(SPACING["xs"], 0))
    def _build_cover(self, parent):
        header = ttk.Frame(parent, style="Surface.TFrame")
        self._localize(ttk.Label(header, style="Surface.TLabel", font=FONTS["section"]), "cover").pack(side=tk.LEFT, padx=(0, SPACING["lg"]))
        self.no_change_cover_check = self._localize(
            SquareCheckbutton(header, self.app.no_change_cover_var, command=self.update_dependencies, fixed_width=190),
            "no_change_cover",
        )
        self.no_change_cover_check.pack(side=tk.LEFT)
        self._tip(self.no_change_cover_check, "tip_no_change_cover")
        frame = ttk.Labelframe(parent, labelwidget=header, style="Surface.TLabelframe", padding=SPACING["sm"])
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=0)
        frame.rowconfigure(0, weight=1)

        controls = ttk.Frame(frame, style="Surface.TFrame")
        controls.grid(row=0, column=0, sticky="nsew", padx=(0, SPACING["lg"]))
        controls.columnconfigure(1, weight=1)
        engine_label = self._localize(
            ttk.Label(controls, style="SurfaceSecondary.TLabel"), "cover_engine"
        )
        engine_label.grid(row=0, column=0, sticky="w", padx=(0, SPACING["sm"]), pady=SPACING["xs"])
        self.cover_engine_combo = ttk.Combobox(
            controls,
            textvariable=self.app.cover_engine_var,
            values=self.app.cover_choice_values("engine"),
            state="readonly",
        )
        self.cover_engine_combo.grid(row=0, column=1, sticky="ew", pady=SPACING["xs"])
        self.cover_engine_combo.bind("<<ComboboxSelected>>", lambda _event: self.app.cover_engine_changed())
        self.cover_controls.append(self.cover_engine_combo)

        fields = (
            ("cover_detail", self.app.cover_detail_var, self.app.cover_choice_values("detail"), "tip_cover_detail"),
            ("seed", self.app.seed_var, None, "tip_seed"),
            ("cover_size", self.app.cover_size_var, "size", "tip_cover_size"),
        )
        for row, (key, variable, values, tip_key) in enumerate(fields, start=1):
            label = self._localize(ttk.Label(controls, style="SurfaceSecondary.TLabel"), key)
            label.grid(row=row, column=0, sticky="w", padx=(0, SPACING["sm"]), pady=SPACING["xs"])
            if isinstance(values, tuple):
                control = ttk.Combobox(controls, textvariable=variable, values=values, state="readonly")
            elif values == "size":
                control = ttk.Spinbox(controls, textvariable=variable, from_=512, to=2048, increment=256)
            else:
                control = ttk.Entry(controls, textvariable=variable)
            control.grid(row=row, column=1, sticky="ew", pady=SPACING["xs"])
            self.cover_controls.extend((label, control))
            if key == "cover_detail":
                self.cover_detail_combo = control
            self._tip(label, tip_key)
            self._tip(control, tip_key)

        options = ttk.Frame(controls, style="Surface.TFrame")
        options.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(SPACING["sm"], 0))
        self.use_lyrics_check = self._localize(
            SquareCheckbutton(options, self.app.use_lyrics_for_cover_var, fixed_width=175),
            "use_lyrics_for_cover_short",
        )
        self.cover_title_check = self._localize(
            SquareCheckbutton(options, self.app.cover_title_var, fixed_width=145),
            "cover_show_title",
        )
        self.cover_artist_check = self._localize(
            SquareCheckbutton(options, self.app.cover_artist_var, fixed_width=145),
            "cover_show_artist",
        )
        self.use_lyrics_check.grid(row=0, column=0, sticky="w", padx=(0, SPACING["md"]))
        self.cover_title_check.grid(row=0, column=1, sticky="w")
        self.cover_artist_check.grid(row=1, column=0, sticky="w", pady=(SPACING["xs"], 0))
        self.embed_cover_check = self._localize(
            SquareCheckbutton(options, self.app.embed_cover_var, fixed_width=145), "embed_cover_short"
        )
        self.embed_cover_check.grid(row=1, column=1, sticky="w", pady=(SPACING["xs"], 0))
        self.cover_controls.extend(
            (self.use_lyrics_check, self.cover_title_check, self.cover_artist_check, self.embed_cover_check)
        )
        self._tip(self.use_lyrics_check, "tip_use_lyrics_for_cover")

        model_row = ttk.Frame(controls, style="Surface.TFrame")
        model_row.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(SPACING["md"], 0))
        model_row.columnconfigure(0, weight=1)
        provider = ttk.Label(
            model_row,
            textvariable=self.app.cover_provider_status_var,
            style="SurfaceSecondary.TLabel",
            wraplength=340,
        )
        provider.grid(row=0, column=0, sticky="w")
        self.model_button = self._localize(
            ttk.Button(model_row, command=self.app.manage_image_model), "cover_model_manage"
        )
        self.model_button.grid(row=0, column=1, sticky="e", padx=(SPACING["sm"], 0))
        self.cover_controls.extend((provider, self.model_button))

        preview = ttk.Frame(frame, style="Surface.TFrame")
        preview.grid(row=0, column=1, sticky="n")
        preview_box = tk.Frame(
            preview,
            width=220,
            height=220,
            bg=COLORS["field"],
            highlightthickness=1,
            highlightbackground=COLORS["border"],
        )
        preview_box.pack_propagate(False)
        preview_box.pack()
        self.cover_preview_image = self._localize(
            tk.Label(
                preview_box,
                bg=COLORS["field"],
                fg=COLORS["secondary"],
                anchor="center",
                justify=tk.CENTER,
                wraplength=190,
                font=FONTS["small"],
            ),
            "cover_preview_empty",
        )
        self.cover_preview_image.pack(fill=tk.BOTH, expand=True)
        preview_actions = ttk.Frame(preview, style="Surface.TFrame")
        preview_actions.pack(fill=tk.X, pady=(SPACING["sm"], 0))
        self.cover_quick_button = self._localize(
            ttk.Button(preview_actions, command=lambda: self.app.preview_cover(quick=True)),
            "cover_quick_preview",
        )
        self.cover_variant_button = self._localize(
            ttk.Button(preview_actions, command=lambda: self.app.preview_cover(True, True)),
            "cover_new_variant",
        )
        self.cover_preview_button = self._localize(
            ttk.Button(preview_actions, style="Primary.TButton", command=self.app.preview_cover),
            "cover_preview",
        )
        self.cover_quick_button.pack(fill=tk.X)
        self.cover_variant_button.pack(fill=tk.X, pady=(SPACING["xs"], 0))
        self.cover_preview_button.pack(fill=tk.X, pady=(SPACING["xs"], 0))
        self.cover_controls.extend((self.cover_quick_button, self.cover_preview_button, self.cover_variant_button))

        descriptions = self._section(frame, "song_descriptions", 1, 0, columnspan=2, sticky="ew", pady=(SPACING["md"], 0))
        descriptions.columnconfigure(0, weight=1)
        toolbar = ttk.Frame(descriptions, style="Surface.TFrame")
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.columnconfigure(0, weight=1)
        self.description_track_combo = ttk.Combobox(
            toolbar,
            textvariable=self.app.description_track_var,
            state="readonly",
        )
        self.description_track_combo.grid(row=0, column=0, sticky="ew", padx=(0, SPACING["sm"]))
        self.description_track_combo.bind("<<ComboboxSelected>>", lambda _event: self.show_selected_description())
        self.description_generate_button = self._localize(
            ttk.Button(toolbar, command=self.app.generate_song_descriptions), "descriptions_generate"
        )
        self.description_generate_button.grid(row=0, column=1, padx=(0, SPACING["sm"]))
        self.description_regenerate_button = self._localize(
            ttk.Button(toolbar, command=lambda: self.app.generate_song_descriptions(True, True)), "description_regenerate"
        )
        self.description_regenerate_button.grid(row=0, column=2)
        status = ttk.Label(
            descriptions,
            textvariable=self.app.description_status_var,
            style="SurfaceSecondary.TLabel",
        )
        status.grid(row=1, column=0, sticky="w", pady=(SPACING["xs"], 0))
        self.description_text = tk.Text(
            descriptions,
            height=4,
            wrap="word",
            bg=COLORS["field"],
            fg=COLORS["text"],
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=8,
            font=FONTS["small"],
            state=tk.DISABLED,
        )
        self.description_text.grid(row=2, column=0, sticky="ew", pady=(SPACING["xs"], 0))

    def _build_lyrics(self, parent):
        frame = self._section(parent, "lyrics_workspace", 0, 0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(3, weight=1)

        toolbar = ttk.Frame(frame, style="Surface.TFrame")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, SPACING["sm"]))
        self.load_lyrics_button = self._localize(
            ttk.Button(toolbar, command=self.app.load_existing_lyrics), "lyrics_load"
        )
        self.recognize_lyrics_button = self._localize(
            ttk.Button(toolbar, style="Primary.TButton", command=self.app.recognize_lyrics),
            "lyrics_recognize",
        )
        self.save_lyrics_button = self._localize(
            ttk.Button(toolbar, command=self.app.save_lyrics_file), "lyrics_save"
        )
        self.load_lyrics_button.pack(side=tk.LEFT, padx=(0, SPACING["sm"]))
        self.recognize_lyrics_button.pack(side=tk.LEFT, padx=(0, SPACING["sm"]))
        self.save_lyrics_button.pack(side=tk.LEFT)

        options = ttk.Frame(frame, style="Surface.TFrame")
        options.grid(row=1, column=0, sticky="ew", pady=(0, SPACING["sm"]))
        format_label = self._localize(
            ttk.Label(options, style="SurfaceSecondary.TLabel"), "lyrics_format"
        )
        format_label.pack(side=tk.LEFT, padx=(0, SPACING["sm"]))
        self.lyrics_format = ttk.Combobox(
            options,
            textvariable=self.app.lyrics_format_var,
            values=("txt", "lrc"),
            state="readonly",
            width=7,
        )
        self.lyrics_format.pack(side=tk.LEFT)
        language_label = self._localize(
            ttk.Label(options, style="SurfaceSecondary.TLabel"), "lyrics_language"
        )
        language_label.pack(side=tk.LEFT, padx=(SPACING["md"], SPACING["sm"]))
        self.lyrics_language = ttk.Combobox(
            options,
            textvariable=self.app.lyrics_language_var,
            values=("auto", "ru", "en", "de", "fr", "es", "it"),
            state="readonly",
            width=7,
        )
        self.lyrics_language.pack(side=tk.LEFT)
        self.overwrite_lyrics_check = self._localize(
            SquareCheckbutton(options, self.app.overwrite_lyrics_var, fixed_width=170),
            "overwrite_lyrics",
        )
        self.overwrite_lyrics_check.pack(side=tk.RIGHT, padx=(SPACING["sm"], 0))
        self.use_lyrics_check = self._localize(
            SquareCheckbutton(
                options,
                self.app.use_lyrics_for_cover_var,
                fixed_width=175,
            ),
            "use_lyrics_for_cover_short",
        )
        self.use_lyrics_check.pack(side=tk.RIGHT)
        self._tip(self.recognize_lyrics_button, "tip_lyrics_recognize")
        self._tip(self.lyrics_format, "tip_lyrics_format")
        self._tip(self.use_lyrics_check, "tip_use_lyrics_for_cover")

        status = ttk.Label(
            frame,
            textvariable=self.app.lyrics_status_var,
            style="SurfaceSecondary.TLabel",
            anchor="w",
        )
        status.grid(row=2, column=0, sticky="ew", pady=(0, SPACING["sm"]))

        editor_wrap = tk.Frame(
            frame,
            bg=COLORS["field"],
            highlightthickness=1,
            highlightbackground=COLORS["border"],
        )
        editor_wrap.grid(row=3, column=0, sticky="nsew")
        editor_wrap.columnconfigure(0, weight=1)
        editor_wrap.rowconfigure(0, weight=1)
        self.lyrics_editor = tk.Text(
            editor_wrap,
            height=11,
            wrap="word",
            undo=True,
            bg=COLORS["field"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            selectbackground=COLORS["accent"],
            selectforeground=COLORS["white"],
            relief="flat",
            borderwidth=0,
            padx=12,
            pady=10,
            font=FONTS["body"],
        )
        scrollbar = ttk.Scrollbar(editor_wrap, orient="vertical", command=self.lyrics_editor.yview)
        self.lyrics_editor.configure(yscrollcommand=scrollbar.set)
        self.lyrics_editor.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.lyrics_controls = [
            self.load_lyrics_button,
            self.recognize_lyrics_button,
            self.save_lyrics_button,
            self.lyrics_format,
            self.lyrics_language,
            self.overwrite_lyrics_check,
        ]

    def _build_processing(self, parent):
        frame = self._section(parent, "processing", 0, 0, sticky="ew", pady=(0, SPACING["md"]))
        frame.columnconfigure(1, weight=1)
        stages = ttk.Frame(frame, style="Surface.TFrame")
        stages.grid(row=0, column=0, columnspan=3, sticky="w")
        stage_label = self._localize(ttk.Label(stages, style="SurfaceSecondary.TLabel"), "stages")
        stage_label.pack(side=tk.LEFT, padx=(0, SPACING["md"]))
        for key, variable in (
            ("stage_audio", self.app.process_audio_var),
            ("stage_metadata", self.app.process_metadata_var),
            ("stage_lyrics", self.app.process_lyrics_var),
            ("stage_cover", self.app.process_cover_var),
        ):
            check = self._localize(
                SquareCheckbutton(stages, variable, fixed_width=105), key
            )
            check.pack(side=tk.LEFT, padx=(0, SPACING["md"]))
        actions = ttk.Frame(frame, style="Surface.TFrame")
        actions.grid(row=1, column=2, sticky="e", pady=(SPACING["sm"], 0))
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
        self.progress.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(0, SPACING["lg"]), pady=(SPACING["sm"], 0))

    def _build_log(self, parent):
        frame = self._section(parent, "log", 1, 0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        actions = ttk.Frame(frame, style="Surface.TFrame")
        actions.grid(row=0, column=0, sticky="e", pady=(0, SPACING["sm"]))
        self.copy_log_button = self._localize(
            ttk.Button(actions, command=self.app.copy_log), "copy_log"
        )
        self.clear_log_button = self._localize(
            ttk.Button(actions, command=self.app.clear_log), "clear_log"
        )
        self.copy_log_button.pack(side=tk.LEFT, padx=(0, SPACING["sm"]))
        self.clear_log_button.pack(side=tk.LEFT)
        log_wrap = tk.Frame(
            frame,
            bg=COLORS["log"],
            highlightthickness=1,
            highlightbackground=COLORS["border"],
        )
        log_wrap.grid(row=1, column=0, sticky="nsew")
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
            state=tk.DISABLED,
        )
        scrollbar = ttk.Scrollbar(log_wrap, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)
        self.log.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_menu = tk.Menu(self.log, tearoff=False)
        self.log_menu.add_command(label=self.app.t("copy"), command=self.app.copy_log_selection)
        self.log_menu.add_command(label=self.app.t("select_all"), command=self.app.select_all_log)
        self.log.bind("<Button-3>", self._show_log_menu)

    def update_dependencies(self):
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
        self.cover_detail_combo.configure(values=self.app.cover_choice_values("detail"))
        self.cover_engine_combo.configure(values=self.app.cover_choice_values("engine"))
        self.audio_profile_combo.configure(values=self.app.audio_profile_values())
        self.log_menu.entryconfigure(0, label=self.app.t("copy"))
        self.log_menu.entryconfigure(1, label=self.app.t("select_all"))
        if self.busy:
            self.run_button.configure(text=self.app.t("processing_busy"))

    def get_lyrics_text(self):
        return self.lyrics_editor.get("1.0", tk.END).strip()

    def set_lyrics_text(self, text):
        self.lyrics_editor.delete("1.0", tk.END)
        self.lyrics_editor.insert("1.0", text)

    def set_lyrics_busy(self, busy):
        state = tk.DISABLED if busy else tk.NORMAL
        self.load_lyrics_button.configure(state=state)
        self.recognize_lyrics_button.configure(state=state)
        self.save_lyrics_button.configure(state=state)
        self.lyrics_format.configure(state="disabled" if busy else "readonly")
        self.lyrics_language.configure(state="disabled" if busy else "readonly")
        self.overwrite_lyrics_check.configure(state=state)

    def show_cover_preview(self, path):
        image = Image.open(path).convert("RGB")
        image.thumbnail((220, 220), Image.Resampling.LANCZOS)
        self._cover_preview_photo = ImageTk.PhotoImage(image)
        self.cover_preview_image.configure(image=self._cover_preview_photo, text="")

    def set_cover_preview_busy(self, busy):
        state = tk.DISABLED if busy else tk.NORMAL
        is_m2p = self.app.cover_choice("engine", self.app.cover_engine_var.get()) == "music2picture_v2"
        self.cover_quick_button.configure(state=tk.NORMAL if not busy and is_m2p else tk.DISABLED)
        self.cover_preview_button.configure(state=state)
        self.cover_variant_button.configure(state=state)

    def set_audio_preview_ready(self, ready):
        state = tk.NORMAL if ready else tk.DISABLED
        self.audio_original_button.configure(state=state)
        self.audio_processed_button.configure(state=state)
        self.audio_stop_button.configure(state=state)

    def set_audio_recommendation_ready(self, ready):
        self.audio_apply_button.configure(state=tk.NORMAL if ready else tk.DISABLED)

    def set_audio_task_busy(self, busy):
        state = tk.DISABLED if busy else tk.NORMAL
        self.audio_analyze_button.configure(state=state)
        self.audio_preview_button.configure(state=state)

    def update_engine_dependencies(self):
        is_ai = self.app.cover_choice("engine", self.app.cover_engine_var.get()) == "ai"
        self.model_button.configure(state=tk.NORMAL if is_ai and not self.busy else tk.DISABLED)
        self.cover_quick_button.configure(state=tk.DISABLED if is_ai or self.busy else tk.NORMAL)

    def set_description_results(self, records):
        mapping = {}
        for record in records:
            path = Path(record.get("path", ""))
            label = f"{path.name}  |  {path.parent.name}"
            suffix = 2
            unique = label
            while unique in mapping:
                unique = f"{label} ({suffix})"
                suffix += 1
            mapping[unique] = record
        self.description_records = mapping
        values = tuple(mapping)
        self.description_track_combo.configure(values=values)
        current = self.app.description_track_var.get()
        if current not in mapping:
            self.app.description_track_var.set(values[0] if values else "")
        self.show_selected_description()

    def selected_description_path(self):
        record = self.description_records.get(self.app.description_track_var.get())
        return record.get("path", "") if record else ""

    def show_selected_description(self):
        record = self.description_records.get(self.app.description_track_var.get(), {})
        description = record.get("song_description", "")
        brief = record.get("visual_brief", "")
        text = description + (("\n\n" + brief) if description and brief else brief)
        self.description_text.configure(state=tk.NORMAL)
        self.description_text.delete("1.0", tk.END)
        self.description_text.insert("1.0", text)
        self.description_text.configure(state=tk.DISABLED)

    def _show_log_menu(self, event):
        self.log.focus_set()
        try:
            self.log_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.log_menu.grab_release()

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
        state = tk.DISABLED if busy else tk.NORMAL
        self.description_generate_button.configure(state=state)
        self.description_regenerate_button.configure(state=state)
        self.update_engine_dependencies()
        self.stop_button.configure(state=tk.NORMAL if busy else tk.DISABLED)
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()
