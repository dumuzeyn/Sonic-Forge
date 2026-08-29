import argparse
import json
import sys
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cover_engine.concepts import CoverConcept
from cover_engine.diversity import DiversityController
from cover_engine.profiles import VisualProfile
from cover_engine.providers import AutoImageProvider, CoverRequest
from cover_engine.semantic_quality import SemanticQualityEvaluator
from cover_engine.typography import TypographyEngine


def main():
    parser = argparse.ArgumentParser(description="Finalize one reviewed AI candidate as a demo cover.")
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--concept", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--artist", default="")
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--size", type=int, default=512)
    parser.add_argument("--detail", choices=("simple", "balanced", "rich"), default="simple")
    args = parser.parse_args()

    data = json.loads(args.profile.read_text(encoding="utf-8"))
    candidate_data = next(
        item for item in data["candidates"]
        if item["concept"]["concept_id"].upper() == args.concept.upper()
    )
    concept = CoverConcept(**candidate_data["concept"])
    profile = VisualProfile(**data["visual_profile"])
    provider = AutoImageProvider(allow_fallback=False)
    try:
        artwork = provider.generate(CoverRequest(
            profile, concept, args.size, args.seed, args.detail, None, None,
        ))
    finally:
        provider.close()

    assessment = DiversityController().assess(concept, artwork.image)
    assessment = SemanticQualityEvaluator().apply(assessment, artwork.image, concept)
    if not assessment.accepted:
        raise RuntimeError("Проверенный вариант отклонён: " + "; ".join(assessment.reasons))

    typography = TypographyEngine()
    final = typography.compose(
        artwork.image,
        args.title,
        args.artist,
        profile=concept,
        enabled=True,
        show_artist=bool(args.artist),
        language=profile.language,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    final.save(args.output, "PNG", optimize=True)

    preview_path = args.profile.parent / candidate_data["preview"]
    preview = artwork.image.copy()
    preview.thumbnail((320, 320), Image.Resampling.LANCZOS)
    preview.save(preview_path, "JPEG", quality=78, optimize=True)
    data["cover_concept"] = concept.to_dict()
    data["provider"] = artwork.provider
    data["fallback"] = artwork.fallback
    data["provider_note"] = artwork.note
    data["quality_assessment"] = assessment.to_dict()
    data["typography"] = typography.last_layout
    for item in data["candidates"]:
        item["selected"] = item["concept"]["concept_id"] == concept.concept_id
        if item["selected"]:
            item["provider"] = artwork.provider
            item["fallback"] = artwork.fallback
            item["assessment"] = assessment.to_dict()
    args.profile.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Сохранён вариант {concept.concept_id}: {args.output}")


if __name__ == "__main__":
    main()
