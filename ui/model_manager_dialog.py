import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from cover_engine.model_manager import ImageModelManager, RECOMMENDED_MODEL
from .theme import COLORS, FONTS, SPACING
from .windowing import show_centered


class ImageModelManagerDialog(tk.Toplevel):
    def __init__(self, app, manager=None, first_use=False):
        super().__init__(app)
        self.app = app
        self.manager = manager or ImageModelManager()
        self.first_use = first_use
        self.events = queue.Queue()
        self.cancel_event = threading.Event()
        self.worker = None
        self.runtime_only = False
        self.localized = []
        self.progress_key = None
        self.progress_values = {}
        self.status_var = tk.StringVar()
        self.progress_var = tk.StringVar()
        self.title(app.t("model_manager_title"))
        self.configure(bg=COLORS["bg"])
        self.transient(app)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self._build()
        self.refresh()
        self.update_idletasks()
        show_centered(self, max(560, self.winfo_reqwidth()), self.winfo_reqheight() + 8, parent=app)
        self.grab_set()

    def _build(self):
        content = ttk.Frame(self, padding=SPACING["lg"])
        content.pack(fill=tk.BOTH, expand=True)
        intro_key = "model_manager_intro_first" if self.first_use else "model_manager_intro"
        intro = ttk.Label(
            content,
            text=self.app.t(intro_key),
            style="Secondary.TLabel",
            wraplength=520,
            justify=tk.LEFT,
        )
        self.localized.append((intro, intro_key))
        intro.pack(fill=tk.X, pady=(0, SPACING["md"]))
        ttk.Label(content, text=RECOMMENDED_MODEL, font=FONTS["section"]).pack(anchor="w")
        size_label = ttk.Label(
            content,
            text=self.app.t("model_manager_size"),
            style="Secondary.TLabel",
        )
        self.localized.append((size_label, "model_manager_size"))
        size_label.pack(anchor="w", pady=(2, SPACING["xs"]))
        quality_label = ttk.Label(
            content,
            text=self.app.t("model_manager_quality"),
            style="Secondary.TLabel",
            wraplength=520,
            justify=tk.LEFT,
        )
        self.localized.append((quality_label, "model_manager_quality"))
        quality_label.pack(fill=tk.X, pady=(0, SPACING["md"]))
        ttk.Label(
            content,
            textvariable=self.status_var,
            style="SurfaceSecondary.TLabel",
            wraplength=520,
        ).pack(fill=tk.X)
        self.progress = ttk.Progressbar(content, mode="indeterminate")
        self.progress.pack(fill=tk.X, pady=(SPACING["sm"], 2))
        ttk.Label(
            content,
            textvariable=self.progress_var,
            style="Secondary.TLabel",
        ).pack(fill=tk.X)
        actions = ttk.Frame(content)
        actions.pack(fill=tk.X, pady=(SPACING["md"], 0))
        self.download_button = ttk.Button(
            actions,
            text=self.app.t("model_download"),
            style="Primary.TButton",
            command=self.download,
        )
        self.select_button = ttk.Button(
            actions,
            text=self.app.t("model_select"),
            command=self.select_model,
        )
        self.remove_button = ttk.Button(
            actions,
            text=self.app.t("model_remove"),
            command=self.remove_model,
        )
        self.close_button = ttk.Button(actions, text=self.app.t("close"), command=self.close)
        self.localized.extend(
            (
                (self.download_button, "model_download"),
                (self.select_button, "model_select"),
                (self.remove_button, "model_remove"),
            )
        )
        self.download_button.pack(side=tk.LEFT, padx=(0, SPACING["sm"]))
        self.select_button.pack(side=tk.LEFT, padx=(0, SPACING["sm"]))
        self.remove_button.pack(side=tk.LEFT)
        self.close_button.pack(side=tk.RIGHT)

    def refresh(self):
        status = self.manager.status()
        if status.ready:
            semantic_key = "model_semantic_ready" if status.semantic_path else "model_semantic_missing"
            self.status_var.set(
                self.app.t("model_status_ready").format(path=status.model_path)
                + "\n"
                + self.app.t(semantic_key)
            )
        else:
            self.status_var.set(self.app.t("model_status_missing"))
        self.remove_button.configure(
            state=tk.NORMAL if self.manager.recommended_path.is_file() else tk.DISABLED
        )

    def download(self):
        self.runtime_only = False
        self._start_download()

    def _start_download(self):
        if self.worker and self.worker.is_alive():
            return
        self.cancel_event.clear()
        self._set_busy(True)
        self.worker = threading.Thread(target=self._download_worker, daemon=True)
        self.worker.start()
        self.after(100, self._poll)

    def _download_worker(self):
        try:
            operation = (
                self.manager.download_runtime
                if self.runtime_only
                else self.manager.download_recommended
            )
            operation(
                progress=lambda stage, current, total: self.events.put(
                    ("progress", stage, current, total)
                ),
                cancel_event=self.cancel_event,
            )
            self.events.put(("done",))
        except InterruptedError:
            self.events.put(("cancelled",))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def _poll(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "progress":
                    _, stage, current, total = event
                    self.progress_key = {
                        "runtime": "model_stage_runtime",
                        "semantic": "model_stage_semantic",
                    }.get(stage, "model_stage_model")
                    self.progress_values = {"percent": f"  {current / total:.0%}" if total else ""}
                    self._refresh_progress()
                elif event[0] == "done":
                    self._set_busy(False)
                    self._set_progress("model_download_done")
                    self.refresh()
                elif event[0] == "cancelled":
                    self._set_busy(False)
                    self._set_progress("model_download_cancelled")
                elif event[0] == "error":
                    self._set_busy(False)
                    self._set_progress("model_download_error", error=event[1])
        except queue.Empty:
            pass
        if self.worker and self.worker.is_alive():
            self.after(100, self._poll)

    def select_model(self):
        path = filedialog.askopenfilename(
            parent=self,
            title=self.app.t("model_select"),
            filetypes=(
                ("Image model", "*.safetensors *.ckpt *.gguf"),
                ("All files", "*.*"),
            ),
        )
        if not path:
            return
        try:
            self.manager.set_custom_model(path)
            self.refresh()
            if not self.manager.runtime_path() and messagebox.askyesno(
                self.app.app_name(),
                self.app.t("model_runtime_confirm"),
                parent=self,
            ):
                self.runtime_only = True
                self._start_download()
        except ValueError as exc:
            messagebox.showerror(self.app.app_name(), str(exc), parent=self)

    def remove_model(self):
        if not messagebox.askyesno(
            self.app.app_name(),
            self.app.t("model_remove_confirm"),
            parent=self,
        ):
            return
        self.manager.remove_recommended()
        self.refresh()

    def _set_busy(self, busy):
        state = tk.DISABLED if busy else tk.NORMAL
        self.download_button.configure(state=state)
        self.select_button.configure(state=state)
        self.remove_button.configure(state=state)
        if busy:
            self.progress.start(12)
            self.close_button.configure(text=self.app.t("stop"), command=self.close)
        else:
            self.progress.stop()
            self.close_button.configure(text=self.app.t("close"), command=self.close)

    def _set_progress(self, key, **values):
        self.progress_key = key
        self.progress_values = values
        self._refresh_progress()

    def _refresh_progress(self):
        if not self.progress_key:
            self.progress_var.set("")
            return
        values = dict(self.progress_values)
        percent = values.pop("percent", "")
        self.progress_var.set(self.app.t(self.progress_key).format(**values) + percent)

    def apply_language(self):
        self.title(self.app.t("model_manager_title"))
        for widget, key in self.localized:
            widget.configure(text=self.app.t(key))
        self.close_button.configure(
            text=self.app.t("stop" if self.worker and self.worker.is_alive() else "close")
        )
        self.refresh()
        self._refresh_progress()

    def close(self):
        if self.worker and self.worker.is_alive():
            self.cancel_event.set()
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()
