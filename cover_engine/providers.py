import base64
import io
import json
import os
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageStat

from .local_generation import StableDiffusionCppBackend
from .model_manager import ImageModelManager
from .music2picture_fallback import Music2PictureFallbackProvider


@dataclass(frozen=True)
class CoverRequest:
    profile: object
    concept: object
    size: int
    seed: int | None = None
    detail: str = "balanced"
    audio_path: Path | None = None
    cancel_event: object | None = None
    analysis_bundle: object | None = None


@dataclass(frozen=True)
class GeneratedArtwork:
    image: Image.Image
    provider: str
    fallback: bool = False
    note: str = ""


class ImageGenerationProvider(ABC):
    name = "provider"

    @abstractmethod
    def generate(self, request):
        raise NotImplementedError

    def close(self):
        return None


# Compatibility name for integrations created against the previous provider API.
ImageGeneratorProvider = ImageGenerationProvider


class LocalImageProvider(ImageGenerationProvider):
    name = "Local AI"

    def __init__(self, manager=None, backend=None):
        self.manager = manager or ImageModelManager()
        self.backend = backend or StableDiffusionCppBackend()

    @property
    def status(self):
        return self.manager.status()

    def generate(self, request):
        status = self.manager.status()
        if not status.ready:
            raise RuntimeError(status.description)
        print("Загрузка локальной модели...")
        print("Создание изображения...")
        image = self.backend.generate(request, status.runtime_path, status.model_path)
        info = getattr(self.backend, "last_generation_info", {})
        note = "; ".join(f"{key}={value}" for key, value in info.items())
        return GeneratedArtwork(image.convert("RGB"), f"{self.name}: {self.backend.name}", note=note)


class Music2PictureProvider(ImageGenerationProvider):
    name = "Music2Picture v2"

    def __init__(self, provider=None, as_fallback=True):
        self.provider = provider or Music2PictureFallbackProvider()
        self.as_fallback = bool(as_fallback)

    def generate(self, request):
        image, _label = self.provider.generate(request)
        return GeneratedArtwork(
            image,
            "Music2Picture v2",
            fallback=self.as_fallback,
            note="universal_adaptive_renderer" if not self.as_fallback else "ai_fallback=music2picture_v2",
        )


class AutoImageProvider(ImageGenerationProvider):
    name = "automatic local generation"

    def __init__(self, primary=None, fallback=None, allow_fallback=True):
        self.primary = primary or LocalImageProvider()
        self.fallback_provider = fallback or Music2PictureProvider()
        self.allow_fallback = allow_fallback

    @property
    def status(self):
        status = getattr(self.primary, "status", None)
        return status.description if status is not None else self.primary.name

    def generate(self, request):
        try:
            artwork = self.primary.generate(request)
            _validate_generated_artwork(artwork.image)
            return artwork
        except InterruptedError:
            raise
        except Exception as exc:
            if not self.allow_fallback:
                raise
            reason = _safe_error(exc)
            print(f"Ошибка локального AI backend: {reason}")
            print("Fallback used: Music2Picture; причина указана выше.")
            artwork = self.fallback_provider.generate(request)
            return GeneratedArtwork(
                artwork.image,
                artwork.provider,
                True,
                f"{artwork.note}; local_error={reason}",
            )
        finally:
            self.primary.close()

    def close(self):
        self.primary.close()
        self.fallback_provider.close()


class MockImageProvider(ImageGenerationProvider):
    name = "mock"

    def generate(self, request):
        signature = getattr(request.concept, "signature", "0" * 12)
        value = int(signature[:12], 16)
        colors = ("#183153", "#8f1d2c", "#2f6b3c", "#8a5a18", "#51327a", "#176b72")
        image = Image.new("RGB", (request.size, request.size), colors[value % len(colors)])
        draw = ImageDraw.Draw(image)
        accent = colors[(value // 7 + 2) % len(colors)]
        inset = request.size * (.10 + (value % 8) * .018)
        draw.rectangle((0, request.size*.66, request.size, request.size), fill=accent)
        draw.ellipse((inset, request.size*.12, request.size-inset, request.size*.78), fill="#e9e4d4")
        draw.polygon(
            ((request.size*.12, request.size*.88), (request.size*.52, request.size*.22), (request.size*.88, request.size*.88)),
            fill=colors[(value // 13 + 4) % len(colors)],
        )
        return GeneratedArtwork(image, self.name)


class CloudImageProvider(ImageGenerationProvider):
    name = "custom cloud"

    def __init__(self, generate_callback=None):
        self.generate_callback = generate_callback

    def generate(self, request):
        if self.generate_callback is None:
            raise RuntimeError("Cloud image provider is not configured")
        image = self.generate_callback(request.concept.prompt, request.size, request.seed)
        return GeneratedArtwork(image.convert("RGB"), self.name)


class OpenAIImageProvider(ImageGenerationProvider):
    """Optional cloud provider. It is never selected by the normal local workflow."""

    name = "OpenAI GPT Image"

    def __init__(self, api_key=None, model=None, endpoint=None, timeout=180):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model or os.environ.get("SONIC_FORGE_IMAGE_MODEL", "gpt-image-2")
        self.endpoint = endpoint or os.environ.get(
            "SONIC_FORGE_IMAGE_ENDPOINT", "https://api.openai.com/v1/images/generations"
        )
        self.timeout = timeout

    def generate(self, request):
        if not self.api_key.strip():
            raise RuntimeError("Cloud image provider is not configured")
        quality = {"simple": "low", "balanced": "medium", "rich": "high"}.get(
            request.detail, "medium"
        )
        body = json.dumps({
            "model": self.model,
            "prompt": request.concept.prompt,
            "size": "1024x1024",
            "quality": quality,
            "output_format": "png",
        }).encode("utf-8")
        http_request = urllib.request.Request(
            self.endpoint,
            data=body,
            method="POST",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(http_request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Cloud image provider returned HTTP {exc.code}") from exc
        encoded = payload.get("data", [{}])[0].get("b64_json")
        if not encoded:
            raise RuntimeError("Cloud image provider returned no image data")
        image = Image.open(io.BytesIO(base64.b64decode(encoded))).convert("RGB")
        return GeneratedArtwork(
            image.resize((request.size, request.size), Image.Resampling.LANCZOS),
            self.name,
        )


def _safe_error(exc):
    text = str(exc).replace("\r", " ").replace("\n", " ").strip()
    return text[:240] or type(exc).__name__


def _validate_generated_artwork(image):
    if image is None or image.width < 64 or image.height < 64:
        raise RuntimeError("Локальный AI не создал допустимое изображение")
    gray = image.convert("L")
    low, high = gray.getextrema()
    if high - low < 12 or ImageStat.Stat(gray).stddev[0] < 4:
        raise RuntimeError("Локальный AI создал пустое изображение")
