import hashlib
from dataclasses import asdict, dataclass


COMPOSITIONS = (
    "cinematic_scene",
    "object_centered",
    "editorial_poster",
    "surreal_artwork",
    "environmental_portrait",
    "wide_landscape",
    "symbolic_minimal",
    "abstract_expressive",
    "double_exposure",
    "fragmented_collage",
    "central_emblem",
    "asymmetrical_scene",
    "strong_negative_space",
    "theatrical_still_life",
)

COMPOSITION_DIRECTIONS = {
    "cinematic_scene": "a complete cinematic scene where the metaphor object dominates the foreground, with middle distance and background only supporting the story",
    "object_centered": "one recognizable physical object as the visual thesis, filling a large part of the cover and grounded in a specific environment",
    "editorial_poster": "a bold editorial poster made from one photographed physical subject, asymmetrical hierarchy, and deliberate negative space",
    "surreal_artwork": "a believable location transformed around one large precise surreal object that expresses the emotional conflict",
    "environmental_portrait": "a character revealed through their surroundings and action; never a featureless centered silhouette",
    "wide_landscape": "a deep landscape with foreground evidence, middle-distance action, and a strong horizon",
    "symbolic_minimal": "one concrete symbol as the dominant cover subject and one supporting environmental clue; restrained but never a gradient or empty studio render",
    "abstract_expressive": "material, painterly expression derived from a concrete lyric image, retaining a recognizable focal object",
    "double_exposure": "a controlled double exposure joining the central object with the song's specific setting",
    "fragmented_collage": "an authored editorial collage of photographs, paper, and one repeated lyrical clue, with clear hierarchy",
    "central_emblem": "a large readable physical emblem built from song-specific materials, with the world visible only as context",
    "asymmetrical_scene": "the main subject placed off-center with active depth and intentional open space for the title",
    "strong_negative_space": "a small but unmistakable subject balanced by meaningful open environment, not empty darkness",
    "theatrical_still_life": "a cinematic still life where lyric-specific objects are large, close, tactile, and staged with depth and motivated light",
}

LOCAL_COMPOSITION_DIRECTIONS = {
    "cinematic_scene": "cinematic wide shot",
    "object_centered": "bold object-centered framing",
    "editorial_poster": "asymmetrical editorial poster",
    "surreal_artwork": "believable surreal scene",
    "environmental_portrait": "off-center environmental portrait",
    "wide_landscape": "deep wide landscape",
    "symbolic_minimal": "minimal symbolic still life",
    "abstract_expressive": "expressive material artwork with a recognizable object",
    "double_exposure": "controlled double exposure",
    "fragmented_collage": "layered photographic collage",
    "central_emblem": "large central physical emblem",
    "asymmetrical_scene": "off-center subject with open environment",
    "strong_negative_space": "small clear subject in meaningful open space",
    "theatrical_still_life": "theatrical still life in a real setting",
}

PALETTE_WORLDS = (
    ("midnight_red", ("midnight blue", "graphite", "cold white", "small signal-red accent")),
    ("sunset_amber", ("burnished amber", "sunset orange", "deep plum", "warm cream")),
    ("red_black", ("charcoal black", "crimson red", "burnt orange", "hard white")),
    ("pastel_air", ("dusty rose", "pale mint", "soft lilac", "warm ivory")),
    ("monochrome", ("ink black", "paper white", "silver gray", "one muted accent")),
    ("neon_night", ("electric violet", "cyan", "magenta", "deep navy")),
    ("earth", ("forest green", "weathered brown", "clay red", "cloud gray")),
    ("silver", ("silver gray", "pearl", "steel blue", "black")),
    ("gold_black", ("matte black", "antique gold", "electric white", "burgundy accent")),
    ("dusty_film", ("faded olive", "dusty blue", "tobacco brown", "washed cream")),
    ("daylight_primary", ("clear sky blue", "sunflower yellow", "vermilion", "clean white")),
    ("coastal", ("sea green", "weathered turquoise", "coral red", "sand white")),
)

