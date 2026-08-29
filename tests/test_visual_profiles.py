import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from cover_engine import (
    CoverComposer,
    CoverConceptBuilder,
    DiversityController,
    MockImageProvider,
    SongContext,
    VisualProfileBuilder,
)
from cover_engine.concepts import COMPOSITIONS
from cover_engine.typography import TypographyEngine

class VisualProfileTests(unittest.TestCase):
    def test_lyrics_have_priority_over_conflicting_title(self):
        song = SongContext(
            title="Огненная корона",
            lyrics="Последний поезд уходит ночью сквозь дождь, дорога хранит память о доме",
            speed=.7,
            beat_density=.75,
            hardness=.55,
        )
        profile = VisualProfileBuilder().build(song, seed=7)
        concept = CoverConceptBuilder().build(song, profile, seed=7)
        self.assertEqual(profile.themes[0], "night")
        self.assertIn("journey", profile.themes)
        self.assertNotEqual(concept.main_symbol, "a crown slowly becoming ash")
        self.assertTrue(profile.lyrics_used)
        self.assertAlmostEqual(sum(profile.style_weights.values()), 1.0, places=3)

    def test_composition_catalog_has_at_least_ten_directions(self):
        self.assertGreaterEqual(len(COMPOSITIONS), 10)
        self.assertEqual(len(COMPOSITIONS), len(set(COMPOSITIONS)))

    def test_different_songs_change_scene_symbol_and_composition(self):
        builder = VisualProfileBuilder()
        concepts = []
        songs = (
            SongContext(title="Последний поезд", lyrics="ночной поезд, дождь, дорога домой"),
            SongContext(title="Стеклянное сердце", lyrics="сердце из стекла над городом"),
            SongContext(title="Космический цветок", lyrics="цветок растет среди звезд в космосе"),
            SongContext(title="Летний двор", lyrics="детство и дом, солнечный двор"),
            SongContext(title="Корона из пепла", lyrics="корона горит, огонь и пепел"),
        )
        for index, song in enumerate(songs):
            profile = builder.build(song, seed=index + 20)
            concepts.append(
                CoverConceptBuilder().build_candidates(song, profile, seed=index + 20)[index % 4]
            )
        self.assertGreaterEqual(len({item.scene for item in concepts}), 4)
        self.assertGreaterEqual(len({item.main_symbol for item in concepts}), 5)
        self.assertGreaterEqual(len({item.composition for item in concepts}), 4)

    def test_visual_profile_contains_semantic_and_audio_evidence(self):
        profile = VisualProfileBuilder().build(SongContext(
            title="Последний звонок",
            lyrics="Ночью под дождём я звоню тебе с вокзала, но поезд увозит меня домой",
            bpm=142,
            beat_density=.82,
            hardness=.71,
            tempo_variation=.63,
        ))
        self.assertEqual(profile.language, "ru")
        self.assertIn("railway platform", profile.settings)
        self.assertIn("telephone", profile.objects)
        self.assertTrue(profile.conflicts)
        self.assertIn("fast pulse", profile.audio_character)
        self.assertTrue(profile.lyrics_used)

    def test_four_candidates_differ_in_scene_object_palette_and_composition(self):
        song = SongContext(
            title="Дорога сквозь дождь",
            lyrics="Ночной поезд, мокрая улица, красный зонт, дорога и возвращение домой",
        )
        profile = VisualProfileBuilder().build(song, seed=41)
        concepts = CoverConceptBuilder().build_candidates(song, profile, seed=41)
        self.assertEqual(len(concepts), 4)
        self.assertEqual(len({item.candidate_type for item in concepts}), 4)
        self.assertEqual(len({item.composition for item in concepts}), 4)
        self.assertEqual(len({item.palette_name for item in concepts}), 4)
        self.assertGreaterEqual(len({item.scene for item in concepts}), 3)
        self.assertGreaterEqual(len({item.main_symbol for item in concepts}), 3)

    def test_generic_concept_is_rejected_by_quality_gate(self):
        song = SongContext(title="Солнечный двор", lyrics="детство, дом и тёплый летний двор")
        profile = VisualProfileBuilder().build(song, seed=3)
        concept = CoverConceptBuilder().build(song, profile, seed=3)
        generic = replace(concept, scene="a dark corridor with a bright doorway in darkness")
        image = Image.effect_noise((320, 320), 80).convert("RGB")
        assessment = DiversityController().assess(generic, image)
        self.assertFalse(assessment.accepted)
        self.assertTrue(any("шаблонный мотив" in reason for reason in assessment.reasons))

    def test_batch_controller_blocks_fourth_repeated_structure(self):
        song = SongContext(title="Повтор", lyrics="город и ночная улица")
        profile = VisualProfileBuilder().build(song, seed=8)
        concept = CoverConceptBuilder().build(song, profile, seed=8)
        image = Image.effect_noise((320, 320), 90).convert("RGB")
        controller = DiversityController()
        assessment = controller.assess(concept, image)
        for _ in range(3):
            controller.register(concept, assessment)
        _, reasons = controller.concept_score(concept)
        self.assertTrue(any("серийный повтор" in reason for reason in reasons))

    def test_composer_writes_provider_and_concept_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cover.png"
            composer = CoverComposer(provider=MockImageProvider())
            _, _, concept, artwork = composer.create(
                SongContext(title="Крылья над городом", artist="Автор"),
                path,
                size=320,
                seed=1,
            )
            with Image.open(path) as image:
                self.assertEqual(image.size, (320, 320))
            profile_path = path.parent / ".sonicforge" / "cover.profile.json"
            data = json.loads(profile_path.read_text(encoding="utf-8"))
            self.assertEqual(data["provider"], "mock")
            self.assertEqual(data["cover_concept"]["scene"], concept.scene)
            self.assertGreaterEqual(len(data["candidates"]), 4)
            self.assertTrue(any(item["selected"] for item in data["candidates"]))
            self.assertIn("typography", data)
            self.assertFalse(artwork.fallback)

    def test_direct_cover_generates_one_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cover.png"
            composer = CoverComposer(provider=MockImageProvider())
            composer.create(
                SongContext(title="Один готовый вариант", artist="Автор"),
                path,
                size=192,
                seed=4,
                candidate_limit=1,
            )
            profile_path = path.parent / ".sonicforge" / "cover.profile.json"
            data = json.loads(profile_path.read_text(encoding="utf-8"))
            self.assertEqual(len(data["candidates"]), 1)

    def test_mixed_language_title_stays_inside_safe_area(self):
        engine = TypographyEngine()
        image = Image.new("RGB", (512, 512), "#d8dee8")
        result = engine.compose(
            image,
            "Acheron × Мало тебя",
            "Исполнитель",
            profile=SimpleNamespace(typography_style="editorial title", text_position="top"),
            language="mixed",
        )
        self.assertEqual(result.size, (512, 512))
        self.assertEqual(engine.last_layout["language"], "mixed")
        self.assertLessEqual(engine.last_layout["line_count"], 4)
        self.assertTrue(all(0 <= value <= 512 for value in engine.last_layout["safe_area"]))

if __name__ == "__main__":
    unittest.main()
