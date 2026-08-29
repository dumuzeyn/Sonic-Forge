import hashlib
import re
from dataclasses import asdict, dataclass


STYLE_NAMES = ("cinematic", "surreal", "editorial", "symbolic")
GENERIC_AVOID = (
    "dark corridor",
    "empty tunnel",
    "stairway in a void",
    "lone centered silhouette",
    "teal-blue mist",
    "bright doorway in darkness",
    "generic foggy room",
    "abstract light portal",
)


@dataclass(frozen=True)
class SongContext:
    title: str
    artist: str = ""
    album: str = ""
    genre: str = ""
    lyrics: str = ""
    duration: float = 0.0
    bpm: float = 100.0
    speed: float = 0.5
    beat_density: float = 0.5
    rhythmicity: float = 0.5
    tempo_variation: float = 0.3
    change_rate: float = 0.3
    relaxation: float = 0.5
    hardness: float = 0.5
    brightness: float = 0.5
    bass_weight: float = 0.5
    dynamic_range: float = 0.5
    mood_override: str = "auto"
    visual_dna: object | None = None
    visual_plan: object | None = None
    song_description: str = ""
    visual_brief: str = ""


@dataclass(frozen=True)
class VisualProfile:
    mood: str
    emotional_tone: str
    themes: tuple[str, ...]
    imagery: tuple[str, ...]
    style_weights: dict[str, float]
    energy: float
    drama: float
    abstraction: float
    lyrics_used: bool
    signature: str
    language: str = "unknown"
    settings: tuple[str, ...] = ()
    objects: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    relationships: tuple[str, ...] = ()
    audio_character: tuple[str, ...] = ()
    do_not_use: tuple[str, ...] = GENERIC_AVOID
    song_description: str = ""
    visual_brief: str = ""
    visual_plan: dict | None = None

    def to_dict(self):
        return asdict(self)


