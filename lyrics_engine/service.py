import re
from pathlib import Path

from .formats import load_sidecar
from .models import LyricsResult
from .providers import FasterWhisperProvider


CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
LATIN_RE = re.compile(r"[A-Za-z]")


class LyricsService:
    def __init__(self, provider=None, metadata_reader=None):
        self.provider = provider or FasterWhisperProvider()
        self.metadata_reader = metadata_reader

    def load_existing(self, audio_path):
        result = load_sidecar(audio_path)
        if result is None and self.metadata_reader is not None:
            tags = self.metadata_reader(Path(audio_path))
            text = tags.get("lyrics") or tags.get("unsyncedlyrics") or ""
            if text.strip():
                result = LyricsResult(text=text.strip(), source="metadata")
        if result is None:
            return None
        return self._with_language(result)

    def recognize(self, audio_path, cancel_event=None, progress=None, language=None):
        result = self.provider.transcribe(
            audio_path, cancel_event=cancel_event, progress=progress, language=language
        )
        result = self._with_language(result)
        if not self.is_usable(result):
            return LyricsResult(
                text="",
                language=result.language,
                language_confidence=result.language_confidence,
                quality="low",
                instrumental=True,
                source=result.source,
            )
        return result

    def resolve_for_cover(self, audio_path, supplied_text=""):
        if supplied_text and supplied_text.strip():
            return supplied_text.strip()
        result = self.load_existing(audio_path)
        return result.text if result else ""

    @staticmethod
    def is_usable(result):
        words = re.findall(r"[\w'-]+", result.text or "", re.UNICODE)
        speech_duration = sum(max(0.0, segment.end - segment.start) for segment in result.segments)
        confidences = [segment.confidence for segment in result.segments if segment.confidence is not None]
        average = sum(confidences) / len(confidences) if confidences else 1.0
        if result.instrumental or len(words) < 3 or average < 0.35:
            return False
        return not result.segments or speech_duration >= 1.0

    @staticmethod
    def _with_language(result):
        language, confidence, mixed = detect_text_languages(result.text)
        provider_language = result.language if result.language != "unknown" else language
        if mixed:
            provider_language = "mixed"
        provider_confidence = result.language_confidence
        if provider_confidence is None:
            provider_confidence = confidence
        return LyricsResult(
            text=result.text,
            segments=result.segments,
            language=provider_language,
            language_confidence=provider_confidence,
            mixed_languages=mixed,
            quality=result.quality if result.quality != "unknown" else _quality_from_text(result.text),
            instrumental=result.instrumental,
            source=result.source,
        )


def detect_text_languages(text):
    cyrillic = len(CYRILLIC_RE.findall(text or ""))
    latin = len(LATIN_RE.findall(text or ""))
    total = cyrillic + latin
    if total == 0:
        return "unknown", 0.0, ()
    cyrillic_share = cyrillic / total
    latin_share = latin / total
    if cyrillic_share >= 0.85:
        return "ru", cyrillic_share, ()
    if latin_share >= 0.85:
        return "en/latin", latin_share, ()
    mixed = tuple(code for code, share in (("ru", cyrillic_share), ("en/latin", latin_share)) if share >= 0.12)
    return "mixed", max(cyrillic_share, latin_share), mixed


def _quality_from_text(text):
    words = len((text or "").split())
    if words >= 80:
        return "high"
    if words >= 20:
        return "medium"
    return "low"
