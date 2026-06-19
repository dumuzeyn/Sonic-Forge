import argparse
import importlib.util
import sys
from pathlib import Path

import music2picture
import music_metadata


SCRIPT_DIR = Path(__file__).resolve().parent

# PyCharm / direct Python run settings.
# Set RUN_FROM_CODE = True, edit the paths below, then press Run.
RUN_FROM_CODE = False
CODE_SOURCE = r"C:\Path\To\MusicFolder"
CODE_OUTPUT = r"C:\Path\To\ProcessedMusic"
CODE_GENRE = None
CODE_COLOR_MODE = "drive"  # "bpm" = original cover colors, "drive" = local drive colors
CODE_FINAL_GAIN = 1.15
CODE_DENOISE = True
CODE_DENOISE_STRENGTH = 4.0
CODE_LIMITER = True
CODE_OVERWRITE_GENRE = False


def load_python_file(name, filename):
    module_path = SCRIPT_DIR / filename
    spec = importlib.util.spec_from_file_location(name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


normalize_music_file = load_python_file("normalize_music_file", "Normalize-Music.py")


def ask_path(prompt):
    while True:
        value = input(prompt).strip().strip('"')
        if value:
            return value
        print("Please enter a path.")


def ask_settings():
    source = ask_path("Source folder or audio file: ")
    output = ask_path("Output folder: ")
    genre = input("Genre for songs without genre, or Enter for auto-detect: ").strip()
    return source, output, genre or None


def process_music(
    source,
    output,
    genre=None,
    color_mode="drive",
    final_gain=1.15,
    denoise=True,
    denoise_strength=4.0,
    limiter=True,
    overwrite_genre=False,
):
    source_path = Path(source).expanduser()
    output_path = Path(output).expanduser()
    covers_path = output_path / "covers"

    print("\nStep 1/3: normalize, gently denoise, and safely boost audio")
    normalize_music_file.normalize_music(
        source_path,
        output_path,
        final_gain=final_gain,
        denoise=denoise,
        denoise_strength=denoise_strength,
        limiter=limiter,
    )

    print("\nStep 2/3: write clean title/genre metadata")
    music_metadata.require_ffmpeg()
    music_metadata.update_music_metadata(
        output_path,
        genre_override=genre,
        overwrite_genre=overwrite_genre,
    )

    print("\nStep 3/3: create and embed covers")
    music2picture.require_ffmpeg()
    music2picture.make_covers(
        output_path,
        covers_path,
        size=1000,
        patterns=2,
        center_title=True,
        embed=True,
        color_mode=color_mode,
    )

    print(f"\nDone. Songs are saved in: {output_path.resolve()}")
    print(f"Covers are saved in: {covers_path.resolve()}")


def main():
    parser = argparse.ArgumentParser(
        description="All-in-one music processor: normalize audio, clean metadata, create and embed covers."
    )
    parser.add_argument("--source", help="Folder with source songs or one audio file.")
    parser.add_argument("--output", help="Folder where processed songs and covers will be saved.")
    parser.add_argument("--genre", help="Set genre for songs that do not already have genre. Omit for auto-detect.")
    parser.add_argument("--color-mode", choices=["bpm", "drive"], default="drive", help="Cover color mode. drive is the local-dynamics palette.")
    parser.add_argument("--final-gain", type=float, default=1.15, help="Extra gain after loudnorm. Lower than old 1.30 to avoid artifacts.")
    parser.add_argument("--denoise", dest="denoise", action="store_true", default=True, help="Use gentle denoise. Enabled by default.")
    parser.add_argument("--no-denoise", dest="denoise", action="store_false", help="Disable denoise.")
    parser.add_argument("--denoise-strength", type=float, default=4.0, help="Gentle denoise amount in dB.")
    parser.add_argument("--limiter", dest="limiter", action="store_true", default=True, help="Use final limiter. Enabled by default.")
    parser.add_argument("--no-limiter", dest="limiter", action="store_false", help="Disable final limiter.")
    parser.add_argument("--overwrite-genre", action="store_true", help="Replace existing genre tags. Default keeps them.")
    args = parser.parse_args()

    if args.source and args.output:
        source, output, genre = args.source, args.output, args.genre
    else:
        source, output, genre = ask_settings()

    process_music(
        source,
        output,
        genre=genre,
        color_mode=args.color_mode,
        final_gain=args.final_gain,
        denoise=args.denoise,
        denoise_strength=args.denoise_strength,
        limiter=args.limiter,
        overwrite_genre=args.overwrite_genre,
    )


def run_from_code_settings():
    process_music(
        CODE_SOURCE,
        CODE_OUTPUT,
        genre=CODE_GENRE,
        color_mode=CODE_COLOR_MODE,
        final_gain=CODE_FINAL_GAIN,
        denoise=CODE_DENOISE,
        denoise_strength=CODE_DENOISE_STRENGTH,
        limiter=CODE_LIMITER,
        overwrite_genre=CODE_OVERWRITE_GENRE,
    )


if __name__ == "__main__":
    try:
        if RUN_FROM_CODE:
            run_from_code_settings()
        else:
            main()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
