# backend/music_variations.py
"""
Utility functions for Task 2.6:
- generate_variations(base_prompt, num_variations=3, duration=30, model_name=None)
- extend_music(base_audio_path, extra_seconds, model_name=None)
- batch_generate(prompts: list[str], duration=30, model_name=None)

These functions rely on your existing backend modules:
- InputProcessor
- PromptEnhancer
- generate_from_enhanced

They save outputs into examples/outputs with unique names and return lists of file paths.
"""

import os
import time
import uuid
import shutil
from typing import List, Tuple

from backend.input_processor import InputProcessor
from backend.prompt_enhancer import PromptEnhancer
from backend.generate import generate_from_enhanced

OUTPUT_DIR = os.path.join("examples", "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _save_unique(src_path: str, prefix: str = "melodai") -> str:
    """Copy src_path to OUTPUT_DIR with a unique filename and return path."""
    if not src_path:
        raise ValueError("src_path required")

    ext = os.path.splitext(src_path)[1] or ".wav"
    dest_name = f"{prefix}_{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(OUTPUT_DIR, dest_name)
    try:
        shutil.copy(src_path, dest_path)
    except Exception:
        # fallback: create an empty file if copy fails (shouldn't normally)
        with open(dest_path, "wb") as fh:
            fh.write(b"")
    return dest_path


def generate_variations(base_prompt: str, num_variations: int = 3, duration: int = 30, model_name: str = None) -> List[Tuple[str, str]]:
    """
    Generate `num_variations` variations for the base_prompt.
    Returns list of tuples (audio_path, enhanced_prompt_used).
    """
    results = []
    # 1) extract params
    processor = InputProcessor(api_key=None)
    extracted = processor.process_input(base_prompt)
    if not isinstance(extracted, dict):
        extracted = {"prompt": base_prompt}
    extracted["duration"] = duration

    enhancer = PromptEnhancer()
    # We'll produce small controlled variations by adjusting a 'seed' hint inside the prompt
    for i in range(num_variations):
        # append a small variation hint to encourage differences
        variation_hint = f"(variation {i+1})"
        modified = dict(extracted)
        # merge hint into prompt text
        modified_prompt_text = f"{modified.get('prompt', base_prompt)} {variation_hint}"
        modified["prompt"] = modified_prompt_text
        try:
            enhanced_prompt = enhancer.enrich_prompt(modified)
        except Exception:
            enhanced_prompt = modified_prompt_text

        # generate audio via generate_from_enhanced
        raw_path = generate_from_enhanced(enhanced_prompt, duration, model_name=model_name)
        saved = _save_unique(raw_path, prefix=f"variation{i+1}")
        results.append((saved, enhanced_prompt))
        # tiny pause to avoid bursting external rates
        time.sleep(0.2)
    return results


def extend_music(base_audio_path: str, extra_seconds: int = 30, model_name: str = None) -> str:
    """
    Extend an existing audio file by generating continuation that tries to preserve coherence.
    Approach: create a pseudo-prompt describing the original audio (minimal) and request continuation.
    Returns path to combined audio (original + extension).
    """
    if not os.path.exists(base_audio_path):
        raise FileNotFoundError(base_audio_path)

    # Create a 'continuation prompt' — lightweight: mention length to extend & reuse filename
    # In real pipeline you'd analyze audio and feed to model; here we use a prompt-based continuation.
    prompt = f"Continue the previous audio seamlessly for another {extra_seconds} seconds, preserving theme and instrumentation."

    enhancer = PromptEnhancer()
    try:
        enhanced_prompt = enhancer.enrich_prompt({"prompt": prompt, "duration": extra_seconds})
    except Exception:
        enhanced_prompt = prompt

    # generate extension audio
    ext_raw = generate_from_enhanced(enhanced_prompt, extra_seconds, model_name=model_name)

    # Copy both files into a single concatenated file (WAV copy)
    # We'll attempt a byte-level concatenation only if formats match; otherwise keep as separate files and return ext path
    import wave
    from pathlib import Path

    base = Path(base_audio_path)
    ext = Path(ext_raw)

    combined_name = f"extended_{uuid.uuid4().hex}.wav"
    combined_path = os.path.join(OUTPUT_DIR, combined_name)

    try:
        # Read WAV frames and combine (works for WAV PCM)
        with wave.open(str(base), 'rb') as wf_base:
            params = wf_base.getparams()
            frames_base = wf_base.readframes(wf_base.getnframes())

        with wave.open(str(ext), 'rb') as wf_ext:
            # if sample widths or channels or framerate differ, fallback to copying ext
            if wf_ext.getparams()[:3] != params[:3]:
                # incompatible params; return ext file instead
                return _save_unique(str(ext), prefix="extension")
            frames_ext = wf_ext.readframes(wf_ext.getnframes())

        # write combined
        with wave.open(combined_path, 'wb') as wf_out:
            wf_out.setparams(params)
            wf_out.writeframes(frames_base)
            wf_out.writeframes(frames_ext)

        return combined_path

    except Exception:
        # fallback: return ext file (saved uniquely)
        return _save_unique(str(ext), prefix="extension")


def batch_generate(prompts: list, duration: int = 30, model_name: str = None) -> List[Tuple[str, str]]:
    """
    Generate audio for each prompt in prompts (list of strings).
    Returns list of tuples (saved_audio_path, enhanced_prompt).
    """
    outputs = []
    enhancer = PromptEnhancer()
    processor = InputProcessor(api_key=None)

    for p in prompts:
        extracted = processor.process_input(p)
        if not isinstance(extracted, dict):
            extracted = {"prompt": p}
        extracted["duration"] = duration

        try:
            enhanced_prompt = enhancer.enrich_prompt(extracted)
        except Exception:
            enhanced_prompt = extracted.get("prompt", p)

        raw = generate_from_enhanced(enhanced_prompt, duration, model_name=model_name)
        saved = _save_unique(raw, prefix="batch")
        outputs.append((saved, enhanced_prompt))
        time.sleep(0.15)
    return outputs
