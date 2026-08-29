import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image


SUBPROCESS_STARTUP_KWARGS = (
    {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
)


class LocalGenerationError(RuntimeError):
    pass


class StableDiffusionCppBackend:
    name = "stable-diffusion.cpp"

    def generate(self, request, runtime_path, model_path):
        try:
            return self._run(request, runtime_path, model_path, economy=False)
        except LocalGenerationError as exc:
            if not _is_memory_error(str(exc)):
                raise
            print("Недостаточно видеопамяти. Повтор в экономном режиме...")
            return self._run(request, runtime_path, model_path, economy=True)

    def _run(self, request, runtime_path, model_path, economy):
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
        return image.resize((request.size, request.size), Image.Resampling.LANCZOS)

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
        quality_steps = {"simple": 14, "balanced": 18, "rich": 22}
        steps = 10 if economy else quality_steps.get(request.detail, 18)
        side = 384 if economy else 512
        command = [
            str(runtime_path),
            "-m",
            str(model_path),
            "-p",
            getattr(request.concept, "render_prompt", "") or request.concept.prompt,
            "-n",
            (
                "text, letters, words, logo, watermark, border, low quality, blurry, "
                "duplicate object, generic album cover, corridor, hallway, tunnel, passage, "
                "stairwell, lone centered silhouette, person, human, portrait, teal fog, "
                "monochrome cyan color cast, glowing doorway, light portal, empty room, "
                "abstract orb, perfect sphere, procedural gradient, waveform, equalizer, "
                "music note, meaningless floating geometry"
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
            "2.2" if lcm else "6.5",
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
