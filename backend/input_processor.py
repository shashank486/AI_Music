# backend/input_processor.py

import os
import re
import json
import logging
from typing import Dict, Any
from openai import OpenAI

logger = logging.getLogger(__name__)


# ===============================
# LLM PROMPT TEMPLATE
# ===============================
LLM_EXTRACTION_PROMPT = """
You are a Music Input Extraction AI.

Your task:
Given a user request for music, extract structured parameters.

Return ONLY JSON with this structure:
{
  "mood": "happy/sad/calm/energetic/romantic/dark/etc.",
  "energy": 1-10,
  "style": "genre like edm, lo-fi, ambient, classical, jazz, etc.",
  "tempo": "slow/medium/fast",
  "instruments": ["list", "of", "instruments"],
  "context": "situation or use-case",
  "notes": "short explanation"
}

User request: "{user_input}"

Follow rules:
- If unclear, guess reasonable defaults.
- Use simple words.
- Always return valid JSON ONLY.
"""


# ===============================
# DEFAULT PARAMETERS
# ===============================
DEFAULT_OUTPUT = {
    "mood": "neutral",
    "energy": 5,
    "style": "ambient",
    "tempo": "medium",
    "instruments": [],
    "context": "general",
    "notes": "Default fallback used"
}


# ===============================
# FALLBACK KEYWORD EXTRACTOR
# ===============================
def fallback_extract(user_text: str) -> Dict[str, Any]:
    text = user_text.lower()
    output = DEFAULT_OUTPUT.copy()

    # Mood detection
    if any(w in text for w in ["happy", "joy", "bright"]):
        output["mood"] = "happy"
    elif any(w in text for w in ["sad", "emotional", "heartbreak"]):
        output["mood"] = "sad"
    elif any(w in text for w in ["calm", "relax", "meditation"]):
        output["mood"] = "calm"
    elif any(w in text for w in ["energetic", "workout", "power"]):
        output["mood"] = "energetic"

    # Tempo
    if "slow" in text:
        output["tempo"] = "slow"
    elif "fast" in text or "workout" in text:
        output["tempo"] = "fast"

    # Instruments
    instruments = []
    for inst in ["piano", "guitar", "drums", "violin", "bass", "synth", "flute", "bells", "pads"]:
        if inst in text:
            instruments.append(inst)

    output["instruments"] = instruments

    # Style / Genre
    if "lofi" in text or "lo-fi" in text:
        output["style"] = "lofi"
    elif "edm" in text or "dance" in text:
        output["style"] = "edm"
    elif "ambient" in text:
        output["style"] = "ambient"

    output["context"] = "general"
    output["notes"] = "Keyword fallback extraction applied"

    return output


# ===============================
# MAIN CLASS — INPUT PROCESSOR
# ===============================
class InputProcessor:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = None

        if self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key)
            except Exception as e:
                logger.error("Failed to initialize OpenAI client: %s", e)
                self.client = None

    def _call_llm(self, user_text: str) -> Dict[str, Any]:
        """Call LLM and parse JSON output."""
        prompt = LLM_EXTRACTION_PROMPT.format(user_input=user_text)

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=300
            )
            text = response.choices[0].message.content.strip()

            # extract JSON using regex
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            else:
                raise ValueError("No JSON detected in LLM response")

        except Exception as e:
            logger.error("LLM call failed: %s", e)
            return None

    def process_input(self, user_text: str) -> Dict[str, Any]:
        """Main method called by backend."""
        user_text = user_text.strip()
        if not user_text:
            return DEFAULT_OUTPUT

        # Try LLM first
        if self.client:
            llm_result = self._call_llm(user_text)
            if llm_result:
                llm_result["notes"] = "Processed using LLM"
                return llm_result

        # Fallback if LLM unavailable
        return fallback_extract(user_text)
