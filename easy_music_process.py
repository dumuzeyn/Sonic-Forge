import argparse
import importlib.util
import sys
from pathlib import Path

import music2picture
import music_metadata


SCRIPT_DIR = Path(__file__).resolve().parent


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
        print("Введите путь к папке.")


def ask_settings():
    source = ask_path("Папка с песнями: ")
    output = ask_path("Папка, куда все сохранить: ")
    genre = input("Жанр для всех песен или Enter для автоопределения: ").strip()
    return source, output, genre or None


def process_music(source, output, genre=None):
    source_path = Path(source).expanduser()
    output_path = Path(output).expanduser()
    covers_path = output_path / "covers"

    print("\nШаг 1/3: нормализация и усиление звука")
    normalize_music_file.normalize_music(source_path, output_path)

    print("\nШаг 2/3: запись чистых тегов title и genre")
    music_metadata.require_ffmpeg()
    music_metadata.update_music_metadata(output_path, genre_override=genre)

    print("\nШаг 3/3: создание и привязка обложек")
    music2picture.require_ffmpeg()
    music2picture.make_covers(
        output_path,
        covers_path,
        size=1000,
        patterns=2,
        center_title=True,
        embed=True,
    )

    print(f"\nГотово. Песни сохранены в: {output_path.resolve()}")
    print(f"Обложки сохранены в: {covers_path.resolve()}")


def main():
    parser = argparse.ArgumentParser(
        description="Simple all-in-one music processor: normalize, clean metadata, create and embed covers."
    )
    parser.add_argument("--source", help="Folder with source songs.")
    parser.add_argument("--output", help="Folder where processed songs and covers will be saved.")
    parser.add_argument("--genre", help="Set one genre for all songs. Leave empty or omit for auto-detect.")
    args = parser.parse_args()

    if args.source and args.output:
        source, output, genre = args.source, args.output, args.genre
    else:
        source, output, genre = ask_settings()

    process_music(source, output, genre=genre)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
