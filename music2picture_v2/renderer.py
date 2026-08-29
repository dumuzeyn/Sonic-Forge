from __future__ import annotations

import hashlib
import math

import numpy as np
from PIL import Image, ImageColor, ImageDraw, ImageFilter

from .models import VisualDNA, VisualPlan


def render_cover(visual_dna: VisualDNA, visual_plan: VisualPlan, size: int = 1000, seed: int | None = None) -> Image.Image:
    """Render the single adaptive Music2Picture v2 visual system."""
    work_size = max(192, min(int(size), 900))
    rng = np.random.default_rng(deterministic_seed(visual_dna.fingerprint, seed))
    image = Image.fromarray(_background(visual_plan, work_size, rng), "RGB")
    image = _add_flow_layers(image, visual_dna, visual_plan, rng)
    image = _add_structural_trace(image, visual_dna, visual_plan)
    image = _add_fragmentation(image, visual_plan, rng)
    image = _add_focal_mass(image, visual_dna, visual_plan)
    image = _finish(image, visual_dna, visual_plan, rng)
    if image.size != (size, size):
        image = image.resize((size, size), Image.Resampling.LANCZOS)
    return image.convert("RGB")


def deterministic_seed(fingerprint: str, seed: int | None = None) -> int:
    if seed is not None:
        return int(seed) & 0x7FFFFFFF
    digest = hashlib.sha256(str(fingerprint).encode("ascii", errors="ignore")).digest()
    return int.from_bytes(digest[:8], "little") & 0x7FFFFFFF


