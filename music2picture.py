import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


AUDIO_EXTENSIONS = {".mp3", ".flac", ".wav", ".m4a", ".aac", ".ogg", ".opus", ".wma"}

# PyCharm / direct Python run settings.
# Set RUN_FROM_CODE = True, edit the paths below, then press Run in PyCharm.
RUN_FROM_CODE = False
CODE_MODE = "covers"  # "covers" or "process"
CODE_SOURCE = r"C:\Path\To\MusicOrSong.mp3"
CODE_OUTPUT = r"C:\Path\To\OutputFolder"

# Cover settings.
CODE_SIZE = 1000
CODE_PATTERNS = 2  # 1 = simpler pattern, 2 = richer pattern
CODE_CENTER_TITLE = True  # True = draw file name in the middle, False = only artwork
CODE_EMBED_COVER = False  # True = attach generated PNG as MP3 cover art

# Music processing settings.
CODE_INTEGRATED_LUFS = -14.0
CODE_TRUE_PEAK = -1.5
CODE_LRA = 11.0
CODE_FINAL_GAIN = 1.30
CODE_COLOR_MODE = "bpm"  # "bpm" = original colors, "drive" = local drive colors



def require_ffmpeg():
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg was not found in PATH.")
    if not shutil.which("ffprobe"):
        raise RuntimeError("ffprobe was not found in PATH.")


def run(command):
    subprocess.run(command, check=True, text=True, encoding="utf-8", errors="replace")


def audio_files(source):
    source = Path(source)
    if source.is_file() and source.suffix.lower() in AUDIO_EXTENSIONS:
        return [source]
    return sorted(p for p in source.rglob("*") if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS)


def clean_stem(path):
    return Path(path).stem.rstrip(". ")



def output_mp3_path(source_root, output_root, audio_path):
    relative = audio_path.relative_to(source_root)
    return output_root / relative.with_suffix(".mp3")


def loudnorm_stats(audio_path, integrated_lufs, true_peak, lra):
    loudnorm = f"loudnorm=I={integrated_lufs}:TP={true_peak}:LRA={lra}:print_format=json"
    command = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-vn",
        "-i",
        str(audio_path),
        "-af",
        loudnorm,
        "-f",
        "null",
        "NUL",
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    text = result.stderr
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise RuntimeError(f"Could not read loudnorm stats for {audio_path}")
    return json.loads(text[start : end + 1])


def normalize_music(source, output, integrated_lufs=-14.0, true_peak=-1.5, lra=11.0, final_gain=1.30):
    source_root = Path(source).resolve()
    output_root = Path(output).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    files = audio_files(source_root)

    if source_root.is_file():
        source_root = source_root.parent

    if not files:
        print(f"No supported audio files found in {source_root}")
        return

    for index, audio_path in enumerate(files, start=1):
        target = output_mp3_path(source_root, output_root, audio_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        if target.exists():
            print(f"[{index}/{len(files)}] Skip existing: {audio_path.name}")
            continue

        print(f"[{index}/{len(files)}] Analyze: {audio_path.name}")
        stats = loudnorm_stats(audio_path, integrated_lufs, true_peak, lra)
        loudnorm = (
            f"loudnorm=I={integrated_lufs}:TP={true_peak}:LRA={lra}:"
            f"measured_I={stats['input_i']}:"
            f"measured_TP={stats['input_tp']}:"
            f"measured_LRA={stats['input_lra']}:"
            f"measured_thresh={stats['input_thresh']}:"
            f"offset={stats['target_offset']}:"
            f"linear=true:print_format=summary,"
            f"volume={final_gain}"
        )

        print(f"[{index}/{len(files)}] Normalize: {audio_path.name}")
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
                loudnorm,
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
                str(target),
            ]
        )

    print(f"Done. Processed music is in: {output_root}")


def read_audio(audio_path, sample_rate=22050):
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(audio_path),
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-f",
        "f32le",
        "pipe:1",
    ]
    raw = subprocess.check_output(command)
    data = np.frombuffer(raw, dtype=np.float32)
    if data.size == 0:
        raise RuntimeError(f"No audio data decoded from {audio_path}")
    peak = np.max(np.abs(data))
    return data / peak if peak > 0 else data


