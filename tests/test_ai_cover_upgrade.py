import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from PIL import Image

from cover_engine import CoverComposer, CoverConceptBuilder, MockImageProvider, SongContext, VisualProfileBuilder
from cover_engine.diversity import ArtworkAssessment
from cover_engine.model_manager import ImageModelManager
from cover_engine.ranking import CandidateReranker
from cover_engine.semantic_quality import SemanticQualityEvaluator
from cover_engine.titles import clean_artist, clean_title, resolve_title
from cover_engine.typography import TypographyEngine


def replace_namespace(value, **changes):
    data = vars(value).copy()
    data.update(changes)
    return SimpleNamespace(**data)


class FakeSemanticEvaluator:
    def __init__(self):
        self.calls = 0

    def status(self):
        return True, "test semantic evaluator loaded"

    def apply(self, assessment, _image, _concept):
        self.calls += 1
        metrics = dict(assessment.metrics)
        metrics["semantic_relevance"] = 0.93
        return replace(assessment, metrics=metrics)


class AICoverUpgradeTests(unittest.TestCase):
    def test_title_cleaning_and_short_mode_keep_original_identity(self):
        dirty = "07 - bring_me_to_life (Official Audio).mp3"
        self.assertEqual(clean_title(dirty), "bring me to life")
        resolved = resolve_title(dirty, "stylized")
        self.assertEqual(resolved.original, dirty)
        self.assertEqual(resolved.selected, "Bring Me to Life")
        long_title = resolve_title("The Last Train Through the City at Night", "short")
        self.assertLessEqual(len(long_title.selected.split()), 4)
        self.assertTrue(set(long_title.selected.lower().split()).issubset(set(long_title.cleaned.lower().split())))
        self.assertEqual(clean_title("Mr. Brightside"), "Mr. Brightside")
        self.assertEqual(clean_title("A-ha - Take On Me.mp3"), "A-ha — Take On Me")
        self.assertEqual(clean_artist("M-Band [drivemusic.me]"), "M-Band")

    def test_stylized_title_has_structure_and_low_confidence_falls_back(self):
        profile = SimpleNamespace(
            themes=("night",), imagery=("city lights",), objects=("train",), conflicts=("departure",)
        )
        treatment = resolve_title("Echoes — After Midnight (Acoustic)", "stylized", profile=profile)
        self.assertIn(":", treatment.selected)
        self.assertGreaterEqual(len(treatment.display_lines), 2)
        self.assertTrue(treatment.emphasis_words)
        self.assertFalse(treatment.fallback_used)
        weak = resolve_title("01 - track.mp3", "stylized", profile=profile)
        self.assertTrue(weak.fallback_used)
        self.assertEqual(weak.selected, weak.cleaned)

    def test_compact_prompt_has_one_thesis_and_dynamic_negative_prompt(self):
        song = SongContext(
            title="Последний звонок",
            lyrics="Ночью под дождём я звоню тебе с вокзала, поезд увозит меня домой",
        )
        profile = VisualProfileBuilder().build(song, seed=3)
        concepts = CoverConceptBuilder().build_candidates(song, profile, seed=3)
        prompt_families = {item.prompt.split(":", 1)[0] for item in concepts}
        self.assertGreaterEqual(len(prompt_families), 4)
        self.assertTrue(all(len(item.prompt) < 1450 for item in concepts))
        self.assertTrue(all(len(item.render_prompt) < 700 for item in concepts))
        portrait = next(item for item in concepts if item.candidate_type == "portrait")
        self.assertNotIn("person, human, portrait", portrait.negative_prompt)
        self.assertIn("deformed face", portrait.negative_prompt)
        self.assertNotIn("no people", portrait.negative_prompt)

    def test_semantic_evaluator_participates_in_main_composer_path(self):
        semantic = FakeSemanticEvaluator()
        with tempfile.TemporaryDirectory() as directory:
            composer = CoverComposer(provider=MockImageProvider(), semantic=semantic)
            composer.create(
                SongContext(title="Signal in Rain", lyrics="a phone call across a rainy station"),
                Path(directory) / "cover.png",
                size=192,
                seed=4,
                candidate_limit=1,
            )
        self.assertEqual(semantic.calls, 1)

    def test_ranking_weights_change_winner_for_semantic_relevance(self):
        base = ArtworkAssessment(50, True, (), {}, "0" * 64, (40, 40, 40))
        common = {
            "aesthetic_quality": .7,
            "composition_quality": .7,
            "title_safe_area": .7,
            "diversity": .7,
            "artifact_penalty": 0,
            "genericity_penalty": 0,
        }
        low = replace(base, metrics={**common, "semantic_relevance": .1})
        high = replace(base, metrics={**common, "semantic_relevance": .9})
        reranker = CandidateReranker()
        self.assertGreater(reranker.apply(high, True).score, reranker.apply(low, True).score)

    def test_semantic_model_is_auto_installed_when_runtime_is_ready(self):
        manager = mock.Mock()
        evaluator = SemanticQualityEvaluator(manager=manager)
        with mock.patch.object(
            SemanticQualityEvaluator, "runtime_available", new_callable=mock.PropertyMock, return_value=True
        ), mock.patch.object(
            evaluator, "status", side_effect=[(False, "missing"), (True, "ready")]
        ):
            available, reason = evaluator.ensure_available(auto_download=True)
        self.assertTrue(available)
        self.assertEqual(reason, "ready")
        manager.download_semantic.assert_called_once()

    def test_typography_uses_song_image_and_title_treatment(self):
        engine = TypographyEngine()
        treatment = resolve_title("Echoes — After Midnight", "stylized")
        concept = SimpleNamespace(
            typography_style="cinematic", text_position="left", candidate_type="cinematic",
            composition="asymmetrical_scene", typography_locked=False,
        )
        aggressive = SimpleNamespace(
            narrative_mode="aggressive", mood="intense", energy=.9, drama=.9,
            typography_mood_hint="heavy dramatic hierarchy",
        )
        engine.compose(
            Image.new("RGB", (320, 320), (20, 24, 28)), "Echoes — After Midnight",
            profile=concept, song_profile=aggressive, title_treatment=treatment,
        )
        dark_layout = dict(engine.last_layout)
        dream = SimpleNamespace(
            narrative_mode="dreamlike", mood="calm", energy=.35, drama=.25,
            typography_mood_hint="airy lyrical hierarchy",
        )
        engine.compose(
            Image.new("RGB", (320, 320), (220, 205, 230)), "Echoes — After Midnight",
            profile=replace_namespace(concept, candidate_type="surreal"),
            song_profile=dream, title_treatment=treatment,
        )
        dream_layout = dict(engine.last_layout)
        self.assertEqual(dark_layout["style"], "dark dramatic")
        self.assertEqual(dream_layout["style"], "dreamy")
        self.assertEqual(dark_layout["layout_strategy"], "split_lines")
        self.assertGreater(dark_layout["letter_spacing"], 0)
        self.assertGreater(dream_layout["letter_spacing"], dark_layout["letter_spacing"])

    def test_runtime_install_also_requests_semantic_model(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = ImageModelManager(Path(directory))
            runtime = manager.runtime_dir / "sd-cli.exe"
            runtime.parent.mkdir(parents=True)
            runtime.touch()
            with mock.patch.object(manager, "download_semantic", return_value=manager.semantic_path) as semantic:
                manager.download_runtime()
            semantic.assert_called_once()


if __name__ == "__main__":
    unittest.main()
