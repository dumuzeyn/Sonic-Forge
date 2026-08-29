from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from music2picture_v2 import (
    DEFAULT_PIPELINE,
    DescriptionStore,
    audio_files,
    generate_descriptions,
    render_cover,
)


STARTUP_KWARGS = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
ENGINE_AI = "ai"
ENGINE_MUSIC2PICTURE_V2 = "music2picture_v2"
COVER_ENGINES = (ENGINE_AI, ENGINE_MUSIC2PICTURE_V2)


def require_ffmpeg():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("FFmpeg and FFprobe are required")


def clean_stem(path):
    return Path(path).stem.replace("_normalized", "").strip()


def check_cancelled(cancel_event):
    if cancel_event is not None and cancel_event.is_set():
        raise InterruptedError("Processing was cancelled")


def make_cover(
    audio_path,
    output_path,
    size=1000,
    seed=None,
    lyrics_text="",
    detail="balanced",
    text_mode="none",
    mood_override="auto",
    engine=ENGINE_AI,
    provider=None,
    composer=None,
    cancel_event=None,
    regenerate_description=False,
    **_compatibility,
):
    """Analyze one track, persist its text artifacts, then render with one engine."""
    require_ffmpeg()
    path = Path(audio_path).resolve()
    output_path = Path(output_path)
    if engine not in COVER_ENGINES:
        raise ValueError(f"Unknown cover engine: {engine}")
    check_cancelled(cancel_event)

    import music_metadata
    from lyrics_engine import LyricsService

    tags = music_metadata.read_all_metadata(path)
    resolved_lyrics = LyricsService(metadata_reader=music_metadata.read_all_metadata).resolve_for_cover(
        path, supplied_text=lyrics_text
    )
    variation = int(seed or 0)
    stages = {
        "loading_audio": "Загрузка звука",
        "analysing_rhythm": "Анализ ритма",
        "analysing_timbre": "Анализ тембра",
        "analysing_harmony": "Анализ гармонии",
        "analysing_structure": "Анализ структуры песни",
        "building_visual_dna": "Создание VisualDNA",
        "creating_song_description": "Создание описания песни",
        "creating_visual_plan": "Создание визуального плана",
        "creating_visual_brief": "Подготовка задания для генератора",
    }

    def progress(stage):
        check_cancelled(cancel_event)
        print(stages.get(stage, stage))

    bundle = DEFAULT_PIPELINE.analyse(
        path,
        metadata=tags,
        lyrics=resolved_lyrics,
        mood_override=mood_override,
        variation=variation,
        progress=progress,
        force=regenerate_description,
    )
    DescriptionStore().put(path, bundle)
    print(f"Описание песни: {bundle.song_description}")
    check_cancelled(cancel_event)

    title = tags.get("title") or clean_stem(path)
    artist = tags.get("artist", "")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if engine == ENGINE_MUSIC2PICTURE_V2:
        print("Движок обложки: Music2Picture v2")
        image = render_cover(bundle.visual_dna, bundle.visual_plan, size=size, seed=seed)
        if text_mode != "none":
            from cover_engine.typography import TypographyEngine

            image = TypographyEngine().compose(
                image,
                title,
                artist,
                enabled=True,
                show_artist=text_mode == "title_artist",
                language=bundle.language,
            )
        image.save(output_path, "PNG", optimize=True)
        _save_music2picture_profile(output_path, path, bundle, seed, text_mode)
        print(f"Обложка сохранена: {output_path} (Music2Picture v2)")
        return output_path

    print("Движок обложки: локальная AI-генерация")
    from cover_engine import AutoImageProvider, CoverComposer, SongContext

    dna = bundle.visual_dna
    song = SongContext(
        title=title,
        artist=artist,
        album=tags.get("album", ""),
        genre=tags.get("genre", ""),
        lyrics=resolved_lyrics,
        duration=bundle.analysis.duration,
        bpm=dna.tempo,
        speed=dna.arousal,
        beat_density=dna.rhythmic_density,
        rhythmicity=dna.rhythmic_regularity,
        tempo_variation=dna.dynamic_complexity,
        change_rate=dna.section_contrast,
        relaxation=dna.relaxation,
        hardness=dna.aggressiveness,
        brightness=dna.brightness,
        bass_weight=dna.bass_mass,
        dynamic_range=dna.original_dynamic_range,
        mood_override=mood_override,
        visual_dna=dna,
        visual_plan=bundle.visual_plan,
        song_description=bundle.song_description,
        visual_brief=bundle.visual_brief,
    )
    owns_provider = provider is None and composer is None
    if composer is None:
        provider = provider or AutoImageProvider()
        composer = CoverComposer(provider=provider)
    try:
        result, _profile, _concept, artwork = composer.create(
            song,
            output_path,
            size=size,
            seed=seed,
            text_mode=text_mode,
            detail=detail,
            audio_path=path,
            cancel_event=cancel_event,
            analysis_bundle=bundle,
        )
    finally:
        if owns_provider and provider is not None:
            provider.close()
    print(f"Обложка сохранена: {result} ({artwork.provider})")
    return result


