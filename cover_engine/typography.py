from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageStat


FONT_CANDIDATES = (
    "C:/Windows/Fonts/seguisb.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/dejavusans-bold.ttf",
)
ARTISTIC_FONT_CANDIDATES = (
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/ariblk.ttf",
)

PLACEMENTS = ("top", "bottom", "left", "right", "center")
STYLE_SCALE = {
    "cinematic title": .064,
    "compact title": .058,
    "editorial title": .068,
    "expressive title": .064,
    "artistic title": .145,
}


class TypographyEngine:
    def __init__(self):
        self.last_layout = {}

    def compose(self, image, title, artist="", profile=None, enabled=True, show_artist=True, language="unknown"):
        self.last_layout = {}
        if not enabled or not title.strip():
            return image
        canvas = image.convert("RGBA")
        size = canvas.width
        style = getattr(profile, "typography_style", "compact title")
        preferred = getattr(profile, "text_position", "bottom")
        placement = "center" if style == "artistic title" else self._safe_placement(image, preferred)
        max_width = int(size * (.78 if style == "artistic title" else (.56 if placement in ("left", "right") else .68)))
        max_height = int(size * (.52 if style == "artistic title" else (.21 if style == "editorial title" else .18)))
        base_scale = STYLE_SCALE.get(style, .088)
        display_title = self._display_title(title.strip(), style, language)
        font_candidates = ARTISTIC_FONT_CANDIDATES if style == "artistic title" else FONT_CANDIDATES
        font, lines = self._fit(
            display_title, max_width, max_height, size, base_scale, font_candidates=font_candidates
        )
        draw_probe = ImageDraw.Draw(Image.new("L", (4, 4)))
        line_gap = max(4, int(font.size * .11))
        boxes = [draw_probe.textbbox((0, 0), line, font=font, stroke_width=1) for line in lines]
        title_height = sum(box[3] - box[1] for box in boxes) + line_gap * max(0, len(lines) - 1)
        artist_text = artist.strip().upper() if show_artist and artist.strip() else ""
        artist_font = self._fit_single_line(
            artist_text,
            max_width,
            max(12, int(font.size * .29)),
            max(10, int(size * .018)),
            font_candidates=font_candidates,
        )
        artist_height = int(artist_font.size * 1.55) if artist_text else 0
        block_height = title_height + artist_height
        x, y, anchor = self._origin(placement, size, max_width, block_height)
        block_box = self._block_box(x, y, max_width, block_height, anchor, size)
        fill, stroke, veil = self._colors(image, block_box, force_light=style == "artistic title")
        artistic_accent = self._artistic_accent(image, block_box) if style == "artistic title" else None
        if artistic_accent:
            fill = tuple(round(fill[index] * .90 + artistic_accent[index] * .10) for index in range(3)) + (255,)

        overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        if veil:
            veil_mask = Image.new("L", canvas.size, 0)
            mask_draw = ImageDraw.Draw(veil_mask)
            mask_draw.rounded_rectangle(block_box, radius=int(size * .035), fill=veil[3])
            veil_mask = veil_mask.filter(ImageFilter.GaussianBlur(max(3, int(size * .028))))
            veil_layer = Image.new("RGBA", canvas.size, (*veil[:3], 0))
            veil_layer.putalpha(veil_mask)
            overlay = Image.alpha_composite(overlay, veil_layer)
            draw = ImageDraw.Draw(overlay)
        if artistic_accent:
            accent_mask = Image.new("L", canvas.size, 0)
            accent_draw = ImageDraw.Draw(accent_mask)
            accent_y = y
            for line, box in zip(lines, boxes):
                line_width = box[2] - box[0]
                line_height = box[3] - box[1]
                line_x = self._line_x(x, line_width, anchor, size)
                accent_draw.text(
                    (line_x, accent_y - box[1]),
                    line,
                    font=font,
                    fill=150,
                    stroke_width=max(1, size // 360),
                    stroke_fill=105,
                )
                accent_y += line_height + line_gap
            if artist_text:
                artist_width = draw_probe.textlength(artist_text, font=artist_font)
                artist_x = self._line_x(x, artist_width, anchor, size)
                accent_draw.text(
                    (artist_x, accent_y + artist_font.size * .25), artist_text, font=artist_font, fill=125
                )
            accent_mask = accent_mask.filter(ImageFilter.GaussianBlur(max(2, int(size * .007))))
            accent_layer = Image.new("RGBA", canvas.size, (*artistic_accent, 0))
            accent_layer.putalpha(accent_mask)
            overlay = Image.alpha_composite(overlay, accent_layer)
            draw = ImageDraw.Draw(overlay)
        cursor_y = y
        for line, box in zip(lines, boxes):
            line_width = box[2] - box[0]
            line_height = box[3] - box[1]
            line_x = self._line_x(x, line_width, anchor, size)
            draw.text(
                (line_x, cursor_y - box[1]),
                line,
                font=font,
                fill=fill,
                stroke_width=max(1, size // (430 if style == "artistic title" else 500)),
                stroke_fill=stroke,
            )
            cursor_y += line_height + line_gap
        if artist_text:
            artist_width = draw_probe.textlength(artist_text, font=artist_font)
            artist_x = self._line_x(x, artist_width, anchor, size)
            draw.text(
                (artist_x, cursor_y + artist_font.size * .25),
                artist_text,
                font=artist_font,
                fill=(*fill[:3], 225),
                stroke_width=max(1, size // 700),
                stroke_fill=stroke,
            )
        self.last_layout = {
            "placement": placement,
            "preferred_placement": preferred,
            "style": style,
            "language": language,
            "font_size": font.size,
            "line_count": len(lines),
            "safe_area": tuple(round(value, 1) for value in block_box),
            "adaptive_veil": bool(veil),
            "background_accent": artistic_accent,
        }
        return Image.alpha_composite(canvas, overlay).convert("RGB")

    @staticmethod
    def _display_title(title, style, language):
        if style == "artistic title":
            return title.replace("_", " ").upper()
        if style == "editorial title" and len(title) <= 34:
            return title.upper()
        if language == "mixed":
            return title.replace(" x ", " × ").replace(" X ", " × ")
        return title

    def _safe_placement(self, image, preferred):
        gray = image.convert("L")
        edge = gray.filter(ImageFilter.FIND_EDGES)
        size = image.width
        regions = {
            "top": (int(size*.06), int(size*.05), int(size*.94), int(size*.36)),
            "bottom": (int(size*.06), int(size*.64), int(size*.94), int(size*.95)),
            "left": (int(size*.05), int(size*.10), int(size*.70), int(size*.62)),
            "right": (int(size*.30), int(size*.10), int(size*.95), int(size*.62)),
            "center": (int(size*.12), int(size*.34), int(size*.88), int(size*.66)),
        }
        scores = {}
        for placement, box in regions.items():
            local_gray = gray.crop(box)
            local_edge = edge.crop(box)
            variation = ImageStat.Stat(local_gray).stddev[0]
            edge_level = ImageStat.Stat(local_edge).mean[0]
            score = 100 - variation * .72 - edge_level * 1.15
            if placement == preferred:
                score += 8
            if placement == "center":
                score -= 9
            scores[placement] = score
        return max(PLACEMENTS, key=lambda value: scores[value])

    @staticmethod
    def _origin(placement, size, width, height):
        if placement == "left":
            return size * .07, size * .12, "la"
        if placement == "right":
            return size * .93, size * .12, "ra"
        if placement == "top":
            return size * .50, size * .065, "ma"
        if placement == "bottom":
            return size * .50, size - height - size * .075, "ma"
        return size * .50, size * .50 - height * .50, "ma"

    @staticmethod
    def _line_x(x, line_width, anchor, size):
        if anchor == "ma":
            return (size - line_width) / 2
        if anchor == "ra":
            return x - line_width
        return x

    @staticmethod
    def _block_box(x, y, width, height, anchor, size):
        padding_x = size * .025
        padding_y = size * .018
        if anchor == "ma":
            left, right = x - width / 2 - padding_x, x + width / 2 + padding_x
        elif anchor == "ra":
            left, right = x - width - padding_x, x + padding_x
        else:
            left, right = x - padding_x, x + width + padding_x
        return (
            max(0, left),
            max(0, y - padding_y),
            min(size, right),
            min(size, y + height + padding_y),
        )

    @staticmethod
    def _colors(image, block_box, force_light=False):
        crop = image.crop(tuple(int(value) for value in block_box)).convert("RGB")
        gray = crop.convert("L")
        stat = ImageStat.Stat(gray)
        mean = stat.mean[0]
        variation = stat.stddev[0]
        if force_light:
            fill = (250, 250, 248, 255)
            stroke = (5, 7, 11, 145)
            veil_alpha = int(max(34, min(82, 35 + (mean - 70) * .28 + variation * .30)))
            veil = (5, 7, 12, veil_alpha)
        elif mean < 132:
            fill = (250, 250, 248, 255)
            stroke = (8, 10, 14, 210)
            veil = (5, 7, 12, 66) if variation > 46 else None
        else:
            fill = (15, 17, 22, 255)
            stroke = (255, 255, 255, 210)
            veil = (255, 255, 255, 62) if variation > 46 else None
        return fill, stroke, veil

    @staticmethod
    def _artistic_accent(image, block_box):
        crop = image.crop(tuple(int(value) for value in block_box)).convert("RGB").resize((48, 48))
        colors = crop.quantize(colors=10, method=Image.Quantize.MEDIANCUT).convert("RGB").getcolors(48 * 48)
        if not colors:
            return None

        def score(item):
            count, (red, green, blue) = item
            high, low = max(red, green, blue), min(red, green, blue)
            saturation = high - low
            brightness = (red + green + blue) / 3
            usable_light = 1.0 - min(abs(brightness - 145) / 180, .75)
            return saturation * usable_light * (1.0 + count / (48 * 48))

        return max(colors, key=score)[1]

    def _fit(self, text, max_width, max_height, canvas_size, base_scale, font_candidates=None):
        words = text.replace("_", " ").split()
        minimum = int(canvas_size * .018)
        maximum = int(canvas_size * base_scale)
        for font_size in range(maximum, minimum - 1, -2):
            font = self._font(font_size, font_candidates)
            lines = self._wrap(words, font, max_width)
            draw = ImageDraw.Draw(Image.new("L", (4, 4)))
            boxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
            height = sum(box[3] - box[1] for box in boxes) + max(0, len(lines)-1) * int(font_size*.11)
            orphan_fragment = any(
                len(line.strip()) <= 2 and line.strip() not in {"×", "X", "&"}
                for line in lines
            )
            if len(lines) <= 4 and height <= max_height and not orphan_fragment:
                return font, lines
        font = self._font(minimum, font_candidates)
        return font, self._wrap(words, font, max_width)

    def _fit_single_line(self, text, max_width, maximum, minimum, font_candidates=None):
        draw = ImageDraw.Draw(Image.new("L", (4, 4)))
        for size in range(maximum, minimum - 1, -1):
            font = self._font(size, font_candidates)
            if draw.textlength(text, font=font) <= max_width:
                return font
        return self._font(minimum, font_candidates)

    def _wrap(self, words, font, max_width):
        draw = ImageDraw.Draw(Image.new("L", (4, 4)))
        expanded = []
        for word in words or [""]:
            if draw.textlength(word, font=font) <= max_width:
                expanded.append(word)
                continue
            expanded.extend(self._split_word(word, font, max_width, draw))
        lines = []
        current = ""
        for word in expanded:
            candidate = f"{current} {word}".strip()
            if current and draw.textlength(candidate, font=font) > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        return lines

    @staticmethod
    def _split_word(word, font, max_width, draw):
        pieces = []
        current = ""
        for character in word:
            candidate = current + character
            if current and draw.textlength(candidate, font=font) > max_width:
                pieces.append(current)
                current = character
            else:
                current = candidate
        if current:
            pieces.append(current)
        return pieces

    @staticmethod
    def _font(size, candidates=None):
        for candidate in candidates or FONT_CANDIDATES:
            if Path(candidate).exists():
                return ImageFont.truetype(candidate, size)
        return ImageFont.load_default()
