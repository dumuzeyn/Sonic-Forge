from collections import deque
from dataclasses import asdict, dataclass

from PIL import Image, ImageFilter, ImageStat


GENERIC_MARKERS = (
    "dark corridor",
    "empty tunnel",
    "stairway in a void",
    "lone centered silhouette",
    "bright doorway in darkness",
    "generic foggy room",
    "abstract light portal",
    "human-scale object transformed by light",
    "single figure crossing a vast empty place",
)


@dataclass(frozen=True)
class ArtworkAssessment:
    score: float
    accepted: bool
    reasons: tuple[str, ...]
    metrics: dict[str, float]
    fingerprint: str
    color_vector: tuple[float, float, float]

    def to_dict(self):
        return asdict(self)


class DiversityController:
    """Keeps a short memory of a batch and rejects visual repetition."""

    def __init__(self, history_size=8, strength=1.0):
        self.history = deque(maxlen=max(5, int(history_size)))
        self.strength = max(0.0, min(2.0, float(strength)))

    def concept_score(self, concept):
        score = concept.specificity * 36.0 + 44.0
        if any(
            word in concept.scene.lower()
            for word in (
                "corridor", "hallway", "passage", "apartment", "archive room",
                "transit hall", "ceremonial hall", "interior",
            )
        ):
            score -= 28
        recent = tuple(self.history)[-5:]
        repetition_reasons = []
        for field, penalty in (
            ("scene", 18), ("main_symbol", 24), ("visual_metaphor", 16),
            ("composition", 14), ("palette_name", 13), ("candidate_type", 8),
            ("human_presence", 7), ("text_position", 5),
        ):
            repeats = sum(1 for item in recent if item.get(field) == getattr(concept, field))
            score -= repeats * penalty * self.strength
            if field in {"scene", "main_symbol", "visual_metaphor", "composition", "palette_name"} and len(recent) >= 3:
                if all(item.get(field) == getattr(concept, field) for item in recent[-3:]):
                    repetition_reasons.append(f"серийный повтор: {field}")
        generic = self.generic_reasons(concept) + tuple(repetition_reasons)
        score -= 28 * len(generic)
        return round(score, 2), generic

    def rank(self, concepts):
        return tuple(sorted(concepts, key=lambda item: self.concept_score(item)[0], reverse=True))

    def assess(self, concept, image, comparison_fingerprints=()):
        rgb = image.convert("RGB")
        gray = rgb.convert("L")
        stat = ImageStat.Stat(gray)
        low, high = gray.getextrema()
        histogram = gray.histogram()
        pixels = max(1, rgb.width * rgb.height)
        dark_ratio = sum(histogram[:42]) / pixels
        bright_ratio = sum(histogram[220:]) / pixels
        saturation = ImageStat.Stat(rgb.convert("HSV").getchannel("S")).mean[0]
        color_vector = tuple(round(float(value), 2) for value in ImageStat.Stat(rgb).mean[:3])
        edge_mean = ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES)).mean[0]
        entropy = gray.entropy()
        fingerprint = _difference_hash(gray)
        prior_fingerprints = [item["fingerprint"] for item in self.history if item.get("fingerprint")]
        prior_fingerprints.extend(value for value in comparison_fingerprints if value)
        similarity = max((_hash_similarity(fingerprint, value) for value in prior_fingerprints), default=0.0)
        recent_colors = [item["color_vector"] for item in self.history if item.get("color_vector")]
        color_distance = min((_color_distance(color_vector, value) for value in recent_colors), default=255.0)
        concept_score, generic = self.concept_score(concept)
        score = concept_score
        score += min(12.0, stat.stddev[0] * .20)
        score += min(8.0, entropy)
        score += min(8.0, edge_mean * .16)
        if saturation > 22:
            score += 4
        reasons = list(generic)
        if high - low < 24 or stat.stddev[0] < 9:
            reasons.append("слишком малый визуальный диапазон")
            score -= 32
        if dark_ratio > .72:
            reasons.append("изображение слишком тёмное и пустое")
            score -= 28
        if bright_ratio > .74:
            reasons.append("изображение пересвечено")
            score -= 18
        if edge_mean < 2.0 and entropy < 4.5:
            reasons.append("нет читаемого предметного фокуса")
            score -= 20
        if similarity > .91:
            reasons.append("слишком похоже на недавнюю обложку")
            score -= 45
        if color_distance < 11 and similarity > .76:
            reasons.append("повторяет цветовой мир недавней обложки")
            score -= 24
        aesthetic_quality = _clamp01(
            stat.stddev[0] / 58 * .30
            + entropy / 8.0 * .26
            + min(saturation, 110) / 110 * .18
            + (1.0 - min(1.0, dark_ratio + bright_ratio)) * .26
        )
        composition_quality = _clamp01(
            min(1.0, (high - low) / 150) * .42
            + min(1.0, edge_mean / 18) * .34
            + min(1.0, stat.stddev[0] / 52) * .24
        )
        title_safe_area = _title_safe_score(gray)
        diversity = _clamp01((1.0 - similarity) * .78 + min(1.0, color_distance / 80) * .22)
        artifact_penalty = _clamp01(
            max(0.0, dark_ratio - .55) * 2.0
            + max(0.0, bright_ratio - .55) * 1.7
            + (1.0 if high - low < 24 else 0.0)
        )
        genericity_penalty = _clamp01(len(generic) * .55 + (1.0 if edge_mean < 2 and entropy < 4.5 else 0.0))
        concept_fit = _clamp01(
            concept.specificity * .58
            + min(1.0, edge_mean / 16) * .18
            + (1.0 - min(1.0, dark_ratio + bright_ratio)) * .14
            + (0.10 if getattr(concept, "main_symbol", "") else 0.0)
        )
        metrics = {
            "dynamic_range": round(float(high - low), 2),
            "luminance_stddev": round(float(stat.stddev[0]), 2),
            "dark_ratio": round(float(dark_ratio), 4),
            "bright_ratio": round(float(bright_ratio), 4),
            "saturation": round(float(saturation), 2),
            "edge_density": round(float(edge_mean), 2),
            "entropy": round(float(entropy), 3),
            "recent_similarity": round(float(similarity), 4),
            "recent_color_distance": round(float(color_distance), 3),
            "aesthetic_quality": round(aesthetic_quality, 4),
            "composition_quality": round(composition_quality, 4),
            "title_safe_area": round(title_safe_area, 4),
            "diversity": round(diversity, 4),
            "artifact_penalty": round(artifact_penalty, 4),
            "genericity_penalty": round(genericity_penalty, 4),
            "concept_fit": round(concept_fit, 4),
        }
        accepted = not reasons and score >= 55
        return ArtworkAssessment(round(score, 2), accepted, tuple(reasons), metrics, fingerprint, color_vector)

    def register(self, concept, assessment):
        self.history.append({
            "scene": concept.scene,
            "main_symbol": concept.main_symbol,
            "composition": concept.composition,
            "palette_name": concept.palette_name,
            "text_position": concept.text_position,
            "candidate_type": concept.candidate_type,
            "visual_metaphor": getattr(concept, "visual_metaphor", ""),
            "human_presence": getattr(concept, "human_presence", "optional"),
            "fingerprint": assessment.fingerprint,
            "color_vector": assessment.color_vector,
        })

    @staticmethod
    def generic_reasons(concept):
        haystack = f"{concept.scene} {concept.main_symbol}".lower()
        return tuple(f"шаблонный мотив: {marker}" for marker in GENERIC_MARKERS if marker in haystack)

    @staticmethod
    def needs_alternative_branch(assessments):
        values = tuple(assessments)
        if len(values) < 2:
            return False
        return any(
            item.metrics.get("recent_similarity", 0.0) > .86
            or (
                item.metrics.get("recent_similarity", 0.0) > .76
                and item.metrics.get("recent_color_distance", 255.0) < 16
            )
            for item in values[1:]
        )


