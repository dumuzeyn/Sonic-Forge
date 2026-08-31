import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageStat


FONT_CANDIDATES = (
    "C:/Windows/Fonts/seguisb.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/dejavusans-bold.ttf",
)
ARTISTIC_FONT_CANDIDATES = (
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/ariblk.ttf",
)
SERIF_FONT_CANDIDATES = (
    "C:/Windows/Fonts/georgiab.ttf",
    "C:/Windows/Fonts/timesbd.ttf",
)

PLACEMENTS = ("top", "bottom", "left", "right", "center")
STYLE_SCALE = {
    "cinematic title": .064,
    "compact title": .058,
    "editorial title": .068,
    "expressive title": .064,
    "artistic title": .150,
    "minimal clean": .060,
    "cinematic": .078,
    "dark dramatic": .080,
    "dreamy": .066,
    "electronic neon": .069,
    "indie editorial": .067,
    "elegant serif": .070,
    "bold modern": .078,
}
STYLE_TRACKING = {
    "minimal clean": .105,
    "cinematic": .045,
    "dark dramatic": .012,
    "dreamy": .080,
    "electronic neon": .070,
    "indie editorial": .035,
    "elegant serif": .025,
    "bold modern": .010,
    "artistic title": .018,
}


class TypographyEngine:
    def __init__(self):
        self.last_layout = {}

    def compose(
        self, image, title, artist="", profile=None, enabled=True, show_artist=True,
        language="unknown", song_profile=None, title_treatment=None,
    ):
        self.last_layout = {}
        if not enabled or not title.strip():
            return image
        canvas = image.convert("RGBA")
        size = canvas.width
        style = self._contextual_style(image, profile, song_profile)
        preferred = getattr(profile, "text_position", "bottom")
        treatment_lines = tuple(getattr(title_treatment, "display_lines", ()) or ())
        layout_strategy = self._layout_strategy(profile, style, preferred, treatment_lines)
        placement = self._placement_for_strategy(
            image, preferred, style, layout_strategy
        )
        max_width = int(size * (.82 if style == "artistic title" else (.56 if placement in ("left", "right") else .68)))
        max_height = int(size * (.52 if style == "artistic title" else (.21 if style == "editorial title" else .18)))
        base_scale = STYLE_SCALE.get(style, .088)
        display_title = self._display_title(title.strip(), style, language)
        font_candidates = self._font_candidates(style)
        tracking_ratio = STYLE_TRACKING.get(style, .025)
        font, lines = self._fit(
            display_title, max_width, max_height, size, base_scale,
            font_candidates=font_candidates,
            preferred_lines=treatment_lines,
            tracking_ratio=tracking_ratio,
        )
        tracking = max(.5, round(font.size * tracking_ratio, 2)) if tracking_ratio > 0 else 0
        draw_probe = ImageDraw.Draw(Image.new("L", (4, 4)))
        line_gap = max(4, int(font.size * (.16 if style in {"dreamy", "elegant serif"} else .11)))
        boxes = [draw_probe.textbbox((0, 0), line, font=font, stroke_width=1) for line in lines]
        title_height = sum(box[3] - box[1] for box in boxes) + line_gap * max(0, len(lines) - 1)
        artist_text = self._artist_display(artist, style) if show_artist and artist.strip() else ""
        artist_tracking = max(1, int(font.size * .055)) if artist_text else 0
        artist_font = self._fit_single_line(
            artist_text,
            max_width,
            max(12, int(font.size * .29)),
            max(10, int(size * .018)),
            font_candidates=font_candidates,
            tracking=artist_tracking,
        )
        artist_height = int(artist_font.size * 1.55) if artist_text else 0
        block_height = title_height + artist_height
        x, y, anchor = self._origin(placement, size, max_width, block_height)
        block_box = self._block_box(x, y, max_width, block_height, anchor, size)
        fill, stroke, veil = self._colors(image, block_box, force_light=style == "artistic title")
        accent_styles = {
            "artistic title", "cinematic", "dark dramatic", "dreamy",
            "electronic neon", "indie editorial", "elegant serif", "bold modern",
        }
        artistic_accent = self._artistic_accent(image, block_box) if style in accent_styles else None
        if artistic_accent:
            tint = .18 if style == "artistic title" else .10
            fill = tuple(round(fill[index] * (1 - tint) + artistic_accent[index] * tint) for index in range(3)) + (255,)
            stroke = tuple(round(stroke[index] * .76 + artistic_accent[index] * .24) for index in range(3)) + (185,)
            if veil:
                veil = tuple(round(veil[index] * .78 + artistic_accent[index] * .22) for index in range(3)) + (veil[3],)

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
                line_width = self._text_length(line, font, tracking)
                line_height = box[3] - box[1]
                line_x = self._line_x(x, line_width, anchor, size)
                self._draw_tracked(
                    accent_draw,
                    (line_x, accent_y - box[1]),
                    line,
                    font=font,
                    fill=180,
                    stroke_width=max(1, size // 360),
                    stroke_fill=130,
                    tracking=tracking,
                )
                accent_y += line_height + line_gap
            if artist_text:
                artist_width = self._text_length(artist_text, artist_font, artist_tracking)
                artist_x = self._line_x(x, artist_width, anchor, size)
                self._draw_tracked(
                    accent_draw,
                    (artist_x, accent_y + artist_font.size * .25),
                    artist_text,
                    font=artist_font,
                    fill=125,
                    tracking=artist_tracking,
                )
            accent_mask = accent_mask.filter(ImageFilter.GaussianBlur(max(2, int(size * .009))))
            accent_layer = Image.new("RGBA", canvas.size, (*artistic_accent, 0))
            accent_layer.putalpha(accent_mask)
            overlay = Image.alpha_composite(overlay, accent_layer)
            draw = ImageDraw.Draw(overlay)
            self._draw_style_accent(
                draw, style, block_box, y, title_height, artistic_accent, size, anchor
            )
        cursor_y = y
        heavy_styles = {"cinematic", "dark dramatic", "electronic neon", "bold modern"}
        emphasis_words = tuple(getattr(title_treatment, "emphasis_words", ()) or ())
        emphasis_fill = None
        if artistic_accent and emphasis_words:
            emphasis_fill = tuple(
                round(fill[index] * .72 + artistic_accent[index] * .28) for index in range(3)
            ) + (255,)
        for line, box in zip(lines, boxes):
            line_width = self._text_length(line, font, tracking)
            line_height = box[3] - box[1]
            line_x = self._line_x(x, line_width, anchor, size)
            self._draw_tracked(
                draw,
                (line_x, cursor_y - box[1]),
                line,
                font=font,
                fill=fill,
                stroke_width=max(2 if style in heavy_styles else 1, size // (430 if style == "artistic title" else 500)),
                stroke_fill=stroke,
                tracking=tracking,
                emphasis_words=emphasis_words,
                emphasis_fill=emphasis_fill,
            )
            cursor_y += line_height + line_gap
        if artist_text:
            artist_width = self._text_length(artist_text, artist_font, artist_tracking)
            artist_x = self._line_x(x, artist_width, anchor, size)
            self._draw_tracked(
                draw,
                (artist_x, cursor_y + artist_font.size * .25),
                artist_text,
                font=artist_font,
                fill=(*fill[:3], 225),
                stroke_width=max(1, size // 700),
                stroke_fill=stroke,
                tracking=artist_tracking,
            )
        self.last_layout = {
            "placement": placement,
            "preferred_placement": preferred,
            "style": style,
            "layout_strategy": layout_strategy,
            "language": language,
            "font_size": font.size,
            "letter_spacing": tracking,
            "line_count": len(lines),
            "safe_area": tuple(round(value, 1) for value in block_box),
            "adaptive_veil": bool(veil),
            "background_accent": artistic_accent,
            "song_typography_hint": getattr(song_profile, "typography_mood_hint", ""),
            "title_confidence": getattr(title_treatment, "confidence", None),
            "emphasis_words": emphasis_words,
        }
        return Image.alpha_composite(canvas, overlay).convert("RGB")

    @staticmethod
    def _display_title(title, style, language):
        if language == "mixed":
            return title.replace(" x ", " × ").replace(" X ", " × ")
        return title.replace("_", " ")

    @staticmethod
    def _artist_display(artist, style):
        value = artist.strip()
        if style in {"electronic neon", "bold modern", "dark dramatic"}:
            return value.upper()
        return value

    @staticmethod
    def _contextual_style(image, concept, song_profile):
        requested = getattr(concept, "typography_style", "compact title")
        if getattr(concept, "typography_locked", False):
            return requested
        family = getattr(concept, "candidate_type", "")
        narrative = getattr(song_profile, "narrative_mode", "")
        mood = getattr(song_profile, "mood", "")
        rgb = image.convert("RGB")
        hsv = ImageStat.Stat(rgb.convert("HSV"))
        brightness = ImageStat.Stat(rgb.convert("L")).mean[0]
        saturation = hsv.mean[1]
        if family == "minimal":
            return "minimal clean"
        if narrative == "rhythmic_mechanical" or (saturation > 92 and getattr(song_profile, "energy", 0) > .66):
            return "electronic neon"
        if narrative in {"aggressive", "epic"} or (brightness < 82 and getattr(song_profile, "drama", 0) > .68):
            return "dark dramatic"
        if narrative in {"dreamlike", "luminous"}:
            return "dreamy" if family in {"surreal", "abstract"} else "minimal clean"
        if narrative == "intimate" or mood in {"romantic", "melancholic"}:
            return "elegant serif" if family in {"portrait", "symbolic", "cinematic"} else "indie editorial"
        if family == "editorial":
            return "indie editorial"
        if family == "portrait":
            return "elegant serif"
        if family == "symbolic" and getattr(song_profile, "energy", 0) > .62:
            return "bold modern"
        return requested

    @staticmethod
    def _layout_strategy(concept, style, preferred, treatment_lines):
        composition = getattr(concept, "composition", "")
        if style == "artistic title":
            return "centered"
        if style == "minimal clean" and len(treatment_lines) <= 1:
            return "minimal_caption"
        if len(treatment_lines) > 1:
            return "split_lines"
        if preferred in {"left", "right"} or composition in {"editorial_poster", "asymmetrical_scene", "strong_negative_space"}:
            return "corner_anchored"
        if composition in {"surreal_artwork", "double_exposure"} and style == "dreamy":
            return "centered"
        return preferred if preferred in {"top", "bottom"} else "bottom"

    def _placement_for_strategy(self, image, preferred, style, strategy):
        if style == "artistic title" or strategy == "centered":
            return "center"
        if strategy == "minimal_caption":
            return self._safe_placement(image, "bottom", allowed=("bottom", "left", "right"))
        if strategy == "corner_anchored":
            corner = preferred if preferred in {"left", "right"} else "left"
            return self._safe_placement(image, corner, allowed=("left", "right"))
        return self._safe_placement(image, preferred)

    @staticmethod
    def _font_candidates(style):
        if style == "artistic title":
            return ARTISTIC_FONT_CANDIDATES
        if style == "elegant serif":
            return SERIF_FONT_CANDIDATES + FONT_CANDIDATES
        if style in {"cinematic", "bold modern", "dark dramatic", "electronic neon"}:
            return ARTISTIC_FONT_CANDIDATES
        return FONT_CANDIDATES

    @staticmethod
    def _draw_style_accent(draw, style, block_box, y, title_height, accent, size, anchor):
        left, _top, right, _bottom = block_box
        color = (*accent, 205)
        shadow = (8, 10, 14, 135)
        rule_y = int(y + title_height + size * .014)
        if style in {"cinematic", "elegant serif", "dreamy"}:
            width = min((right - left) * .44, size * .28)
            center = (left + right) / 2
            line = (int(center - width / 2), rule_y, int(center + width / 2), rule_y)
            draw.line((line[0], line[1] + 2, line[2], line[3] + 2), fill=shadow, width=max(2, size // 260))
            draw.line(line, fill=color, width=max(2, size // 300))
        elif style == "indie editorial":
            bar_x = int(right - size * .018) if anchor == "ra" else int(left + size * .018)
            draw.line(
                (bar_x, int(y), bar_x, int(y + title_height)),
                fill=color,
                width=max(3, size // 135),
            )
        elif style in {"bold modern", "dark dramatic"}:
            bar_height = max(3, size // 110)
            draw.rectangle(
                (int(left + size * .02), rule_y, int(right - size * .02), rule_y + bar_height),
                fill=(*accent, 150),
            )

    def _safe_placement(self, image, preferred, allowed=None):
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
        return max(allowed or PLACEMENTS, key=lambda value: scores[value])

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

    def _fit(
        self, text, max_width, max_height, canvas_size, base_scale,
        font_candidates=None, preferred_lines=(), tracking_ratio=0.0,
    ):
        words = text.replace("_", " ").split()
        minimum = int(canvas_size * .018)
        maximum = int(canvas_size * base_scale)
        for font_size in range(maximum, minimum - 1, -2):
            font = self._font(font_size, font_candidates)
            tracking = max(.5, round(font_size * tracking_ratio, 2)) if tracking_ratio > 0 else 0
            if preferred_lines:
                lines = []
                for preferred in preferred_lines:
                    lines.extend(self._wrap(preferred.split(), font, max_width, tracking))
            else:
                lines = self._wrap(words, font, max_width, tracking)
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
        tracking = max(.5, round(minimum * tracking_ratio, 2)) if tracking_ratio > 0 else 0
        return font, self._wrap(words, font, max_width, tracking)

    def _fit_single_line(self, text, max_width, maximum, minimum, font_candidates=None, tracking=0):
        for size in range(maximum, minimum - 1, -1):
            font = self._font(size, font_candidates)
            if self._text_length(text, font, tracking) <= max_width:
                return font
        return self._font(minimum, font_candidates)

    def _wrap(self, words, font, max_width, tracking=0):
        expanded = []
        for word in words or [""]:
            if self._text_length(word, font, tracking) <= max_width:
                expanded.append(word)
                continue
            expanded.extend(self._split_word(word, font, max_width, tracking))
        lines = []
        current = ""
        for word in expanded:
            candidate = f"{current} {word}".strip()
            if current and self._text_length(candidate, font, tracking) > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        return lines

    def _split_word(self, word, font, max_width, tracking=0):
        pieces = []
        current = ""
        for character in word:
            candidate = current + character
            if current and self._text_length(candidate, font, tracking) > max_width:
                pieces.append(current)
                current = character
            else:
                current = candidate
        if current:
            pieces.append(current)
        return pieces

    @staticmethod
    def _text_length(text, font, tracking=0):
        draw = ImageDraw.Draw(Image.new("L", (4, 4)))
        return sum(float(draw.textlength(character, font=font)) for character in text) + max(0, len(text) - 1) * tracking

    @classmethod
    def _draw_tracked(
        cls, draw, position, text, font, fill, tracking=0, stroke_width=0,
        stroke_fill=None, emphasis_words=(), emphasis_fill=None,
    ):
        x, y = position
        emphasis = {str(word).lower().strip(".,:;!?()[]") for word in emphasis_words}
        for token in re_split_words(text):
            token_key = token.lower().strip(".,:;!?()[]")
            token_fill = emphasis_fill if token_key in emphasis and emphasis_fill else fill
            for character in token:
                draw.text(
                    (x, y), character, font=font, fill=token_fill,
                    stroke_width=stroke_width, stroke_fill=stroke_fill,
                )
                x += cls._text_length(character, font) + tracking

    @staticmethod
    def _font(size, candidates=None):
        for candidate in candidates or FONT_CANDIDATES:
            if Path(candidate).exists():
                return ImageFont.truetype(candidate, size)
        return ImageFont.load_default()


def re_split_words(text):
    return re.findall(r"\s+|[^\s]+", text)
