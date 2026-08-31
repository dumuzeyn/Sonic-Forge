from dataclasses import dataclass, field


DEFAULT_RERANK_WEIGHTS = {
    "semantic_relevance": 0.27,
    "aesthetic_quality": 0.18,
    "composition_quality": 0.15,
    "title_safe_area": 0.11,
    "diversity": 0.12,
    "concept_fit": 0.09,
    "artifact_penalty": 0.05,
    "genericity_penalty": 0.03,
}


@dataclass(frozen=True)
class CoverGenerationConfig:
    use_semantic_reranking: bool = True
    title_mode: str = "cleaned"
    typography_style_mode: str = "auto"
    dynamic_negative_prompt: bool = True
    prompt_compaction: bool = True
    diversity_strength: float = 1.0
    allow_human_subjects_auto: bool = True
    short_artistic_title_enabled: bool = True
    auto_download_semantic: bool = True
    rerank_weights: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_RERANK_WEIGHTS)
    )
