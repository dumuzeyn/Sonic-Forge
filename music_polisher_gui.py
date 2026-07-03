import queue
import os
import sys
import threading
import traceback
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import easy_music_process
import music2picture


APP_NAMES = {
    "ru": "Кузница Звука",
    "en": "Sonic Forge",
}

I18N = {
    "ru": {
        "language_button": "English",
        "description": "Приложение подготавливает музыкальные файлы: нормализует громкость, записывает метаданные, создает обложку и переносит готовый результат в выбранную папку только после полного завершения обработки.",
        "source": "Источник",
        "output": "Папка назначения",
        "genre": "Жанр",
        "artist": "Исполнитель",
        "album": "Альбом",
        "album_artist": "Исполнитель альбома",
        "composer": "Композитор",
        "date": "Год",
        "track": "Номер трека",
        "comment": "Комментарий",
        "overwrite_genre": "Заменить существующий жанр",
        "color_mode": "Цветовая схема",
        "seed": "Seed",
        "metadata": "Метаданные",
        "audio": "Звук",
        "integrated_lufs": "Средняя громкость LUFS",
        "true_peak": "Пиковый предел",
        "lra": "Диапазон громкости",
        "final_gain": "Финальное усиление",
        "denoise": "Шумоподавление",
        "denoise_strength": "Сила шумоподавления",
        "limiter": "Лимитер",
        "cover": "Обложка",
        "cover_size": "Размер",
        "cover_patterns": "Детализация",
        "center_title": "Название по центру",
        "embed_cover": "Встроить обложку",
        "no_change_cover": "Не менять обложку",
        "choose_file": "Файл",
        "choose_folder": "Папка",
        "run": "Запустить",
        "clear_log": "Очистить журнал",
        "log_ready": "Готов к работе.",
        "run_started": "Запуск обработки.",
        "run_finished": "Обработка завершена.",
        "error": "Ошибка",
        "missing_paths": "Выберите источник и папку назначения.",
        "bad_seed": "Seed должен быть целым числом или пустым полем.",
        "source_dialog_file": "Выберите аудиофайл",
        "source_dialog_folder": "Выберите папку с музыкой",
        "output_dialog_folder": "Выберите папку назначения",
        "tip_source": "Один аудиофайл или папка с несколькими песнями.",
        "tip_output": "Папка, куда будут перенесены готовые файлы. Во время обработки она не изменяется.",
        "tip_genre": "Жанр, который будет записан в метаданные. Если поле пустое, программа попробует определить жанр автоматически.",
        "tip_artist": "Имя исполнителя. Если поле пустое, исполнитель останется пустым.",
        "tip_album": "Название альбома. Если поле пустое, альбом останется пустым.",
        "tip_album_artist": "Исполнитель альбома. Если поле пустое, это поле останется пустым.",
        "tip_composer": "Композитор или автор музыки. Если поле пустое, это поле останется пустым.",
        "tip_date": "Год или дата выпуска. Если поле пустое, дата останется пустой.",
        "tip_track": "Номер трека, например 1 или 1/12. Если поле пустое, номер трека останется пустым.",
        "tip_comment": "Комментарий к файлу. Если поле пустое, комментарий останется пустым.",
        "tip_overwrite_genre": "Если включено, выбранный жанр заменит жанр, который уже записан в файле.",
        "tip_color_mode": "Схема цветов для обложки. Доступны только четыре официальных режима: ocean, plasma, fusion, aurora.",
        "tip_seed": "Целое число для повторяемой генерации обложек. Оставьте пустым, чтобы обложки каждый раз отличались.",
        "tip_integrated_lufs": "Целевая средняя громкость трека. Значение -14 LUFS обычно дает громкий, но умеренный результат.",
        "tip_true_peak": "Максимальный пик громкости после обработки. Отрицательное значение снижает риск перегруза.",
        "tip_lra": "Желаемый диапазон громкости. Меньше значение делает громкость ровнее, больше сохраняет динамику.",
        "tip_final_gain": "Дополнительное усиление после нормализации. Слишком высокое значение может добавить резкость.",
        "tip_denoise": "Мягко снижает фоновый шум перед нормализацией. Если песня теряет детали, отключите параметр.",
        "tip_denoise_strength": "Сила шумоподавления. Умеренные значения обычно безопаснее для качества музыки.",
        "tip_limiter": "Ограничивает финальные пики, чтобы уменьшить вероятность искажений.",
        "tip_cover_size": "Размер создаваемой обложки в пикселях. 1000 подходит для большинства MP3-файлов.",
        "tip_cover_patterns": "Сложность рисунка обложки: 1 проще, 2 детальнее.",
        "tip_center_title": "Добавляет название песни в центр обложки.",
        "tip_embed_cover": "Встраивает созданную обложку непосредственно в MP3-файл.",
        "tip_no_change_cover": "Если включено, приложение не будет создавать и встраивать новую обложку.",
    },
    "en": {
        "language_button": "Русский",
        "description": "The application prepares music files by normalizing loudness, writing metadata, generating cover art, and publishing the finished result to the selected folder only after the full process succeeds.",
        "source": "Source",
        "output": "Output folder",
        "genre": "Genre",
        "artist": "Artist",
        "album": "Album",
        "album_artist": "Album artist",
        "composer": "Composer",
        "date": "Year",
        "track": "Track",
        "comment": "Comment",
        "overwrite_genre": "Overwrite existing genre",
        "color_mode": "Color mode",
        "seed": "Seed",
        "metadata": "Metadata",
        "audio": "Audio",
        "integrated_lufs": "Integrated LUFS",
        "true_peak": "True peak",
        "lra": "Loudness range",
        "final_gain": "Final gain",
        "denoise": "Denoise",
        "denoise_strength": "Denoise strength",
        "limiter": "Limiter",
        "cover": "Cover",
        "cover_size": "Size",
        "cover_patterns": "Patterns",
        "center_title": "Center title",
        "embed_cover": "Embed cover",
        "no_change_cover": "Do not change cover",
        "choose_file": "File",
        "choose_folder": "Folder",
        "run": "Run",
        "clear_log": "Clear log",
        "log_ready": "Ready.",
        "run_started": "Processing started.",
        "run_finished": "Processing finished.",
        "error": "Error",
        "missing_paths": "Choose source and output paths.",
        "bad_seed": "Seed must be an integer or empty.",
        "source_dialog_file": "Choose audio file",
        "source_dialog_folder": "Choose source folder",
        "output_dialog_folder": "Choose output folder",
        "tip_source": "A single audio file or a folder containing several songs.",
        "tip_output": "The folder that will receive finished files. It is not changed while processing is still running.",
        "tip_genre": "Genre written to metadata. Leave it empty to let the application estimate the genre automatically.",
        "tip_artist": "Artist name. Leave empty to keep this field empty.",
        "tip_album": "Album title. Leave empty to keep this field empty.",
        "tip_album_artist": "Album artist. Leave empty to keep this field empty.",
        "tip_composer": "Composer or music author. Leave empty to keep this field empty.",
        "tip_date": "Release year or date. Leave empty to keep this field empty.",
        "tip_track": "Track number, for example 1 or 1/12. Leave empty to keep this field empty.",
        "tip_comment": "File comment. Leave empty to keep this field empty.",
        "tip_overwrite_genre": "When enabled, the selected genre replaces the genre already stored in the file.",
        "tip_color_mode": "Cover color scheme. Only four official modes are available: ocean, plasma, fusion, aurora.",
        "tip_seed": "Integer for repeatable cover generation. Leave empty to generate a different cover each time.",
        "tip_integrated_lufs": "Target average loudness. -14 LUFS usually gives a loud but moderate result.",
        "tip_true_peak": "Maximum loudness peak after processing. A negative value reduces clipping risk.",
        "tip_lra": "Target loudness range. Lower values sound more even; higher values preserve more dynamics.",
        "tip_final_gain": "Extra gain after normalization. Too much gain can make the result harsh.",
        "tip_denoise": "Gently reduces background noise before normalization. Disable it if a song loses detail.",
        "tip_denoise_strength": "Denoise amount. Moderate values are usually safer for music quality.",
        "tip_limiter": "Limits final peaks to reduce the chance of distortion.",
        "tip_cover_size": "Generated cover size in pixels. 1000 is suitable for most MP3 files.",
        "tip_cover_patterns": "Cover pattern complexity: 1 is simpler, 2 is more detailed.",
        "tip_center_title": "Adds the song title to the center of the cover.",
        "tip_embed_cover": "Embeds the generated cover directly into the MP3 file.",
        "tip_no_change_cover": "When enabled, the application does not create or embed new cover art.",
    },
}

