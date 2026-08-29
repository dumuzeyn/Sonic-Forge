import json
import hashlib
import os
import re
import shutil
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path


RECOMMENDED_MODEL = "DreamShaper 8 Quality"
RECOMMENDED_MODEL_FILE = "DreamShaper_8_pruned.safetensors"
RECOMMENDED_MODEL_URL = (
    "https://huggingface.co/Lykon/DreamShaper/resolve/main/"
    "DreamShaper_8_pruned.safetensors?download=true"
)
LEGACY_RECOMMENDED_MODEL_FILES = ("DreamShaper8_LCM.safetensors",)
RECOMMENDED_MODEL_SIZE = 2_132_625_894
RECOMMENDED_MODEL_SHA256 = "879db523c30d3b9017143d56705015e15a2cb5628762c11d086fed9538abd7fd"
SEMANTIC_MODEL_FILE = "CLIP_ViT-B-32_laion2B.safetensors"
SEMANTIC_MODEL_URL = (
    "https://huggingface.co/laion/CLIP-ViT-B-32-laion2B-s34B-b79K/resolve/main/"
    "open_clip_model.safetensors?download=true"
)
SEMANTIC_MODEL_SIZE = 605_143_316
SEMANTIC_MODEL_SHA256 = "ac4f8c4b88af6d963118cbf40ad93176d092abbedfcb752601ae1866352656e6"
RUNTIME_RELEASE_API = "https://api.github.com/repos/leejet/stable-diffusion.cpp/releases/latest"
RUNTIME_ASSET_SUFFIX = "bin-win-vulkan-x64.zip"


@dataclass(frozen=True)
class ModelStatus:
    ready: bool
    model_path: Path | None
    runtime_path: Path | None
    semantic_path: Path | None
    description: str