def make_covers(
    source,
    output,
    size=1000,
    embed=False,
    seed=None,
    lyrics_text="",
    lyrics_lookup=None,
    detail="balanced",
    text_mode="none",
    mood_override="auto",
    engine=ENGINE_AI,
    provider=None,
    cancel_event=None,
    continue_on_error=True,
):
    source_path = Path(source).resolve()
    output_root = Path(output).resolve()
    files = audio_files(source_path)
    if not files:
        raise RuntimeError(f"No supported audio files found in {source_path}")
    source_base = source_path.parent if source_path.is_file() else source_path
    owns_provider = engine == ENGINE_AI and provider is None
    composer = None
    if engine == ENGINE_AI:
        from cover_engine import AutoImageProvider, CoverComposer

        provider = provider or AutoImageProvider()
        composer = CoverComposer(provider=provider)
    results = []
    errors = []
    try:
        for index, path in enumerate(files, start=1):
            check_cancelled(cancel_event)
            relative = path.relative_to(source_base).with_suffix("")
            target = output_root / relative.parent / f"{relative.name}_cover_{size}.png"
            relative_key = str(relative).replace("\\", "/")
            file_lyrics = lyrics_text
            if lyrics_lookup:
                file_lyrics = lyrics_lookup.get(relative_key, lyrics_lookup.get(path.stem, file_lyrics))
            print(f"[{index}/{len(files)}] {path.name}")
            try:
                cover = make_cover(
                    path,
                    target,
                    size=size,
                    seed=None if seed is None else int(seed) + index - 1,
                    lyrics_text=file_lyrics,
                    detail=detail,
                    text_mode=text_mode,
                    mood_override=mood_override,
                    engine=engine,
                    provider=provider,
                    composer=composer,
                    cancel_event=cancel_event,
                )
                if embed:
                    embed_cover(path, cover)
                results.append(cover)
            except InterruptedError:
                raise
            except Exception as exc:
                errors.append((path, str(exc)))
                print(f"Ошибка для {path.name}: {exc}")
                if not continue_on_error or len(files) == 1:
                    raise
    finally:
        if owns_provider and provider is not None:
            provider.close()
    print(f"Готово обложек: {len(results)}; ошибок: {len(errors)}")
    return results