def _difference_hash(gray):
    sample = gray.resize((17, 16), Image.Resampling.LANCZOS)
    values = list(sample.get_flattened_data())
    bits = []
    for row in range(16):
        start = row * 17
        bits.extend(values[start + column] > values[start + column + 1] for column in range(16))
    return f"{sum(int(bit) << index for index, bit in enumerate(bits)):064x}"


def _hash_similarity(left, right):
    if not left or not right or len(left) != len(right):
        return 0.0
    distance = (int(left, 16) ^ int(right, 16)).bit_count()
    return 1.0 - distance / (len(left) * 4)


def _color_distance(left, right):
    return sum((a - b) ** 2 for a, b in zip(left, right)) ** .5


def _title_safe_score(gray):
    width, height = gray.size
    regions = (
        (0, 0, width, height // 3),
        (0, height * 2 // 3, width, height),
        (0, 0, width // 2, height),
        (width // 2, 0, width, height),
        (width // 6, height // 3, width * 5 // 6, height * 2 // 3),
    )
    scores = []
    for box in regions:
        crop = gray.crop(box)
        variation = ImageStat.Stat(crop).stddev[0]
        edges = ImageStat.Stat(crop.filter(ImageFilter.FIND_EDGES)).mean[0]
        scores.append(_clamp01(1.0 - variation / 92 * .58 - edges / 42 * .42))
    return max(scores, default=0.0)


def _clamp01(value):
    return max(0.0, min(1.0, float(value)))