# cues, theme, imagery, settings, physical symbols, conflicts
THEME_RULES = (
    (("ноч", "night", "moon", "луна", "темн"), "night", ("moonlight", "wet reflections", "sleeping windows"), ("night city", "moonlit field"), ("moon", "street lamp", "window"), ("visibility against darkness",)),
    (("люб", "love", "heart", "серд", "kiss", "поцел"), "love", ("touch", "shared warmth", "fragile closeness"), ("private room", "summer garden"), ("letter", "flower", "two chairs"), ("closeness against separation",)),
    (("огонь", "fire", "burn", "flame", "плам", "пеп"), "fire", ("embers", "smoke", "heat distortion"), ("burned field", "ceremonial hall"), ("match", "charred crown", "burning photograph"), ("destruction against renewal",)),
    (("дорог", "road", "drive", "train", "поезд", "путь", "car", "машин"), "journey", ("passing lights", "tracks", "distant destination"), ("railway platform", "open road", "moving carriage"), ("train", "road sign", "suitcase", "car"), ("departure against return",)),
    (("дожд", "rain", "storm", "гроза"), "rain", ("rain on glass", "puddled reflections", "storm clouds"), ("rainy street", "bus shelter", "coast in a storm"), ("umbrella", "wet photograph", "rain-streaked window"), ("shelter against exposure",)),
    (("море", "sea", "ocean", "wave", "волна", "shore", "берег"), "sea", ("tide", "salt spray", "vast water"), ("open coast", "flooded room", "harbor"), ("paper boat", "lighthouse", "shell"), ("distance against belonging",)),
    (("город", "city", "street", "улиц", "neon", "такси", "taxi"), "city", ("apartment lights", "traffic traces", "shop reflections"), ("lived-in city", "rooftop", "night intersection"), ("phone booth", "neon sign", "taxi"), ("anonymity against connection",)),
    (("небо", "sky", "star", "звезд", "space", "косм", "planet"), "space", ("stars", "immense atmosphere", "orbital light"), ("observatory", "lunar plain", "high plateau"), ("telescope", "satellite", "constellation map"), ("human scale against infinity",)),
    (("время", "time", "clock", "час", "memory", "памят", "вспом"), "memory", ("faded film", "layered seasons", "dust in sunlight"), ("old apartment", "archive room", "childhood courtyard"), ("clock", "photograph", "house key", "cassette"), ("past against present",)),
    (("корон", "king", "queen", "crown", "empire", "власт"), "power", ("ceremony", "monumental scale", "fractured authority"), ("public square", "throne room", "empty arena"), ("crown", "banner", "empty chair"), ("control against collapse",)),
    (("свобод", "free", "fly", "wing", "крыл", "escape", "побег"), "freedom", ("open air", "wind", "wide horizon"), ("high cliff", "open roof", "grassland"), ("kite", "open cage", "torn banner"), ("constraint against release",)),
    (("один", "alone", "lonely", "пуст", "lost", "одиноч"), "loneliness", ("unanswered space", "one distant light", "empty seat"), ("late diner", "empty beach", "sleeping district"), ("unanswered telephone", "single chair", "unlit window"), ("absence against memory",)),
    (("цвет", "flower", "rose", "роза", "garden", "сад", "трав", "grass", "земл", "earth"), "nature", ("petals", "roots", "living growth", "green grass under open sky"), ("overgrown greenhouse", "field", "garden through concrete", "earth seen from orbit"), ("flower", "seed", "branch", "grass-covered globe"), ("growth against distance", "growth against decay")),
    (("бой", "war", "fight", "battle", "bullet", "войн", "оруж"), "conflict", ("fracture", "impact", "resistance"), ("industrial yard", "abandoned stadium", "scarred landscape"), ("broken shield", "red thread", "discarded helmet"), ("resistance against force",)),
    (("дом", "home", "двор", "child", "детств", "мама", "mother"), "home", ("familiar objects", "summer light", "domestic traces"), ("kitchen", "courtyard", "family hallway"), ("house key", "family table", "toy"), ("belonging against distance",)),
    (("стекл", "glass", "mirror", "зеркал", "оскол"), "fragility", ("refraction", "cracks", "multiple reflections"), ("glass pavilion", "dressing room", "city window"), ("mirror", "glass heart", "broken photograph"), ("appearance against truth",)),
    (("сцен", "stage", "spotlight", "толп", "crowd", "show", "perform"), "performance", ("spotlight", "curtain texture", "crowd glow"), ("theater stage", "backstage", "open-air concert"), ("microphone", "empty spotlight", "mask"), ("public confidence against private doubt",)),
    (("телефон", "phone", "call", "звон", "message", "письм", "letter"), "communication", ("unanswered signal", "handwritten marks", "distance between voices"), ("phone booth", "bedroom at night", "post office"), ("telephone", "sealed letter", "message screen"), ("speech against silence",)),
    (("деньги", "money", "rich", "богат", "gold", "золот"), "wealth", ("reflections on metal", "luxury surfaces", "excess"), ("hotel lobby", "vault room", "city penthouse"), ("gold watch", "empty glass", "burning banknote"), ("possession against emptiness",)),
    (("танц", "dance", "dancing", "ритм", "rhythm"), "dance", ("body movement", "floor reflections", "rhythmic repetition"), ("dance floor", "empty ballroom", "street celebration"), ("dancing shoes", "spinning dress", "metronome"), ("movement against sadness",)),
    (("сон", "dream", "dreaming", "просну", "awake"), "dream", ("impossible scale", "half-remembered places", "soft spatial distortion"), ("bedroom opening into a landscape", "sleeping city", "impossible garden"), ("pillow", "closed eye", "paper moon"), ("dream against waking life",)),
    (("зим", "winter", "snow", "снег", "лед", "ice", "cold", "холод"), "winter", ("snow texture", "frosted breath", "long blue shadows"), ("snowbound village", "frozen lake", "winter station"), ("red scarf", "frozen watch", "footprints"), ("cold against human warmth",)),
    (("машин", "machine", "robot", "android", "механ", "engine", "двигат", "ink", "чернил"), "machine", ("gears", "ink traces", "mechanical repetition"), ("abandoned workshop", "printing room", "industrial theater"), ("mechanical hand", "ink bottle", "worn gear"), ("human feeling against machinery",)),
    (("карт", "card", "tarot", "судьб", "fate", "fortune"), "fate", ("arranged signs", "folded possibilities", "ritual texture"), ("fortune teller table", "windy town square", "candlelit room"), ("playing card", "compass", "sealed envelope"), ("choice against destiny",)),
    (("смерт", "death", "dead", "умира", "grave", "могил"), "mortality", ("vanishing traces", "wilted matter", "late light"), ("overgrown cemetery", "empty hospital room", "autumn field"), ("stopped watch", "wilted flower", "empty coat"), ("life against disappearance",)),
    (("друг", "friend", "friendship", "товарищ"), "friendship", ("shared objects", "parallel paths", "familiar gestures"), ("two-seat diner", "school courtyard", "open road"), ("two cups", "shared headphones", "handwritten note"), ("loyalty against distance",)),
    (("маск", "mask", "лицо", "face", "identity", "кто я", "who am i"), "identity", ("revealed layers", "double reflection", "costume texture"), ("dressing room", "crowded street", "portrait studio"), ("mask", "mirror", "name tag"), ("public image against inner self",)),
)

