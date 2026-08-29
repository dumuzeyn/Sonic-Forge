"""Compatibility facade for the embedded Music2Picture v2 renderer."""

from pathlib import Path

from music2picture_v2 import DEFAULT_PIPELINE, audio_files, render_cover


def make_cover(
    audio_path,
    output_path,
    size=1000,
    patterns=2,
    center_title=False,
    seed=None,
    analysis_bundle=None,
    **_ignored,
):
    del patterns, center_title
    bundle = analysis_bundle or DEFAULT_PIPELINE.analyse(audio_path)
    image = render_cover(bundle.visual_dna, bundle.visual_plan, size=size, seed=seed)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, "PNG", optimize=True)
    return output_path


def make_covers(source, output, size=1000, seed=None, **kwargs):
    source_path = Path(source).resolve()
    source_base = source_path.parent if source_path.is_file() else source_path
    output = Path(output).resolve()
    results = []
    for index, path in enumerate(audio_files(source_path)):
        relative = path.relative_to(source_base).with_suffix("")
        target = output / relative.parent / f"{relative.name}_cover_{size}.png"
        results.append(make_cover(path, target, size=size, seed=None if seed is None else seed + index, **kwargs))
    return results