MOOD_PALETTE_PREFERENCES = {
    "calm": ("pastel_air", "coastal", "silver", "earth"),
    "melancholic": ("dusty_film", "midnight_red", "monochrome", "silver"),
    "intense": ("red_black", "gold_black", "monochrome", "neon_night"),
    "energetic": ("daylight_primary", "neon_night", "sunset_amber", "red_black"),
    "romantic": ("pastel_air", "sunset_amber", "midnight_red", "gold_black"),
    "passionate": ("red_black", "sunset_amber", "neon_night", "gold_black"),
    "reflective": ("dusty_film", "earth", "silver", "midnight_red"),
}

CANDIDATE_BLUEPRINTS = (
    ("cinematic", ("cinematic_scene", "wide_landscape", "asymmetrical_scene"), "cinematic title", "natural motivated light"),
    ("symbolic", ("object_centered", "symbolic_minimal", "theatrical_still_life"), "compact title", "precise studio-meets-environment light"),
    ("editorial", ("editorial_poster", "fragmented_collage", "central_emblem"), "editorial title", "graphic directional light"),
    ("surreal", ("surreal_artwork", "double_exposure", "abstract_expressive"), "expressive title", "dreamlike but physically coherent light"),
)


@dataclass(frozen=True)
class CoverConcept:
    scene: str
    main_symbol: str
    composition: str
    text_position: str
    palette: tuple[str, ...]
    prompt: str
    signature: str
    concept_id: str = "A"
    candidate_type: str = "cinematic"
    palette_name: str = "custom"
    atmosphere: str = ""
    lighting: str = ""
    typography_style: str = "compact title"
    conflict: str = ""
    avoid: tuple[str, ...] = ()
    specificity: float = 0.5
    render_prompt: str = ""

    def to_dict(self):
        return asdict(self)


