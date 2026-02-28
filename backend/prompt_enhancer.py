# backend/prompt_enhancer.py

import json
import os
import random
from typing import Dict, List


# ----------------------------
# Load mood templates from JSON
# ----------------------------
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "mood_templates.json")

DEFAULT_TEMPLATES = {
    "happy": "upbeat, cheerful, bright instruments, major key, energetic rhythm, {tempo} BPM",
    "sad": "emotional, slow tempo, minor key, soft piano and strings, melancholic, {tempo} BPM",
    "energetic": "high-energy, fast-paced rhythms, strong beats, powerful synths, {tempo} BPM",
    "calm": "soft ambient pads, gentle textures, slow relaxing atmosphere, {tempo} BPM"
}


def load_templates():
    if os.path.exists(TEMPLATE_PATH):
        try:
            with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return DEFAULT_TEMPLATES
    return DEFAULT_TEMPLATES


MOOD_TEMPLATES = load_templates()


# ----------------------------
# Helper utilities
# ----------------------------
def tempo_to_bpm(tempo):
    if isinstance(tempo, int):
        return tempo
    if not tempo:
        return 90
    t = str(tempo).lower()
    if t == "slow":
        return 60
    if t == "medium":
        return 90
    if t == "fast":
        return 128
    digits = "".join([c for c in t if c.isdigit()])
    return int(digits) if digits else 90


# ----------------------------
# Prompt Enhancer Class
# ----------------------------
class PromptEnhancer:
    def __init__(self, seed=42):
        random.seed(seed)
        self.templates = MOOD_TEMPLATES

    def _apply_template(self, mood: str, tempo: str):
        bpm = tempo_to_bpm(tempo)
        template = self.templates.get(mood.lower(), "")
        return template.replace("{tempo}", str(bpm))

    def enrich_prompt(self, params: Dict, variation: int = 0) -> str:
        """
        Input: structured parameters from InputProcessor
        Output: Enhanced descriptive prompt
        """
        base = params.get("prompt", "")
        mood = params.get("mood", "")
        style = params.get("style", "")
        tempo = params.get("tempo", "")
        key = params.get("key", "")
        duration = params.get("duration", 8)
        instruments = params.get("instruments", [])

        mood_desc = self._apply_template(mood, tempo)

        inst_line = ""
        if instruments:
            inst_line = "Instruments: " + ", ".join(instruments)

        variation_words = ["lush", "warm", "crispy", "smooth", "glassy", "ambient"]
        texture = random.choice(variation_words) if variation else ""

        enhanced = (
            f"{base} | "
            f"{mood_desc} | "
            f"Style: {style}. | "
            f"{inst_line} | "
            f"Key: {key}. | "
            f"Texture: {texture}. | "
            f"Structure: intro, build, climax, outro | "
            f"Duration: {duration}s."
        )

        return enhanced

    def generate_variations(self, params: Dict, n: int = 3) -> List[str]:
        versions = []
        for i in range(n):
            versions.append(self.enrich_prompt(params, variation=i))
        return versions
