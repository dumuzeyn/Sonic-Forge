import json
from dataclasses import replace
from pathlib import Path

from PIL import Image, ImageStat

from .concepts import CoverConceptBuilder
from .config import CoverGenerationConfig
from .diversity import DiversityController
from .profiles import VisualProfileBuilder
from .providers import AutoImageProvider, CoverRequest
from .ranking import CandidateReranker
from .semantic_quality import SemanticQualityEvaluator
from .titles import clean_artist, resolve_title
from .typography import TypographyEngine


class CoverComposer:
    def __init__(self, provider=None, profile_builder=None, concept_builder=None, typography=None, diversity=None, semantic=None, config=None):
        self.config = config or CoverGenerationConfig()
        self.provider = provider or AutoImageProvider()
        self.profile_builder = profile_builder or VisualProfileBuilder()
        self.concept_builder = concept_builder or CoverConceptBuilder(self.config)
        self.typography = typography or TypographyEngine()
        self.diversity = diversity or DiversityController(strength=self.config.diversity_strength)
        self.semantic = semantic or (SemanticQualityEvaluator() if self.config.use_semantic_reranking else None)
        self.reranker = CandidateReranker(self.config.rerank_weights)
        self._semantic_active = False

    def create(
        self,
        song,
        output_path,
        size=1000,
        seed=None,
        text_mode="title_artist",
        detail="balanced",
        audio_path=None,
        cancel_event=None,
        analysis_bundle=None,
        candidate_limit=None,
        title_mode=None,
    ):
        profile = self.profile_builder.build(song, seed=seed)
        self._log_profile(profile)
        self._semantic_active = self._prepare_semantic()
        concepts = self.concept_builder.build_candidates(song, profile, seed=seed, detail=detail, count=4)
        ranked = self.diversity.rank(concepts)
        generation_pool = ranked[:3] if detail == "simple" else ranked
        if candidate_limit is not None:
            generation_pool = generation_pool[:max(1, int(candidate_limit))]
        print(f"Подготовлено вариантов: {len(generation_pool)}")
        results = self._generate_candidates(
            generation_pool, profile, size, seed, detail, audio_path, cancel_event, analysis_bundle,
        )
        results = self._rerank_results(results)
        if candidate_limit is None and self.diversity.needs_alternative_branch(
            item[2] for item in results if not item[1].fallback
        ):
            print("Первые варианты слишком похожи. Создаётся альтернативная художественная ветка...")
            alternatives = self.concept_builder.build_candidates(
                song, profile, seed=seed, detail=detail, count=4, offset=3,
            )
            results.extend(self._generate_candidates(
                self.diversity.rank(alternatives)[:2], profile, size,
                None if seed is None else seed + 70001,
                detail, audio_path, cancel_event, analysis_bundle,
                comparison_fingerprints=tuple(item[2].fingerprint for item in results),
                label_prefix="D",
            ))
            results = self._rerank_results(results)
        local_results = [item for item in results if not item[1].fallback]
        accepted = [item for item in local_results if item[2].accepted]
        if local_results and not accepted and candidate_limit is None:
            print("Все первые варианты отклонены контролем качества. Создаются новые трактовки...")
            recovery = self.concept_builder.build_candidates(
                song, profile, seed=seed, detail=detail, count=4, offset=1,
            )
            results.extend(self._generate_candidates(
                self.diversity.rank(recovery)[:2], profile, size,
                None if seed is None else seed + 40009,
                detail, audio_path, cancel_event, analysis_bundle,
                comparison_fingerprints=tuple(item[2].fingerprint for item in results),
                label_prefix="R",
            ))
            results = self._rerank_results(results)
            local_results = [item for item in results if not item[1].fallback]
            accepted = [item for item in results if not item[1].fallback and item[2].accepted]

        fallback_results = [item for item in results if item[1].fallback]
        if accepted:
            concept, artwork, assessment = max(accepted, key=lambda item: item[2].score)
        elif local_results:
            concept, artwork, assessment = max(local_results, key=lambda item: item[2].score)
        elif fallback_results:
            concept, artwork, assessment = max(fallback_results, key=lambda item: item[2].score)
        else:
            reasons = sorted({reason for _, _, assessment in results for reason in assessment.reasons})
            raise RuntimeError("Все AI-варианты отклонены: " + "; ".join(reasons or ("недостаточное качество",)))

        _check_cancelled(cancel_event)
        if artwork.fallback:
            print(f"Fallback used: {artwork.provider}; reason: {artwork.note}")
        else:
            print(f"Local AI used: {artwork.provider}")
        print(
            f"Выбран лучший вариант: {concept.concept_id}; итог={assessment.score:.1f}; "
            f"смысл={assessment.metrics.get('semantic_relevance', 0):.2f}; "
            f"эстетика={assessment.metrics.get('aesthetic_quality', 0):.2f}; "
            f"композиция={assessment.metrics.get('composition_quality', 0):.2f}; "
            f"зона текста={assessment.metrics.get('title_safe_area', 0):.2f}; "
            f"соответствие концепции={assessment.metrics.get('concept_fit', 0):.2f}"
        )

        title_resolution = resolve_title(
            song.title,
            title_mode or self.config.title_mode,
            profile=profile,
            short_enabled=self.config.short_artistic_title_enabled,
        )
        print(
            f"Режим названия: {title_resolution.mode}; отображается: {title_resolution.selected}; "
            f"уверенность={title_resolution.confidence:.2f}; fallback={'да' if title_resolution.fallback_used else 'нет'}"
        )
        if self.config.typography_style_mode != "auto":
            concept = replace(
                concept,
                typography_style=self.config.typography_style_mode,
                typography_locked=True,
            )

        image = self.typography.compose(
            artwork.image,
            title_resolution.selected,
            clean_artist(song.artist),
            profile=concept,
            song_profile=profile,
            title_treatment=title_resolution,
            enabled=text_mode != "none",
            show_artist=text_mode == "title_artist",
            language=profile.language,
        )
        _check_cancelled(cancel_event)
        typography_layout = getattr(self.typography, "last_layout", {})
        if text_mode != "none":
            print("Название и исполнитель добавлены на обложку")
        self._validate(image, size)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path, format="PNG", optimize=True)
        with Image.open(output_path) as saved_image:
            self._validate(saved_image.convert("RGB"), size)
        self.diversity.register(concept, assessment)
        self._save_profile(
            output_path, profile, concept, artwork, assessment, results,
            typography_layout, analysis_bundle, title_resolution, self.config,
        )
        return output_path, profile, concept, artwork

    def _generate_candidates(
        self,
        concepts,
        profile,
        size,
        seed,
        detail,
        audio_path,
        cancel_event,
        analysis_bundle,
        comparison_fingerprints=(),
        label_prefix="",
    ):
        results = []
        local_fingerprints = list(comparison_fingerprints)
        for index, concept in enumerate(concepts):
            _check_cancelled(cancel_event)
            label = f"{label_prefix}{index + 1}" if label_prefix else concept.concept_id
            print(f"Генерация варианта {label}: {concept.candidate_type}...")
            candidate_seed = None if seed is None else int(seed) + index * 7919
            artwork = self.provider.generate(CoverRequest(
                profile=profile,
                concept=concept,
                size=size,
                seed=candidate_seed,
                detail=detail,
                audio_path=audio_path,
                cancel_event=cancel_event,
                analysis_bundle=analysis_bundle,
            ))
            assessment = self.diversity.assess(concept, artwork.image, local_fingerprints)
            if self._semantic_active and not artwork.fallback:
                try:
                    assessment = self.semantic.apply(assessment, artwork.image, concept)
                except Exception as exc:
                    self._semantic_active = False
                    print(f"  Семантическая проверка отключена: {exc}")
            if "semantic_combined" in assessment.metrics:
                print(
                    "  Семантика: "
                    f"объект={assessment.metrics['semantic_object']:.3f}; "
                    f"концепция={assessment.metrics['semantic_combined']:.3f}; "
                    f"шаблон={assessment.metrics['semantic_generic']:.3f}; "
                    f"человек={assessment.metrics['semantic_forbidden_human']:.3f}; "
                    f"псевдотекст={assessment.metrics['semantic_forbidden_text']:.3f}"
                )
            results.append((concept, artwork, assessment))
            if artwork.fallback:
                print(f"  Аварийный вариант: {artwork.note}")
                break
            if assessment.reasons:
                print(f"  Отклонён: {', '.join(assessment.reasons)}")
            else:
                print("  Передан в итоговое сравнение")
            local_fingerprints.append(assessment.fingerprint)
        return results

    def _prepare_semantic(self):
        if self.semantic is None:
            print("Семантический reranking отключён настройкой")
            return False
        if hasattr(self.semantic, "prepare"):
            available, reason = self.semantic.prepare(
                auto_download=self.config.auto_download_semantic
            )
        else:
            available, reason = self.semantic.status()
        print(f"Semantic evaluator: {'loaded' if available else 'not loaded'}; {reason}")
        return available

    def _rerank_results(self, results):
        reranked = []
        for concept, artwork, assessment in results:
            final = self.reranker.apply(assessment, self._semantic_active and not artwork.fallback)
            print(
                f"  Оценка {concept.concept_id}: {final.score:.1f} | "
                f"semantic={final.metrics.get('semantic_relevance', 0):.2f}, "
                f"aesthetic={final.metrics.get('aesthetic_quality', 0):.2f}, "
                f"composition={final.metrics.get('composition_quality', 0):.2f}, "
                f"text={final.metrics.get('title_safe_area', 0):.2f}, "
                f"diversity={final.metrics.get('diversity', 0):.2f}, "
                f"concept-fit={final.metrics.get('concept_fit', 0):.2f}"
            )
            reranked.append((concept, artwork, final))
        return reranked

    @staticmethod
    def _log_profile(profile):
        print("Анализ смысла песни...")
        print(f"Характер: {profile.narrative_mode}; {profile.core_emotional_thesis}")
        print(f"Главная метафора: {profile.visual_metaphor}")
        print(f"Предлагаемая сцена: {profile.scene_suggestion}")
        print(f"Развитие настроения: {profile.mood_arc}")
        print(f"Уровень абстракции: {profile.abstraction_level}")
        print(f"Присутствие человека: {profile.human_presence_suggestion}")
        print(f"Характер типографики: {profile.typography_mood_hint}")
        print(f"Язык: {profile.language}; текст песни использован: {'да' if profile.lyrics_used else 'нет'}")

    @staticmethod
    def _validate(image, size):
        if image.size != (size, size):
            raise RuntimeError("Generated cover has an invalid size")
        gray = image.convert("L")
        extrema = gray.getextrema()
        if extrema[1] - extrema[0] < 12 or ImageStat.Stat(gray).stddev[0] < 4:
            raise RuntimeError("Generated cover is blank or has insufficient visual range")

    @staticmethod
    def _save_profile(output_path, profile, concept, artwork, assessment, results, typography_layout, analysis_bundle=None, title_resolution=None, config=None):
        cache_dir = output_path.parent / ".sonicforge"
        cache_dir.mkdir(parents=True, exist_ok=True)
        preview_dir = cache_dir / "candidates"
        preview_dir.mkdir(parents=True, exist_ok=True)
        candidates = []
        for candidate, candidate_artwork, candidate_assessment in results:
            preview_name = f"{output_path.stem}_{candidate.concept_id}_{candidate.signature[:8]}.jpg"
            preview_path = preview_dir / preview_name
            preview = candidate_artwork.image.convert("RGB").copy()
            preview.thumbnail((320, 320), Image.Resampling.LANCZOS)
            preview.save(preview_path, "JPEG", quality=78, optimize=True)
            candidates.append({
                "concept": candidate.to_dict(),
                "provider": candidate_artwork.provider,
                "fallback": candidate_artwork.fallback,
                "assessment": candidate_assessment.to_dict(),
                "selected": candidate.signature == concept.signature,
                "preview": str(Path("candidates") / preview_name),
            })
        data = {
            "analysis_bundle": analysis_bundle.to_dict() if hasattr(analysis_bundle, "to_dict") else None,
            "visual_profile": profile.to_dict(),
            "cover_concept": concept.to_dict(),
            "provider": artwork.provider,
            "fallback": artwork.fallback,
            "provider_note": artwork.note,
            "quality_assessment": assessment.to_dict(),
            "typography": typography_layout,
            "title_resolution": title_resolution.to_dict() if title_resolution else None,
            "generation_config": {
                "use_semantic_reranking": config.use_semantic_reranking,
                "title_mode": config.title_mode,
                "typography_style_mode": config.typography_style_mode,
                "dynamic_negative_prompt": config.dynamic_negative_prompt,
                "prompt_compaction": config.prompt_compaction,
                "diversity_strength": config.diversity_strength,
                "allow_human_subjects_auto": config.allow_human_subjects_auto,
                "short_artistic_title_enabled": config.short_artistic_title_enabled,
                "auto_download_semantic": config.auto_download_semantic,
                "rerank_weights": config.rerank_weights,
            } if config else None,
            "candidates": candidates,
        }
        profile_path = cache_dir / f"{output_path.stem}.profile.json"
        temporary = profile_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(profile_path)


def _check_cancelled(cancel_event):
    if cancel_event is not None and cancel_event.is_set():
        raise InterruptedError("Создание обложки остановлено")
