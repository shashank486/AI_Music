# backend/test_prompt_enhancer.py

from backend.prompt_enhancer import PromptEnhancer

params = {
    "prompt": "calming music for meditation",
    "mood": "calm",
    "style": "ambient",
    "tempo": "slow",
    "instruments": ["piano", "bells"],
    "duration": 12,
    "key": "C major"
}

enh = PromptEnhancer()

vars = enh.generate_variations(params, n=3)

print("\n=== ENHANCED PROMPTS ===")
for i, p in enumerate(vars, start=1):
    print(f"\nVariation {i}:\n{p}")
