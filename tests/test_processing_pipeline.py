import tempfile
import unittest
import wave
import json
from pathlib import Path
from unittest import mock

from easy_music_process import process_music
from lyrics_engine import LyricsResult, LyricsService, TranscriptSegment
from lyrics_engine.providers import MockLyricsProvider
from cover_engine import MockImageProvider


class FailingLyricsProvider:
    def transcribe(self, *args, **kwargs):
        raise RuntimeError("forced lyrics failure")

class ProcessingPipelineTests(unittest.TestCase):
    def test_cover_analysis_and_generation_happen_before_remaining_outputs(self):
        events = []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "song.wav"
            _write_silence(source)

            def normalize(_source, staging, **_kwargs):
                events.append("audio")
                Path(staging).mkdir(parents=True, exist_ok=True)

            with (
                mock.patch("easy_music_process.music2picture.make_covers", side_effect=lambda *a, **k: events.append("cover")),
                mock.patch("easy_music_process.normalize_music_file.normalize_music", side_effect=normalize),
                mock.patch("easy_music_process.music_metadata.update_music_metadata", side_effect=lambda *a, **k: events.append("metadata")),
                mock.patch("easy_music_process.music_metadata.require_ffmpeg"),
                mock.patch("easy_music_process.music2picture.require_ffmpeg"),
                mock.patch("lyrics_engine.recognize_batch", side_effect=lambda *a, **k: events.append("lyrics") or {}),
                mock.patch("easy_music_process.music2picture.apply_generated_covers", side_effect=lambda *a, **k: events.append("attach")),
            ):
                process_music(source, root / "out", process_steps={"audio", "metadata", "lyrics", "cover"})
        self.assertEqual(events, ["cover", "audio", "metadata", "lyrics", "attach"])

    def test_lyrics_is_an_independent_batch_stage(self):
        result = LyricsResult(
            text="Это настоящий тестовый текст песни",
            segments=(TranscriptSegment(0, 3, "Это настоящий тестовый текст песни", .95),),
            source="mock",
        )
        service = LyricsService(provider=MockLyricsProvider(result))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            output = root / "output"
            source.mkdir()
            for name in ("one.wav", "two.wav"):
                with wave.open(str(source / name), "wb") as audio:
                    audio.setnchannels(1)
                    audio.setsampwidth(2)
                    audio.setframerate(8000)
                    audio.writeframes(b"\0\0" * 24000)
            process_music(
                source,
                output,
                process_steps={"lyrics"},
                lyrics_service=service,
                lyrics_format="txt",
            )
            self.assertTrue((output / "one.txt").is_file())
            self.assertTrue((output / "two.txt").is_file())
            self.assertTrue((output / "one.wav").is_file())

    def test_instrumental_does_not_create_garbage_sidecar(self):
        service = LyricsService(provider=MockLyricsProvider(LyricsResult(text="oh", instrumental=False, source="mock")))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "instrumental.wav"
            with wave.open(str(source), "wb") as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(8000)
                audio.writeframes(b"\0\0" * 8000)
            process_music(source, root / "out", process_steps={"lyrics"}, lyrics_service=service)
            self.assertFalse((root / "out" / "instrumental.txt").exists())

    def test_existing_lyrics_reach_cover_semantics_before_generation(self):
        result = LyricsResult(
            text="ночной поезд уходит сквозь дождь по дороге домой",
            segments=(TranscriptSegment(0, 3, "ночной поезд уходит сквозь дождь по дороге домой", .95),),
            source="mock",
        )
        service = LyricsService(provider=MockLyricsProvider(result))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "song.wav"
            _write_silence(source)
            source.with_suffix(".txt").write_text(result.text, encoding="utf-8")
            output = root / "out"
            process_music(
                source,
                output,
                process_steps={"lyrics", "cover"},
                lyrics_service=service,
                cover_provider=MockImageProvider(),
                cover_size=128,
            )
            profile_path = output / "covers" / ".sonicforge" / "song_cover_128.profile.json"
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            self.assertTrue(profile["visual_profile"]["lyrics_used"])
            self.assertIn("night", profile["visual_profile"]["themes"])
            self.assertTrue((output / "song.txt").is_file())

    def test_lyrics_failure_does_not_block_cover(self):
        service = LyricsService(provider=FailingLyricsProvider())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "song.wav"
            _write_silence(source)
            output = root / "out"
            process_music(
                source,
                output,
                process_steps={"lyrics", "cover"},
                lyrics_service=service,
                cover_provider=MockImageProvider(),
                cover_size=128,
            )
            self.assertTrue((output / "covers" / "song_cover_128.png").is_file())


def _write_silence(path):
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        audio.writeframes(b"\0\0" * 24000)

if __name__ == "__main__":
    unittest.main()
