import os
import math
import queue
import sys
import threading
import traceback
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import psutil
from PIL import Image, ImageTk

import easy_music_process
import music_metadata
import music2picture
from cover_engine import ImageModelManager
from lyrics_engine import LyricsResult, LyricsService, TranscriptSegment, save_lyrics
from ui.dialogs import AdditionalMetadataDialog, AdvancedAudioDialog
from ui.i18n import APP_NAMES, I18N
from ui.layout import SonicForgeView
from ui.model_manager_dialog import ImageModelManagerDialog
from ui.theme import COLORS, FONTS, SIZES, SPACING, configure_styles
from ui.windowing import show_centered


AUDIO_FILE_TYPES = [
    ("Audio files", "*.mp3 *.flac *.wav *.m4a *.aac *.ogg *.opus *.wma"),
    ("All files", "*.*"),
]

COVER_CHOICES = {
    "engine": {
        "ru": {"AI-обложка": "ai", "Music2Picture v2": "music2picture_v2"},
        "en": {"AI Cover Generation": "ai", "Music2Picture v2": "music2picture_v2"},
    },
    "mood": {
        "ru": {"Автоматически": "auto", "Спокойное": "calm", "Меланхоличное": "melancholic", "Энергичное": "energetic", "Напряжённое": "intense", "Романтичное": "romantic"},
        "en": {"Automatic": "auto", "Calm": "calm", "Melancholic": "melancholic", "Energetic": "energetic", "Intense": "intense", "Romantic": "romantic"},
    },
    "detail": {
        "ru": {"Быстрое": "simple", "Высокое": "balanced", "Максимальное": "rich"},
        "en": {"Fast": "simple", "High": "balanced", "Maximum": "rich"},
    },
}

AUDIO_PROFILE_CHOICES = {
    "ru": {
        "Сбалансированный": "balanced",
        "Сохранить характер": "preserve",
        "Громче и плотнее": "dense",
        "Чистый звук": "clean",
        "Больше баса": "bass",
        "Ярче и подробнее": "bright",
        "Шире": "wide",
        "Своя настройка": "custom",
    },
    "en": {
        "Balanced": "balanced",
        "Preserve character": "preserve",
        "Louder and denser": "dense",
        "Clean sound": "clean",
        "More bass": "bass",
        "Brighter and clearer": "bright",
        "Wider": "wide",
        "Custom": "custom",
    },
}

AUDIO_OPTION_CHOICES = {
    "denoise": {
        "ru": {"Выкл.": "off", "Авто": "auto", "Вручную": "manual"},
        "en": {"Off": "off", "Auto": "auto", "Manual": "manual"},
    },
    "sample_rate": {
        "ru": {"Как в оригинале": "source", "44,1 kHz": "44100", "48 kHz": "48000"},
        "en": {"As source": "source", "44.1 kHz": "44100", "48 kHz": "48000"},
    },
    "channels": {
        "ru": {"Как в оригинале": "source", "Моно": "1", "Стерео": "2"},
        "en": {"As source": "source", "Mono": "1", "Stereo": "2"},
    },
    "quality": {
        "ru": {"Максимальное": "maximum", "Высокое": "high", "Среднее": "medium"},
        "en": {"Maximum": "maximum", "High": "high", "Medium": "medium"},
    },
}


def resource_path(relative_path):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative_path


def configure_bundled_ffmpeg():
    ffmpeg_dir = resource_path("ffmpeg")
    if ffmpeg_dir.exists():
        os.environ["PATH"] = str(ffmpeg_dir) + os.pathsep + os.environ.get("PATH", "")


def enable_high_dpi():
    if sys.platform != "win32":
        return
    try:
        import ctypes

        try:
            if not ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
                raise ctypes.WinError()
        except Exception:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


class QueueWriter:
    def __init__(self, log_queue):
        self.log_queue = log_queue

    def write(self, text):
        if text:
            self.log_queue.put(text)

    def flush(self):
        pass


class SonicForgeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        self.language = "ru"
        self.log_queue = queue.Queue()
        self.worker = None
        self.cancel_event = threading.Event()
        self.advanced_dialog = None
        self.metadata_dialog = None
        self.model_dialog = None
        self.last_cover_path = None
        self.image_model_manager = ImageModelManager()
        self.lyrics_result = None
        self._undo_history = {}
        self._create_variables()
        self._configure_window()
        self.style = configure_styles(self)
        self._configure_fonts()
        self.header_image = self._load_header_image()
        self.view = SonicForgeView(self, self, self.header_image)
        self.view.update_dependencies()
        self._bind_shortcuts()
        self.write_log(self.t("log_ready") + "\n")
        self._show_initial_window()
        self._log_after_id = self.after(100, self._drain_log_queue)
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _create_variables(self):
        self.source_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.title_var = tk.StringVar()
        self.genre_var = tk.StringVar()
        self.artist_var = tk.StringVar()
        self.album_var = tk.StringVar()
        self.album_artist_var = tk.StringVar()
        self.composer_var = tk.StringVar()
        self.date_var = tk.StringVar()
        self.track_var = tk.StringVar()
        self.disc_var = tk.StringVar()
        self.comment_var = tk.StringVar()
        self.publisher_var = tk.StringVar()
        self.copyright_var = tk.StringVar()
        self.lyrics_var = tk.StringVar()
        self.overwrite_genre_var = tk.BooleanVar(value=False)
        self.overwrite_all_metadata_var = tk.BooleanVar(value=False)

        self.integrated_lufs_var = tk.DoubleVar(value=-14.0)
        self.true_peak_var = tk.DoubleVar(value=-1.5)
        self.lra_var = tk.DoubleVar(value=11.0)
        self.final_gain_var = tk.DoubleVar(value=1.0)
        self.denoise_var = tk.BooleanVar(value=False)
        self.denoise_mode_var = tk.StringVar(value="Авто")
        self.auto_denoise_var = tk.BooleanVar(value=True)
        self.denoise_strength_var = tk.DoubleVar(value=4.0)
        self.limiter_var = tk.BooleanVar(value=True)
        self.bass_gain_var = tk.DoubleVar(value=0.0)
        self.mid_gain_var = tk.DoubleVar(value=0.0)
        self.treble_gain_var = tk.DoubleVar(value=0.0)
        self.highpass_enabled_var = tk.BooleanVar(value=False)
        self.lowpass_enabled_var = tk.BooleanVar(value=False)
        self.highpass_hz_var = tk.DoubleVar(value=40.0)
        self.lowpass_hz_var = tk.DoubleVar(value=18000.0)
        self.stereo_width_var = tk.DoubleVar(value=1.0)
        self.compressor_var = tk.BooleanVar(value=False)
        self.compressor_threshold_var = tk.DoubleVar(value=-18.0)
        self.compressor_ratio_var = tk.DoubleVar(value=3.0)
        self.compressor_attack_var = tk.DoubleVar(value=20.0)
        self.compressor_release_var = tk.DoubleVar(value=250.0)
        self.compressor_makeup_var = tk.DoubleVar(value=0.0)
        self.pitch_semitones_var = tk.DoubleVar(value=0.0)
        self.playback_speed_var = tk.DoubleVar(value=1.0)
        self.reverb_mix_var = tk.DoubleVar(value=0.0)
        self.fade_in_var = tk.DoubleVar(value=0.0)
        self.fade_out_var = tk.DoubleVar(value=0.0)
        self.sample_rate_var = tk.StringVar(value="Как в оригинале")
        self.channels_var = tk.StringVar(value="Как в оригинале")
        self.mp3_quality_var = tk.StringVar(value="Максимальное")
        self.audio_profile_var = tk.StringVar(value="Сбалансированный")
        self.audio_intensity_var = tk.DoubleVar(value=50.0)
        self.loudness_macro_var = tk.DoubleVar(value=0.0)
        self.character_macro_var = tk.DoubleVar(value=0.0)
        self.bass_macro_var = tk.DoubleVar(value=0.0)
        self.space_macro_var = tk.DoubleVar(value=0.0)
        self.audio_analysis_var = tk.StringVar(value=self.t("audio_analysis_empty"))
        self.audio_analysis_data = None
        self.audio_recommended_profile = None
        self.audio_warning_var = tk.StringVar(value="")
        self.audio_preview_paths = None

        self.seed_var = tk.StringVar()
        self.cover_size_var = tk.IntVar(value=1000)
        self.cover_engine_var = tk.StringVar(value="AI-обложка")
        self.cover_detail_var = tk.StringVar(value="Быстрое")
        self.cover_mood_var = tk.StringVar(value="Автоматически")
        self.cover_title_var = tk.BooleanVar(value=True)
        self.cover_artist_var = tk.BooleanVar(value=True)
        self.cover_provider_status_var = tk.StringVar()
        self.description_track_var = tk.StringVar()
        self.description_status_var = tk.StringVar()
        self._refresh_model_status()
        self.embed_cover_var = tk.BooleanVar(value=True)
        self.no_change_cover_var = tk.BooleanVar(value=False)
        self.process_metadata_var = tk.BooleanVar(value=True)
        self.process_audio_var = tk.BooleanVar(value=True)
        self.process_lyrics_var = tk.BooleanVar(value=True)
        self.process_cover_var = tk.BooleanVar(value=True)
        self.lyrics_format_var = tk.StringVar(value="txt")
        self.lyrics_language_var = tk.StringVar(value="auto")
        self.overwrite_lyrics_var = tk.BooleanVar(value=False)
        self.use_lyrics_for_cover_var = tk.BooleanVar(value=True)
        self.lyrics_status_key = "lyrics_status_empty"
        self.lyrics_status_args = {}
        self.lyrics_status_var = tk.StringVar(value=self.t(self.lyrics_status_key))

    def _configure_window(self):
        self.title(self.app_name())
        self.configure(bg=COLORS["bg"])
        icon_path = resource_path("assets/sonic_forge_mark.ico")
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except tk.TclError:
                pass

    def _show_initial_window(self):
        self.update_idletasks()
        required_width = self.winfo_reqwidth()
        required_height = self.winfo_reqheight()
        startup_height = required_height + SIZES["window_height_reserve"]
        minimum_width = max(
            required_width,
            math.ceil(startup_height * SIZES["minimum_window_aspect"]),
        )
        minimum_remainder = (minimum_width - SPACING["lg"] * 2) % len(
            self.view.tab_buttons
        )
        if minimum_remainder:
            minimum_width += len(self.view.tab_buttons) - minimum_remainder
        self.minsize(minimum_width, required_height)
        startup_width = minimum_width + SIZES["window_width_reserve"]
        tab_content_width = startup_width - SPACING["lg"] * 2
        remainder = tab_content_width % len(self.view.tab_buttons)
        if remainder:
            startup_width += len(self.view.tab_buttons) - remainder
        self.startup_geometry = show_centered(
            self,
            startup_width,
            startup_height,
        )
        try:
            import pyi_splash

            pyi_splash.close()
        except ImportError:
            pass

    def _configure_fonts(self):
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont"):
            tkfont.nametofont(name).configure(family="Segoe UI", size=10)
        tkfont.nametofont("TkHeadingFont").configure(family="Segoe UI Semibold", size=11)
        self.option_add("*TCombobox*Listbox.background", COLORS["elevated"])
        self.option_add("*TCombobox*Listbox.foreground", COLORS["text"])
        self.option_add("*TCombobox*Listbox.selectBackground", COLORS["accent"])
        self.option_add("*TCombobox*Listbox.font", FONTS["body"])

    def _load_header_image(self):
        path = resource_path("assets/sonic_forge_mark.png")
        image = Image.open(path).convert("RGBA").resize((48, 48), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image)

    def app_name(self):
        return APP_NAMES[self.language]

    def t(self, key):
        return I18N[self.language].get(key, key)

    def cover_choice_values(self, kind):
        return tuple(COVER_CHOICES[kind][self.language])

    def audio_profile_values(self):
        return tuple(AUDIO_PROFILE_CHOICES[self.language])

    def audio_option_values(self, kind):
        return tuple(AUDIO_OPTION_CHOICES[kind][self.language])

    def audio_option_key(self, kind, value=None):
        value = value if value is not None else {
            "denoise": self.denoise_mode_var,
            "sample_rate": self.sample_rate_var,
            "channels": self.channels_var,
            "quality": self.mp3_quality_var,
        }[kind].get()
        for language in ("ru", "en"):
            if value in AUDIO_OPTION_CHOICES[kind][language]:
                return AUDIO_OPTION_CHOICES[kind][language][value]
        return value

    def audio_profile_key(self):
        value = self.audio_profile_var.get()
        for choices in AUDIO_PROFILE_CHOICES.values():
            if value in choices:
                return choices[value]
        return "balanced"

    def cover_choice(self, kind, value):
        for language in ("ru", "en"):
            mapping = COVER_CHOICES[kind][language]
            if value in mapping:
                return mapping[value]
        return value

    def _translate_cover_choices(self):
        for kind, variable in (
            ("engine", self.cover_engine_var),
            ("mood", self.cover_mood_var),
            ("detail", self.cover_detail_var),
        ):
            internal = self.cover_choice(kind, variable.get())
            display = next(
                label for label, value in COVER_CHOICES[kind][self.language].items()
                if value == internal
            )
            variable.set(display)

    def toggle_language(self):
        previous_language = self.language
        profile_key = self.audio_profile_key()
        audio_options = {
            kind: self.audio_option_key(kind)
            for kind in ("denoise", "sample_rate", "channels", "quality")
        }
        self.language = "en" if self.language == "ru" else "ru"
        self._translate_cover_choices()
        self.audio_profile_var.set(
            next(label for label, key in AUDIO_PROFILE_CHOICES[self.language].items() if key == profile_key)
        )
        for kind, key in audio_options.items():
            variable = {
                "denoise": self.denoise_mode_var,
                "sample_rate": self.sample_rate_var,
                "channels": self.channels_var,
                "quality": self.mp3_quality_var,
            }[kind]
            variable.set(next(label for label, value in AUDIO_OPTION_CHOICES[kind][self.language].items() if value == key))
        self.title(self.app_name())
        self.view.apply_language()
        if self.audio_analysis_data is None:
            self.audio_analysis_var.set(self.t("audio_analysis_empty"))
        else:
            self.audio_analysis_var.set(self._format_audio_analysis(*self.audio_analysis_data))
        self._refresh_model_status()
        self._refresh_lyrics_status()
        self._translate_idle_log(previous_language)
        if self.advanced_dialog and self.advanced_dialog.winfo_exists():
            self.advanced_dialog.apply_language()
        if self.metadata_dialog and self.metadata_dialog.winfo_exists():
            self.metadata_dialog.apply_language()
        if self.model_dialog and self.model_dialog.winfo_exists():
            self.model_dialog.apply_language()

    def choose_source_file(self):
        path = filedialog.askopenfilename(
            title=self.t("source_dialog_file"), filetypes=AUDIO_FILE_TYPES
        )
        if path:
            self.stop_audio_preview()
            self.source_var.set(path)
            self.audio_preview_paths = None
            self.view.set_audio_preview_ready(False)
            self.refresh_description_records()
            self.analyze_audio_settings(silent=True)

    def choose_source_folder(self):
        path = filedialog.askdirectory(title=self.t("source_dialog_folder"))
        if path:
            self.source_var.set(path)
            self.refresh_description_records()

    def choose_output_folder(self):
        path = filedialog.askdirectory(title=self.t("output_dialog_folder"))
        if path:
            self.output_var.set(path)

    def show_advanced_audio(self):
        if self.advanced_dialog and self.advanced_dialog.winfo_exists():
            self.advanced_dialog.focus_force()
            return
        self.advanced_dialog = AdvancedAudioDialog(self)

    def show_additional_metadata(self):
        if self.metadata_dialog and self.metadata_dialog.winfo_exists():
            self.metadata_dialog.focus_force()
            return
        self.metadata_dialog = AdditionalMetadataDialog(self)

    def manage_image_model(self, first_use=False):
        if self.model_dialog and self.model_dialog.winfo_exists():
            self.model_dialog.focus_force()
            return self.model_dialog
        self.model_dialog = ImageModelManagerDialog(
            self,
            manager=self.image_model_manager,
            first_use=first_use,
        )
        self.wait_window(self.model_dialog)
        self.model_dialog = None
        self._refresh_model_status()
        return None

    def _refresh_model_status(self):
        if self.cover_choice("engine", self.cover_engine_var.get()) == "music2picture_v2":
            self.cover_provider_status_var.set(self.t("cover_engine_m2p_ready"))
            return
        status = self.image_model_manager.status()
        key = "cover_model_ready" if status.ready else "cover_model_missing"
        self.cover_provider_status_var.set(self.t(key))

    def _set_lyrics_status(self, key, **values):
        self.lyrics_status_key = key
        self.lyrics_status_args = values
        self._refresh_lyrics_status()

    def _refresh_lyrics_status(self):
        values = dict(self.lyrics_status_args)
        if "language" in values:
            values["language"] = self._display_language(values["language"])
        if "mixed" in values and isinstance(values["mixed"], tuple):
            values["mixed"] = (
                ", ".join(self._display_language(code) for code in values["mixed"])
                if values["mixed"]
                else self.t("lyrics_no")
            )
        if "quality" in values:
            values["quality"] = self.t(f"quality_{values['quality']}")
        self.lyrics_status_var.set(self.t(self.lyrics_status_key).format(**values))

    def _display_language(self, code):
        normalized = (code or "unknown").lower()
        key = {
            "ru": "language_name_ru",
            "en": "language_name_en",
            "en/latin": "language_name_en",
            "mixed": "language_name_mixed",
            "unknown": "language_name_unknown",
        }.get(normalized)
        return self.t(key) if key else code

    def _translate_idle_log(self, previous_language):
        current = self.view.log.get("1.0", "end-1c").strip()
        if current == I18N[previous_language]["log_ready"]:
            self.clear_log()
            self.write_log(self.t("log_ready") + "\n")

    def _cover_text_mode(self):
        if not self.cover_title_var.get():
            return "none"
        return "title_artist" if self.cover_artist_var.get() else "title"

    def load_metadata(self):
        source = Path(self.source_var.get().strip())
        if not source.is_file():
            messagebox.showerror(self.app_name(), self.t("metadata_single_file"))
            return
        try:
            tags = music_metadata.read_all_metadata(source)
        except Exception as exc:
            messagebox.showerror(self.app_name(), str(exc))
            return

        def first(*names):
            return next((tags[name] for name in names if tags.get(name)), "")

        values = {
            self.title_var: first("title"),
            self.genre_var: first("genre"),
            self.artist_var: first("artist"),
            self.album_var: first("album"),
            self.album_artist_var: first("album_artist", "albumartist"),
            self.composer_var: first("composer"),
            self.date_var: first("date", "year"),
            self.track_var: first("track", "tracknumber"),
            self.disc_var: first("disc", "discnumber"),
            self.comment_var: first("comment", "description"),
            self.publisher_var: first("publisher", "organization"),
            self.copyright_var: first("copyright"),
            self.lyrics_var: first("lyrics", "unsyncedlyrics"),
        }
        for variable, value in values.items():
            variable.set(value)
        self.write_log("\n" + self.t("metadata_loaded").format(name=source.name) + "\n")

    def clear_metadata(self):
        if not self._paths_ready():
            return
        if messagebox.askyesno(self.app_name(), self.t("clear_confirm")):
            self._run_process({"metadata"}, metadata_mode="clear")

    def _metadata_values(self):
        return {
            "artist": self.artist_var.get(),
            "album": self.album_var.get(),
            "album_artist": self.album_artist_var.get(),
            "composer": self.composer_var.get(),
            "date": self.date_var.get(),
            "track": self.track_var.get(),
            "disc": self.disc_var.get(),
            "comment": self.comment_var.get(),
            "publisher": self.publisher_var.get(),
            "copyright": self.copyright_var.get(),
            "lyrics": self.lyrics_var.get(),
        }

    def _parse_seed(self):
        text = self.seed_var.get().strip()
        return None if not text else int(text)

    def audio_profile_changed(self):
        presets = {
            "balanced": (0, 0, 0, 0),
            "preserve": (0, 0, 0, 0),
            "dense": (42, 5, 8, 0),
            "clean": (0, 12, 0, 0),
            "bass": (0, 0, 52, 0),
            "bright": (0, 55, 0, 0),
            "wide": (0, 0, 0, 55),
        }
        values = presets.get(self.audio_profile_key())
        if values:
            for variable, value in zip(
                (self.loudness_macro_var, self.character_macro_var, self.bass_macro_var, self.space_macro_var),
                values,
            ):
                variable.set(value)
        self._apply_audio_macros()

    def audio_macro_changed(self, _value=None):
        custom = next(label for label, key in AUDIO_PROFILE_CHOICES[self.language].items() if key == "custom")
        self.audio_profile_var.set(custom)
        self._apply_audio_macros()

    def auto_denoise_changed(self):
        mode = "auto" if self.auto_denoise_var.get() else "off"
        self.denoise_mode_var.set(
            next(
                label
                for label, value in AUDIO_OPTION_CHOICES["denoise"][self.language].items()
                if value == mode
            )
        )

    def denoise_mode_changed(self):
        self.auto_denoise_var.set(self.audio_option_key("denoise") == "auto")

    def _apply_audio_macros(self):
        profile = self.audio_profile_key()
        strength = max(0.0, min(1.0, self.audio_intensity_var.get() / 100.0))
        self.integrated_lufs_var.set(round(-14.0 + self.loudness_macro_var.get() * 0.04 * strength, 1))
        self.bass_gain_var.set(round(self.bass_macro_var.get() * 0.04 * strength, 2))
        self.treble_gain_var.set(round(self.character_macro_var.get() * 0.035 * strength, 2))
        self.stereo_width_var.set(round(1.0 + self.space_macro_var.get() * 0.0035 * strength, 2))
        if profile != "custom":
            self.compressor_var.set(profile == "dense")
            if profile == "dense":
                self.compressor_threshold_var.set(round(-14.0 - 8.0 * strength, 1))
                self.compressor_ratio_var.set(round(1.4 + 1.8 * strength, 1))
            self.auto_denoise_var.set(profile not in {"preserve"})
            key = "auto" if self.auto_denoise_var.get() else "off"
            self.denoise_mode_var.set(
                next(label for label, value in AUDIO_OPTION_CHOICES["denoise"][self.language].items() if value == key)
            )
        self.refresh_audio_warning()

    def _audio_processing_values(self):
        self._apply_audio_macros()
        mode = self.audio_option_key("denoise")
        return {
            "integrated_lufs": float(self.integrated_lufs_var.get()),
            "true_peak": float(self.true_peak_var.get()),
            "lra": float(self.lra_var.get()),
            "final_gain": float(self.final_gain_var.get()),
            "denoise": mode == "manual",
            "denoise_mode": mode,
            "denoise_strength": float(self.denoise_strength_var.get()),
            "limiter": bool(self.limiter_var.get()),
            "bass_gain": float(self.bass_gain_var.get()),
            "mid_gain": float(self.mid_gain_var.get()),
            "treble_gain": float(self.treble_gain_var.get()),
            "highpass_hz": float(self.highpass_hz_var.get()) if self.highpass_enabled_var.get() else 0.0,
            "lowpass_hz": float(self.lowpass_hz_var.get()) if self.lowpass_enabled_var.get() else 0.0,
            "stereo_width": float(self.stereo_width_var.get()),
            "compressor": bool(self.compressor_var.get()),
            "compressor_threshold": float(self.compressor_threshold_var.get()),
            "compressor_ratio": float(self.compressor_ratio_var.get()),
            "compressor_attack": float(self.compressor_attack_var.get()),
            "compressor_release": float(self.compressor_release_var.get()),
            "compressor_makeup": float(self.compressor_makeup_var.get()),
            "pitch_semitones": float(self.pitch_semitones_var.get()),
            "playback_speed": float(self.playback_speed_var.get()),
            "reverb_mix": float(self.reverb_mix_var.get()),
            "fade_in": float(self.fade_in_var.get()),
            "fade_out": float(self.fade_out_var.get()),
            "sample_rate": self.audio_option_key("sample_rate"),
            "channels": self.audio_option_key("channels"),
            "mp3_quality": self.audio_option_key("quality"),
        }

    def refresh_audio_warning(self):
        strong = (
            abs(float(self.bass_gain_var.get())) > 8
            or abs(float(self.treble_gain_var.get())) > 8
            or float(self.stereo_width_var.get()) > 1.65
            or float(self.compressor_ratio_var.get()) > 10
        )
        self.audio_warning_var.set(self.t("audio_strong_warning") if strong else "")

    def analyze_audio_settings(self, silent=False):
        if self.worker and self.worker.is_alive():
            return
        source = Path(self.source_var.get().strip())
        if not source.is_file() or source.suffix.lower() not in music_metadata.AUDIO_EXTENSIONS:
            if not silent:
                messagebox.showerror(self.app_name(), self.t("audio_single_file"))
            return
        self.audio_analysis_data = None
        self.audio_recommended_profile = None
        self.view.set_audio_recommendation_ready(False)
        self.audio_analysis_var.set(self.t("audio_analysis_working"))
        self.view.set_audio_task_busy(True)
        self.worker = threading.Thread(target=self._audio_analysis_worker, args=(source,), daemon=True)
        self.worker.start()

    def apply_audio_recommendation(self):
        if not self.audio_recommended_profile:
            return
        label = next(
            text
            for text, key in AUDIO_PROFILE_CHOICES[self.language].items()
            if key == self.audio_recommended_profile
        )
        self.audio_profile_var.set(label)
        self.audio_profile_changed()

    def _audio_analysis_worker(self, source):
        try:
            from music2picture_v2 import analyze_audio_file

            analysis = analyze_audio_file(source)
            noise = easy_music_process.normalize_music_file.detect_stationary_noise(source)
            self.log_queue.put(("__AUDIO_ANALYSIS__", analysis, noise))
        except Exception as exc:
            self.log_queue.put(("__ERROR__", str(exc)))
        finally:
            self.log_queue.put(("__DONE__", None))

    def create_audio_preview(self):
        if self.worker and self.worker.is_alive():
            return
        source = self._single_audio_source()
        if source is None:
            return
        values = self._audio_processing_values()
        self.view.set_audio_task_busy(True)
        self.view.set_audio_preview_ready(False)
        self.worker = threading.Thread(target=self._audio_preview_worker, args=(source, values), daemon=True)
        self.worker.start()

    def _audio_preview_worker(self, source, values):
        try:
            module = easy_music_process.normalize_music_file
            denoise = values["denoise"]
            if values["denoise_mode"] == "auto":
                denoise = module.detect_stationary_noise(source)["apply"]
            _args, rate, _channels = module.output_audio_options(
                source, values["sample_rate"], values["channels"], values["mp3_quality"]
            )
            filters = module.build_preprocessing_filters(
                **{key: value for key, value in values.items() if key in {
                    "denoise_strength", "bass_gain", "mid_gain", "treble_gain", "highpass_hz",
                    "lowpass_hz", "stereo_width", "compressor", "compressor_threshold",
                    "compressor_ratio", "compressor_attack", "compressor_release", "compressor_makeup",
                    "pitch_semitones", "playback_speed", "reverb_mix", "fade_in", "fade_out",
                }},
                denoise=denoise,
                duration=module.probe_duration(source),
                processing_sample_rate=rate,
                source_sample_rate=module.source_audio_properties(source)["sample_rate"],
                output_sample_rate=rate,
                source_channels=module.source_audio_properties(source)["channels"],
                output_channels=_channels,
            )
            directory = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "SonicForge" / "audio_preview"
            paths = module.create_ab_preview(source, directory, filters, cancel_event=self.cancel_event)
            self.log_queue.put(("__AUDIO_PREVIEW__", paths))
        except Exception as exc:
            self.log_queue.put(("__ERROR__", str(exc)))
        finally:
            self.log_queue.put(("__DONE__", None))

    def play_audio_preview(self, processed=False):
        if not self.audio_preview_paths:
            return
        try:
            import winsound

            winsound.PlaySound(
                str(self.audio_preview_paths[1 if processed else 0]),
                winsound.SND_FILENAME | winsound.SND_ASYNC,
            )
        except (ImportError, RuntimeError, OSError):
            pass

    @staticmethod
    def stop_audio_preview():
        try:
            import winsound

            winsound.PlaySound(None, winsound.SND_PURGE)
        except (ImportError, RuntimeError, OSError):
            pass

    def _process_kwargs(self):
        kwargs = {
            "source": self.source_var.get().strip(),
            "output": self.output_var.get().strip(),
            "title": self.title_var.get().strip() or None,
            "genre": self.genre_var.get().strip() or None,
            "overwrite_genre": bool(self.overwrite_genre_var.get()),
            "overwrite_all_metadata": bool(self.overwrite_all_metadata_var.get()),
            "extra_metadata": self._metadata_values(),
            "cover_seed": self._parse_seed(),
            "cover_engine": self.cover_choice("engine", self.cover_engine_var.get()),
            "cover_size": int(self.cover_size_var.get()),
            "cover_detail": self.cover_choice("detail", self.cover_detail_var.get()),
            "cover_text_mode": self._cover_text_mode(),
            "cover_mood": self.cover_choice("mood", self.cover_mood_var.get()),
            "embed_cover": bool(self.embed_cover_var.get()),
            "change_cover": not bool(self.no_change_cover_var.get()),
            "cover_lyrics_text": self.view.get_lyrics_text()
            if self.use_lyrics_for_cover_var.get()
            else "",
            "lyrics_format": self.lyrics_format_var.get(),
            "lyrics_language": self.lyrics_language_var.get(),
            "overwrite_lyrics": bool(self.overwrite_lyrics_var.get()),
        }
        kwargs.update(self._audio_processing_values())
        return kwargs

    def _paths_ready(self):
        if self.source_var.get().strip() and self.output_var.get().strip():
            return True
        messagebox.showerror(self.app_name(), self.t("missing_paths"))
        return False

    def run_selected_steps(self):
        steps = {
            name
            for name, variable in (
                ("audio", self.process_audio_var),
                ("metadata", self.process_metadata_var),
                ("lyrics", self.process_lyrics_var),
                ("cover", self.process_cover_var),
            )
            if variable.get()
        }
        if not steps:
            messagebox.showerror(self.app_name(), self.t("missing_steps"))
            return
        self._run_process(steps)

    def _run_process(self, steps, metadata_mode=None):
        if self.worker and self.worker.is_alive():
            return
        if not self._paths_ready():
            return
        try:
            kwargs = self._process_kwargs()
        except (ValueError, tk.TclError):
            messagebox.showerror(self.app_name(), self.t("bad_seed"))
            return
        kwargs["process_steps"] = set(steps)
        kwargs["metadata_mode"] = metadata_mode or (
            "replace" if self.overwrite_all_metadata_var.get() else "update"
        )
        self.cancel_event.clear()
        kwargs["cancel_event"] = self.cancel_event
        self.view.set_busy(True)
        self.write_log("\n" + self.t("run_started") + "\n")
        self.worker = threading.Thread(target=self._process_worker, args=(kwargs,), daemon=True)
        self.worker.start()

    def _process_worker(self, kwargs):
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout = QueueWriter(self.log_queue)
        sys.stderr = QueueWriter(self.log_queue)
        try:
            easy_music_process.process_music(**kwargs)
            result_key = "run_stopped" if self.cancel_event.is_set() else "run_finished"
            self.log_queue.put(("__MESSAGE__", result_key))
        except Exception:
            if self.cancel_event.is_set():
                self.log_queue.put(("__MESSAGE__", "run_stopped"))
            else:
                self.log_queue.put("\n" + self.t("error") + "\n")
                self.log_queue.put(traceback.format_exc())
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr
            self.log_queue.put(("__DONE__", None))

    def load_existing_lyrics(self):
        source = self._single_audio_source()
        if source is None:
            return
        try:
            result = LyricsService(metadata_reader=music_metadata.read_all_metadata).load_existing(source)
        except Exception as exc:
            messagebox.showerror(self.app_name(), str(exc))
            return
        if result is None:
            messagebox.showinfo(self.app_name(), self.t("lyrics_not_found"))
            return
        self._apply_lyrics_result(result)

    def recognize_lyrics(self):
        if self.worker and self.worker.is_alive():
            return
        source = self._single_audio_source()
        if source is None:
            return
        self.cancel_event.clear()
        self.view.set_busy(True)
        self.view.set_lyrics_busy(True)
        self._set_lyrics_status("lyrics_status_recognizing")
        self.worker = threading.Thread(
            target=self._lyrics_worker,
            args=(source,),
            daemon=True,
        )
        self.worker.start()

    def preview_cover(self, new_variant=False, quick=False):
        if self.worker and self.worker.is_alive():
            return
        source = self._single_audio_source()
        if source is None:
            return
        engine = self.cover_choice("engine", self.cover_engine_var.get())
        try:
            seed = self._parse_seed()
            seed = 0 if seed is None else seed
            if new_variant:
                seed = (seed + 1) % 2_000_000_000
            self.seed_var.set(str(seed))
            size = 384 if quick else int(self.cover_size_var.get())
        except (ValueError, tk.TclError):
            messagebox.showerror(self.app_name(), self.t("bad_seed"))
            return
        output = self.output_var.get().strip()
        if quick:
            cover_dir = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "SonicForge" / "cover_preview"
        else:
            cover_dir = Path(output).expanduser() / "covers" if output else source.parent
        suffix = f"_{seed}" if new_variant else ""
        preview_path = cover_dir / f"{source.stem}_cover_{size}{suffix}.png"
        lyrics_text = self.view.get_lyrics_text() if self.use_lyrics_for_cover_var.get() else ""
        detail = self.cover_choice("detail", self.cover_detail_var.get())
        text_mode = self._cover_text_mode()
        mood = self.cover_choice("mood", self.cover_mood_var.get())
        self.cancel_event.clear()
        self.view.set_busy(True)
        self.view.set_cover_preview_busy(True)
        self.worker = threading.Thread(
            target=self._cover_preview_worker,
            args=(
                source,
                preview_path,
                size,
                seed,
                lyrics_text,
                detail,
                text_mode,
                mood,
                engine,
                bool(self.embed_cover_var.get()),
                quick,
            ),
            daemon=True,
        )
        self.worker.start()

    def _cover_preview_worker(
        self, source, preview_path, size, seed, lyrics_text, detail, text_mode, mood, engine, embed, quick
    ):
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout = QueueWriter(self.log_queue)
        sys.stderr = QueueWriter(self.log_queue)
        try:
            music2picture.make_cover(
                source,
                preview_path,
                size=size,
                seed=seed,
                lyrics_text=lyrics_text,
                detail=detail,
                text_mode=text_mode,
                mood_override=mood,
                engine=engine,
                cancel_event=self.cancel_event,
                candidate_limit=1,
                preview=quick,
            )
            embedded = bool(not quick and embed and music2picture.embed_cover(source, preview_path))
            self.log_queue.put(("__COVER_PREVIEW__", preview_path, embedded, embed and not quick))
        except Exception as exc:
            if not self.cancel_event.is_set():
                self.log_queue.put(("__ERROR__", str(exc)))
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr
            self.log_queue.put(("__DONE__", None))

    def cover_engine_changed(self):
        self._refresh_model_status()
        self.view.update_engine_dependencies()

    def refresh_description_records(self):
        source = self.source_var.get().strip()
        if not source:
            self.view.set_description_results([])
            return
        from music2picture_v2 import DescriptionStore

        self.view.set_description_results(DescriptionStore().list_for_source(source))

    def generate_song_descriptions(self, regenerate=False, selected_only=False):
        if self.worker and self.worker.is_alive():
            return
        source = self.view.selected_description_path() if selected_only else self.source_var.get().strip()
        if not source or not Path(source).exists():
            messagebox.showerror(self.app_name(), self.t("missing_source"))
            return
        self.cancel_event.clear()
        self.view.set_busy(True)
        self.description_status_var.set(self.t("description_working"))
        output = self.output_var.get().strip() or None
        self.worker = threading.Thread(
            target=self._description_worker,
            args=(source, output, regenerate),
            daemon=True,
        )
        self.worker.start()

    def _description_worker(self, source, output, regenerate):
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout = QueueWriter(self.log_queue)
        sys.stderr = QueueWriter(self.log_queue)
        try:
            results = music2picture.generate_text_descriptions(
                source,
                output=output,
                regenerate=regenerate,
                cancel_event=self.cancel_event,
                progress=lambda index, total, path, stage: print(
                    f"[{index}/{total}] {path.name}: {stage}"
                ),
            )
            self.log_queue.put(("__DESCRIPTION_RESULTS__", results))
        except Exception as exc:
            if not self.cancel_event.is_set():
                self.log_queue.put(("__ERROR__", str(exc)))
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr
            self.log_queue.put(("__DONE__", None))

    def _lyrics_worker(self, source):
        try:
            service = LyricsService(metadata_reader=music_metadata.read_all_metadata)
            result = service.recognize(
                source,
                cancel_event=self.cancel_event,
                progress=lambda stage: self.log_queue.put(("__LYRICS_PROGRESS__", stage)),
                language=self.lyrics_language_var.get(),
            )
            self.log_queue.put(("__LYRICS_RESULT__", result))
        except Exception as exc:
            if self.cancel_event.is_set():
                self.log_queue.put(("__MESSAGE__", "run_stopped"))
            else:
                self.log_queue.put(("__LYRICS_ERROR__", str(exc)))
        finally:
            self.log_queue.put(("__DONE__", None))

    def save_lyrics_file(self):
        source = self._single_audio_source()
        if source is None:
            return
        text = self.view.get_lyrics_text().strip()
        if not text:
            messagebox.showerror(self.app_name(), self.t("lyrics_empty"))
            return
        result = self._edited_lyrics_result(text)
        try:
            path = save_lyrics(source, result, self.lyrics_format_var.get())
        except Exception as exc:
            messagebox.showerror(self.app_name(), str(exc))
            return
        self.lyrics_result = result
        self.write_log("\n" + self.t("lyrics_saved").format(path=path) + "\n")
        messagebox.showinfo(self.app_name(), self.t("lyrics_saved").format(path=path))

    def _single_audio_source(self):
        source = Path(self.source_var.get().strip())
        if source.is_file() and source.suffix.lower() in music_metadata.AUDIO_EXTENSIONS:
            return source
        messagebox.showerror(self.app_name(), self.t("lyrics_single_file"))
        return None

    def _edited_lyrics_result(self, text):
        previous = self.lyrics_result
        if previous is None:
            return LyricsResult(text=text, source="manual")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        segments = previous.segments
        if segments and len(lines) == len(segments):
            segments = tuple(
                TranscriptSegment(segment.start, segment.end, line, segment.confidence)
                for segment, line in zip(segments, lines)
            )
        elif segments:
            segments = ()
        return LyricsResult(
            text=text,
            segments=segments,
            language=previous.language,
            language_confidence=previous.language_confidence,
            mixed_languages=previous.mixed_languages,
            quality=previous.quality,
            instrumental=previous.instrumental,
            source="edited",
        )

    def _apply_lyrics_result(self, result):
        self.lyrics_result = result
        self.view.set_lyrics_text(result.text)
        confidence = "-" if result.language_confidence is None else f"{result.language_confidence:.0%}"
        self._set_lyrics_status(
            "lyrics_status_result",
            language=result.language,
            confidence=confidence,
            mixed=result.mixed_languages,
            quality=result.quality,
        )

    def stop_processing(self):
        if not self.worker or not self.worker.is_alive() or self.cancel_event.is_set():
            return
        self.cancel_event.set()
        self.view.stop_button.configure(state=tk.DISABLED)
        threading.Thread(target=self._terminate_media_processes, daemon=True).start()

    def _terminate_media_processes(self):
        try:
            current = psutil.Process(os.getpid())
            processes = [
                process
                for process in current.children(recursive=True)
                if process.name().lower() in {"ffmpeg.exe", "ffprobe.exe", "sd-cli.exe"}
            ]
            for process in processes:
                try:
                    process.terminate()
                except psutil.Error:
                    pass
            _, alive = psutil.wait_procs(processes, timeout=1.5)
            for process in alive:
                try:
                    process.kill()
                except psutil.Error:
                    pass
        except psutil.Error:
            pass

    def _format_audio_analysis(self, analysis, noise):
        loudness = self.t("audio_value_normal")
        if analysis.rms_dbfs < -20:
            loudness = self.t("audio_value_quiet")
        elif analysis.rms_dbfs > -10:
            loudness = self.t("audio_value_loud")
        dynamics = self.t("audio_value_high") if analysis.relative_dynamic_range > 0.55 else self.t("audio_value_moderate")
        bass = self.t("audio_value_strong") if analysis.bass_energy > 0.42 else self.t("audio_value_balanced")
        highs = self.t("audio_value_bright") if analysis.brightness > 0.62 else self.t("audio_value_balanced")
        noise_text = self.t("audio_value_detected") if noise["apply"] else self.t("audio_value_not_detected")
        stereo = self.t("audio_value_wide") if self.stereo_width_var.get() > 1.08 else self.t("audio_value_original")
        recommendation = self.t("audio_recommend_minimal")
        if noise["apply"]:
            recommendation = self.t("audio_recommend_clean")
        elif analysis.rms_dbfs < -20:
            recommendation = self.t("audio_recommend_loudness")
        return self.t("audio_analysis_template").format(
            loudness=loudness,
            dynamics=dynamics,
            bass=bass,
            highs=highs,
            noise=noise_text,
            stereo=stereo,
            recommendation=recommendation,
        )

    def _drain_log_queue(self):
        try:
            while True:
                item = self.log_queue.get_nowait()
                if isinstance(item, tuple) and item[0] == "__DONE__":
                    self.view.set_busy(False)
                    self.view.set_audio_task_busy(False)
                    self.view.set_lyrics_busy(False)
                    self.view.set_cover_preview_busy(False)
                elif isinstance(item, tuple) and item[0] == "__MESSAGE__":
                    self.write_log("\n" + self.t(item[1]) + "\n")
                elif isinstance(item, tuple) and item[0] == "__LYRICS_RESULT__":
                    self._apply_lyrics_result(item[1])
                    self.write_log("\n" + self.t("lyrics_recognized") + "\n")
                elif isinstance(item, tuple) and item[0] == "__LYRICS_PROGRESS__":
                    self._set_lyrics_status("lyrics_status_recognizing")
                elif isinstance(item, tuple) and item[0] == "__LYRICS_ERROR__":
                    self._set_lyrics_status("lyrics_status_error")
                    messagebox.showerror(self.app_name(), item[1])
                elif isinstance(item, tuple) and item[0] == "__ERROR__":
                    messagebox.showerror(self.app_name(), item[1])
                elif isinstance(item, tuple) and item[0] == "__COVER_PREVIEW__":
                    self.write_log("\n" + self.t("cover_preview_ready").format(path=item[1]) + "\n")
                    if item[2]:
                        self.write_log(self.t("cover_embedded") + "\n")
                    elif item[3]:
                        self.write_log(self.t("cover_embed_unsupported") + "\n")
                    self.last_cover_path = Path(item[1])
                    self.view.show_cover_preview(item[1])
                elif isinstance(item, tuple) and item[0] == "__AUDIO_ANALYSIS__":
                    self.audio_analysis_data = (item[1], item[2])
                    if item[2]["apply"]:
                        self.audio_recommended_profile = "clean"
                    elif item[1].rms_dbfs < -20:
                        self.audio_recommended_profile = "balanced"
                    else:
                        self.audio_recommended_profile = "preserve"
                    summary = self._format_audio_analysis(item[1], item[2])
                    self.audio_analysis_var.set(summary)
                    self.view.set_audio_recommendation_ready(True)
                    self.write_log("\n" + summary + "\n")
                elif isinstance(item, tuple) and item[0] == "__AUDIO_PREVIEW__":
                    self.audio_preview_paths = item[1]
                    self.view.set_audio_preview_ready(True)
                    self.write_log("\n" + self.t("audio_preview_ready") + "\n")
                elif isinstance(item, tuple) and item[0] == "__DESCRIPTION_RESULTS__":
                    self.refresh_description_records()
                    errors = sum(result.status == "error" for result in item[1])
                    self.description_status_var.set(
                        self.t("description_done").format(count=len(item[1]) - errors, errors=errors)
                    )
                else:
                    self.write_log(item)
        except queue.Empty:
            pass
        self._log_after_id = self.after(100, self._drain_log_queue)

    def _close(self):
        if self.worker and self.worker.is_alive():
            self.cancel_event.set()
        if self._log_after_id is not None:
            try:
                self.after_cancel(self._log_after_id)
            except tk.TclError:
                pass
            self._log_after_id = None
        self.destroy()

    def write_log(self, text):
        self.view.log.configure(state=tk.NORMAL)
        self.view.log.insert(tk.END, text)
        self.view.log.see(tk.END)
        self.view.log.configure(state=tk.DISABLED)

    def clear_log(self):
        self.view.log.configure(state=tk.NORMAL)
        self.view.log.delete("1.0", tk.END)
        self.view.log.configure(state=tk.DISABLED)

    def copy_log(self):
        text = self.view.log.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(text)

    def copy_log_selection(self):
        try:
            text = self.view.log.get(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            return
        self.clipboard_clear()
        self.clipboard_append(text)

    def select_all_log(self):
        self.view.log.tag_add(tk.SEL, "1.0", "end-1c")
        self.view.log.mark_set(tk.INSERT, "1.0")
        self.view.log.see("1.0")

    def _bind_shortcuts(self):
        for sequence, callback in (
            ("<Control-a>", self._select_all),
            ("<Control-A>", self._select_all),
            ("<Control-c>", lambda event: self._edit_event(event, "<<Copy>>")),
            ("<Control-C>", lambda event: self._edit_event(event, "<<Copy>>")),
            ("<Control-x>", lambda event: self._edit_event(event, "<<Cut>>")),
            ("<Control-X>", lambda event: self._edit_event(event, "<<Cut>>")),
            ("<Control-v>", lambda event: self._edit_event(event, "<<Paste>>")),
            ("<Control-V>", lambda event: self._edit_event(event, "<<Paste>>")),
            ("<Control-z>", self._undo),
            ("<Control-Z>", self._undo),
        ):
            self.bind_all(sequence, callback, add="+")
        self.bind_all("<KeyPress>", self._before_edit, add="+")

    def _editable_widget(self):
        widget = self.focus_get()
        return widget if isinstance(widget, (tk.Entry, tk.Text, ttk.Entry, ttk.Spinbox, ttk.Combobox)) else None

    def _select_all(self, _event=None):
        widget = self._editable_widget()
        if widget is None:
            return None
        if isinstance(widget, tk.Text):
            widget.tag_add(tk.SEL, "1.0", tk.END)
            widget.mark_set(tk.INSERT, "1.0")
        else:
            widget.selection_range(0, tk.END)
            widget.icursor(tk.END)
        return "break"

    def _edit_event(self, _event, event_name):
        widget = self._editable_widget()
        if widget is None:
            return None
        if event_name in {"<<Cut>>", "<<Paste>>"} and not isinstance(widget, tk.Text):
            self._record_undo(widget)
        try:
            widget.event_generate(event_name)
        except tk.TclError:
            return None
        return "break"

    def _before_edit(self, event):
        if event.state & 0x4:
            return None
        widget = self._editable_widget()
        if widget is not None and not isinstance(widget, tk.Text):
            self._record_undo(widget)
        return None

    def _record_undo(self, widget):
        try:
            snapshot = (widget.get(), int(widget.index(tk.INSERT)))
        except (tk.TclError, ValueError):
            return
        history = self._undo_history.setdefault(widget, [])
        if not history or history[-1] != snapshot:
            history.append(snapshot)
            if len(history) > 100:
                del history[0]

    def _undo(self, _event=None):
        widget = self._editable_widget()
        if widget is None:
            return None
        if isinstance(widget, tk.Text):
            try:
                widget.edit_undo()
            except tk.TclError:
                pass
            return "break"
        history = self._undo_history.get(widget, [])
        if not history:
            return "break"
        text, cursor = history.pop()
        try:
            widget.delete(0, tk.END)
            widget.insert(0, text)
            widget.icursor(min(cursor, len(text)))
        except tk.TclError:
            pass
        return "break"


def main():
    enable_high_dpi()
    configure_bundled_ffmpeg()
    app = SonicForgeApp()
    app.mainloop()


if __name__ == "__main__":
    main()
