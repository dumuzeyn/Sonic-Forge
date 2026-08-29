import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

from mutagen import File as MutagenFile


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


def check_cancelled(cancel_event):
    if cancel_event is not None and cancel_event.is_set():
        raise InterruptedError("Processing was cancelled.")


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


def probe_duration(audio_path):
    try:
        audio = MutagenFile(audio_path)
        return max(0.0, float(audio.info.length)) if audio is not None else 0.0
    except (AttributeError, OSError, TypeError, ValueError):
        return 0.0


def normalize_file(
    audio_path,
    target_path,
    stats,
    integrated_lufs,
    true_peak,
    lra,
    final_gain,
    denoise=True,
    denoise_strength=4.0,
    limiter=True,
    bass_gain=0.0,
    mid_gain=0.0,
    treble_gain=0.0,
    highpass_hz=20.0,
    lowpass_hz=20000.0,
    stereo_width=1.0,
    compressor=False,
    compressor_threshold=-18.0,
    compressor_ratio=3.0,
    compressor_attack=20.0,
    compressor_release=250.0,
    compressor_makeup=0.0,
    pitch_semitones=0.0,
    playback_speed=1.0,
    reverb_mix=0.0,
    fade_in=0.0,
    fade_out=0.0,
    cancel_event=None,
):
    check_cancelled(cancel_event)
    target_i = format_float(integrated_lufs)
    target_tp = format_float(true_peak)
    target_lra = format_float(lra)
    final_gain_text = format_float(final_gain)
    filters = []
    if highpass_hz >= 20:
        filters.append(f"highpass=f={format_float(highpass_hz)}")
    if 1000 <= lowpass_hz < 22000:
        filters.append(f"lowpass=f={format_float(lowpass_hz)}")
    if denoise and denoise_strength > 0:
        filters.append(f"afftdn=nr={format_float(denoise_strength)}:nf=-70")
    if abs(bass_gain) > 1e-6:
        filters.append(f"bass=g={format_float(bass_gain)}:f=110:w=0.65")
    if abs(mid_gain) > 1e-6:
        filters.append(
            f"equalizer=f=1100:t=q:w=0.85:g={format_float(mid_gain)}"
        )
    if abs(treble_gain) > 1e-6:
        filters.append(f"treble=g={format_float(treble_gain)}:f=7200:w=0.65")
    if abs(stereo_width - 1.0) > 1e-6:
        filters.append(f"extrastereo=m={format_float(stereo_width)}:c=1")
    if compressor:
        threshold = math.pow(10.0, compressor_threshold / 20.0)
        makeup = math.pow(10.0, compressor_makeup / 20.0)
        filters.append(
            "acompressor="
            f"threshold={format_float(threshold)}:"
            f"ratio={format_float(compressor_ratio)}:"
            f"attack={format_float(compressor_attack)}:"
            f"release={format_float(compressor_release)}:"
            f"makeup={format_float(makeup)}:"
            "knee=2.828:link=average:detection=rms"
        )
    pitch_ratio = math.pow(2.0, pitch_semitones / 12.0)
    if abs(pitch_semitones) > 1e-6:
        filters.extend(
            [
                "aresample=48000",
                f"asetrate={format_float(48000 * pitch_ratio)}",
                "aresample=48000",
                f"atempo={format_float(1.0 / pitch_ratio)}",
            ]
        )
    if abs(playback_speed - 1.0) > 1e-6:
        filters.append(f"atempo={format_float(playback_speed)}")
    if reverb_mix > 0:
        decay = min(0.75, 0.08 + reverb_mix * 0.62)
        filters.append(
            "aecho="
            f"0.8:{format_float(0.72 + reverb_mix * 0.18)}:"
            f"55|110:{format_float(decay)}|{format_float(decay * 0.68)}"
        )
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
        limiter_level = min(0.99, math.pow(10.0, true_peak / 20.0))
        filters.append(
            f"alimiter=limit={format_float(limiter_level)}:attack=5:release=80"
        )
    duration = probe_duration(audio_path) / max(playback_speed, 0.01)
    if fade_in > 0:
        filters.append(f"afade=t=in:st=0:d={format_float(fade_in)}")
    if fade_out > 0 and duration > fade_out:
        filters.append(
            f"afade=t=out:st={format_float(duration - fade_out)}:"
            f"d={format_float(fade_out)}"
        )
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
    check_cancelled(cancel_event)


