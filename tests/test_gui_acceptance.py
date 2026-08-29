import tkinter as tk
import unittest
from tkinter import ttk

import music_polisher_gui
from lyrics_engine import LyricsResult
from ui.model_manager_dialog import ImageModelManagerDialog
from ui.widgets import ModernScale, SquareCheckbutton


class GuiAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = music_polisher_gui.SonicForgeApp()
        cls.app.update_idletasks()

    @classmethod
    def tearDownClass(cls):
        cls.app.destroy()

    def setUp(self):
        if self.app.language != "ru":
            self.app.toggle_language()
        self.app.clear_log()
        self.app.write_log(self.app.t("log_ready") + "\n")
        self.app._set_lyrics_status("lyrics_status_empty")
        self.app.view.show_tab("metadata")
        self.app.update_idletasks()

    def test_window_is_compact_and_pages_do_not_force_resize(self):
        widths = []
        geometry = self.app.geometry()
        for name, page in self.app.view.tab_pages.items():
            self.app.view.show_tab(name)
            self.app.update_idletasks()
            widths.append(page.winfo_reqwidth())
            self.assertEqual(self.app.geometry(), geometry)
        self.assertLessEqual(max(widths), 900)
        width, height = map(int, geometry.split("+")[0].split("x"))
        self.assertGreaterEqual(width / height, 4 / 3)

    def test_log_is_read_only_but_copyable(self):
        self.app.clear_log()
        self.app.write_log("first line\nsecond line\n")
        self.assertEqual(self.app.view.log.cget("state"), tk.DISABLED)
        self.app.select_all_log()
        self.app.copy_log_selection()
        self.assertEqual(self.app.clipboard_get(), "first line\nsecond line\n")
        self.app.copy_log()
        self.assertEqual(self.app.clipboard_get(), "first line\nsecond line\n")

    def test_all_tab_buttons_have_the_same_declared_grid_weight(self):
        tab_bar = next(iter(self.app.view.tab_buttons.values())).master
        weights = [tab_bar.grid_columnconfigure(i)["weight"] for i in range(5)]
        uniforms = [tab_bar.grid_columnconfigure(i)["uniform"] for i in range(5)]
        self.assertEqual(weights, [1] * 5)
        self.assertEqual(uniforms, ["tabs"] * 5)

    def test_audio_page_uses_stable_custom_sliders_and_neutral_defaults(self):
        self.app.view.show_tab("audio")
        self.app.update_idletasks()
        sliders = [widget for widget in _descendants(self.app.view.tab_pages["audio"]) if isinstance(widget, ModernScale)]
        self.assertEqual(len(sliders), 5)
        self.assertEqual(self.app.final_gain_var.get(), 1.0)
        self.assertFalse(self.app.highpass_enabled_var.get())
        self.assertFalse(self.app.lowpass_enabled_var.get())
        self.assertEqual(self.app.audio_option_key("sample_rate"), "source")
        self.assertEqual(self.app.audio_option_key("channels"), "source")

    def test_language_switch_updates_status_log_and_open_dialogs(self):
        self.assertTrue(self.app.lyrics_status_var.get().startswith("Текст ещё"))
        self.app.show_advanced_audio()
        self.app.toggle_language()
        self.app.update_idletasks()
        self.assertTrue(self.app.lyrics_status_var.get().startswith("No lyrics"))
        self.assertEqual(self.app.view.log.get("1.0", "end-1c"), "Ready.\n")
        self.assertEqual(self.app.advanced_dialog.title(), self.app.t("advanced_title"))
        self.app.advanced_dialog.destroy()
        self.app.advanced_dialog = None

        self.app.show_additional_metadata()
        self.app.toggle_language()
        self.app.update_idletasks()
        self.assertEqual(
            self.app.metadata_dialog.title(),
            self.app.t("additional_metadata_title"),
        )
        self.app.metadata_dialog.destroy()
        self.app.metadata_dialog = None

    def test_detected_language_and_quality_relocalize(self):
        self.app._apply_lyrics_result(
            LyricsResult(
                text="Test lyrics here",
                language="en",
                language_confidence=0.91,
                quality="high",
            )
        )
        self.assertIn("Английский", self.app.lyrics_status_var.get())
        self.assertIn("высокое", self.app.lyrics_status_var.get())
        self.app.toggle_language()
        self.assertIn("English", self.app.lyrics_status_var.get())
        self.assertIn("high", self.app.lyrics_status_var.get())

    def test_no_visible_primary_text_is_clipped_in_ru_or_en(self):
        failures = []
        for language in ("ru", "en"):
            if self.app.language != language:
                self.app.toggle_language()
            for page_name, page in self.app.view.tab_pages.items():
                self.app.view.show_tab(page_name)
                self.app.update_idletasks()
                for widget in _descendants(page):
                    if not widget.winfo_ismapped() or not isinstance(
                        widget,
                        (tk.Label, tk.Button, ttk.Label, ttk.Button, ttk.Menubutton, SquareCheckbutton),
                    ):
                        continue
                    text = widget.cget("text") if "text" in widget.keys() else ""
                    if text and widget.winfo_width() + 2 < widget.winfo_reqwidth():
                        failures.append(
                            (language, page_name, text, widget.winfo_width(), widget.winfo_reqwidth())
                        )
        self.assertEqual(failures, [])

    def test_model_dialog_relocalizes_without_reopening(self):
        dialog = ImageModelManagerDialog(self.app, manager=self.app.image_model_manager)
        self.app.model_dialog = dialog
        self.app.toggle_language()
        self.app.update_idletasks()
        self.assertEqual(dialog.title(), self.app.t("model_manager_title"))
        self.assertEqual(dialog.download_button.cget("text"), self.app.t("model_download"))
        dialog.close()
        self.app.model_dialog = None

    def test_cover_engines_are_separate_and_model_button_matches_selection(self):
        self.app.cover_engine_var.set("Music2Picture v2")
        self.app.cover_engine_changed()
        self.assertEqual(self.app.cover_choice("engine", self.app.cover_engine_var.get()), "music2picture_v2")
        self.assertIn("disabled", self.app.view.model_button.state())
        self.app.cover_engine_var.set("AI-обложка")
        self.app.cover_engine_changed()
        self.assertEqual(self.app.cover_choice("engine", self.app.cover_engine_var.get()), "ai")
        self.assertNotIn("disabled", self.app.view.model_button.state())


def _descendants(widget):
    children = list(widget.winfo_children())
    for child in children:
        yield child
        yield from _descendants(child)


if __name__ == "__main__":
    unittest.main()
