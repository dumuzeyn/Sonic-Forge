import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

import open_clip
import torch
from PIL import Image


NEGATIVE_LABELS = (
    "an indoor corridor or hallway",
    "a lone person standing in a dark passage",
    "an empty glowing doorway or tunnel",
    "a generic abstract album cover",
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", type=Path)
    args = parser.parse_args()
    data = json.loads(args.profile.read_text(encoding="utf-8"))
    model, _, preprocess = open_clip.create_model_and_transforms(
        "ViT-B-32", pretrained="laion2b_s34b_b79k", device="cpu"
    )
    tokenizer = open_clip.get_tokenizer("ViT-B-32")
    for item in data["candidates"]:
        concept = item["concept"]
        labels = (
            f"{concept['main_symbol']} in {concept['scene']}",
            concept["main_symbol"],
            concept["scene"],
            f"an empty {concept['scene']} landscape with no main object",
            *NEGATIVE_LABELS,
        )
        preview = args.profile.parent / item["preview"]
        image = preprocess(Image.open(preview).convert("RGB")).unsqueeze(0)
        text = tokenizer(labels)
        with torch.inference_mode():
            image_features = model.encode_image(image)
            text_features = model.encode_text(text)
            image_features /= image_features.norm(dim=-1, keepdim=True)
            text_features /= text_features.norm(dim=-1, keepdim=True)
            similarities = (image_features @ text_features.T)[0]
        ranked = sorted(zip(labels, similarities.tolist()), key=lambda pair: pair[1], reverse=True)
        print(f"\n{item['concept']['concept_id']}  {preview.name}")
        for label, score in ranked:
            print(f"  {score:.4f}  {label}")


if __name__ == "__main__":
    main()
