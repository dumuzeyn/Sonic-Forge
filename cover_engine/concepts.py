import hashlib
from dataclasses import asdict, dataclass

from .config import CoverGenerationConfig


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
    ("cinematic", ("cinematic_scene", "wide_landscape", "asymmetrical_scene"), "cinematic", "natural motivated light"),
    ("symbolic", ("object_centered", "symbolic_minimal", "theatrical_still_life"), "bold modern", "precise studio-meets-environment light"),
    ("editorial", ("editorial_poster", "fragmented_collage", "central_emblem"), "indie editorial", "graphic directional light"),
    ("surreal", ("surreal_artwork", "double_exposure", "abstract_expressive"), "dreamy", "dreamlike but physically coherent light"),
    ("portrait", ("environmental_portrait", "asymmetrical_scene", "cinematic_scene"), "elegant serif", "soft motivated portrait light"),
    ("abstract", ("abstract_expressive", "central_emblem", "double_exposure"), "electronic neon", "material light with controlled color bloom"),
    ("minimal", ("symbolic_minimal", "strong_negative_space", "object_centered"), "minimal clean", "restrained directional light"),
)

PROMPT_TEMPLATES = {
    "symbolic": "SYMBOLIC THESIS: {idea}. One tactile subject: {subject}. Stage it in {scene} as {metaphor}. {atmosphere}. Palette: {palette}. Medium: conceptual still life, {detail}. Composition: {composition}. Keep {text_area} calm for typography.",
    "cinematic": "CINEMATIC MOMENT: {idea}. Capture {subject} during one decisive action in {scene}. The environment expresses {metaphor}. {atmosphere}. Palette: {palette}. Medium: cinematic production still, {detail}. Framing: {composition}; preserve {text_area} negative space.",
    "portrait": "ENVIRONMENTAL PORTRAIT: {idea}. Show {subject} through a specific gesture in {scene}; surroundings reveal {metaphor}. {atmosphere}. Palette: {palette}. Medium: editorial music photography, {detail}. Framing: {composition}; leave {text_area} readable.",
    "abstract": "MATERIAL ABSTRACTION: {idea}. Keep {subject} recognizable while transforming it through {metaphor} in {scene}. {atmosphere}. Palette: {palette}. Medium: tactile pigment, glass and light, {detail}. Structure: {composition}; reserve {text_area} calm space.",
    "surreal": "SURREAL REALITY: {idea}. In believable {scene}, make {subject} physically embody {metaphor}. {atmosphere}. Palette: {palette}. Medium: coherent surreal photography, {detail}. Framing: {composition}; protect {text_area} for type.",
    "editorial": "EDITORIAL STATEMENT: {idea}. Build a bold hierarchy around {subject} in {scene}, using {metaphor} as the graphic argument. {atmosphere}. Palette: {palette}. Medium: authored poster-photography, {detail}. Layout: {composition}; keep {text_area} intentional.",
    "minimal": "MINIMAL CONCEPT: {idea}. Use only {subject} and one environmental clue from {scene} to express {metaphor}. {atmosphere}. Palette: {palette}. Medium: restrained conceptual photography, {detail}. Layout: {composition}; leave generous {text_area} space.",
}


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
    negative_prompt: str = ""
    visual_metaphor: str = ""
    human_presence: str = "optional"
    typography_locked: bool = False

    def to_dict(self):
        return asdict(self)


