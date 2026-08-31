from dataclasses import replace

from .config import DEFAULT_RERANK_WEIGHTS


class CandidateReranker:
    def __init__(self, weights=None):
        self.weights = dict(DEFAULT_RERANK_WEIGHTS)
        self.weights.update(weights or {})

    def apply(self, assessment, semantic_available):
        metrics = dict(assessment.metrics)
        weights = dict(self.weights)
        if not semantic_available:
            weights.pop("semantic_relevance", None)
        total = sum(max(0.0, value) for value in weights.values()) or 1.0
        weights = {key: value / total for key, value in weights.items()}
        positives = (
            "semantic_relevance", "aesthetic_quality", "composition_quality",
            "title_safe_area", "diversity", "concept_fit",
        )
        score = sum(weights.get(key, 0.0) * float(metrics.get(key, 0.0)) for key in positives)
        score -= weights.get("artifact_penalty", 0.0) * float(metrics.get("artifact_penalty", 0.0))
        score -= weights.get("genericity_penalty", 0.0) * float(metrics.get("genericity_penalty", 0.0))
        final_score = round(max(0.0, min(100.0, score * 100.0)), 2)
        metrics["rerank_score"] = final_score
        metrics["semantic_path"] = 1.0 if semantic_available else 0.0
        hard_failure = any(
            marker in reason
            for reason in assessment.reasons
            for marker in (
                "слишком малый", "слишком тёмное", "пересвечено",
                "слишком похоже", "шаблонный мотив",
            )
        )
        return replace(
            assessment,
            score=final_score,
            accepted=not hard_failure and final_score >= 52.0,
            metrics=metrics,
        )