class CoverConceptBuilder:
    def build(self, song, profile, seed=None, detail="balanced"):
        return self.build_candidates(song, profile, seed=seed, detail=detail)[0]

    def build_candidates(self, song, profile, seed=None, detail="balanced", count=4, offset=0):
        count = max(4, int(count))
        base = int(profile.signature[:12], 16) + int(seed or 0) * 31 + offset * 101
        palettes = self._palette_candidates(profile, base)
        concepts = []
        used_compositions = set()
        used_scenes = set()
        used_symbols = set()
        for index in range(count):
            family, choices, typography, lighting = CANDIDATE_BLUEPRINTS[index % len(CANDIDATE_BLUEPRINTS)]
            composition = self._unused(choices, base + index * 7, used_compositions)
            scene = self._scene(profile, family, base + index * 11, used_scenes)
            symbol = self._symbol(song, profile, family, base + index * 13, used_symbols)
            palette_name, palette = palettes[index % len(palettes)]
            text_position = self._text_position(composition, base + index * 17)
            conflict = profile.conflicts[index % len(profile.conflicts)]
            atmosphere = self._atmosphere(profile, family)
            avoid = tuple(profile.do_not_use)
            concept_id = chr(ord("A") + index)
            signature = hashlib.sha256(f"{profile.signature}:{offset}:{index}:{scene}:{symbol}:{composition}".encode()).hexdigest()
            specificity = min(1.0, .42 + .07 * len(profile.themes) + .06 * len(profile.objects) + (.16 if profile.lyrics_used else 0))
            prompt = self._prompt(
                song, profile, scene, symbol, composition, palette, atmosphere,
                lighting, typography, conflict, avoid, detail, family,
            )
            render_prompt = self._render_prompt(
                profile, scene, symbol, composition, palette, lighting, family, detail,
            )
            concepts.append(CoverConcept(
                scene=scene,
                main_symbol=symbol,
                composition=composition,
                text_position=text_position,
                palette=palette,
                prompt=prompt,
                signature=signature,
                concept_id=concept_id,
                candidate_type=family,
                palette_name=palette_name,
                atmosphere=atmosphere,
                lighting=lighting,
                typography_style=typography,
                conflict=conflict,
                avoid=avoid,
                specificity=specificity,
                render_prompt=render_prompt,
            ))
        return tuple(concepts)

    @staticmethod
    def _unused(choices, value, used):
        for shift in range(len(choices)):
            candidate = choices[(value + shift) % len(choices)]
            if candidate not in used:
                used.add(candidate)
                return candidate
        candidate = choices[value % len(choices)]
        used.add(candidate)
        return candidate

    @classmethod
    def _scene(cls, profile, family, value, used):
        settings = list(profile.settings)
        if family in {"cinematic", "surreal"}:
            outdoor = [item for item in settings if not any(
                word in item.lower()
                for word in ("room", "interior", "apartment", "hall", "archive", "kitchen", "bedroom")
            )]
            if outdoor:
                settings = outdoor
        if family == "editorial":
            settings.extend((f"an editorial set built from {profile.imagery[0]}", f"a tactile poster-world inspired by {profile.themes[0]}"))
        elif family == "surreal":
            settings.extend((f"{profile.settings[0]} altered by {profile.imagery[0]}", f"a real landscape where {profile.conflicts[0]} becomes visible"))
        elif family == "symbolic":
            settings.extend((f"a carefully staged corner of {profile.settings[0]}", "a physical still-life environment with visible depth"))
        return cls._unused(tuple(settings), value, used)

    @classmethod
    def _symbol(cls, song, profile, family, value, used):
        family_index = {"cinematic": 0, "symbolic": 1, "editorial": 2, "surreal": 3}.get(family, 0)
        pool_size = min(len(profile.objects), max(4, len(profile.themes)))
        pool = profile.objects[:pool_size]
        subject = pool[family_index % len(pool)]
        if family == "cinematic":
            symbols = (f"{subject} as the large foreground metaphor caught at a decisive physical moment", subject)
        elif family == "symbolic":
            symbols = (f"{subject} as one oversized tactile symbol with clearly readable materials", subject)
        elif family == "editorial":
            symbols = (f"{subject} arranged as a monumental physical emblem", subject)
        else:
            symbols = (f"{subject} transformed by {profile.imagery[family_index % len(profile.imagery)]}", subject)
        symbols = (*symbols, cls._audio_symbol(song))
        return cls._unused(symbols, 0, used)

    @staticmethod
    def _audio_symbol(song):
        if song.hardness > .72:
            return "a scarred loudspeaker splitting a concrete surface"
        if song.relaxation > .68:
            return "wind moving through a field of translucent fabric"
        if song.tempo_variation > .55:
            return "a clockwork object changing shape between beats"
        if song.bass_weight > .62:
            return "a massive weathered bell vibrating above the ground"
        return "a personal object from the song title altered by the rhythm"

    @staticmethod
    def _palette_candidates(profile, base):
        plan = profile.visual_plan or {}
        planned = tuple(plan.get("palette", ()))
        if len(planned) >= 4:
            rotations = (
                planned,
                (planned[1], planned[2], planned[0], planned[3]),
                (planned[0], planned[3], planned[2], planned[1]),
                (planned[2], planned[0], planned[1], planned[3]),
            )
            return tuple((f"VisualDNA {index + 1}", palette) for index, palette in enumerate(rotations))
        preferred = list(MOOD_PALETTE_PREFERENCES.get(profile.mood, MOOD_PALETTE_PREFERENCES["reflective"]))
        lookup = dict(PALETTE_WORLDS)
        all_names = [name for name, _ in PALETTE_WORLDS]
        start = base % len(all_names)
        ordered = preferred + all_names[start:] + all_names[:start]
        unique = tuple(dict.fromkeys(ordered))
        return tuple((name, lookup[name]) for name in unique)

    @staticmethod
    def _text_position(composition, value):
        by_composition = {
            "editorial_poster": ("left", "right", "top"),
            "fragmented_collage": ("top", "left", "bottom"),
            "object_centered": ("top", "bottom", "left"),
            "strong_negative_space": ("left", "right", "top"),
            "wide_landscape": ("top", "bottom"),
            "central_emblem": ("bottom", "top"),
        }
        choices = by_composition.get(composition, ("top", "bottom", "left", "right"))
        return choices[value % len(choices)]

    @staticmethod
    def _atmosphere(profile, family):
        motion = profile.audio_character[2]
        if family == "editorial":
            return f"controlled editorial tension with {motion}"
        if family == "surreal":
            return f"poetic unreality grounded in tactile materials and {motion}"
        if family == "symbolic":
            return f"quiet concentration, {profile.emotional_tone}, immediately readable"
        return f"lived-in cinematic atmosphere, {profile.emotional_tone}, {motion}"

    @staticmethod
    def _prompt(song, profile, scene, symbol, composition, palette, atmosphere, lighting, typography, conflict, avoid, detail, family):
        style_mix = ", ".join(f"{name} {round(weight * 100)}%" for name, weight in profile.style_weights.items())
        detail_text = {"simple": "one unmistakable focal point and restrained supporting detail", "rich": "high material detail on the main object, layered depth, authored production design, and precise lighting"}.get(detail, "clear environmental detail and controlled texture")
        relationship = ", ".join(profile.relationships) if profile.relationships else "an implied human story without a generic anonymous figure"
        return (
            "Create a premium square album cover as a complete authored artwork, suitable for a real music release. "
            f"Interpret the song titled '{song.title}' by '{song.artist or 'an independent artist'}'; do not render these words in the image. "
            f"AUDIO-LED SONG DESCRIPTION: {profile.song_description} "
            f"VISUAL BRIEF: {profile.visual_brief} "
            f"CONCEPT TYPE: {family}. SCENE: {scene}. CENTRAL VISUAL METAPHOR: {symbol}. "
            f"EMOTIONAL CONFLICT: {conflict}. RELATIONSHIP: {relationship}. "
            f"ENVIRONMENTAL IMAGERY: {', '.join(profile.imagery[:5])}. AUDIO CHARACTER: {', '.join(profile.audio_character)}. "
            f"COMPOSITION: {COMPOSITION_DIRECTIONS[composition]}. ATMOSPHERE: {atmosphere}. LIGHTING: {lighting}. "
            f"COLOR WORLD: {', '.join(palette)}; use all colors with natural local variation, not a monochrome wash. "
            f"VISUAL STYLE: {style_mix}; {detail_text}. The central object must occupy roughly 35-55 percent of the cover and be readable at phone-thumbnail size. "
            f"Reserve a calm region suitable for a {typography} without placing text there. "
            "Use real spatial depth, recognizable materials, a clear focal object, and a song-specific narrative clue. Background architecture or landscape must not become the main subject. "
            f"STRICTLY AVOID: {', '.join(avoid)}, generic moody album art, default cyan grading, repeated portal imagery, procedural gradients, waveform, equalizer, music note, circles as decoration, logos, borders, text, letters, words, watermark, duplicated subjects, and meaningless floating geometry. "
            "A scene that could fit any unrelated song is a failed result."
        )

    @staticmethod
    def _render_prompt(profile, scene, symbol, composition, palette, lighting, family, detail):
        material_detail = "highly detailed tactile materials" if detail == "rich" else "clear tactile materials"
        interior_rule = "one open room in wide side view, not a hallway" if any(
            word in scene.lower() for word in ("room", "interior", "apartment", "hall", "archive", "kitchen", "bedroom")
        ) else "wide view of the location"
        return (
            f"dominant album cover subject: {symbol}, large close foreground object, occupies 45 percent of the frame, "
            f"audio-led concept: {profile.song_description}, "
            f"clearly readable materials, {scene} only as background context, visual metaphor for {profile.conflicts[0]}, "
            f"{interior_rule}, {LOCAL_COMPOSITION_DIRECTIONS[composition]}, {', '.join(palette)}, "
            f"{lighting}, {profile.mood} {family} album artwork, {material_detail}, "
            "real spatial depth, background must stay secondary, no people, no human figure, no text"
        )