COLORS = {
    "bg": "#0d0d12",
    "panel": "#15151e",
    "field": "#20202b",
    "border": "#393447",
    "text": "#f4f1ff",
    "muted": "#bbb4cc",
    "accent": "#8d5cff",
    "accent_hot": "#b486ff",
    "button": "#2a2140",
    "button_active": "#3a2b61",
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
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
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


class ToolTip:
    def __init__(self, widget, app, tip_key):
        self.widget = widget
        self.app = app
        self.tip_key = tip_key
        self.window = None
        self.after_id = None
        widget.bind("<Enter>", self._schedule)
        widget.bind("<Leave>", self._hide)
        widget.bind("<ButtonPress>", self._hide)

    def _schedule(self, _event=None):
        self._cancel()
        self.after_id = self.widget.after(450, self._show)

    def _cancel(self):
        if self.after_id is not None:
            self.widget.after_cancel(self.after_id)
            self.after_id = None

    def _show(self):
        text = self.app.t(self.tip_key)
        if self.window is not None or not text:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self.window = tk.Toplevel(self.widget)
        self.window.wm_overrideredirect(True)
        self.window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            self.window,
            text=text,
            justify="left",
            background="#1f1b2d",
            foreground=COLORS["text"],
            relief="solid",
            borderwidth=1,
            padx=10,
            pady=8,
            wraplength=390,
            font=("Segoe UI", 10),
        )
        label.pack()

    def _hide(self, _event=None):
        self._cancel()
        if self.window is not None:
            self.window.destroy()
            self.window = None