RELATIONSHIP_RULES = (
    (("мы ", "we ", "together", "вместе"), "shared bond"),
    (("ты ", "you ", "тебя", "your "), "direct address"),
    (("мама", "mother", "отец", "father", "семь", "family"), "family bond"),
    (("ушел", "ушла", "leave", "left", "goodbye", "прощ"), "separation"),
)


class LyricsAnalyzer:
    def analyze(self, text):
        normalized = re.sub(r"\s+", " ", (text or "").lower())
        values = {"themes": [], "imagery": [], "settings": [], "objects": [], "conflicts": []}
        matches = []
        for words, theme, imagery, settings, objects, conflicts in THEME_RULES:
            if any(word in normalized for word in words):
                values["themes"].append(theme)
                matches.append((imagery, settings, objects, conflicts))
        for position in range(8):
            for imagery, settings, objects, conflicts in matches:
                for key, items in (("imagery", imagery), ("settings", settings), ("objects", objects), ("conflicts", conflicts)):
                    if position < len(items):
                        values[key].append(items[position])
        relationships = [label for cues, label in RELATIONSHIP_RULES if any(cue in normalized for cue in cues)]
        values["relationships"] = relationships
        return {key: tuple(dict.fromkeys(items))[:16] for key, items in values.items()}


class VisualProfileBuilder:
    def __init__(self, lyrics_analyzer=None):
        self.lyrics_analyzer = lyrics_analyzer or LyricsAnalyzer()

    def build(self, song, seed=None):
        lyrics_semantic = self.lyrics_analyzer.analyze(song.lyrics)
        metadata_semantic = self.lyrics_analyzer.analyze(" ".join((song.artist, song.album, song.genre)))
        title_semantic = _title_specific_semantics(song.title)
        audio_semantic = _visual_dna_semantics(song)
        lyrics_used = bool(song.lyrics.strip() and lyrics_semantic["themes"])
        merged = {}
        for key in ("themes", "imagery", "settings", "objects", "conflicts", "relationships"):
            audio_values = tuple(audio_semantic[key])[:6]
            text_allowance = 8 if key == "relationships" else max(2, 8 - len(audio_values))
            text_values = _merge_many(
                (lyrics_semantic[key], title_semantic[key], metadata_semantic[key]),
                text_allowance,
            )
            merged[key] = _merge(audio_values, text_values, 8)
        dna = song.visual_dna
        energy = _clamp(getattr(dna, "arousal", song.speed * .20 + song.beat_density * .18 + song.rhythmicity * .17 + song.hardness * .28 + song.change_rate * .17))
        drama = _clamp(getattr(dna, "tension", song.hardness * .42 + song.dynamic_range * .31 + song.change_rate * .27))
        abstraction = _clamp(getattr(dna, "dynamic_complexity", song.tempo_variation * .30 + song.change_rate * .24 + (.10 if merged["themes"] else .38)))
        mood = song.mood_override if song.mood_override not in ("", "auto") else self._mood_from_dna(song, energy, merged["themes"])
        tone = self._tone_from_dna(song, drama)
        themes = merged["themes"] or (mood,)
        imagery = merged["imagery"] or (self._default_imagery(mood),)
        settings = merged["settings"] or self._default_settings(song, mood)
        objects = merged["objects"] or self._default_objects(song)
        conflicts = merged["conflicts"] or self._default_conflicts(mood)
        weights = self._weights_from_dna(song, energy, drama, abstraction, lyrics_used)
        plan = song.visual_plan.to_dict() if hasattr(song.visual_plan, "to_dict") else dict(song.visual_plan or {})
        return VisualProfile(
            mood=mood,
            emotional_tone=tone,
            themes=tuple(themes),
            imagery=tuple(imagery),
            style_weights=weights,
            energy=energy,
            drama=drama,
            abstraction=abstraction,
            lyrics_used=lyrics_used,
            signature=_signature(song.title, song.artist, song.lyrics, getattr(dna, "fingerprint", ""), str(seed)),
            language=_detect_language(" ".join((song.title, song.lyrics))),
            settings=tuple(settings),
            objects=tuple(objects),
            conflicts=tuple(conflicts),
            relationships=tuple(merged["relationships"]),
            audio_character=self._audio_character_v2(song, energy),
            do_not_use=GENERIC_AVOID,
            song_description=song.song_description,
            visual_brief=song.visual_brief,
            visual_plan=plan,
        )

    @staticmethod
    def _mood_from_dna(song, energy, themes):
        dna = song.visual_dna
        if dna is None:
            return VisualProfileBuilder._mood(song, energy, themes)
        if dna.tension > .70 or dna.aggressiveness > .72:
            return "intense"
        if dna.valence < .36:
            return "melancholic"
        if dna.valence > .68 and dna.arousal > .58:
            return "energetic"
        if dna.valence > .66 and dna.arousal < .58:
            return "romantic"
        if dna.relaxation > .62:
            return "calm"
        return "reflective"

    @staticmethod
    def _tone_from_dna(song, drama):
        dna = song.visual_dna
        if dna is None:
            return VisualProfileBuilder._tone(song, drama)
        if dna.tension > .72:
            return "compressed emotional pressure"
        if dna.relaxation > .65:
            return "open and unhurried"
        if dna.dynamic_complexity > .62:
            return "changing and structurally contrasted"
        return "balanced with a distinct timbral identity"

    @staticmethod
    def _weights_from_dna(song, energy, drama, abstraction, lyrics_used):
        dna = song.visual_dna
        if dna is None:
            return VisualProfileBuilder._weights(song, energy, drama, abstraction, lyrics_used)
        values = {
            "cinematic": .26 + dna.section_contrast * .18 + dna.dynamic_complexity * .10,
            "surreal": .18 + dna.dissonance * .20 + dna.harmonic_complexity * .10,
            "editorial": .18 + dna.rhythmic_regularity * .17 + dna.attack_strength * .08,
            "symbolic": .20 + dna.bass_mass * .13 + (1.0 - dna.dissonance) * .08,
        }
        total = sum(values.values())
        return {key: value / total for key, value in values.items()}

    @staticmethod
    def _audio_character_v2(song, energy):
        dna = song.visual_dna
        if dna is None:
            return VisualProfileBuilder._audio_character(song, energy)
        return (
            f"tempo {dna.tempo:.1f} BPM with confidence {dna.tempo_confidence:.2f}",
            f"arousal {dna.arousal:.2f}, valence {dna.valence:.2f}, tension {dna.tension:.2f}",
            f"roughness {dna.roughness:.2f}, brightness {dna.brightness:.2f}, bass mass {dna.bass_mass:.2f}",
            f"rhythmic density {dna.rhythmic_density:.2f}, regularity {dna.rhythmic_regularity:.2f}",
            f"{dna.section_count} sections with contrast {dna.section_contrast:.2f} and climax at {dna.climax_position:.2f}",
        )

    @staticmethod
    def _mood(song, energy, themes):
        if "love" in themes:
            return "romantic" if song.hardness < .65 else "passionate"
        if "loneliness" in themes or "memory" in themes:
            return "melancholic"
        if "conflict" in themes or song.hardness > .72:
            return "intense"
        if song.relaxation > .65:
            return "calm"
        if energy > .68:
            return "energetic"
        return "reflective"

    @staticmethod
    def _tone(song, drama):
        if drama > .7:
            return "dramatic"
        if song.brightness > .63 and song.relaxation > .4:
            return "hopeful"
        if song.relaxation > .68:
            return "gentle"
        if song.bass_weight > .62:
            return "weighty"
        return "balanced"

    @staticmethod
    def _default_imagery(mood):
        return {"calm": "wide air and soft daylight", "intense": "physical impact and hard directional light", "energetic": "a lived-in place caught in motion", "melancholic": "weathered objects and visible distance", "romantic": "warm tactile detail", "passionate": "heat and luminous tension"}.get(mood, "an authored environment shaped by natural light")

    @staticmethod
    def _default_settings(song, mood):
        if song.hardness > .72:
            return ("scarred industrial exterior", "open concrete arena")
        if song.relaxation > .68:
            return ("quiet sunlit landscape", "tactile domestic interior")
        if mood == "energetic":
            return ("crowded street in motion", "bright performance space")
        return ("specific lived-in environment", "wide outdoor location")

    @staticmethod
    def _default_objects(song):
        if song.hardness > .72:
            return ("fractured steel emblem", "scarred loudspeaker")
        if song.relaxation > .68:
            return ("vessel of still water", "wind-worn fabric")
        if song.bass_weight > .62:
            return ("weathered stone monument", "massive suspended bell")
        return ("recognizable personal object", "physical symbol tied to the title")

    @staticmethod
    def _default_conflicts(mood):
        return ({"calm": "stillness against passing time", "intense": "resistance against pressure", "energetic": "motion against restraint", "melancholic": "memory against absence", "romantic": "closeness against distance"}.get(mood, "inner feeling against the visible world"),)

    @staticmethod
    def _audio_character(song, energy):
        pace = "fast pulse" if song.bpm >= 132 or song.speed > .72 else "slow pulse" if song.bpm < 88 or song.speed < .32 else "moderate pulse"
        density = "dense percussion" if song.beat_density > .68 else "sparse percussion" if song.beat_density < .30 else "steady percussion"
        motion = "volatile tempo" if song.tempo_variation > .58 or song.change_rate > .66 else "stable flow"
        texture = "hard-edged sound" if song.hardness > .66 else "soft relaxed sound" if song.relaxation > .66 else "balanced texture"
        intensity = "high energy" if energy > .68 else "low energy" if energy < .34 else "medium energy"
        return (pace, density, motion, texture, intensity)

    @staticmethod
    def _weights(song, energy, drama, abstraction, lyrics_used):
        raw = {"cinematic": .24 + drama * .40 + song.relaxation * .18, "surreal": .15 + abstraction * .50 + song.tempo_variation * .15, "editorial": .14 + energy * .28 + song.beat_density * .16, "symbolic": .18 + (.34 if lyrics_used else .15) + (1 - abstraction) * .18}
        total = sum(raw.values())
        return {name: round(raw[name] / total, 4) for name in STYLE_NAMES}