def stft_features(audio, n_fft=2048, hop=512):
    if audio.size < n_fft:
        audio = np.pad(audio, (0, n_fft - audio.size))
    frame_count = max(1, 1 + (audio.size - n_fft) // hop)
    usable = audio[: n_fft + hop * (frame_count - 1)]
    frames = np.lib.stride_tricks.sliding_window_view(usable, n_fft)[::hop]
    window = np.hanning(n_fft).astype(np.float32)
    spectrum = np.abs(np.fft.rfft(frames * window, axis=1)).T
    spectrum = np.log1p(spectrum)[:512]
    spectrum -= spectrum.min()
    if spectrum.max() > 0:
        spectrum /= spectrum.max()

    rms = np.sqrt(np.mean(frames * frames, axis=1))
    if rms.max() > 0:
        rms /= rms.max()

    bass = spectrum[:24].mean(axis=0)
    mids = spectrum[24:160].mean(axis=0)
    highs = spectrum[160:].mean(axis=0)
    centroid = (spectrum * np.arange(spectrum.shape[0])[:, None]).sum(axis=0) / (spectrum.sum(axis=0) + 1e-6)
    centroid /= max(1, spectrum.shape[0] - 1)
    return spectrum, rms, bass, mids, highs, centroid


def resample_axis(values, size):
    if values.size == size:
        return values
    source = np.linspace(0, 1, values.size)
    target = np.linspace(0, 1, size)
    return np.interp(target, source, values)


def resize_spectrum(spectrum, freq_bins, time_bins):
    freq_source = np.linspace(0, 1, spectrum.shape[0])
    freq_target = np.linspace(0, 1, freq_bins) ** 1.65
    temp = np.empty((freq_bins, spectrum.shape[1]), dtype=np.float32)
    for t in range(spectrum.shape[1]):
        temp[:, t] = np.interp(freq_target, freq_source, spectrum[:, t])

    time_source = np.linspace(0, 1, temp.shape[1])
    time_target = np.linspace(0, 1, time_bins)
    resized = np.empty((freq_bins, time_bins), dtype=np.float32)
    for f in range(freq_bins):
        resized[f] = np.interp(time_target, time_source, temp[f])
    return resized


def estimate_bpm(rms, sample_rate=22050, hop=512):
    if rms.size < 16:
        return 120.0

    envelope = np.maximum(0, np.diff(rms, prepend=rms[0]))
    envelope -= envelope.mean()
    if np.max(np.abs(envelope)) > 0:
        envelope /= np.max(np.abs(envelope))

    frame_rate = sample_rate / hop
    min_lag = max(1, int(frame_rate * 60 / 200))
    max_lag = min(len(envelope) - 1, int(frame_rate * 60 / 30))
    if max_lag <= min_lag:
        return 120.0

    scores = [float(np.dot(envelope[:-lag], envelope[lag:])) for lag in range(min_lag, max_lag + 1)]
    best_lag = min_lag + int(np.argmax(scores))
    bpm = 60 * frame_rate / best_lag
    while bpm < 30:
        bpm *= 2
    while bpm > 200:
        bpm /= 2
    return float(np.clip(bpm, 30, 200))


def estimate_bpm_curve_from_bass(bass, output_size, sample_rate=22050, hop=512, window_seconds=15):
    bass = bass.astype(np.float32)
    if bass.size < 8:
        return np.full(output_size, 120.0, dtype=np.float32)

    smooth = bass.copy()
    for _ in range(4):
        smooth = (smooth * 2 + np.roll(smooth, 1) + np.roll(smooth, -1)) / 4

    onset = np.maximum(0, np.diff(smooth, prepend=smooth[0]))
    threshold = np.percentile(onset, 78)
    peak_mask = (onset > threshold) & (onset >= np.roll(onset, 1)) & (onset > np.roll(onset, -1))

    frames_per_window = max(1, int(window_seconds * sample_rate / hop))
    global_bpm = estimate_bpm(bass, sample_rate=sample_rate, hop=hop)
    centers = []
    bpm_values = []

    for start in range(0, bass.size, frames_per_window):
        end = min(bass.size, start + frames_per_window)
        bpm = int(np.count_nonzero(peak_mask[start:end])) * (60.0 / window_seconds)
        if bpm < 30 or bpm > 200:
            bpm = global_bpm
        centers.append((start + end - 1) / 2)
        bpm_values.append(float(np.clip(bpm, 30, 200)))

    if len(centers) == 1:
        return np.full(output_size, bpm_values[0], dtype=np.float32)

    source = np.asarray(centers, dtype=np.float32) / max(1, bass.size - 1)
    target = np.linspace(0, 1, output_size, dtype=np.float32)
    curve = np.interp(target, source, np.asarray(bpm_values, dtype=np.float32))
    for _ in range(3):
        curve = (curve * 3 + np.roll(curve, 1) + np.roll(curve, -1)) / 5
    return np.clip(curve, 30, 200).astype(np.float32)


def normalize_feature(values):
    values = np.asarray(values, dtype=np.float32)
    if values.size == 0:
        return values
    low = float(np.percentile(values, 5))
    high = float(np.percentile(values, 95))
    if high <= low + 1e-8:
        return np.zeros_like(values, dtype=np.float32)
    return np.clip((values - low) / (high - low), 0, 1).astype(np.float32)


def estimate_drive_curve(spectrum, rms, centroid, bpm_curve, output_size, sample_rate=22050, hop=512, window_seconds=3.0):
    rms = np.asarray(rms, dtype=np.float32)
    centroid = np.asarray(centroid, dtype=np.float32)
    if rms.size == 0:
        return np.zeros(output_size, dtype=np.float32)

    onset = np.maximum(0, np.diff(rms, prepend=rms[0]))
    frames_per_window = max(1, int(window_seconds * sample_rate / hop))
    density = np.zeros_like(rms, dtype=np.float32)
    for start in range(0, rms.size, frames_per_window):
        end = min(rms.size, start + frames_per_window)
        if end <= start:
            continue
        local = onset[start:end]
        threshold = float(np.percentile(local, 70)) if local.size else 0.0
        density[start:end] = np.count_nonzero(local > threshold) / max(1, end - start)

    spectral_flux = np.zeros_like(rms, dtype=np.float32)
    if spectrum.shape[1] > 1:
        diff = np.diff(spectrum, axis=1, prepend=spectrum[:, :1])
        spectral_flux = np.maximum(0, diff).mean(axis=0).astype(np.float32)

    o = normalize_feature(density)
    r = normalize_feature(rms)
    f = normalize_feature(spectral_flux)
    c = normalize_feature(centroid)
    audio_drive = np.clip(0.4 * o + 0.3 * r + 0.2 * f + 0.1 * c, 0, 1)

    local_bpm = resample_axis(np.asarray(bpm_curve, dtype=np.float32), audio_drive.size)
    bpm_drive = np.clip((local_bpm - 55.0) / 125.0, 0, 1).astype(np.float32)
    drive = np.clip(0.85 * audio_drive + 0.15 * bpm_drive, 0, 1)
    for _ in range(3):
        drive = (drive * 3 + np.roll(drive, 1) + np.roll(drive, -1)) / 5
    return resample_axis(drive.astype(np.float32), output_size).astype(np.float32)


def drive_to_hue(drive):
    stops = np.asarray([0.00, 0.22, 0.44, 0.66, 0.84, 1.00], dtype=np.float32)
    hues = np.asarray([0.77, 0.64, 0.36, 0.17, 0.07, 0.00], dtype=np.float32)
    return np.interp(np.clip(drive, 0, 1), stops, hues).astype(np.float32)


def peak_emphasis(values):
    values = values.astype(np.float32)
    smooth = values.copy()
    for _ in range(6):
        smooth = (smooth * 2 + np.roll(smooth, 1) + np.roll(smooth, -1)) / 4
    peaks = np.maximum(0, values - smooth)
    if peaks.max() > 0:
        peaks /= peaks.max()
    peaks = np.power(peaks, 0.55)
    for _ in range(4):
        peaks = (peaks * 3 + np.roll(peaks, 1) + np.roll(peaks, -1)) / 5
    return np.clip(peaks, 0, 1)


def bpm_to_hue(bpm):
    position = np.clip((bpm - 40.0) / 160.0, 0, 1)
    return 0.78 * position


def hsv_to_rgb_array(h, s, v):
    h = np.mod(h, 1.0)
    i = np.floor(h * 6).astype(np.int32)
    f = h * 6 - i
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    i = np.mod(i, 6)

    rgb = np.zeros(h.shape + (3,), dtype=np.float32)
    masks = [i == n for n in range(6)]
    rgb[masks[0]] = np.stack([v, t, p], axis=-1)[masks[0]]
    rgb[masks[1]] = np.stack([q, v, p], axis=-1)[masks[1]]
    rgb[masks[2]] = np.stack([p, v, t], axis=-1)[masks[2]]
    rgb[masks[3]] = np.stack([p, q, v], axis=-1)[masks[3]]
    rgb[masks[4]] = np.stack([t, p, v], axis=-1)[masks[4]]
    rgb[masks[5]] = np.stack([v, p, q], axis=-1)[masks[5]]
    return rgb


def smooth_random_field(size, cells):
    small = np.random.default_rng().random((cells, cells), dtype=np.float32)
    image = Image.fromarray(np.uint8(small * 255), "L")
    image = image.resize((size, size), Image.Resampling.BICUBIC)
    field = np.asarray(image).astype(np.float32) / 255
    field -= field.min()
    if field.max() > 0:
        field /= field.max()
    return field


def render_random_cover(spec, rms, bass, mids, highs, size, patterns=2, bpm=120.0, bpm_curve=None, color_mode="bpm", drive_curve=None):
    song_map = resize_spectrum(spec, freq_bins=size, time_bins=size)
    song_map = np.flipud(song_map)
    if bpm_curve is None:
        bpm_curve = np.full(size, bpm, dtype=np.float32)
    if drive_curve is None:
        drive_curve = np.full(size, 0.5, dtype=np.float32)
    if color_mode not in {"bpm", "drive"}:
        raise ValueError('color_mode must be "bpm" or "drive".')

    volume = resample_axis(rms, size)
    bass_line = resample_axis(bass, size)
    highs_line = resample_axis(highs, size)
    peaks = peak_emphasis(volume)

    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    base_part = size - 1 - yy
    base_freq = xx

    field_a = smooth_random_field(size, cells=14)
    field_b = smooth_random_field(size, cells=23)
    field_c = smooth_random_field(size, cells=9)

    peak_rows = peaks[np.clip(base_part.astype(np.int32), 0, size - 1)]
    part_warp = (field_a - 0.5) * (70 + 130 * peak_rows)
    freq_warp = (field_b - 0.5) * (90 + 180 * peak_rows)
    if patterns >= 2:
        part_warp += np.sin((xx * 0.018 + field_c * 9) * math.pi) * (28 + 95 * peak_rows)
        freq_warp += np.sin((yy * 0.015 + field_a * 8) * math.pi) * (35 + 110 * peak_rows)

    part_idx = np.clip((base_part + part_warp).astype(np.int32), 0, size - 1)
    freq_idx = np.clip((base_freq + freq_warp).astype(np.int32), 0, size - 1)

    spectrum_value = song_map[freq_idx, part_idx]
    bass_map = bass_line[part_idx]
    high_map = highs_line[part_idx]

    rng = np.random.default_rng()
    if color_mode == "drive":
        local_drive = drive_curve[part_idx]
        drive_sigma = 0.018 + 0.026 * peak_rows
        pixel_drive = rng.normal(local_drive, drive_sigma).astype(np.float32)
        pixel_drive -= np.mean(pixel_drive, axis=1, keepdims=True) - np.mean(local_drive, axis=1, keepdims=True)
        pixel_drive = np.clip(pixel_drive + (spectrum_value - 0.5) * 0.018, 0, 1)
        hue = drive_to_hue(pixel_drive)
        saturation = np.clip(0.62 + spectrum_value * 0.18 + high_map * 0.08 + peak_rows * 0.12, 0, 1)
        value = np.clip(0.14 + spectrum_value * 0.56 + volume[part_idx] * 0.26 + bass_map * 0.12 + peak_rows * 0.30, 0, 1)
    else:
        local_bpm = bpm_curve[part_idx]
        bpm_sigma = 3.0 + 3.0 * peak_rows
        pixel_bpm = rng.normal(local_bpm, bpm_sigma).astype(np.float32)
        pixel_bpm -= np.mean(pixel_bpm, axis=1, keepdims=True) - np.mean(local_bpm, axis=1, keepdims=True)
        pixel_bpm = np.clip(pixel_bpm, 30, 200)

        hue_shift = (field_a - 0.5) * 0.035 + spectrum_value * 0.018
        red_lock = np.clip((40.0 - pixel_bpm) / 10.0, 0, 1)
        hue_shift = np.where(red_lock > 0, np.minimum(hue_shift, 0), hue_shift)
        hue = np.mod(bpm_to_hue(pixel_bpm) + hue_shift, 1.0)
        saturation = np.clip(0.54 + spectrum_value * 0.24 + high_map * 0.10 + peak_rows * 0.18, 0, 1)
        value = np.clip(0.12 + spectrum_value * 0.58 + volume[part_idx] * 0.28 + bass_map * 0.12 + peak_rows * 0.38, 0, 1)

    rgb = hsv_to_rgb_array(hue, saturation, value)
    edge_pattern = np.abs(np.gradient(field_a, axis=0)) + np.abs(np.gradient(field_b, axis=1))
    edge_pattern = np.clip(edge_pattern * 20, 0, 1)
    rgb *= np.clip(0.90 + edge_pattern[..., None] * (0.25 + peak_rows[..., None] * 0.7), 0.72, 1.28)
    return np.clip(rgb * 255, 0, 255).astype(np.uint8)


def title_font(size):
    for candidate in (
        Path("C:/Windows/Fonts/segoeuib.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ):
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def music_edge_color(image, rng):
    arr = np.asarray(image.convert("RGB")).astype(np.float32)
    pixels = arr.reshape(-1, 3)
    scores = pixels.max(axis=1) - pixels.min(axis=1) + pixels.mean(axis=1) * 0.2
    top_count = max(32, len(scores) // 80)
    palette = pixels[np.argpartition(scores, -top_count)[-top_count:]]
    color = palette[int(rng.integers(0, len(palette)))]
    return tuple(int(x) for x in np.clip(color * 1.18, 0, 255))


def wrap_text(text, font, draw, max_width):
    words = text.split()
    if not words:
        return [text]

    lines = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def text_block_size(lines, font, draw, line_gap):
    sizes = [draw.textbbox((0, 0), line, font=font) for line in lines]
    widths = [box[2] - box[0] for box in sizes]
    heights = [box[3] - box[1] for box in sizes]
    return max(widths or [0]), sum(heights) + max(0, len(lines) - 1) * line_gap


def fit_text_to_square(text, square_size):
    probe = Image.new("RGB", (square_size, square_size))
    draw = ImageDraw.Draw(probe)
    best = None
    for font_size in range(12, square_size + 1):
        font = title_font(font_size)
        line_gap = max(4, font_size // 7)
        lines = wrap_text(text, font, draw, square_size)
        width, height = text_block_size(lines, font, draw, line_gap)
        if width <= square_size and height <= square_size:
            best = (font, lines, line_gap, width, height)
        elif best is not None:
            break
    return best


def draw_uniform_outline(overlay, position, text, font, radius):
    mask = Image.new("L", overlay.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.text(position, text, font=font, fill=255)
    expanded = mask.filter(ImageFilter.MaxFilter(radius * 2 + 1))
    outline_arr = np.clip(np.asarray(expanded).astype(np.int16) - np.asarray(mask).astype(np.int16), 0, 255).astype(np.uint8)
    outline = Image.fromarray(outline_arr, "L")
    shadow_layer = Image.new("RGBA", overlay.size, (0, 0, 0, 135))
    overlay.alpha_composite(Image.composite(shadow_layer, Image.new("RGBA", overlay.size, (0, 0, 0, 0)), outline))


def draw_letter_with_colored_side(draw, position, letter, font, fill, edge_fill, edge_side):
    x, y = position
    thickness = max(3, font.size // 18)
    dx, dy = {
        "up": (0, -thickness),
        "down": (0, thickness),
        "left": (-thickness, 0),
        "right": (thickness, 0),
    }[edge_side]
    draw.text((x + dx, y + dy), letter, font=font, fill=edge_fill)
    draw.text((x, y), letter, font=font, fill=fill)


def add_center_title(image, title, square_ratio=0.62):
    if not title:
        return image

    base = image.convert("RGBA")
    width, height = base.size
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    text = title.upper()
    square_size = int(min(width, height) * square_ratio)
    square_left = (width - square_size) / 2
    square_top = (height - square_size) / 2
    padding = max(14, square_size // 22)
    inner_size = square_size - padding * 2

    fit = fit_text_to_square(text, inner_size)
    if fit is None:
        return image

    font, lines, line_gap, _, text_height = fit
    y = square_top + (square_size - text_height) / 2
    rng = np.random.default_rng()

    for line in lines:
        line_bbox = draw.textbbox((0, 0), line, font=font)
        line_width = line_bbox[2] - line_bbox[0]
        line_height = line_bbox[3] - line_bbox[1]
        x = square_left + (square_size - line_width) / 2 - line_bbox[0]
        baseline_y = y - line_bbox[1]

        draw_uniform_outline(overlay, (x, baseline_y), line, font, radius=max(2, font.size // 36))

        cursor = x
        for char in line:
            char_bbox = draw.textbbox((0, 0), char, font=font)
            char_width = char_bbox[2] - char_bbox[0]
            if char.strip():
                edge_color = music_edge_color(image, rng) + (230,)
                edge_side = ["up", "down", "left", "right"][int(rng.integers(0, 4))]
                draw_letter_with_colored_side(
                    draw,
                    (cursor, baseline_y),
                    char,
                    font,
                    (255, 255, 255, 248),
                    edge_color,
                    edge_side,
                )
            cursor += char_width

        y += line_height + line_gap

    return Image.alpha_composite(base, overlay).convert("RGB")


def make_cover(audio_path, output_path, size=1000, patterns=2, center_title=False, color_mode="bpm"):
    audio = read_audio(audio_path)
    spectrum, rms, bass, mids, highs, centroid = stft_features(audio)
    bpm = estimate_bpm(rms)
    bpm_curve = estimate_bpm_curve_from_bass(bass, size)
    drive_curve = None
    if color_mode == "drive":
        drive_curve = estimate_drive_curve(spectrum, rms, centroid, bpm_curve, size)
    rgb = render_random_cover(
        spectrum,
        rms,
        bass,
        mids,
        highs,
        size,
        patterns=patterns,
        bpm=bpm,
        bpm_curve=bpm_curve,
        color_mode=color_mode,
        drive_curve=drive_curve,
    )

    image = Image.fromarray(rgb, "RGB")
    image = ImageEnhance.Color(image).enhance(1.18)
    image = ImageEnhance.Contrast(image).enhance(1.08)
    if center_title:
        image = add_center_title(image, clean_stem(audio_path))

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    if drive_curve is not None:
        print(f"Cover saved: {output_path} (mode: drive, BPM: {bpm:.1f}, drive: {float(np.min(drive_curve)):.2f}-{float(np.max(drive_curve)):.2f})")
    else:
        print(f"Cover saved: {output_path} (mode: bpm, BPM: {bpm:.1f}, local BPM: {float(np.min(bpm_curve)):.1f}-{float(np.max(bpm_curve)):.1f})")
    return output_path


def embed_cover(mp3_path, image_path):
    mp3_path = Path(mp3_path)
    image_path = Path(image_path)
    if mp3_path.suffix.lower() != ".mp3":
        print(f"Skip embed, not an MP3: {mp3_path}")
        return

    temp_path = mp3_path.with_name(f"{mp3_path.stem}.cover_tmp.mp3")
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-i",
            str(mp3_path),
            "-i",
            str(image_path),
            "-map",
            "0:a:0",
            "-map",
            "1:v:0",
            "-c:a",
            "copy",
            "-c:v",
            "mjpeg",
            "-disposition:v:0",
            "attached_pic",
            "-map_metadata",
            "0",
            "-id3v2_version",
            "3",
            str(temp_path),
        ]
    )
    temp_path.replace(mp3_path)
    print(f"Embedded cover into: {mp3_path}")


def make_covers(source, output, size=1000, patterns=2, center_title=False, embed=False, color_mode="bpm"):
    source_path = Path(source).resolve()
    output_root = Path(output).resolve()
    files = audio_files(source_path)
    if not files:
        print(f"No supported audio files found in {source_path}")
        return

    for index, audio_path in enumerate(files, start=1):
        target = output_root / f"{clean_stem(audio_path)}_cover_{size}.png"
        print(f"[{index}/{len(files)}] Cover: {audio_path.name}")
        cover_path = make_cover(audio_path, target, size=size, patterns=patterns, center_title=center_title, color_mode=color_mode)
        if embed:
            embed_cover(audio_path, cover_path)


def main():
    parser = argparse.ArgumentParser(description="Normalize music and generate MP3 cover art.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    process = subparsers.add_parser("process", help="Normalize music and export MP3 files.")
    process.add_argument("--source", required=True)
    process.add_argument("--output", required=True)
    process.add_argument("--integrated-lufs", type=float, default=-14.0)
    process.add_argument("--true-peak", type=float, default=-1.5)
    process.add_argument("--lra", type=float, default=11.0)
    process.add_argument("--final-gain", type=float, default=1.30)

    covers = subparsers.add_parser("covers", help="Generate cover images for one song or a folder.")
    covers.add_argument("--source", required=True, help="Audio file or folder with audio files.")
    covers.add_argument("--output", required=True, help="Folder for generated PNG covers.")
    covers.add_argument("--size", type=int, default=1000)
    covers.add_argument("--patterns", type=int, choices=[1, 2], default=2)
    covers.add_argument("--center-title", action="store_true", help="Draw the file name in the center.")
    covers.add_argument("--embed-cover", action="store_true", help="Attach the generated image as MP3 cover art.")
    covers.add_argument("--color-mode", choices=["bpm", "drive"], default="bpm", help="bpm keeps original colors; drive colors local song drive from violet to red.")

    args = parser.parse_args()
    require_ffmpeg()

    if args.command == "process":
        normalize_music(args.source, args.output, args.integrated_lufs, args.true_peak, args.lra, args.final_gain)
    elif args.command == "covers":
        make_covers(args.source, args.output, args.size, args.patterns, args.center_title, args.embed_cover, color_mode=args.color_mode)


def run_from_code_settings():
    require_ffmpeg()
    if CODE_MODE == "process":
        normalize_music(
            CODE_SOURCE,
            CODE_OUTPUT,
            integrated_lufs=CODE_INTEGRATED_LUFS,
            true_peak=CODE_TRUE_PEAK,
            lra=CODE_LRA,
            final_gain=CODE_FINAL_GAIN,
        )
    elif CODE_MODE == "covers":
        make_covers(
            CODE_SOURCE,
            CODE_OUTPUT,
            size=CODE_SIZE,
            patterns=CODE_PATTERNS,
            center_title=CODE_CENTER_TITLE,
            embed=CODE_EMBED_COVER,
            color_mode=CODE_COLOR_MODE,
        )
    else:
        raise ValueError('CODE_MODE must be "covers" or "process".')


if __name__ == "__main__":
    try:
        if RUN_FROM_CODE:
            run_from_code_settings()
        else:
            main()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
