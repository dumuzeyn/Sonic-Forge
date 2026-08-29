import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import music2picture
from cover_engine import AutoImageProvider, CoverComposer


TRACKS = (
    (
        "Трава у дома.mp3",
        "01_home_beyond_earth.png",
        "Космос, далёкие звёзды и орбита противопоставлены памяти о доме, земле и знакомом дворе.",
    ),
    (
        "В мире морском.mp3",
        "02_underwater_freedom.png",
        "Открытое море, волны, свобода, живой подводный мир и желание уйти от тесных человеческих правил.",
    ),
    (
        "К ЧЕРТУ ЛЮБОВЬ.mp3",
        "03_love_burned_away.png",
        "Прощание после болезненной любви: огонь, разбитое зеркало, гнев, освобождение и окончательный уход.",
    ),
    (
        "Грустный дэнс.mp3",
        "04_sad_dance.png",
        "Одинокий ночной танец после расставания, пустой танцпол, музыка продолжается вопреки печали.",
    ),
    (
        "Карты правду говорят.mp3",
        "05_cards_and_fate.png",
        "Карты, предсказание, выбор и судьба: свечи, стол гадалки и несколько возможных дорог впереди.",
    ),
)


def restore_existing_history(composer, output_dir, before_index):
    cache_dir = output_dir / ".sonicforge"
    for _, output_name, _ in TRACKS[:max(0, before_index - 1)]:
        profile_path = cache_dir / f"{Path(output_name).stem}.profile.json"
        if not profile_path.is_file():
            continue
        data = json.loads(profile_path.read_text(encoding="utf-8"))
        concept = data.get("cover_concept", {})
        assessment = data.get("quality_assessment", {})
        composer.diversity.history.append({
            "scene": concept.get("scene"),
            "main_symbol": concept.get("main_symbol"),
            "composition": concept.get("composition"),
            "palette_name": concept.get("palette_name"),
            "text_position": concept.get("text_position"),
            "candidate_type": concept.get("candidate_type"),
            "fingerprint": assessment.get("fingerprint", ""),
            "color_vector": tuple(assessment.get("color_vector", ())),
        })
        print(f"Учтена предыдущая обложка: {output_name}")


def main():
    parser = argparse.ArgumentParser(description="Generate the five Sonic Forge cover acceptance samples.")
    parser.add_argument("--music-root", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("demo_covers/local_ai"))
    parser.add_argument("--size", type=int, default=768)
    parser.add_argument("--detail", choices=("simple", "balanced", "rich"), default="rich")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--limit", type=int, default=len(TRACKS))
    args = parser.parse_args()

    provider = AutoImageProvider(allow_fallback=False)
    composer = CoverComposer(provider=provider)
    args.output.mkdir(parents=True, exist_ok=True)
    restore_existing_history(composer, args.output, args.start)
    try:
        selected = TRACKS[max(0, args.start - 1):max(0, args.start - 1) + max(1, args.limit)]
        for index, (filename, output_name, semantic_text) in enumerate(selected, start=args.start):
            source = args.music_root / filename
            if not source.is_file():
                raise FileNotFoundError(source)
            print(f"\n=== DEMO {index}/{len(TRACKS)}: {filename} ===")
            music2picture.make_cover(
                source,
                args.output / output_name,
                size=args.size,
                seed=8210 + index * 101,
                lyrics_text=semantic_text,
                detail=args.detail,
                text_mode="title_artist",
                provider=provider,
                composer=composer,
            )
    finally:
        provider.close()


if __name__ == "__main__":
    main()