def _merge(primary, secondary, limit):
    return tuple(dict.fromkeys((*primary, *secondary)))[:limit]


def _merge_many(groups, limit):
    values = []
    for group in groups:
        values.extend(group)
    return tuple(dict.fromkeys(values))[:limit]


def _visual_dna_semantics(song):
    dna = song.visual_dna
    if dna is None:
        return {key: () for key in ("themes", "imagery", "settings", "objects", "conflicts", "relationships")}

    themes = [
        "restrained energy" if dna.arousal < .36 else "driving energy" if dna.arousal > .68 else "mobile energy",
        "open calm" if dna.relaxation > .62 else "compressed tension" if dna.tension > .62 else "balanced tension",
        "bright timbre" if dna.brightness > .62 else "dark timbre" if dna.darkness > .62 else "layered timbre",
        "regular pulse" if dna.rhythmic_regularity > .64 else "unstable pulse" if dna.rhythmic_regularity < .30 else "changing pulse",
        "contrasted structure" if dna.section_contrast > .56 else "continuous structure",
    ]
    imagery = [
        "musical energy changing across a deep foreground, middle distance, and background",
        "material density following the measured bass and absolute loudness",
    ]
    settings = [
        "a broad environment whose regions follow the song's section changes",
        "a tactile scene with depth controlled by rhythmic density",
    ]
    objects = [
        "a physical focal object weighted by the song's bass and dynamics",
        "a material structure whose surface follows timbral roughness",
    ]
    conflicts = [
        "measured musical force against the space surrounding it",
        "rhythmic continuity against structural change",
    ]
    if dna.relaxation > .62:
        themes.extend(("stillness", "breathing space"))
        imagery.extend(("wide translucent layers moving in slow air", "soft light crossing a broad open surface"))
        settings.extend(("an open landscape with long spatial depth", "a quiet architectural clearing"))
        objects.append("a suspended translucent structure shaped by slow movement")
        conflicts.append("stillness against gradual motion")
    if dna.arousal > .66:
        themes.extend(("momentum", "physical force"))
        imagery.extend(("compressed motion released into open space", "directional light cutting through dense material"))
        settings.extend(("a large industrial exterior under active light", "a wind-struck open platform"))
        objects.append("a heavy material form caught at the instant of impact")
        conflicts.append("forward drive against resistance")
    if dna.tension > .62 or dna.dissonance > .60:
        themes.extend(("pressure", "instability"))
        imagery.extend(("fractured surfaces held under tension", "misaligned layers exposing a bright inner material"))
        objects.append("a fractured structure held together by visible tension")
        conflicts.append("instability against cohesion")
    if dna.bass_mass > .62:
        imagery.append("low massive forms casting broad shadows")
        objects.append("a monumental weathered mass that appears to vibrate")
    if dna.brightness > .64:
        imagery.append("crisp reflective edges in open light")
        objects.append("a translucent reflective object splitting daylight")
    if dna.roughness > .63 or dna.attack_strength > .68:
        imagery.append("scarred metal and mineral fragments with sharply readable edges")
        objects.append("a tactile fractured object marked by repeated impacts")
    if dna.rhythmic_regularity > .67:
        settings.append("a repeating architectural field with deliberate spacing")
        imagery.append("measured repetition receding into depth")
    if dna.section_contrast > .58:
        settings.append("a landscape changing visibly from one region to the next")
        imagery.append("alternating calm and saturated zones reflecting the song sections")
        conflicts.append("restraint against expansion")
    if dna.acousticness > dna.electronicness + .16:
        imagery.append("natural fibers, stone, wood, and weathered surfaces")
    elif dna.electronicness > dna.acousticness + .16:
        imagery.append("precise synthetic surfaces interrupted by human wear")

    return {
        "themes": tuple(dict.fromkeys(themes))[:6],
        "imagery": tuple(dict.fromkeys(imagery))[:8],
        "settings": tuple(dict.fromkeys(settings))[:6],
        "objects": tuple(dict.fromkeys(objects))[:7],
        "conflicts": tuple(dict.fromkeys(conflicts))[:5],
        "relationships": (),
    }


