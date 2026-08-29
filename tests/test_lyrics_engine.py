import tempfile
import unittest
from pathlib import Path

from lyrics_engine import LyricsResult, LyricsService, TranscriptSegment, load_sidecar, save_lyrics
from lyrics_engine.providers import MockLyricsProvider
from lyrics_engine.service import detect_text_languages


class LyricsEngineTests(unittest.TestCase):
    def test_txt_and_lrc_use_same_base_name(self):
        result = LyricsResult(
            text="Первая строка\nSecond line",
            segments=(
                TranscriptSegment(1.25, 3.0, "Первая строка"),
                TranscriptSegment(65.5, 68.0, "Second line"),
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "Song.mp3"
            audio.touch()
            txt = save_lyrics(audio, result, "txt")
            self.assertEqual(txt.name, "Song.txt")
            txt.unlink()
            lrc = save_lyrics(audio, result, "lrc")
            self.assertEqual(lrc.name, "Song.lrc")
            self.assertIn("[01:05.50]Second line", lrc.read_text(encoding="utf-8"))
            loaded = load_sidecar(audio)
            self.assertEqual(len(loaded.segments), 2)

    def test_language_detection_reports_mixed_script(self):
        language, confidence, mixed = detect_text_languages("Привет my love, это наша night")
        self.assertEqual(language, "mixed")
        self.assertGreater(confidence, 0.4)
        self.assertEqual(set(mixed), {"ru", "en/latin"})

    def test_service_provider_route_and_error_are_testable(self):
        expected = LyricsResult(text="Hello world again", source="mock")
        service = LyricsService(provider=MockLyricsProvider(expected))
        actual = service.recognize("unused.mp3")
        self.assertEqual(actual.text, expected.text)
        self.assertEqual(actual.language, "en/latin")


if __name__ == "__main__":
    unittest.main()