class SquareCheckbutton(tk.Frame):
    def __init__(self, parent, variable, text="", command=None):
        super().__init__(parent, bg=COLORS["bg"])
        self.variable = variable
        self.command = command
        self.canvas = tk.Canvas(
            self,
            width=18,
            height=18,
            bg=COLORS["bg"],
            highlightthickness=0,
            bd=0,
        )
        self.label = tk.Label(
            self,
            text=text,
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=("Segoe UI", 10),
        )
        self.canvas.pack(side=tk.LEFT, padx=(0, 7))
        self.label.pack(side=tk.LEFT)
        self.canvas.bind("<Button-1>", self._toggle)
        self.label.bind("<Button-1>", self._toggle)
        self.bind("<Button-1>", self._toggle)
        self.variable.trace_add("write", self._redraw)
        self._redraw()

    def configure(self, cnf=None, **kwargs):
        text = kwargs.pop("text", None)
        if text is not None:
            self.label.configure(text=text)
        if kwargs:
            super().configure(cnf, **kwargs)

    config = configure

    def _toggle(self, _event=None):
        self.variable.set(not bool(self.variable.get()))
        if self.command:
            self.command()

    def _redraw(self, *_args):
        selected = bool(self.variable.get())
        self.canvas.delete("all")
        border = COLORS["accent_hot"] if selected else COLORS["border"]
        fill = COLORS["accent"] if selected else COLORS["field"]
        self.canvas.create_rectangle(2, 2, 16, 16, outline=border, fill=fill, width=2)


class SonicForgeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.language = "ru"
        self.log_queue = queue.Queue()
        self.worker = None
        self.localized_widgets = []
        self.frame_titles = []

        self.source_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.genre_var = tk.StringVar()
        self.artist_var = tk.StringVar()
        self.album_var = tk.StringVar()
        self.album_artist_var = tk.StringVar()
        self.composer_var = tk.StringVar()
        self.date_var = tk.StringVar()
        self.track_var = tk.StringVar()
        self.comment_var = tk.StringVar()
        self.color_var = tk.StringVar(value="plasma")
        self.seed_var = tk.StringVar()
        self.integrated_lufs_var = tk.DoubleVar(value=-14.0)
        self.true_peak_var = tk.DoubleVar(value=-1.5)
        self.lra_var = tk.DoubleVar(value=11.0)
        self.final_gain_var = tk.DoubleVar(value=1.15)
        self.denoise_var = tk.BooleanVar(value=True)
        self.denoise_strength_var = tk.DoubleVar(value=4.0)
        self.limiter_var = tk.BooleanVar(value=True)
        self.overwrite_genre_var = tk.BooleanVar(value=False)
        self.cover_size_var = tk.IntVar(value=1000)
        self.cover_patterns_var = tk.IntVar(value=2)
        self.center_title_var = tk.BooleanVar(value=True)
        self.embed_cover_var = tk.BooleanVar(value=True)
        self.no_change_cover_var = tk.BooleanVar(value=False)

        self._configure_window()
        self._configure_fonts()
        self._configure_style()
        self._bind_edit_shortcuts()
        self._build_ui()
        self._apply_language()
        self.after(100, self._drain_log_queue)

    def t(self, key):
        return I18N[self.language][key]

    def _configure_window(self):
        self.geometry("1280x920")
        self.minsize(1180, 860)
        self.configure(bg=COLORS["bg"])
        icon_path = resource_path("assets/sonic_forge_mark.ico")
        png_path = resource_path("assets/sonic_forge_mark.png")
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except tk.TclError:
                pass
        if png_path.exists():
            try:
                self.icon_image = tk.PhotoImage(file=str(png_path))
                self.iconphoto(True, self.icon_image)
            except tk.TclError:
                self.icon_image = None

    def _configure_fonts(self):
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont"):
            font = tkfont.nametofont(name)
            font.configure(family="Segoe UI", size=max(font.cget("size"), 10))
        tkfont.nametofont("TkHeadingFont").configure(family="Segoe UI", size=11, weight="bold")

    def _configure_style(self):
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure(".", background=COLORS["bg"], foreground=COLORS["text"], fieldbackground=COLORS["field"], bordercolor=COLORS["border"], lightcolor=COLORS["border"], darkcolor=COLORS["border"])
        self.style.configure("TFrame", background=COLORS["bg"])
        self.style.configure("Panel.TFrame", background=COLORS["panel"])
        self.style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"])
        self.style.configure("Muted.TLabel", background=COLORS["bg"], foreground=COLORS["muted"])
        self.style.configure("Title.TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=("Segoe UI", 20, "bold"))
        self.style.configure("TLabelframe", background=COLORS["bg"], foreground=COLORS["text"], bordercolor=COLORS["border"])
        self.style.configure("TLabelframe.Label", background=COLORS["bg"], foreground=COLORS["accent_hot"], font=("Segoe UI", 11, "bold"))
        self.style.configure("TButton", background=COLORS["button"], foreground=COLORS["text"], borderwidth=1, focusthickness=1, focuscolor=COLORS["accent"], padding=(12, 7))
        self.style.map("TButton", background=[("active", COLORS["button_active"]), ("pressed", COLORS["accent"])])
        self.style.configure("Accent.TButton", background=COLORS["accent"], foreground="#ffffff", font=("Segoe UI", 10, "bold"))
        self.style.map("Accent.TButton", background=[("active", COLORS["accent_hot"]), ("pressed", "#6f45d8")])
        self.style.configure("TEntry", fieldbackground=COLORS["field"], foreground=COLORS["text"], insertcolor=COLORS["text"], bordercolor=COLORS["border"], padding=5)
        self.style.configure("TSpinbox", fieldbackground=COLORS["field"], foreground=COLORS["text"], insertcolor=COLORS["text"], bordercolor=COLORS["border"], padding=5)
        self.style.configure("TCombobox", fieldbackground=COLORS["field"], foreground=COLORS["text"], arrowcolor=COLORS["accent"], bordercolor=COLORS["border"], padding=5)
        self.style.map("TCombobox", fieldbackground=[("readonly", COLORS["field"])], foreground=[("readonly", COLORS["text"])])
        self.style.configure("TCheckbutton", background=COLORS["bg"], foreground=COLORS["text"], indicatorcolor=COLORS["field"], indicatormargin=6, indicatordiameter=16)
        self.style.map(
            "TCheckbutton",
            background=[("active", COLORS["bg"])],
            foreground=[("active", COLORS["text"])],
            indicatorcolor=[("selected", COLORS["accent"]), ("!selected", COLORS["field"])],
        )
        self.style.configure("Horizontal.TProgressbar", background=COLORS["accent"], troughcolor=COLORS["field"], bordercolor=COLORS["border"])

    def _bind_edit_shortcuts(self):
        bindings = {
            "<Control-a>": self._select_all,
            "<Control-A>": self._select_all,
            "<Control-c>": self._copy,
            "<Control-C>": self._copy,
            "<Control-x>": self._cut,
            "<Control-X>": self._cut,
            "<Control-v>": self._paste,
            "<Control-V>": self._paste,
            "<Control-z>": self._undo,
            "<Control-Z>": self._undo,
            "<Shift-Insert>": self._paste,
        }
        for sequence, handler in bindings.items():
            self.bind_all(sequence, handler, add="+")
        self.bind_all("<Control-KeyPress>", self._keycode_fallback, add="+")

    def _keycode_fallback(self, event):
        keycode_map = {
            65: self._select_all,
            67: self._copy,
            86: self._paste,
            88: self._cut,
            90: self._undo,
        }
        handler = keycode_map.get(event.keycode)
        if handler:
            return handler(event)
        return None

    def _focused_edit_widget(self):
        widget = self.focus_get()
        if widget is None:
            return None
        classes = {"Entry", "TEntry", "Spinbox", "TSpinbox", "Text", "TCombobox"}
        if widget.winfo_class() in classes:
            return widget
        return None

    def _select_all(self, _event=None):
        widget = self._focused_edit_widget()
        if widget is None:
            return None
        try:
            if widget.winfo_class() == "Text":
                widget.tag_add("sel", "1.0", "end-1c")
            else:
                widget.selection_range(0, tk.END)
                widget.icursor(tk.END)
            return "break"
        except tk.TclError:
            return None

    def _copy(self, _event=None):
        return self._generate_edit_event("<<Copy>>")

    def _cut(self, _event=None):
        return self._generate_edit_event("<<Cut>>")

    def _paste(self, _event=None):
        return self._generate_edit_event("<<Paste>>")

    def _undo(self, _event=None):
        return self._generate_edit_event("<<Undo>>")

    def _generate_edit_event(self, event_name):
        widget = self._focused_edit_widget()
        if widget is None:
            return None
        try:
            widget.event_generate(event_name)
            return "break"
        except tk.TclError:
            return None

    def _localized(self, widget, key):
        self.localized_widgets.append((widget, key))
        return widget

    def _with_tip(self, widget, tip_key):
        ToolTip(widget, self, tip_key)
        return widget

    def _label(self, parent, key, tip_key=None, style=None):
        label = self._localized(ttk.Label(parent, style=style), key)
        if tip_key:
            self._with_tip(label, tip_key)
        return label

    def _button(self, parent, key, command, style=None):
        return self._localized(ttk.Button(parent, command=command, style=style), key)

    def _checkbutton(self, parent, key, variable, tip_key):
        widget = self._localized(SquareCheckbutton(parent, variable=variable), key)
        return self._with_tip(widget, tip_key)

    def _frame_title(self, frame, key):
        self.frame_titles.append((frame, key))
        return frame

    def _build_ui(self):
        root = ttk.Frame(self, padding=18)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(10, weight=1)

        header = ttk.Frame(root)
        header.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 16))
        header.columnconfigure(1, weight=1)
        self.title_label = ttk.Label(header, style="Title.TLabel")
        self.title_label.grid(row=0, column=1, sticky="w")
        self.description_label = self._localized(ttk.Label(header, style="Muted.TLabel", wraplength=690, justify="left"), "description")
        self.description_label.grid(row=1, column=1, sticky="w", pady=(4, 0))
        self.language_button = self._button(header, "language_button", self._toggle_language)
        self.language_button.grid(row=0, column=2, sticky="ne")

        self._label(root, "source", "tip_source").grid(row=1, column=0, sticky="w", pady=5)
        self.source_entry = ttk.Entry(root, textvariable=self.source_var)
        self.source_entry.grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        source_buttons = ttk.Frame(root)
        source_buttons.grid(row=1, column=2, sticky="e", pady=5)
        self._button(source_buttons, "choose_file", self._choose_source_file).pack(side=tk.LEFT, padx=(0, 6))
        self._button(source_buttons, "choose_folder", self._choose_source_folder).pack(side=tk.LEFT)

        self._label(root, "output", "tip_output").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(root, textvariable=self.output_var).grid(row=2, column=1, sticky="ew", padx=10, pady=5)
        self._button(root, "choose_folder", self._choose_output_folder).grid(row=2, column=2, sticky="e", pady=5)

        metadata_box = self._frame_title(ttk.LabelFrame(root), "metadata")
        metadata_box.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(12, 8))
        for col in range(6):
            metadata_box.columnconfigure(col, weight=1 if col in {1, 3, 5} else 0)
        self._label(metadata_box, "genre", "tip_genre").grid(row=0, column=0, sticky="w", padx=10, pady=6)
        ttk.Entry(metadata_box, textvariable=self.genre_var, width=16).grid(row=0, column=1, sticky="ew", padx=8, pady=6)
        self._label(metadata_box, "artist", "tip_artist").grid(row=0, column=2, sticky="w", padx=10, pady=6)
        ttk.Entry(metadata_box, textvariable=self.artist_var, width=18).grid(row=0, column=3, sticky="ew", padx=8, pady=6)
        self._label(metadata_box, "album", "tip_album").grid(row=0, column=4, sticky="w", padx=10, pady=6)
        ttk.Entry(metadata_box, textvariable=self.album_var, width=18).grid(row=0, column=5, sticky="ew", padx=8, pady=6)
        self._label(metadata_box, "album_artist", "tip_album_artist").grid(row=1, column=0, sticky="w", padx=10, pady=6)
        ttk.Entry(metadata_box, textvariable=self.album_artist_var, width=16).grid(row=1, column=1, sticky="ew", padx=8, pady=6)
        self._label(metadata_box, "composer", "tip_composer").grid(row=1, column=2, sticky="w", padx=10, pady=6)
        ttk.Entry(metadata_box, textvariable=self.composer_var, width=18).grid(row=1, column=3, sticky="ew", padx=8, pady=6)
        self._label(metadata_box, "date", "tip_date").grid(row=1, column=4, sticky="w", padx=10, pady=6)
        ttk.Entry(metadata_box, textvariable=self.date_var, width=18).grid(row=1, column=5, sticky="ew", padx=8, pady=6)
        self._label(metadata_box, "track", "tip_track").grid(row=2, column=0, sticky="w", padx=10, pady=6)
        ttk.Entry(metadata_box, textvariable=self.track_var, width=16).grid(row=2, column=1, sticky="ew", padx=8, pady=6)
        self._label(metadata_box, "comment", "tip_comment").grid(row=2, column=2, sticky="w", padx=10, pady=6)
        ttk.Entry(metadata_box, textvariable=self.comment_var, width=18).grid(row=2, column=3, columnspan=2, sticky="ew", padx=8, pady=6)
        self._checkbutton(metadata_box, "overwrite_genre", self.overwrite_genre_var, "tip_overwrite_genre").grid(row=2, column=5, sticky="w", padx=10, pady=6)

        self._label(root, "color_mode", "tip_color_mode").grid(row=4, column=0, sticky="w", pady=5)
        color_values = sorted(music2picture.COLOR_MODES)
        ttk.Combobox(root, textvariable=self.color_var, values=color_values, state="readonly").grid(row=4, column=1, sticky="ew", padx=10, pady=5)
        seed_box = ttk.Frame(root)
        seed_box.grid(row=4, column=2, sticky="e", pady=5)
        self._label(seed_box, "seed", "tip_seed").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Entry(seed_box, textvariable=self.seed_var, width=12).pack(side=tk.LEFT)

        audio_box = self._frame_title(ttk.LabelFrame(root), "audio")
        audio_box.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(8, 8))
        for col in range(6):
            audio_box.columnconfigure(col, weight=1 if col in {1, 3, 5} else 0)
        self._label(audio_box, "integrated_lufs", "tip_integrated_lufs").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        ttk.Spinbox(audio_box, from_=-30.0, to=-5.0, increment=0.5, textvariable=self.integrated_lufs_var, width=8).grid(row=0, column=1, sticky="w", padx=8, pady=8)
        self._label(audio_box, "true_peak", "tip_true_peak").grid(row=0, column=2, sticky="w", padx=10, pady=8)
        ttk.Spinbox(audio_box, from_=-6.0, to=0.0, increment=0.1, textvariable=self.true_peak_var, width=8).grid(row=0, column=3, sticky="w", padx=8, pady=8)
        self._label(audio_box, "lra", "tip_lra").grid(row=0, column=4, sticky="w", padx=10, pady=8)
        ttk.Spinbox(audio_box, from_=1.0, to=30.0, increment=0.5, textvariable=self.lra_var, width=8).grid(row=0, column=5, sticky="w", padx=8, pady=8)
        self._label(audio_box, "final_gain", "tip_final_gain").grid(row=1, column=0, sticky="w", padx=10, pady=8)
        ttk.Spinbox(audio_box, from_=0.5, to=2.0, increment=0.05, textvariable=self.final_gain_var, width=8).grid(row=1, column=1, sticky="w", padx=8, pady=8)
        self._checkbutton(audio_box, "denoise", self.denoise_var, "tip_denoise").grid(row=1, column=2, sticky="w", padx=10, pady=8)
        self._label(audio_box, "denoise_strength", "tip_denoise_strength").grid(row=1, column=3, sticky="e", padx=8, pady=8)
        ttk.Spinbox(audio_box, from_=0.0, to=20.0, increment=0.5, textvariable=self.denoise_strength_var, width=8).grid(row=1, column=4, sticky="w", padx=8, pady=8)
        self._checkbutton(audio_box, "limiter", self.limiter_var, "tip_limiter").grid(row=1, column=5, sticky="w", padx=10, pady=8)

        cover_box = self._frame_title(ttk.LabelFrame(root), "cover")
        cover_box.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(4, 8))
        self._label(cover_box, "cover_size", "tip_cover_size").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        ttk.Spinbox(cover_box, from_=256, to=3000, increment=128, textvariable=self.cover_size_var, width=8).grid(row=0, column=1, sticky="w", padx=8, pady=8)
        self._label(cover_box, "cover_patterns", "tip_cover_patterns").grid(row=0, column=2, sticky="w", padx=10, pady=8)
        ttk.Combobox(cover_box, textvariable=self.cover_patterns_var, values=[1, 2], state="readonly", width=6).grid(row=0, column=3, sticky="w", padx=8, pady=8)
        self._checkbutton(cover_box, "center_title", self.center_title_var, "tip_center_title").grid(row=0, column=4, sticky="w", padx=10, pady=8)
        self._checkbutton(cover_box, "embed_cover", self.embed_cover_var, "tip_embed_cover").grid(row=0, column=5, sticky="w", padx=10, pady=8)
        self._checkbutton(cover_box, "no_change_cover", self.no_change_cover_var, "tip_no_change_cover").grid(row=1, column=0, sticky="w", padx=10, pady=8)

        buttons = ttk.Frame(root)
        buttons.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(8, 12))
        buttons.columnconfigure(0, weight=1)
        self.run_button = self._button(buttons, "run", self._run, style="Accent.TButton")
        self.run_button.grid(row=0, column=1, padx=5)
        self._button(buttons, "clear_log", self._clear_log).grid(row=0, column=2, padx=5)

        self.progress = ttk.Progressbar(root, mode="indeterminate")
        self.progress.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        self.log = tk.Text(root, height=16, wrap="word", undo=True, bg="#0a0a0f", fg=COLORS["text"], insertbackground=COLORS["text"], relief="solid", borderwidth=1, highlightthickness=1, highlightbackground=COLORS["border"], font=("Consolas", 10))
        self.log.grid(row=10, column=0, columnspan=3, sticky="nsew")
        scrollbar = ttk.Scrollbar(root, command=self.log.yview)
        scrollbar.grid(row=10, column=3, sticky="ns")
        self.log.configure(yscrollcommand=scrollbar.set)

    def _apply_language(self):
        app_name = APP_NAMES[self.language]
        self.title(app_name)
        self.title_label.configure(text=app_name)
        for widget, key in self.localized_widgets:
            widget.configure(text=self.t(key))
        for frame, key in self.frame_titles:
            frame.configure(text=self.t(key))
        self.log.delete("1.0", tk.END)
        self._write_log(self.t("log_ready") + "\n")

    def _toggle_language(self):
        self.language = "en" if self.language == "ru" else "ru"
        self._apply_language()

    def _choose_source_file(self):
        path = filedialog.askopenfilename(
            title=self.t("source_dialog_file"),
            filetypes=[("Audio files", "*.mp3 *.flac *.wav *.m4a *.aac *.ogg *.opus *.wma"), ("All files", "*.*")],
        )
        if path:
            self.source_var.set(path)

    def _choose_source_folder(self):
        path = filedialog.askdirectory(title=self.t("source_dialog_folder"))
        if path:
            self.source_var.set(path)

    def _choose_output_folder(self):
        path = filedialog.askdirectory(title=self.t("output_dialog_folder"))
        if path:
            self.output_var.set(path)

    def _parse_seed(self):
        seed = self.seed_var.get().strip()
        if not seed:
            return None
        return int(seed)

    def _run(self):
        if self.worker and self.worker.is_alive():
            return

        source = self.source_var.get().strip()
        output = self.output_var.get().strip()
        if not source or not output:
            messagebox.showerror(APP_NAMES[self.language], self.t("missing_paths"))
            return
        try:
            cover_seed = self._parse_seed()
        except ValueError:
            messagebox.showerror(APP_NAMES[self.language], self.t("bad_seed"))
            return

        kwargs = {
            "source": source,
            "output": output,
            "genre": self.genre_var.get().strip() or None,
            "color_mode": self.color_var.get(),
            "integrated_lufs": float(self.integrated_lufs_var.get()),
            "true_peak": float(self.true_peak_var.get()),
            "lra": float(self.lra_var.get()),
            "final_gain": float(self.final_gain_var.get()),
            "denoise": bool(self.denoise_var.get()),
            "denoise_strength": float(self.denoise_strength_var.get()),
            "limiter": bool(self.limiter_var.get()),
            "overwrite_genre": bool(self.overwrite_genre_var.get()),
            "extra_metadata": {
                "artist": self.artist_var.get(),
                "album": self.album_var.get(),
                "album_artist": self.album_artist_var.get(),
                "composer": self.composer_var.get(),
                "date": self.date_var.get(),
                "track": self.track_var.get(),
                "comment": self.comment_var.get(),
            },
            "cover_seed": cover_seed,
            "cover_size": int(self.cover_size_var.get()),
            "cover_patterns": int(self.cover_patterns_var.get()),
            "center_title": bool(self.center_title_var.get()),
            "embed_cover": bool(self.embed_cover_var.get()),
            "change_cover": not bool(self.no_change_cover_var.get()),
        }

        self.run_button.configure(state=tk.DISABLED)
        self.progress.start(12)
        self._write_log("\n" + self.t("run_started") + "\n")
        self.worker = threading.Thread(target=self._worker_run, args=(kwargs,), daemon=True)
        self.worker.start()

    def _worker_run(self, kwargs):
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout = QueueWriter(self.log_queue)
        sys.stderr = QueueWriter(self.log_queue)
        try:
            easy_music_process.process_music(**kwargs)
            self.log_queue.put("\n" + self.t("run_finished") + "\n")
        except Exception:
            self.log_queue.put("\n" + self.t("error") + "\n")
            self.log_queue.put(traceback.format_exc())
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr
            self.log_queue.put(("__DONE__", None))

    def _drain_log_queue(self):
        try:
            while True:
                item = self.log_queue.get_nowait()
                if isinstance(item, tuple) and item[0] == "__DONE__":
                    self.progress.stop()
                    self.run_button.configure(state=tk.NORMAL)
                else:
                    self._write_log(item)
        except queue.Empty:
            pass
        self.after(100, self._drain_log_queue)

    def _write_log(self, text):
        self.log.insert(tk.END, text)
        self.log.see(tk.END)

    def _clear_log(self):
        self.log.delete("1.0", tk.END)


if __name__ == "__main__":
    enable_high_dpi()
    configure_bundled_ffmpeg()
    app = SonicForgeApp()
    app.mainloop()