def _title_specific_semantics(title):
    normalized = (title or "").lower()
    values = {key: [] for key in ("themes", "imagery", "settings", "objects", "conflicts", "relationships")}
    def add(theme=(), imagery=(), settings=(), objects=(), conflicts=()):
        values["themes"].extend(theme)
        values["imagery"].extend(imagery)
        values["settings"].extend(settings)
        values["objects"].extend(objects)
        values["conflicts"].extend(conflicts)

    if "трав" in normalized and "дом" in normalized:
        add(
            theme=("home", "nature", "space"),
            imagery=("green grass under open sky", "earth seen from orbit", "sunlit home garden"),
            settings=("home garden", "earth seen from orbit", "childhood courtyard"),
            objects=("small home surrounded by tall grass", "grass-covered globe", "family house"),
            conflicts=("earthly home against cosmic distance",),
        )
    if any(word in normalized for word in ("море", "морск", "sea", "ocean")):
        add(
            theme=("sea", "freedom"),
            imagery=("wide horizon", "salt spray", "moving tide"),
            settings=("open coast", "harbor", "high cliff above the sea"),
            objects=("paper boat on a wave", "weathered lighthouse", "open cage with sea wind"),
            conflicts=("constraint against release",),
        )
    if any(word in normalized for word in ("любов", "love")) and any(word in normalized for word in ("черт", "hell", "burn")):
        add(
            theme=("love", "fire", "freedom"),
            imagery=("embers on broken glass", "red smoke", "burned letters"),
            settings=("burned field", "night street after rain", "empty room after departure"),
            objects=("charred heart-shaped mirror", "burning letter", "broken red mask"),
            conflicts=("painful attachment against release",),
        )
    if any(word in normalized for word in ("дэнс", "dance", "танц")) and any(word in normalized for word in ("груст", "sad")):
        add(
            theme=("dance", "loneliness"),
            imagery=("floor reflections", "last light on a dance floor", "slow moving shadows"),
            settings=("empty dance floor", "late club after closing", "rainy street outside a club"),
            objects=("lonely dancing shoes", "spinning disco ball", "single chair under colored light"),
            conflicts=("movement against sadness",),
        )
    if any(word in normalized for word in ("карт", "card", "tarot")):
        add(
            theme=("fate", "mystery"),
            imagery=("arranged signs", "candle light", "folded possibilities"),
            settings=("fortune teller table", "candlelit room", "windy town square"),
            objects=("open playing cards", "compass over cards", "sealed envelope beside candles"),
            conflicts=("choice against destiny",),
        )
    return {key: tuple(dict.fromkeys(items)) for key, items in values.items()}


def _detect_language(text):
    cyrillic = len(re.findall(r"[А-Яа-яЁё]", text or ""))
    latin = len(re.findall(r"[A-Za-z]", text or ""))
    if cyrillic and latin:
        ratio = min(cyrillic, latin) / max(cyrillic, latin)
        return "mixed" if ratio > .16 else ("ru" if cyrillic > latin else "en")
    if cyrillic:
        return "ru"
    if latin:
        return "en"
    return "unknown"


def _signature(*parts):
    return hashlib.sha256("\n".join(parts).encode("utf-8", "replace")).hexdigest()


def _clamp(value):
    return max(0.0, min(1.0, float(value)))
