import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

from cover_engine.model_manager import ImageModelManager
from cover_engine.local_generation import LocalGenerationError, StableDiffusionCppBackend
from cover_engine.music2picture_fallback import Music2PictureFallbackProvider
from cover_engine.providers import (
    AutoImageProvider,
    CoverRequest,
    GeneratedArtwork,
    ImageGenerationProvider,
    Music2PictureProvider,
)


class FailingProvider(ImageGenerationProvider):
    name = "failing local"

    def generate(self, request):
        raise RuntimeError("forced local failure")


class FixedFallback(ImageGenerationProvider):
    name = "fixed fallback"

    def generate(self, request):
        return GeneratedArtwork(
            Image.new("RGB", (request.size, request.size), "#b91c1c"),
            "Music2Picture v2",
            fallback=True,
            note="ai_fallback=music2picture_v2",
        )


class BlankProvider(ImageGenerationProvider):
    name = "blank local"

    def generate(self, request):
        return GeneratedArtwork(Image.new("RGB", (request.size, request.size), "white"), self.name)


class CoverProviderTests(unittest.TestCase):
    def test_auto_provider_survives_local_failure(self):
        provider = AutoImageProvider(primary=FailingProvider(), fallback=FixedFallback())
        result = provider.generate(CoverRequest(object(), object(), 64))
        self.assertTrue(result.fallback)
        self.assertEqual(result.provider, "Music2Picture v2")
        self.assertIn("local_error=forced local failure", result.note)

    def test_invalid_local_image_also_uses_fallback(self):
        provider = AutoImageProvider(primary=BlankProvider(), fallback=FixedFallback())
        result = provider.generate(CoverRequest(object(), object(), 64))
        self.assertTrue(result.fallback)
        self.assertIn("пустое изображение", result.note)

    def test_music2picture_v2_is_one_independent_engine(self):
        bundle = mock.Mock()
        bundle.visual_dna = object()
        bundle.visual_plan = object()
        with tempfile.TemporaryDirectory() as directory, mock.patch(
            "cover_engine.music2picture_fallback.render_cover",
            return_value=Image.new("RGB", (32, 32), "#202020"),
        ) as render:
            audio = Path(directory) / "song.wav"
            audio.touch()
            provider = Music2PictureProvider(Music2PictureFallbackProvider(), as_fallback=False)
            request = CoverRequest(object(), object(), 32, audio_path=audio, analysis_bundle=bundle)
            result = provider.generate(request)
            self.assertFalse(result.fallback)
            self.assertEqual(result.provider, "Music2Picture v2")
            render.assert_called_once_with(bundle.visual_dna, bundle.visual_plan, size=32, seed=None)

    def test_model_manager_accepts_custom_model_and_keeps_it_external(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = root / "custom.safetensors"
            model.touch()
            manager = ImageModelManager(root / "managed")
            manager.set_custom_model(model)
            runtime = manager.runtime_dir / "sd-cli.exe"
            runtime.parent.mkdir(parents=True)
            runtime.touch()
            with mock.patch.object(manager, "semantic_model_path", return_value=root / "semantic.safetensors"):
                status = manager.status()
            self.assertTrue(status.ready)
            self.assertEqual(status.model_path, model.resolve())
            self.assertNotEqual(status.model_path.parent, manager.root)

    def test_memory_error_retries_in_economy_mode(self):
        backend = StableDiffusionCppBackend()
        expected = Image.new("RGB", (32, 32), "#333333")
        request = CoverRequest(object(), object(), 32)
        with mock.patch.object(
            backend,
            "_run",
            side_effect=[LocalGenerationError("CUDA out of memory"), expected],
        ) as run:
            actual = backend.generate(request, "runtime.exe", "model.safetensors")
        self.assertIs(actual, expected)
        self.assertFalse(run.call_args_list[0].kwargs["economy"])
        self.assertTrue(run.call_args_list[1].kwargs["economy"])

    def test_stop_process_escalates_and_waits_for_exit(self):
        process = mock.Mock()
        process.wait.side_effect = [subprocess.TimeoutExpired("sd-cli", 3), 0]
        StableDiffusionCppBackend._stop_process(process)
        process.terminate.assert_called_once_with()
        process.kill.assert_called_once_with()
        self.assertEqual(process.wait.call_count, 2)


if __name__ == "__main__":
    unittest.main()
