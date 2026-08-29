from pathlib import Path

from music2picture_v2 import DEFAULT_PIPELINE, render_cover


class Music2PictureFallbackProvider:
    """Expose the universal Music2Picture v2 renderer to cover providers."""

    name = "Music2Picture v2"

    def generate(self, request):
        if not request.audio_path:
            raise RuntimeError("Music2Picture v2 requires the source audio file")
        if request.cancel_event is not None and request.cancel_event.is_set():
            raise InterruptedError("Создание обложки остановлено")
        bundle = request.analysis_bundle
        if bundle is None:
            bundle = DEFAULT_PIPELINE.analyse(Path(request.audio_path))
        image = render_cover(bundle.visual_dna, bundle.visual_plan, size=request.size, seed=request.seed)
        print("Используется единый адаптивный движок Music2Picture v2.")
        return image, "v2"