def generate_text_descriptions(
    source,
    *,
    output=None,
    regenerate=False,
    include_visual_brief=True,
    cancel_event=None,
    progress=None,
):
    import music_metadata
    from lyrics_engine import LyricsService

    lyrics_service = LyricsService(metadata_reader=music_metadata.read_all_metadata)

    def lyrics_reader(path):
        value = lyrics_service.load_existing(path)
        return value.text if value is not None else ""

    results = generate_descriptions(
        source,
        metadata_reader=music_metadata.read_all_metadata,
        lyrics_reader=lyrics_reader,
        regenerate=regenerate,
        include_visual_brief=include_visual_brief,
        cancel_event=cancel_event,
        progress=progress,
    )
    if output:
        records = []
        for item in results:
            records.append({
                "path": str(item.path),
                "status": item.status,
                "fingerprint": item.fingerprint,
                "song_description": item.song_description,
                "visual_brief": item.visual_brief,
                "error": item.error,
            })
        DescriptionStore().export(records, Path(output) / ".sonicforge" / "track_descriptions.json")
    return results


def embed_cover(mp3_path, image_path):
    mp3_path = Path(mp3_path)
    if mp3_path.suffix.lower() != ".mp3":
        return False
    temporary = mp3_path.with_name(f"{mp3_path.stem}.cover_tmp.mp3")
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(mp3_path), "-i", str(image_path),
            "-map", "0:a:0", "-map", "1:v:0", "-c:a", "copy", "-c:v", "mjpeg",
            "-disposition:v:0", "attached_pic", "-map_metadata", "0", "-id3v2_version", "3", str(temporary),
        ],
        check=True,
        **STARTUP_KWARGS,
    )
    temporary.replace(mp3_path)
    return True


def apply_generated_covers(audio_root, generated_root, published_root, size=1000, embed=True, cancel_event=None):
    audio_root = Path(audio_root).resolve()
    generated_root = Path(generated_root).resolve()
    published_root = Path(published_root).resolve()
    files = audio_files(audio_root)
    base = audio_root.parent if audio_root.is_file() else audio_root
    applied = 0
    for audio_path in files:
        check_cancelled(cancel_event)
        relative = audio_path.relative_to(base).with_suffix("")
        cover = generated_root / relative.parent / f"{relative.name}_cover_{size}.png"
        if not cover.exists():
            print(f"Обложка не найдена для {audio_path.name}")
            continue
        published = published_root / relative.parent / cover.name
        published.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cover, published)
        profile = cover.parent / ".sonicforge" / f"{cover.stem}.profile.json"
        if profile.exists():
            published_profile = published.parent / ".sonicforge" / profile.name
            published_profile.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(profile, published_profile)
        if embed:
            embed_cover(audio_path, cover)
        applied += 1
    print(f"Обложки привязаны к файлам: {applied}")
    return applied


def _save_music2picture_profile(output_path, audio_path, bundle, seed, text_mode):
    import json

    directory = output_path.parent / ".sonicforge"
    directory.mkdir(parents=True, exist_ok=True)
    data = {
        "engine": "Music2Picture v2",
        "audio_path": str(audio_path),
        "seed": seed,
        "text_mode": text_mode,
        "analysis_bundle": bundle.to_dict(),
    }
    target = directory / f"{output_path.stem}.profile.json"
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(target)


def main():
    parser = argparse.ArgumentParser(description="Sonic Forge cover and song-description tools")
    subparsers = parser.add_subparsers(dest="command", required=True)
    covers = subparsers.add_parser("covers")
    covers.add_argument("--source", required=True)
    covers.add_argument("--output", required=True)
    covers.add_argument("--engine", choices=COVER_ENGINES, default=ENGINE_AI)
    covers.add_argument("--size", type=int, default=1000)
    covers.add_argument("--seed", type=int)
    covers.add_argument("--text-mode", choices=("none", "title", "title_artist"), default="none")
    descriptions = subparsers.add_parser("describe")
    descriptions.add_argument("--source", required=True)
    descriptions.add_argument("--output")
    descriptions.add_argument("--regenerate", action="store_true")
    args = parser.parse_args()
    if args.command == "covers":
        make_covers(args.source, args.output, engine=args.engine, size=args.size, seed=args.seed, text_mode=args.text_mode)
    else:
        generate_text_descriptions(args.source, output=args.output, regenerate=args.regenerate)


if __name__ == "__main__":
    main()
