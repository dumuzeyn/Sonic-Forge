from pathlib import Path

from .formats import find_sidecar, save_lyrics
from .service import LyricsService

def recognize_batch(
    source,
    staging,
    output=None,
    service=None,
    export_format="txt",
    overwrite=False,
    language="auto",
    cancel_event=None,
):
    import music_metadata

    source = Path(source).resolve()
    staging = Path(staging).resolve()
    output = Path(output).resolve() if output else None
    service = service or LyricsService(metadata_reader=music_metadata.read_all_metadata)
    source_base = source.parent if source.is_file() else source
    lyrics_lookup = {}
    staged_files = music_metadata.audio_files(staging)
    original_files = {
        path.relative_to(source_base).with_suffix(""): path
        for path in music_metadata.audio_files(source)
    }
    for index, staged_audio in enumerate(staged_files, start=1):
        if cancel_event is not None and cancel_event.is_set():
            raise InterruptedError("Lyrics recognition was cancelled")
        relative = staged_audio.relative_to(staging)
        original = original_files.get(relative.with_suffix(""))
        output_audio = output / relative if output else None
        existing_output = find_sidecar(output_audio) if output_audio else None
        if not overwrite and existing_output:
            destination = staged_audio.with_suffix(existing_output.suffix)
            destination.write_bytes(existing_output.read_bytes())
            loaded = service.load_existing(output_audio)
            if loaded and loaded.text.strip():
                lyrics_lookup[_relative_key(staged_audio, staging)] = loaded.text
            print(f"[{index}/{len(staged_files)}] Lyrics preserved: {staged_audio.name}")
            continue
        if not overwrite and original is not None and find_sidecar(original):
            existing = service.load_existing(original)
            if existing and existing.text.strip():
                existing_format = find_sidecar(original).suffix.lstrip(".")
                save_lyrics(staged_audio, existing, existing_format)
                lyrics_lookup[_relative_key(staged_audio, staging)] = existing.text
                print(f"[{index}/{len(staged_files)}] Existing lyrics copied: {staged_audio.name}")
                continue
        print(f"[{index}/{len(staged_files)}] Recognize lyrics: {staged_audio.name}")
        try:
            result = service.recognize(
                staged_audio,
                cancel_event=cancel_event,
                language=language,
            )
        except InterruptedError:
            raise
        except Exception as exc:
            message = str(exc).replace("\r", " ").replace("\n", " ").strip()
            print(
                f"[{index}/{len(staged_files)}] Lyrics unavailable: "
                f"{staged_audio.name} ({message[:180] or type(exc).__name__})"
            )
            continue
        if result.instrumental or not result.text.strip():
            print(f"[{index}/{len(staged_files)}] No reliable vocal text found: {staged_audio.name}")
            continue
        save_lyrics(staged_audio, result, export_format)
        lyrics_lookup[_relative_key(staged_audio, staging)] = result.text
    return lyrics_lookup

def _relative_key(audio_path, root):
    return str(Path(audio_path).relative_to(root).with_suffix("")).replace("\\", "/")
