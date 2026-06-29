import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


AUDIO_EXTENSIONS = {".mp3", ".flac", ".wav", ".m4a", ".aac", ".ogg", ".opus", ".wma"}
SUBPROCESS_STARTUP_KWARGS = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}


def default_music_folder():
    music_root = Path.home() / "Music"
    music_folder_name = "".join(chr(code) for code in [1052, 1091, 1079, 1099, 1082, 1072])
    return music_root / music_folder_name


def require_ffmpeg():
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg was not found in PATH.")


def run(command, **kwargs):
    return subprocess.run(
        command,
        check=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        **SUBPROCESS_STARTUP_KWARGS,
        **kwargs,
    )


def audio_files(source_root):
    source_root = Path(source_root)
    if source_root.is_file() and source_root.suffix.lower() in AUDIO_EXTENSIONS:
        return [source_root]
    return sorted(
        path
        for path in source_root.rglob("*")
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
    )


def format_float(value):
    return f"{value:g}"


def loudnorm_stats(audio_path, integrated_lufs, true_peak, lra):
    target_i = format_float(integrated_lufs)
    target_tp = format_float(true_peak)
    target_lra = format_float(lra)
    first_pass_filter = f"loudnorm=I={target_i}:TP={target_tp}:LRA={target_lra}:print_format=json"

    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-vn",
            "-i",
            str(audio_path),
            "-af",
            first_pass_filter,
            "-f",
            "null",
            "NUL",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        **SUBPROCESS_STARTUP_KWARGS,
    )

    text = result.stderr
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise RuntimeError("Could not analyze loudness.")
    return json.loads(text[start : end + 1])


def output_path_for(source_root, output_root, audio_path):
    relative = audio_path.relative_to(source_root)
    return output_root / relative.with_suffix(".mp3")


def normalize_file(audio_path, target_path, stats, integrated_lufs, true_peak, lra, final_gain, denoise=True, denoise_strength=4.0, limiter=True):
    target_i = format_float(integrated_lufs)
    target_tp = format_float(true_peak)
    target_lra = format_float(lra)
    final_gain_text = format_float(final_gain)
    filters = []
    if denoise and denoise_strength > 0:
        filters.append(f"afftdn=nr={format_float(denoise_strength)}:nf=-70")
    filters.append(
        f"loudnorm=I={target_i}:TP={target_tp}:LRA={target_lra}:"
        f"measured_I={stats['input_i']}:"
        f"measured_TP={stats['input_tp']}:"
        f"measured_LRA={stats['input_lra']}:"
        f"measured_thresh={stats['input_thresh']}:"
        f"offset={stats['target_offset']}:"
        f"linear=true:print_format=summary"
    )
    if final_gain and abs(final_gain - 1.0) > 1e-6:
        filters.append(f"volume={final_gain_text}")
    if limiter:
        filters.append("alimiter=limit=0.95:attack=5:release=80")
    second_pass_filter = ",".join(filters)

    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-i",
            str(audio_path),
            "-map",
            "0:a:0",
            "-vn",
            "-af",
            second_pass_filter,
            "-c:a",
            "libmp3lame",
            "-b:a",
            "320k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-map_metadata",
            "0",
            "-id3v2_version",
            "3",
            str(target_path),
        ]
    )


def normalize_music(source, output=None, integrated_lufs=-14.0, true_peak=-1.5, lra=11.0, final_gain=1.15, denoise=True, denoise_strength=4.0, limiter=True):
    require_ffmpeg()

    source_root = Path(source) if source else default_music_folder()
    output_root = Path(output) if output else source_root.with_name(source_root.name + "_normalized_plus30")

    if not source_root.exists():
        raise RuntimeError(f"Source does not exist: {source_root}")
    if not (source_root.is_dir() or source_root.is_file()):
        raise RuntimeError(f"Source must be an audio file or a folder: {source_root}")

    source_root = source_root.resolve()
    source_base = source_root.parent if source_root.is_file() else source_root
    output_root = output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    files = audio_files(source_root)
    if not files:
        print(f"No supported audio files found in {source_root}")
        return

    total = len(files)
    for index, audio_path in enumerate(files, start=1):
        relative = audio_path.relative_to(source_base)
        target_path = output_path_for(source_base, output_root, audio_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if target_path.exists():
            print(f"[{index}/{total}] Skip existing: {relative}")
            continue

        print(f"[{index}/{total}] Analyze: {relative}")
        try:
            stats = loudnorm_stats(audio_path, integrated_lufs, true_peak, lra)
        except Exception as exc:
            print(f"Warning: Could not analyze loudness, skipping: {relative} ({exc})", file=sys.stderr)
            continue

        print(f"[{index}/{total}] Normalize: {relative}")
        try:
            normalize_file(
                audio_path,
                target_path,
                stats,
                integrated_lufs,
                true_peak,
                lra,
                final_gain,
                denoise=denoise,
                denoise_strength=denoise_strength,
                limiter=limiter,
            )
        except subprocess.CalledProcessError:
            if target_path.exists():
                target_path.unlink()
            print(f"Warning: Failed: {relative}", file=sys.stderr)

    print(f"Done. Normalized files are in: {output_root}")


def main():
    parser = argparse.ArgumentParser(description="Normalize a music file or folder with ffmpeg loudnorm and export MP3 files.")
    parser.add_argument("--source", "--Source", help="Source music file or folder. Default: ~/Music/Muzyka in Russian.")
    parser.add_argument("--output", "--Output", help="Output folder. Default: source folder name + _normalized_plus30.")
    parser.add_argument("--integrated-lufs", "--IntegratedLufs", type=float, default=-14.0)
    parser.add_argument("--true-peak", "--TruePeak", type=float, default=-1.5)
    parser.add_argument("--lra", "--Lra", type=float, default=11.0)
    parser.add_argument("--final-gain", "--FinalGain", type=float, default=1.15)
    parser.add_argument("--denoise", dest="denoise", action="store_true", default=True, help="Apply gentle FFT denoise before normalization. Enabled by default.")
    parser.add_argument("--no-denoise", dest="denoise", action="store_false", help="Disable denoise and use only loudnorm/limiter.")
    parser.add_argument("--denoise-strength", "--DenoiseStrength", type=float, default=4.0, help="Gentle denoise amount in dB. Keep low to avoid damaging music.")
    parser.add_argument("--limiter", dest="limiter", action="store_true", default=True, help="Apply limiter after gain. Enabled by default.")
    parser.add_argument("--no-limiter", dest="limiter", action="store_false", help="Disable final limiter.")
    args = parser.parse_args()

    normalize_music(
        args.source,
        args.output,
        integrated_lufs=args.integrated_lufs,
        true_peak=args.true_peak,
        lra=args.lra,
        final_gain=args.final_gain,
        denoise=args.denoise,
        denoise_strength=args.denoise_strength,
        limiter=args.limiter,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
