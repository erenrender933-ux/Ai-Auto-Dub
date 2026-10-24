VOICES = {
    "male": "ta-IN-ValluvarNeural",
    "female": "ta-IN-PallaviNeural",
}

# Pitch variation so two speakers of the same gender sound different
PITCHES = ["+0Hz", "+15Hz", "-15Hz", "+8Hz", "-8Hz"]


class VoiceAssigner:
    """Same speaker in the same gender always gets the same voice."""

    def __init__(self) -> None:
        self._map: dict[tuple[str, str], int] = {}
        self._count = {"male": 0, "female": 0}

    def get(self, gender: str, speaker: str) -> tuple[str, str]:
        g = "female" if gender == "female" else "male"
        key = (g, speaker)
        if key not in self._map:
            self._map[key] = self._count[g]
            self._count[g] += 1
        idx = self._map[key]
        return VOICES[g], PITCHES[idx % len(PITCHES)]