def normalize_music(
    source,
    output=None,
    integrated_lufs=-14.0,
    true_peak=-1.5,
    lra=11.0,
    final_gain=1.15,
    denoise=True,
    denoise_strength=4.0,
    limiter=True,
    bass_gain=0.0,
    mid_gain=0.0,
    treble_gain=0.0,
    highpass_hz=20.0,
    lowpass_hz=20000.0,
    stereo_width=1.0,
    compressor=False,
    compressor_threshold=-18.0,
    compressor_ratio=3.0,
    compressor_attack=20.0,
    compressor_release=250.0,
    compressor_makeup=0.0,
    pitch_semitones=0.0,
    playback_speed=1.0,
    reverb_mix=0.0,
    fade_in=0.0,
    fade_out=0.0,
    cancel_event=None,
):
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
        check_cancelled(cancel_event)
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
            check_cancelled(cancel_event)
            print(f"Warning: Could not analyze loudness, skipping: {relative} ({exc})", file=sys.stderr)
            continue

        check_cancelled(cancel_event)
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
                bass_gain=bass_gain,
                mid_gain=mid_gain,
                treble_gain=treble_gain,
                highpass_hz=highpass_hz,
                lowpass_hz=lowpass_hz,
                stereo_width=stereo_width,
                compressor=compressor,
                compressor_threshold=compressor_threshold,
                compressor_ratio=compressor_ratio,
                compressor_attack=compressor_attack,
                compressor_release=compressor_release,
                compressor_makeup=compressor_makeup,
                pitch_semitones=pitch_semitones,
                playback_speed=playback_speed,
                reverb_mix=reverb_mix,
                fade_in=fade_in,
                fade_out=fade_out,
                cancel_event=cancel_event,
            )
        except subprocess.CalledProcessError:
            if target_path.exists():
                target_path.unlink()
            check_cancelled(cancel_event)
            print(f"Warning: Failed: {relative}", file=sys.stderr)

    check_cancelled(cancel_event)
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
    parser.add_argument("--bass-gain", type=float, default=0.0)
    parser.add_argument("--mid-gain", type=float, default=0.0)
    parser.add_argument("--treble-gain", type=float, default=0.0)
    parser.add_argument("--highpass-hz", type=float, default=20.0)
    parser.add_argument("--lowpass-hz", type=float, default=20000.0)
    parser.add_argument("--stereo-width", type=float, default=1.0)
    parser.add_argument("--compressor", action="store_true")
    parser.add_argument("--compressor-threshold", type=float, default=-18.0)
    parser.add_argument("--compressor-ratio", type=float, default=3.0)
    parser.add_argument("--compressor-attack", type=float, default=20.0)
    parser.add_argument("--compressor-release", type=float, default=250.0)
    parser.add_argument("--compressor-makeup", type=float, default=0.0)
    parser.add_argument("--pitch-semitones", type=float, default=0.0)
    parser.add_argument("--playback-speed", type=float, default=1.0)
    parser.add_argument("--reverb-mix", type=float, default=0.0)
    parser.add_argument("--fade-in", type=float, default=0.0)
    parser.add_argument("--fade-out", type=float, default=0.0)
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
        bass_gain=args.bass_gain,
        mid_gain=args.mid_gain,
        treble_gain=args.treble_gain,
        highpass_hz=args.highpass_hz,
        lowpass_hz=args.lowpass_hz,
        stereo_width=args.stereo_width,
        compressor=args.compressor,
        compressor_threshold=args.compressor_threshold,
        compressor_ratio=args.compressor_ratio,
        compressor_attack=args.compressor_attack,
        compressor_release=args.compressor_release,
        compressor_makeup=args.compressor_makeup,
        pitch_semitones=args.pitch_semitones,
        playback_speed=args.playback_speed,
        reverb_mix=args.reverb_mix,
        fade_in=args.fade_in,
        fade_out=args.fade_out,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
