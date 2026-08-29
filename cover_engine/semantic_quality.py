from dataclasses import dataclass, replace

from .model_manager import ImageModelManager


GENERIC_LABELS = (
    "an indoor corridor or hallway",
    "a lone person standing in a dark passage",
    "an empty glowing doorway or tunnel",
    "a generic abstract album cover",
)

FORBIDDEN_HUMAN_LABELS = (
    "a person",
    "an astronaut",
    "a lone human figure",
    "a centered human silhouette",
    "a space landscape with an astronaut",
)

FORBIDDEN_TEXT_LABELS = (
    "an image containing printed words or letters",
    "a sign with text inside the artwork",
    "unreadable fake typography in the image",
)


@dataclass(frozen=True)
class SemanticAssessment:
    combined: float
    object_score: float
    scene_score: float
    empty_scene: float
    generic_score: float
    forbidden_human_score: float
    forbidden_text_score: float
    score_adjustment: float
    reasons: tuple[str, ...]


class SemanticQualityEvaluator:
    """Uses local CLIP to verify that generated pixels match the chosen concept."""

    def __init__(self, manager=None):
        self.manager = manager or ImageModelManager()
        self.model = None
        self.preprocess = None
        self.tokenizer = None

    @property
    def available(self):
        return self.manager.semantic_model_path() is not None

    def apply(self, assessment, image, concept):
        semantic = self.assess(image, concept)
        metrics = dict(assessment.metrics)
        metrics.update({
            "semantic_combined": round(semantic.combined, 4),
            "semantic_object": round(semantic.object_score, 4),
            "semantic_scene": round(semantic.scene_score, 4),
            "semantic_empty_scene": round(semantic.empty_scene, 4),
            "semantic_generic": round(semantic.generic_score, 4),
            "semantic_forbidden_human": round(semantic.forbidden_human_score, 4),
            "semantic_forbidden_text": round(semantic.forbidden_text_score, 4),
            "semantic_adjustment": round(semantic.score_adjustment, 2),
        })
        reasons = tuple(dict.fromkeys((*assessment.reasons, *semantic.reasons)))
        score = round(assessment.score + semantic.score_adjustment, 2)
        return replace(
            assessment,
            score=score,
            accepted=not reasons and score >= 55,
            reasons=reasons,
            metrics=metrics,
        )

    def assess(self, image, concept):
        self._load()
        labels = (
            f"{concept.main_symbol} in {concept.scene}",
            concept.main_symbol,
            concept.scene,
            f"an empty {concept.scene} landscape with no main object",
            *GENERIC_LABELS,
            *FORBIDDEN_HUMAN_LABELS,
            *FORBIDDEN_TEXT_LABELS,
        )
        import torch

        image_tensor = self.preprocess(image.convert("RGB")).unsqueeze(0)
        text_tensor = self.tokenizer(labels)
        with torch.inference_mode():
            image_features = self.model.encode_image(image_tensor)
            text_features = self.model.encode_text(text_tensor)
            image_features /= image_features.norm(dim=-1, keepdim=True)
            text_features /= text_features.norm(dim=-1, keepdim=True)
            values = (image_features @ text_features.T)[0].tolist()
        combined, object_score, scene_score, empty_scene, *tail = values
        generic = tail[:len(GENERIC_LABELS)]
        forbidden_humans = tail[len(GENERIC_LABELS):len(GENERIC_LABELS) + len(FORBIDDEN_HUMAN_LABELS)]
        forbidden_text = tail[len(GENERIC_LABELS) + len(FORBIDDEN_HUMAN_LABELS):]
        generic_score = max(generic)
        forbidden_human_score = max(forbidden_humans)
        forbidden_text_score = max(forbidden_text)
        object_margin = combined - empty_scene
        generic_margin = combined - generic_score
        reasons = []
        if object_score < .19:
            reasons.append("семантическая проверка не нашла главный объект")
        if object_margin < .012:
            reasons.append("сцена выглядит пустой: выбранная метафора не подтверждена")
        if generic_margin < .008:
            reasons.append("изображение ближе к шаблонной обложке, чем к выбранной концепции")
        if forbidden_human_score > .23 and forbidden_human_score > object_score - .02:
            reasons.append("модель добавила человека или силуэт вместо предметной метафоры")
        if forbidden_text_score > .22 and forbidden_text_score > object_score - .035:
            reasons.append("внутри изображения появились случайные буквы или псевдотекст")
        adjustment = (
            (object_score - .19) * 145
            + object_margin * 150
            + generic_margin * 100
            - max(0.0, forbidden_human_score - .18) * 120
            - max(0.0, forbidden_text_score - .18) * 110
        )
        return SemanticAssessment(
            combined=float(combined),
            object_score=float(object_score),
            scene_score=float(scene_score),
            empty_scene=float(empty_scene),
            generic_score=float(generic_score),
            forbidden_human_score=float(forbidden_human_score),
            forbidden_text_score=float(forbidden_text_score),
            score_adjustment=max(-70.0, min(36.0, float(adjustment))),
            reasons=tuple(reasons),
        )

    def _load(self):
        if self.model is not None:
            return
        model_path = self.manager.semantic_model_path()
        if model_path is None:
            raise RuntimeError("Не установлена локальная модель семантической проверки")
        import open_clip

        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32",
            pretrained=str(model_path),
            device="cpu",
        )
        self.model.eval()
        self.tokenizer = open_clip.get_tokenizer("ViT-B-32")
