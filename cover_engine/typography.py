from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageStat


FONT_CANDIDATES = (
    "C:/Windows/Fonts/seguisb.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/dejavusans-bold.ttf",
)

PLACEMENTS = ("top", "bottom", "left", "right", "center")
STYLE_SCALE = {
    "cinematic title": .064,
    "compact title": .058,
    "editorial title": .068,
    "expressive title": .064,
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
        placement = self._safe_placement(image, preferred)
        max_width = int(size * (.56 if placement in ("left", "right") else .68))
        max_height = int(size * (.21 if style == "editorial title" else .18))
        base_scale = STYLE_SCALE.get(style, .088)
        display_title = self._display_title(title.strip(), style, language)
        font, lines = self._fit(display_title, max_width, max_height, size, base_scale)
        draw_probe = ImageDraw.Draw(Image.new("L", (4, 4)))
        line_gap = max(4, int(font.size * .11))
        boxes = [draw_probe.textbbox((0, 0), line, font=font, stroke_width=1) for line in lines]
        title_height = sum(box[3] - box[1] for box in boxes) + line_gap * max(0, len(lines) - 1)
        artist_text = artist.strip().upper() if show_artist and artist.strip() else ""
        artist_font = self._fit_single_line(
            artist_text, max_width, max(12, int(font.size * .29)), max(10, int(size * .018))
        )
        artist_height = int(artist_font.size * 1.55) if artist_text else 0
        block_height = title_height + artist_height
        x, y, anchor = self._origin(placement, size, max_width, block_height)
        block_box = self._block_box(x, y, max_width, block_height, anchor, size)
        fill, stroke, veil = self._colors(image, block_box)

        overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        if veil:
            draw.rectangle(block_box, fill=veil)
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
                stroke_width=max(1, size // 500),
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
        }
        return Image.alpha_composite(canvas, overlay).convert("RGB")

    @staticmethod
    def _display_title(title, style, language):
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
    def _colors(image, block_box):
        crop = image.crop(tuple(int(value) for value in block_box)).convert("RGB")
        gray = crop.convert("L")
        stat = ImageStat.Stat(gray)
        mean = stat.mean[0]
        variation = stat.stddev[0]
        if mean < 132:
            fill = (250, 250, 248, 255)
            stroke = (8, 10, 14, 210)
            veil = (5, 7, 12, 66) if variation > 46 else None
        else:
            fill = (15, 17, 22, 255)
            stroke = (255, 255, 255, 210)
            veil = (255, 255, 255, 62) if variation > 46 else None
        return fill, stroke, veil

    def _fit(self, text, max_width, max_height, canvas_size, base_scale):
        words = text.replace("_", " ").split()
        minimum = int(canvas_size * .018)
        maximum = int(canvas_size * base_scale)
        for font_size in range(maximum, minimum - 1, -2):
            font = self._font(font_size)
            lines = self._wrap(words, font, max_width)
            draw = ImageDraw.Draw(Image.new("L", (4, 4)))
            boxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
            height = sum(box[3] - box[1] for box in boxes) + max(0, len(lines)-1) * int(font_size*.11)
            if len(lines) <= 4 and height <= max_height:
                return font, lines
        font = self._font(minimum)
        return font, self._wrap(words, font, max_width)

    def _fit_single_line(self, text, max_width, maximum, minimum):
        draw = ImageDraw.Draw(Image.new("L", (4, 4)))
        for size in range(maximum, minimum - 1, -1):
            font = self._font(size)
            if draw.textlength(text, font=font) <= max_width:
                return font
        return self._font(minimum)

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
    def _font(size):
        for candidate in FONT_CANDIDATES:
            if Path(candidate).exists():
                return ImageFont.truetype(candidate, size)
        return ImageFont.load_default()
