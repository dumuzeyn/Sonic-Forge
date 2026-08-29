import json
from pathlib import Path

from PIL import Image, ImageStat

from .concepts import CoverConceptBuilder
from .diversity import DiversityController
from .profiles import VisualProfileBuilder
from .providers import AutoImageProvider, CoverRequest
from .semantic_quality import SemanticQualityEvaluator
from .typography import TypographyEngine


class CoverComposer:
    def __init__(self, provider=None, profile_builder=None, concept_builder=None, typography=None, diversity=None, semantic=None):
        self.provider = provider or AutoImageProvider()
        self.profile_builder = profile_builder or VisualProfileBuilder()
        self.concept_builder = concept_builder or CoverConceptBuilder()
        self.typography = typography or TypographyEngine()
        self.diversity = diversity or DiversityController()
        self.semantic = semantic
        if self.semantic is None and getattr(self.provider, "name", "") != "mock":
            self.semantic = SemanticQualityEvaluator()

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
    ):
        profile = self.profile_builder.build(song, seed=seed)
        concepts = self.concept_builder.build_candidates(song, profile, seed=seed, detail=detail, count=4)
        ranked = self.diversity.rank(concepts)
        self._log_profile(profile)
        if profile.song_description:
            print(f"Описание песни: {profile.song_description}")
        if profile.visual_brief:
            print("Визуальный план создан на основе анализа звука.")
        print("Создано 4 разных художественных концепции:")
        for concept in concepts:
            score, generic = self.diversity.concept_score(concept)
            suffix = f"; ограничение: {', '.join(generic)}" if generic else ""
            print(
                f"  {concept.concept_id}: {concept.candidate_type}; "
                f"сцена={concept.scene}; символ={concept.main_symbol}; "
                f"палитра={concept.palette_name}; композиция={concept.composition}; "
                f"оценка концепции={score:.1f}{suffix}"
            )

        generation_pool = ranked[:3] if detail == "simple" else ranked
        results = self._generate_candidates(
            generation_pool, profile, size, seed, detail, audio_path, cancel_event, analysis_bundle,
        )
        local_results = [item for item in results if not item[1].fallback]
        accepted = [item for item in local_results if item[2].accepted]
        if local_results and not accepted:
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
            accepted = [item for item in results if not item[1].fallback and item[2].accepted]

        fallback_results = [item for item in results if item[1].fallback]
        if accepted:
            concept, artwork, assessment = max(accepted, key=lambda item: item[2].score)
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
            f"Выбран вариант {concept.concept_id}: {concept.main_symbol}; "
            f"палитра={concept.palette_name}; композиция={concept.composition}; "
            f"оценка={assessment.score:.1f}"
        )

        image = self.typography.compose(
            artwork.image,
            song.title,
            song.artist,
            profile=concept,
            enabled=text_mode != "none",
            show_artist=text_mode == "title_artist",
            language=profile.language,
        )
        _check_cancelled(cancel_event)
        typography_layout = getattr(self.typography, "last_layout", {})
        if text_mode != "none":
            print(
                "Текст размещён: "
                f"{typography_layout.get('placement', concept.text_position)}; "
                f"стиль={typography_layout.get('style', concept.typography_style)}"
            )
        self._validate(image, size)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path, format="PNG", optimize=True)
        with Image.open(output_path) as saved_image:
            self._validate(saved_image.convert("RGB"), size)
        self.diversity.register(concept, assessment)
        self._save_profile(output_path, profile, concept, artwork, assessment, results, typography_layout, analysis_bundle)
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
            if self.semantic is not None and not artwork.fallback:
                assessment = self.semantic.apply(assessment, artwork.image, concept)
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
            if assessment.accepted:
                print(f"  Принят в финальный отбор: {assessment.score:.1f}")
            else:
                print(f"  Отклонён: {', '.join(assessment.reasons)}")
            local_fingerprints.append(assessment.fingerprint)
        return results

    @staticmethod
    def _log_profile(profile):
        print("Анализ смысла песни...")
        print(f"Темы: {', '.join(profile.themes)}")
        print(f"Образы: {', '.join(profile.imagery)}")
        print(f"Места действия: {', '.join(profile.settings)}")
        print(f"Смысловые предметы: {', '.join(profile.objects)}")
        print(f"Эмоциональный конфликт: {', '.join(profile.conflicts)}")
        print(f"Язык: {profile.language}; текст песни использован: {'да' if profile.lyrics_used else 'нет'}")
        print(f"Характер звука: {', '.join(profile.audio_character)}")

    @staticmethod
    def _validate(image, size):
        if image.size != (size, size):
            raise RuntimeError("Generated cover has an invalid size")
        gray = image.convert("L")
        extrema = gray.getextrema()
        if extrema[1] - extrema[0] < 12 or ImageStat.Stat(gray).stddev[0] < 4:
            raise RuntimeError("Generated cover is blank or has insufficient visual range")

    @staticmethod
    def _save_profile(output_path, profile, concept, artwork, assessment, results, typography_layout, analysis_bundle=None):
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
            "candidates": candidates,
        }
        profile_path = cache_dir / f"{output_path.stem}.profile.json"
        temporary = profile_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(profile_path)


def _check_cancelled(cancel_event):
    if cancel_event is not None and cancel_event.is_set():
        raise InterruptedError("Создание обложки остановлено")