class CoverConceptBuilder:
    def __init__(self, config=None):
        self.config = config or CoverGenerationConfig()

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
        blueprints = self._blueprints(profile)
        for index in range(count):
            family, choices, typography, lighting = blueprints[index % len(blueprints)]
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
            if not self.config.prompt_compaction and profile.visual_brief:
                prompt += f" SOURCE VISUAL BRIEF: {profile.visual_brief[:500]}"
            render_prompt = self._render_prompt(
                profile, scene, symbol, composition, palette, lighting, family, detail,
            )
            human_presence = self._human_presence(profile, family)
            negative_prompt = (
                self._negative_prompt(profile, scene, family, composition, human_presence)
                if self.config.dynamic_negative_prompt
                else "text, letters, logo, watermark, low quality, blurry focal subject, duplicate main subject"
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
                negative_prompt=negative_prompt,
                visual_metaphor=profile.visual_metaphor,
                human_presence=human_presence,
            ))
        return tuple(concepts)

    def _blueprints(self, profile):
        lookup = {item[0]: item for item in CANDIDATE_BLUEPRINTS}
        order = {
            "intimate": ("portrait", "cinematic", "symbolic", "editorial", "surreal"),
            "dreamlike": ("surreal", "abstract", "cinematic", "minimal", "editorial"),
            "rhythmic_mechanical": ("editorial", "abstract", "cinematic", "symbolic", "minimal"),
            "aggressive": ("cinematic", "editorial", "symbolic", "surreal", "abstract"),
            "tragic": ("cinematic", "portrait", "symbolic", "surreal", "minimal"),
            "luminous": ("cinematic", "editorial", "portrait", "minimal", "surreal"),
        }.get(profile.narrative_mode, ("cinematic", "symbolic", "editorial", "surreal", "minimal"))
        if not self.config.allow_human_subjects_auto:
            order = tuple(name for name in order if name != "portrait")
        return tuple(lookup[name] for name in order)

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
        if family in {"cinematic", "surreal", "abstract"}:
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
        elif family == "portrait":
            settings.extend((f"a lived-in part of {profile.settings[0]}", f"{profile.settings[0]} during a specific human action"))
        elif family == "minimal":
            settings.extend((f"a restrained section of {profile.settings[0]}",))
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
        elif family == "portrait":
            symbols = (f"a specific person interacting with {subject}, face and gesture carrying the emotional conflict", subject)
        elif family == "abstract":
            symbols = (f"{subject} dissolving into tactile pigment, glass, smoke, and light while remaining recognizable", subject)
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
        detail_text = {"simple": "restrained detail", "rich": "precise tactile detail and layered depth"}.get(detail, "controlled material detail")
        template = PROMPT_TEMPLATES.get(family, PROMPT_TEMPLATES["cinematic"])
        prompt = template.format(
            idea=profile.core_emotional_thesis,
            subject=symbol,
            scene=scene,
            metaphor=profile.visual_metaphor,
            atmosphere=f"{atmosphere}; {profile.mood_arc}",
            palette=", ".join(palette),
            detail=detail_text,
            composition=COMPOSITION_DIRECTIONS[composition],
            text_area=typography,
        )
        return prompt + " Premium square album artwork, one dominant thesis, readable at phone size, no rendered lettering."

    @staticmethod
    def _render_prompt(profile, scene, symbol, composition, palette, lighting, family, detail):
        material_detail = "precise tactile detail" if detail == "rich" else "clear tactile materials"
        family_direction = {
            "symbolic": "one tactile symbol with physically readable materials",
            "cinematic": "one decisive cinematic action with foreground, middle distance and background",
            "portrait": "specific human gesture, readable face, surroundings carrying the story",
            "abstract": "material abstraction anchored by one recognizable object",
            "surreal": "one impossible transformation inside a believable physical world",
            "editorial": "bold asymmetric editorial hierarchy around one photographed subject",
            "minimal": "one subject and one supporting clue, generous meaningful negative space",
        }.get(family, "one dominant album-cover subject")
        return (
            f"premium {family} album cover; {profile.core_emotional_thesis}; subject: {symbol}; "
            f"scene: {scene}; {family_direction}; {LOCAL_COMPOSITION_DIRECTIONS[composition]}; "
            f"palette: {', '.join(palette)}; {lighting}; {material_detail}; no rendered text"
        )

    @staticmethod
    def _negative_prompt(profile, scene, family, composition, human_presence="optional"):
        negatives = [
            "text", "letters", "words", "logo", "watermark", "border", "low quality",
            "blurry focal subject", "duplicate main subject", "waveform", "equalizer",
            "music note", "generic stock album cover", "meaningless floating geometry",
        ]
        if family == "portrait":
            negatives.extend(("anonymous silhouette", "deformed face", "extra fingers", "duplicate person", "blank expression"))
        elif family == "minimal":
            negatives.extend(("visual clutter", "crowd", "busy background", "multiple competing objects"))
        elif family == "abstract":
            negatives.extend(("plain gradient", "perfect sphere", "empty procedural noise"))
        else:
            negatives.extend(("featureless centered silhouette", "empty scene without the main subject"))
        if not any(word in scene.lower() for word in ("room", "interior", "hall", "kitchen", "bedroom")):
            negatives.extend(("generic corridor", "glowing doorway", "empty tunnel"))
        if composition == "strong_negative_space" and "empty scene without the main subject" in negatives:
            negatives.remove("empty scene without the main subject")
        if human_presence == "avoid":
            negatives.extend(("posed portrait", "crowd distracting from the main object"))
        return ", ".join(dict.fromkeys(negatives))

    def _human_presence(self, profile, family):
        if family == "portrait":
            return "required"
        if not self.config.allow_human_subjects_auto:
            return "avoid"
        suggestion = profile.human_presence_suggestion.lower()
        if any(word in suggestion for word in ("welcome", "portrait", "gesture", "allow")):
            return "allowed"
        return "optional"
