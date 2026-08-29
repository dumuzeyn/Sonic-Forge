from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from .pipeline import DEFAULT_PIPELINE, Music2PicturePipeline
from .storage import DescriptionStore


AUDIO_EXTENSIONS = {".mp3", ".flac", ".wav", ".m4a", ".aac", ".ogg", ".opus", ".wma"}


@dataclass(frozen=True)
class BatchDescriptionResult:
    path: Path
    status: str
    song_description: str = ""
    visual_brief: str = ""
    fingerprint: str = ""
    error: str = ""


BatchProgress = Callable[[int, int, Path, str], None]


def audio_files(source: str | Path) -> list[Path]:
    path = Path(source).resolve()
    if path.is_file():
        return [path] if path.suffix.lower() in AUDIO_EXTENSIONS else []
    if not path.is_dir():
        return []
    return sorted((item for item in path.rglob("*") if item.is_file() and item.suffix.lower() in AUDIO_EXTENSIONS), key=lambda item: str(item).lower())


def generate_descriptions(
    source: str | Path,
    *,
    pipeline: Music2PicturePipeline | None = None,
    store: DescriptionStore | None = None,
    metadata_reader: Callable[[Path], Mapping[str, object]] | None = None,
    lyrics_reader: Callable[[Path], str] | None = None,
    regenerate: bool = False,
    include_visual_brief: bool = True,
    mood_override: str = "auto",
    progress: BatchProgress | None = None,
    cancel_event=None,
) -> list[BatchDescriptionResult]:
    """Generate and persist independent descriptions for every valid track."""
    pipeline = pipeline or DEFAULT_PIPELINE
    store = store or DescriptionStore()
    files = audio_files(source)
    results: list[BatchDescriptionResult] = []
    total = len(files)
    for index, path in enumerate(files, start=1):
        if cancel_event is not None and cancel_event.is_set():
            raise InterruptedError("Description generation was cancelled")
        cached = None if regenerate else store.get(path)
        if cached is not None:
            _notify(progress, index, total, path, "cached")
            results.append(BatchDescriptionResult(
                path=path,
                status="cached",
                song_description=cached.get("song_description", ""),
                visual_brief=cached.get("visual_brief", "") if include_visual_brief else "",
                fingerprint=cached.get("fingerprint", ""),
            ))
            continue
        try:
            metadata = dict(metadata_reader(path)) if metadata_reader else {}
            lyrics = lyrics_reader(path) if lyrics_reader else ""
            bundle = pipeline.analyse(
                path,
                metadata=metadata,
                lyrics=lyrics or "",
                mood_override=mood_override,
                force=regenerate,
                progress=lambda stage, i=index, p=path: _notify(progress, i, total, p, stage),
            )
            record = store.put(path, bundle)
            results.append(BatchDescriptionResult(
                path=path,
                status="generated",
                song_description=record["song_description"],
                visual_brief=record["visual_brief"] if include_visual_brief else "",
                fingerprint=record["fingerprint"],
            ))
            _notify(progress, index, total, path, "saved")
        except InterruptedError:
            raise
        except Exception as exc:
            results.append(BatchDescriptionResult(path=path, status="error", error=str(exc)))
            _notify(progress, index, total, path, "error")
    return results


def _notify(callback, index, total, path, stage):
    if callback is not None:
        callback(index, total, path, stage)