def _background(plan: VisualPlan, size: int, rng: np.random.Generator) -> np.ndarray:
    colors = np.asarray([ImageColor.getrgb(value) for value in plan.palette], dtype=np.float32)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    x = xx / max(1, size - 1)
    y = yy / max(1, size - 1)
    fx, fy = plan.focal_position
    distance = np.sqrt((x - fx) ** 2 + (y - fy) ** 2)
    directional = x * (0.25 + plan.directionality * 0.55) + y * (0.75 - plan.directionality * 0.55)
    radial = np.clip(1.0 - distance * (1.0 + plan.visual_weight), 0.0, 1.0)
    broad = np.clip(directional * 0.55 + radial * 0.45, 0.0, 1.0)
    field = colors[0] * (1.0 - broad[..., None]) + colors[1] * broad[..., None]
    light = np.clip((radial - 0.25) * 1.5, 0.0, 1.0)[..., None]
    field = field * (1.0 - light * 0.42) + colors[2] * light * 0.42
    noise = rng.normal(0.0, 1.0, (max(8, size // 18), max(8, size // 18))).astype(np.float32)
    noise_image = Image.fromarray(np.uint8(np.clip(noise * 35 + 128, 0, 255)), "L")
    noise_image = noise_image.resize((size, size), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(max(1, size // 55)))
    texture = (np.asarray(noise_image, dtype=np.float32) - 128.0) / 128.0
    strength = 7.0 + plan.background_complexity * 18.0 + plan.texture_roughness * 10.0
    return np.uint8(np.clip(field + texture[..., None] * strength, 0, 255))


def _add_flow_layers(image, dna, plan, rng):
    size = image.width
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    palette = [ImageColor.getrgb(color) for color in plan.palette]
    count = int(4 + plan.density * 17 + plan.repetition * 8)
    amplitude = size * (0.035 + plan.flow * 0.13 + dna.spectral_flux * 0.06)
    width = max(2, int(size * (0.006 + plan.visual_weight * 0.014)))
    for index in range(count):
        phase = rng.uniform(0, math.tau)
        frequency = 0.7 + plan.repetition * 2.8 + rng.uniform(-0.25, 0.45)
        baseline = size * ((index + 1) / (count + 1))
        drift = (plan.directionality - 0.5) * size * 0.24
        points = []
        for step in range(65):
            x = size * step / 64.0
            section = dna.energy_curve[min(len(dna.energy_curve) - 1, step)] if dna.energy_curve else 0.5
            wave = math.sin(step / 64.0 * math.tau * frequency + phase)
            secondary = math.sin(step / 64.0 * math.tau * (frequency * 0.47 + 0.2) - phase) * 0.38
            y = baseline + (wave + secondary) * amplitude * (0.45 + section * 0.75) + drift * (step / 64.0 - 0.5)
            points.append((x, y))
        color = palette[(index + int(plan.primary_hue // 60)) % len(palette)]
        alpha = min(205, int(28 + 105 * plan.flow + 60 * dna.rhythmic_regularity))
        draw.line(points, fill=(*color, alpha), width=width + index % 3, joint="curve")
    blur = max(0.4, size * (0.002 + (1.0 - plan.edge_sharpness) * 0.006))
    angle = (plan.directionality - 0.5) * 105.0 + (dna.climax_position - 0.5) * 30.0
    overlay = overlay.filter(ImageFilter.GaussianBlur(blur)).rotate(angle, resample=Image.Resampling.BICUBIC)
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def _add_structural_trace(image, dna, plan):
    if not dna.energy_curve:
        return image
    size = image.width
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    curve = np.asarray(dna.energy_curve, dtype=np.float32)
    baseline = size * (0.58 - (dna.climax_position - 0.5) * 0.15)
    scale_y = size * (0.12 + plan.directionality * 0.08)
    points = [(size * i / max(1, len(curve) - 1), baseline - (float(v) - 0.5) * scale_y) for i, v in enumerate(curve)]
    accent = ImageColor.getrgb(plan.palette[3])
    width = max(2, int(size * (0.004 + dna.attack_strength * 0.008)))
    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).line(points, fill=(*accent, 105), width=width * 5, joint="curve")
    glow = glow.filter(ImageFilter.GaussianBlur(width * 2.4))
    draw.line(points, fill=(*accent, 120 + int(dna.attack_strength * 110)), width=width, joint="curve")
    angle = (plan.directionality - 0.5) * 75.0
    glow = glow.rotate(angle, resample=Image.Resampling.BICUBIC)
    overlay = overlay.rotate(angle, resample=Image.Resampling.BICUBIC)
    return Image.alpha_composite(Image.alpha_composite(image.convert("RGBA"), glow), overlay).convert("RGB")


def _add_fragmentation(image, plan, rng):
    amount = plan.fragmentation * (0.45 + plan.dispersion * 0.55)
    if amount < 0.08:
        return image
    size = image.width
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    colors = [ImageColor.getrgb(value) for value in plan.palette[1:]]
    fx, fy = plan.focal_position[0] * size, plan.focal_position[1] * size
    for index in range(int(5 + amount * 34)):
        angle = rng.uniform(0, math.tau)
        radius = size * rng.uniform(0.08, 0.52) * (0.5 + plan.dispersion)
        cx, cy = fx + math.cos(angle) * radius, fy + math.sin(angle) * radius
        length = size * rng.uniform(0.018, 0.075) * (0.5 + plan.angularity)
        width = length * rng.uniform(0.18, 0.55)
        points = ((cx + math.cos(angle) * length, cy + math.sin(angle) * length), (cx + math.cos(angle + 2.2) * width, cy + math.sin(angle + 2.2) * width), (cx + math.cos(angle - 2.2) * width, cy + math.sin(angle - 2.2) * width))
        draw.polygon(points, fill=(*colors[index % len(colors)], int(20 + amount * 105)))
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def _add_focal_mass(image, dna, plan):
    size = image.width
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    fx, fy = (value * size for value in plan.focal_position)
    radius = size * (0.09 + plan.focal_size * 0.24)
    color = ImageColor.getrgb(plan.palette[2])
    rings = int(8 + plan.visual_weight * 12)
    for ring in range(rings, 0, -1):
        ratio = ring / rings
        rx = radius * ratio * (0.75 + plan.spatial_balance * 0.55)
        ry = radius * ratio * (1.20 - plan.spatial_balance * 0.30)
        alpha = int((1.0 - ratio) * 30 + 7 + dna.bass_mass * 18)
        draw.ellipse((fx - rx, fy - ry, fx + rx, fy + ry), fill=(*color, alpha))
    blur = size * (0.012 + (1.0 - plan.edge_sharpness) * 0.022)
    return Image.alpha_composite(image.convert("RGBA"), layer.filter(ImageFilter.GaussianBlur(blur))).convert("RGB")


def _finish(image, dna, plan, rng):
    size = image.width
    array = np.asarray(image, dtype=np.float32)
    grain = rng.normal(0.0, 1.0, array.shape[:2]).astype(np.float32)
    array = np.clip(array + grain[..., None] * (1.0 + plan.granularity * 6.5), 0, 255)
    contrast = 0.88 + plan.contrast * 0.35
    result = Image.fromarray(np.uint8(np.clip((array - 127.5) * contrast + 127.5, 0, 255)), "RGB")
    if plan.edge_sharpness > 0.48:
        detail = result.filter(ImageFilter.UnsharpMask(radius=max(1, size // 400), percent=int(30 + plan.edge_sharpness * 75), threshold=3))
        result = Image.blend(result, detail, 0.28 + dna.attack_strength * 0.22)
    return result
