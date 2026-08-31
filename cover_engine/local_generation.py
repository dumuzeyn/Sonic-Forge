import os
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image, ImageFilter


SUBPROCESS_STARTUP_KWARGS = (
    {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
)


class LocalGenerationError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelCapabilities:
    backend: str
    native_sizes: tuple[int, ...]
    max_native_size: int
    supports_upscale_enhancement: bool
    supports_cpu_fallback: bool

    def to_dict(self):
        return asdict(self)


class StableDiffusionCppBackend:
    name = "stable-diffusion.cpp"

    QUALITY_PROFILES = {
        "economy": {"native_size": 384, "steps": 10, "cfg": 5.8, "sharpen": 0.00},
        "simple": {"native_size": 384, "steps": 14, "cfg": 6.2, "sharpen": 0.00},
        "balanced": {"native_size": 512, "steps": 20, "cfg": 6.7, "sharpen": 0.10},
        "quality": {"native_size": 512, "steps": 24, "cfg": 6.9, "sharpen": 0.14},
        "rich": {"native_size": 512, "steps": 28, "cfg": 7.0, "sharpen": 0.18},
    }

    def __init__(self):
        self.last_generation_info = {}

    def generate(self, request, runtime_path, model_path):
        try:
            return self._run(request, runtime_path, model_path, economy=False)
        except LocalGenerationError as exc:
            if not _is_memory_error(str(exc)):
                raise
            print("Недостаточно видеопамяти. Повтор в экономном режиме...")
            return self._run(request, runtime_path, model_path, economy=True)

    def _run(self, request, runtime_path, model_path, economy):
        capabilities = self.capabilities(model_path)
        with tempfile.TemporaryDirectory(prefix="sonicforge_local_ai_") as directory:
            output = Path(directory) / "generated.png"
            command = self._command(
                request,
                runtime_path,
                model_path,
                output,
                economy,
                self._preferred_backend(runtime_path),
            )
            log_path = Path(directory) / "generation.log"
            with log_path.open("w+", encoding="utf-8", errors="replace") as log:
                process = None
                try:
                    process = subprocess.Popen(
                        command,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        **SUBPROCESS_STARTUP_KWARGS,
                    )
                    while process.poll() is None:
                        if request.cancel_event is not None and request.cancel_event.is_set():
                            self._stop_process(process)
                            raise InterruptedError("Создание обложки остановлено")
                        time.sleep(0.15)
                    log.seek(0)
                    lines = log.read().splitlines()
                finally:
                    if process is not None and process.poll() is None:
                        self._stop_process(process)
            if process.returncode != 0 or not output.is_file():
                detail = "\n".join(lines[-12:])
                raise LocalGenerationError(detail or f"Локальный движок завершился с кодом {process.returncode}")
            with Image.open(output) as generated:
                image = generated.convert("RGB").copy()
        native_size = image.width
        upscale = request.size != native_size
        if upscale:
            image = image.resize((request.size, request.size), Image.Resampling.LANCZOS)
            amount = self.QUALITY_PROFILES.get(request.detail, self.QUALITY_PROFILES["balanced"])["sharpen"]
            if amount:
                enhanced = image.filter(ImageFilter.UnsharpMask(radius=1.2, percent=55, threshold=5))
                image = Image.blend(image, enhanced, amount)
        self.last_generation_info = {
            "quality": "economy" if economy else request.detail,
            "native_size": native_size,
            "output_size": request.size,
            "upscaled": upscale,
            "capabilities": capabilities.to_dict(),
        }
        if upscale:
            print(f"Нативная генерация: {native_size}×{native_size}; улучшение до {request.size}×{request.size}")
        return image

    @staticmethod
    def _stop_process(process):
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)

    @staticmethod
    def _command(request, runtime_path, model_path, output, economy, backend=None):
        lcm = "lcm" in Path(model_path).name.lower()
        profile = StableDiffusionCppBackend.QUALITY_PROFILES.get(
            "economy" if economy else request.detail,
            StableDiffusionCppBackend.QUALITY_PROFILES["balanced"],
        )
        steps = profile["steps"]
        side = profile["native_size"]
        command = [
            str(runtime_path),
            "-m",
            str(model_path),
            "-p",
            getattr(request.concept, "render_prompt", "") or request.concept.prompt,
            "-n",
            getattr(request.concept, "negative_prompt", "") or (
                "text, letters, words, logo, watermark, low quality, blurry focal subject"
            ),
            "-o",
            str(output),
            "-W",
            str(side),
            "-H",
            str(side),
            "--steps",
            str(steps),
            "--cfg-scale",
            "2.2" if lcm else str(profile["cfg"]),
            "--sampling-method",
            "lcm" if lcm else "dpm++2m",
            "-s",
            str(request.seed if request.seed is not None else -1),
            "--vae-tiling",
        ]
        if economy:
            command.extend(("--backend", "cpu", "--params-backend", "cpu"))
        elif backend:
            command.extend(
                (
                    "--backend",
                    backend,
                    "--params-backend",
                    "cpu",
                    "--max-vram",
                    "-0.5",
                    "--stream-layers",
                )
            )
        else:
            command.extend(("--auto-fit", "--max-vram", "-1"))
        return command

    @staticmethod
    def capabilities(model_path):
        # The current SD 1.x compatible path is honest about its native limit.
        return ModelCapabilities(
            backend="stable-diffusion.cpp",
            native_sizes=(384, 512),
            max_native_size=512,
            supports_upscale_enhancement=True,
            supports_cpu_fallback=True,
        )

    @staticmethod
    def _preferred_backend(runtime_path):
        try:
            result = subprocess.run(
                [str(runtime_path), "--list-devices"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
                **SUBPROCESS_STARTUP_KWARGS,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        devices = []
        for line in result.stdout.splitlines():
            if "\t" not in line:
                continue
            name, description = line.split("\t", 1)
            if name.lower().startswith(("vulkan", "cuda")):
                devices.append((name, description.lower()))
        for vendor in ("nvidia", "amd", "radeon", "arc"):
            match = next((name for name, text in devices if vendor in text), None)
            if match:
                return match
        return devices[-1][0] if devices else None


def _is_memory_error(message):
    normalized = message.lower()
    return any(
        marker in normalized
        for marker in ("out of memory", "cuda error", "vram", "allocation", "not enough memory")
    )