class ImageModelManager:
    def __init__(self, root=None):
        base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
        self.root = Path(root) if root else base / "SonicForge" / "models" / "image"
        self.runtime_dir = self.root / "stable-diffusion-cpp"
        self.recommended_path = self.root / RECOMMENDED_MODEL_FILE
        self.semantic_path = self.root / SEMANTIC_MODEL_FILE
        self.settings_path = self.root / "model.json"

    def status(self):
        model_path = self.model_path()
        runtime_path = self.runtime_path()
        semantic_path = self.semantic_model_path()
        if model_path and runtime_path:
            return ModelStatus(True, model_path, runtime_path, semantic_path, f"{model_path.name} готова")
        missing = []
        if not model_path:
            missing.append("AI-модель")
        if not runtime_path:
            missing.append("локальный движок")
        return ModelStatus(False, model_path, runtime_path, semantic_path, "Не установлено: " + ", ".join(missing))

    def model_path(self):
        custom = self._settings().get("custom_model", "")
        if custom:
            path = Path(custom)
            if path.is_file():
                return path
        if self.recommended_path.is_file() and self.recommended_path.stat().st_size == RECOMMENDED_MODEL_SIZE:
            return self.recommended_path
        return None

    def runtime_path(self):
        direct = self.runtime_dir / "sd-cli.exe"
        if direct.is_file():
            return direct
        if self.runtime_dir.is_dir():
            match = next(self.runtime_dir.rglob("sd-cli.exe"), None)
            if match:
                return match
        return None

    def semantic_model_path(self):
        if self.semantic_path.is_file() and self.semantic_path.stat().st_size == SEMANTIC_MODEL_SIZE:
            return self.semantic_path
        return None

    def set_custom_model(self, path):
        path = Path(path).expanduser().resolve()
        if not path.is_file() or path.suffix.lower() not in {".safetensors", ".ckpt", ".gguf"}:
            raise ValueError("Выберите существующую модель .safetensors, .ckpt или .gguf")
        self._write_settings({"custom_model": str(path)})
        return path

    def use_recommended(self):
        self._write_settings({"custom_model": ""})

    def remove_recommended(self):
        if self.recommended_path.exists():
            self.recommended_path.unlink()
        for filename in LEGACY_RECOMMENDED_MODEL_FILES:
            legacy_path = self.root / filename
            if legacy_path.exists():
                legacy_path.unlink()
        self.semantic_path.unlink(missing_ok=True)

    def download_recommended(self, progress=None, cancel_event=None):
        self.root.mkdir(parents=True, exist_ok=True)
        if not self.runtime_path():
            self._download_runtime(progress, cancel_event)
        if not self.recommended_path.is_file() or self.recommended_path.stat().st_size != RECOMMENDED_MODEL_SIZE:
            partial = self.recommended_path.with_suffix(self.recommended_path.suffix + ".part")
            if self.recommended_path.is_file() and not partial.exists():
                self.recommended_path.replace(partial)
            else:
                self.recommended_path.unlink(missing_ok=True)
            self._download(
                RECOMMENDED_MODEL_URL,
                self.recommended_path,
                "model",
                progress,
                cancel_event,
            )
        self._verify_recommended()
        self.use_recommended()
        return self.status()

    def download_runtime(self, progress=None, cancel_event=None):
        self.root.mkdir(parents=True, exist_ok=True)
        if not self.runtime_path():
            self._download_runtime(progress, cancel_event)
        return self.status()

    def _download_runtime(self, progress, cancel_event):
        request = urllib.request.Request(
            RUNTIME_RELEASE_API,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "SonicForge"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            release = json.loads(response.read().decode("utf-8"))
        asset = next(
            (
                item
                for item in release.get("assets", ())
                if item.get("name", "").endswith(RUNTIME_ASSET_SUFFIX)
            ),
            None,
        )
        if not asset:
            raise RuntimeError("Не найдена совместимая Windows-сборка локального движка")
        archive = self.root / "stable-diffusion-cpp.zip"
        self._download(asset["browser_download_url"], archive, "runtime", progress, cancel_event)
        if self.runtime_dir.exists():
            shutil.rmtree(self.runtime_dir)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as bundle:
            destination = self.runtime_dir.resolve()
            for member in bundle.infolist():
                target = (destination / member.filename).resolve()
                if destination not in target.parents and target != destination:
                    raise RuntimeError("Архив локального движка содержит недопустимый путь")
            bundle.extractall(self.runtime_dir)
        archive.unlink(missing_ok=True)
        if not self.runtime_path():
            raise RuntimeError("В загруженном архиве не найден sd-cli.exe")

    @staticmethod
    def _download(url, destination, stage, progress, cancel_event):
        temporary = destination.with_suffix(destination.suffix + ".part")
        try:
            current = temporary.stat().st_size if temporary.is_file() else 0
            total = 0
            attempts = 0
            while not total or current < total:
                if attempts >= 6:
                    raise RuntimeError("Сервер несколько раз прервал загрузку модели")
                headers = {"User-Agent": "SonicForge"}
                if current:
                    headers["Range"] = f"bytes={current}-"
                request = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(request, timeout=90) as response:
                    partial = getattr(response, "status", 200) == 206
                    if current and not partial:
                        temporary.unlink(missing_ok=True)
                        current = 0
                    content_range = response.headers.get("Content-Range", "")
                    match = re.search(r"/(\d+)$", content_range)
                    content_length = int(response.headers.get("Content-Length", 0))
                    total = int(match.group(1)) if match else current + content_length
                    mode = "ab" if current and partial else "wb"
                    with temporary.open(mode) as stream:
                        while True:
                            if cancel_event is not None and cancel_event.is_set():
                                raise InterruptedError("Загрузка отменена")
                            chunk = response.read(1024 * 1024)
                            if not chunk:
                                break
                            stream.write(chunk)
                            current += len(chunk)
                            if progress:
                                progress(stage, current, total)
                attempts += 1
            if total and current != total:
                raise RuntimeError(f"Загружен неполный файл: {current} из {total} байт")
            temporary.replace(destination)
        except Exception:
            if cancel_event is not None and cancel_event.is_set():
                temporary.unlink(missing_ok=True)
            raise

    def _verify_recommended(self):
        self._verify_file(
            self.recommended_path,
            RECOMMENDED_MODEL_SIZE,
            RECOMMENDED_MODEL_SHA256,
            "рекомендуемой модели",
        )

    @staticmethod
    def _verify_file(path, expected_size, expected_sha256, label):
        if not path.is_file() or path.stat().st_size != expected_size:
            path.unlink(missing_ok=True)
            raise RuntimeError(f"Файл {label} имеет неверный размер")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest().lower() != expected_sha256:
            path.unlink(missing_ok=True)
            raise RuntimeError(f"Контрольная сумма {label} не совпала")

    def _settings(self):
        if not self.settings_path.is_file():
            return {}
        try:
            return json.loads(self.settings_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _write_settings(self, values):
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = self.settings_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(values, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.settings_path)
