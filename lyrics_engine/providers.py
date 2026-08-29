import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from abc import ABC, abstractmethod

from .models import LyricsResult, TranscriptSegment


class LyricsProvider(ABC):
    name = "provider"

    @abstractmethod
    def transcribe(self, audio_path, cancel_event=None, progress=None, language=None):
        raise NotImplementedError


class FasterWhisperProvider(LyricsProvider):
    name = "faster-whisper"

    def __init__(self, model_name=None, device=None, compute_type=None):
        self.model_name = model_name or os.environ.get("SONIC_FORGE_WHISPER_MODEL", "base")
        self.device = device or os.environ.get("SONIC_FORGE_WHISPER_DEVICE", "cpu")
        self.compute_type = compute_type or os.environ.get("SONIC_FORGE_WHISPER_COMPUTE", "int8")

    @classmethod
    def available(cls):
        return importlib.util.find_spec("faster_whisper") is not None

    def transcribe(self, audio_path, cancel_event=None, progress=None, language=None):
        if not self.available():
            raise RuntimeError(
                "Локальный модуль распознавания не установлен. Установите faster-whisper "
                "или загрузите уже готовый TXT/LRC рядом с песней."
            )
        from faster_whisper import WhisperModel

        if progress:
            progress("loading_model")
        model = WhisperModel(self.model_name, device=self.device, compute_type=self.compute_type)
        segments = []
        with self._vocal_audio(audio_path) as prepared_audio:
            raw_segments, info = model.transcribe(
                str(prepared_audio),
                language=None if language in (None, "", "auto") else language,
                beam_size=5,
                vad_filter=True,
                word_timestamps=False,
                condition_on_previous_text=True,
            )
            for raw in raw_segments:
                if cancel_event is not None and cancel_event.is_set():
                    raise InterruptedError("Lyrics recognition was cancelled.")
                text = raw.text.strip()
                if text:
                    confidence = max(
                        0.0,
                        min(1.0, 1.0 - float(getattr(raw, "no_speech_prob", 0.0))),
                    )
                    segments.append(
                        TranscriptSegment(float(raw.start), float(raw.end), text, confidence)
                    )
                    if progress:
                        progress("transcribing")
        text = "\n".join(segment.text for segment in segments)
        probability = getattr(info, "language_probability", None)
        average = sum(segment.confidence or 0 for segment in segments) / max(1, len(segments))
        return LyricsResult(
            text=text,
            segments=tuple(segments),
            language=getattr(info, "language", "unknown") or "unknown",
            language_confidence=float(probability) if probability is not None else None,
            quality=_quality(average),
            instrumental=not bool(segments),
            source=self.name,
        )

    def _vocal_audio(self, audio_path):
        return _PreparedVocalAudio(audio_path)


class MockLyricsProvider(LyricsProvider):
    name = "mock"

    def __init__(self, result):
        self.result = result

    def transcribe(self, audio_path, cancel_event=None, progress=None, language=None):
        return self.result


def _quality(confidence):
    if confidence >= 0.82:
        return "high"
    if confidence >= 0.58:
        return "medium"
    return "low"


class _PreparedVocalAudio:
    def __init__(self, audio_path):
        self.audio_path = audio_path
        self.directory = None
        self.path = audio_path

    def __enter__(self):
        if not shutil.which("ffmpeg"):
            return self.audio_path
        self.directory = tempfile.TemporaryDirectory(prefix="sonicforge_lyrics_")
        self.path = os.path.join(self.directory.name, "vocals.wav")
        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(self.audio_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-af",
            "highpass=f=100,lowpass=f=10000,dynaudnorm=f=150:g=9",
            self.path,
        ]
        kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, **kwargs)
        return self.path

    def __exit__(self, exc_type, exc_value, traceback):
        if self.directory is not None:
            self.directory.cleanup()
