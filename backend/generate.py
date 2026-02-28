# backend/generate.py
"""
Optimized MusicGen backend loader + generator with audio post-processing.

Goals:
- Cache model + processor in memory (avoid repeated loads)
- Use device-aware mixed precision where available (MPS/CUDA)
- Use torch.inference_mode / no_grad for faster inference
- Move tensors to device once
- Use fallback safe paths when API differences exist
- Integrate audio post-processing suite
"""



from transformers import AutoProcessor, MusicgenForConditionalGeneration
import torch
import numpy as np
import scipy.io.wavfile
from pathlib import Path
import warnings
import time
from contextlib import nullcontext
from typing import Dict, Any




# Import cache manager with centralized helper and fallback
try:
    from .cache_manager import get_cache_manager
except ImportError:
    try:
        from backend.cache_manager import get_cache_manager
    except ImportError:
        # Create a dummy cache manager as absolute fallback
        class _DummyCacheManager:
            def get_cache_key(self, prompt, params): 
                import hashlib
                import json
                param_str = json.dumps(params, sort_keys=True)
                key_string = f"{prompt}|{param_str}"
                return hashlib.md5(key_string.encode()).hexdigest()
            
            def get(self, cache_key): 
                return None
            
            def set(self, cache_key, audio_file, metadata): 
                pass
        
        def get_cache_manager():
            return _DummyCacheManager()

# Import audio processor
try:
    from .audio_processor import AudioProcessor, process_audio_file
except ImportError:
    try:
        from backend.audio_processor import AudioProcessor, process_audio_file
    except ImportError:
        # Create dummy audio processor as fallback
        class AudioProcessor:
            def enhance_audio(self, audio_file, output_file=None, effects_config=None):
                return audio_file
        
        def process_audio_file(audio_file, output_dir=None, effects=None):
            return {'enhanced': audio_file}

# GLOBAL CACHE
_MODEL_CACHE = {
    "name": None,
    "processor": None,
    "model": None,
    "device": None,
}


def get_device():
    """Prefer GPU backends if available (MPS/CUDA), otherwise CPU."""
    # prefer cuda if available (not required for you if on mac)
    if torch.cuda.is_available():
        return torch.device("cuda")
    try:
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return torch.device("mps")
    except Exception:
        pass
    return torch.device("cpu")


def load_model(model_name="facebook/musicgen-small"):
    """
    Load and cache the processor + model and return (processor, model, device).
    Calling this repeatedly is cheap after caching.
    """
    device = get_device()

    if _MODEL_CACHE["name"] == model_name and _MODEL_CACHE["processor"] and _MODEL_CACHE["model"]:
        return _MODEL_CACHE["processor"], _MODEL_CACHE["model"], _MODEL_CACHE["device"]

    print(f"[generate] Loading model '{model_name}' on device {device} ...")
    processor = AutoProcessor.from_pretrained(model_name)
    model = MusicgenForConditionalGeneration.from_pretrained(model_name)

    # Move model to device (best-effort)
    try:
        model.to(device)
    except Exception as e:
        warnings.warn(f"Could not move model to {device}. Falling back to CPU. Reason: {e}")
        device = torch.device("cpu")
        model.to(device)

    # Set model to eval
    model.eval()

    # Cache
    _MODEL_CACHE["name"] = model_name
    _MODEL_CACHE["processor"] = processor
    _MODEL_CACHE["model"] = model
    _MODEL_CACHE["device"] = device

    print("[generate] Model loaded and cached.")
    return processor, model, device


def save_audio(path, audio, sr=32000):
    """Save numpy audio (float or int) to 16-bit WAV."""
    audio = np.asarray(audio).squeeze()
    if audio.size == 0:
        audio = np.zeros(1000, dtype=np.float32)

    # Normalize floats to int16
    if np.issubdtype(audio.dtype, np.floating):
        max_val = np.max(np.abs(audio)) or 1.0
        audio_int16 = (audio / max_val * 32767).astype(np.int16)
    else:
        audio_int16 = audio.astype(np.int16)

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    scipy.io.wavfile.write(path, sr, audio_int16)


def _safe_autocast_ctx(device):
    """
    Return a context manager for mixed precision appropriate to device.
    For CUDA -> torch.cuda.amp.autocast(); for MPS -> torch.autocast("mps", dtype=torch.float16)
    For CPU -> nullcontext (no autocast).
    """
    try:
        if device.type == "cuda":
            return torch.cuda.amp.autocast()
        if device.type == "mps":
            # PyTorch 2.0 supports torch.autocast("mps", dtype=torch.float16)
            return torch.autocast("mps", dtype=torch.float16)
    except Exception:
        pass
    return nullcontext()


def generate_music(prompt, duration=8, outfile="output.wav", model_name="facebook/musicgen-small", 
                  enable_post_processing=True, post_processing_config=None):
    """
    Generate audio from plain prompt with optional post-processing.
    - duration: seconds requested
    - outfile: filename under examples/outputs/
    - enable_post_processing: whether to apply audio enhancement
    - post_processing_config: configuration for audio effects
    - returns: output path (string)
    """

    # Ensure cache manager is available - this is the key fix
    cache_manager = None
    try:
        # Try different import strategies
        try:
            from .cache_manager import get_cache_manager as _get_cm
        except ImportError:
            try:
                from backend.cache_manager import get_cache_manager as _get_cm
            except ImportError:
                try:
                    import sys
                    import os
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    if current_dir not in sys.path:
                        sys.path.insert(0, current_dir)
                    from cache_manager import get_cache_manager as _get_cm
                except ImportError:
                    # Final fallback - create a no-op cache manager
                    class _DummyCacheManager:
                        def get_cache_key(self, prompt, params): return "dummy"
                        def get(self, cache_key): return None
                        def set(self, cache_key, audio_file, metadata): pass
                    
                    def _get_cm():
                        return _DummyCacheManager()
        
        cache_manager = _get_cm()
    except Exception as e:
        print(f"[generate] Warning: Cache manager not available: {e}")
        # Create dummy cache manager as fallback
        class _DummyCacheManager:
            def get_cache_key(self, prompt, params): return "dummy"
            def get(self, cache_key): return None
            def set(self, cache_key, audio_file, metadata): pass
        
        cache_manager = _DummyCacheManager()

    # Check cache first (include post-processing in cache key)
    params = {"duration": duration, "model_name": model_name, "post_processing": enable_post_processing}
    cache_key = cache_manager.get_cache_key(prompt, params)
    cached_result = cache_manager.get(cache_key)

    if cached_result:
        cached_file, metadata = cached_result
        print(f"[generate] Cache hit! Using cached audio: {cached_file}")

        # Copy cached file to requested output location
        out_path = str(Path("examples/outputs") / outfile)
        import shutil
        shutil.copy2(cached_file, out_path)
        return out_path

    print("[generate] Cache miss, generating new audio...")

    start_time = time.time()
    processor, model, device = load_model(model_name)

    TOKENS_PER_SECOND = 25  # MusicGen approximate token rate
    max_new_tokens = max(20, int(duration * TOKENS_PER_SECOND))

    print("[generate] Preparing input...")
    # prepare inputs once
    inputs = processor(text=[prompt], return_tensors="pt")

    # move inputs to device
    try:
        inputs = {k: v.to(device) for k, v in inputs.items()}
    except Exception:
        # fallback: keep on CPU
        pass

    # Choose a lighter sampling configuration to speed up generation.
    # Lower guidance_scale and simpler generation options reduce compute.
    guidance_scale = 1.0
    do_sample = True  # sampling gives variety; set False for deterministic (beam search) but slower for long outputs

    print(f"[generate] Duration {duration}s -> tokens {max_new_tokens} (device={device})")

    # Try higher-performance path: if model exposes a helper (some versions)
    audio = None
    ctx = _safe_autocast_ctx(device)

    # Use inference_mode for speed
    with torch.inference_mode():
        with ctx:
            try:
                # Some MusicGen releases include generate_audio / generate_audio_stream.
                # Try calling a direct helper first (faster API when available).
                if hasattr(model, "generate_audio"):
                    print("[generate] Using model.generate_audio() API")
                    audio_tensor = model.generate_audio(
                        prompt,
                        max_new_tokens=max_new_tokens,
                        do_sample=do_sample,
                        guidance_scale=guidance_scale,
                    )
                    # audio_tensor might be a torch.Tensor or numpy array
                    if isinstance(audio_tensor, torch.Tensor):
                        audio = audio_tensor.cpu().numpy()
                    else:
                        audio = np.asarray(audio_tensor)
                else:
                    # Fallback: use model.generate() with prepared inputs
                    print("[generate] Using model.generate() fallback")
                    gen = model.generate(
                        **inputs,
                        max_new_tokens=max_new_tokens,
                        do_sample=do_sample,
                        guidance_scale=guidance_scale,
                        num_return_sequences=1,
                    )
                    # gen may be audio-like output or token ids depending on implementation
                    # Most MusicGen versions return waveform tensor as first element
                    if isinstance(gen, (list, tuple)):
                        candidate = gen[0]
                    else:
                        candidate = gen
                    if isinstance(candidate, torch.Tensor):
                        audio = candidate.cpu().numpy()
                    else:
                        audio = np.asarray(candidate)
            except Exception as e:
                # Last-resort fallback: run on CPU with no autocast
                warnings.warn(f"[generate] Primary generation path failed: {e}. Retrying on CPU without autocast.")
                cpu_device = torch.device("cpu")
                try:
                    model.to(cpu_device)
                except Exception:
                    pass
                try:
                    inputs_cpu = processor(text=[prompt], return_tensors="pt")
                    audio_out = model.generate(
                        **inputs_cpu,
                        max_new_tokens=max_new_tokens,
                        do_sample=do_sample,
                        guidance_scale=guidance_scale,
                        num_return_sequences=1,
                    )
                    if isinstance(audio_out, (list, tuple)):
                        audio_candidate = audio_out[0]
                    else:
                        audio_candidate = audio_out
                    if isinstance(audio_candidate, torch.Tensor):
                        audio = audio_candidate.cpu().numpy()
                    else:
                        audio = np.asarray(audio_candidate)
                except Exception as e2:
                    raise RuntimeError(f"Generation failed on fallback CPU path: {e2}") from e

    # Ensure audio is numpy
    if audio is None:
        raise RuntimeError("Audio generation returned no data.")

    # Save audio initially
    raw_audio_path = str(Path("examples/outputs") / f"raw_{outfile}")
    save_audio(raw_audio_path, audio, sr=32000)

    # Apply post-processing if enabled
    final_output_path = str(Path("examples/outputs") / outfile)
    if enable_post_processing:
        print("[generate] Applying audio post-processing...")
        try:
            processor = AudioProcessor()
            enhanced_file = processor.enhance_audio(
                raw_audio_path,
                output_file=final_output_path,
                effects_config=post_processing_config
            )
            final_output_path = enhanced_file
            print("[generate] Audio post-processing completed.")
        except Exception as e:
            warnings.warn(f"[generate] Post-processing failed, using raw audio: {e}")
            # Fallback to raw audio
            import shutil
            shutil.copy2(raw_audio_path, final_output_path)
    else:
        # No post-processing, use raw audio
        import shutil
        shutil.copy2(raw_audio_path, final_output_path)

    # Cache the generated audio
    try:
        generation_time = time.time() - start_time
        metadata = {
            "prompt": prompt,
            "params": params,
            "generation_time": generation_time,
            "model_name": model_name,
            "duration": duration,
            "timestamp": time.time(),
            "post_processing_enabled": enable_post_processing
        }
        cache_manager.set(cache_key, final_output_path, metadata)
        print(f"[generate] Cached audio for future use (generation took {generation_time:.2f}s)")
    except Exception as e:
        print(f"[generate] Cache storage failed: {e}")

    print(f"[generate] Saved: {final_output_path}")
    
    # Display cache statistics after generation
    try:
        cache_stats = cache_manager.get_formatted_stats()
        print("\n" + cache_stats)
    except Exception as e:
        print(f"[generate] Cache statistics display failed: {e}")
    
    return final_output_path


def generate_from_enhanced(prompt, duration, model_name="facebook/musicgen-small", 
                          enable_post_processing=True, post_processing_config=None):
    """Wrapper used by higher-level pipeline with post-processing support."""

    # Try to use quality scorer for auto-retry if available
    try:
        try:
            from .quality_scorer import QualityScorer
        except ImportError:
            try:
                from backend.quality_scorer import QualityScorer
            except ImportError:
                import sys
                import os
                current_dir = os.path.dirname(os.path.abspath(__file__))
                if current_dir not in sys.path:
                    sys.path.insert(0, current_dir)
                from quality_scorer import QualityScorer
        
        scorer = QualityScorer()

        def generate_callable(p, d, m):
            return generate_music(p, duration=d, outfile="enhanced_output.wav", 
                                model_name=m, enable_post_processing=enable_post_processing,
                                post_processing_config=post_processing_config)

        report, paths = scorer.evaluate_and_maybe_retry(
            generate_callable=generate_callable,
            base_prompt=prompt,
            duration=duration,
            model_name=model_name,
            expected_params={"duration": duration}
        )

        # Return the best quality file (last one if retries happened)
        if paths:
            return paths[-1]  # return the final/best attempt
        else:
            # Fallback to original method if quality scorer fails
            return generate_music(prompt, duration=duration, outfile="enhanced_output.wav", 
                                model_name=model_name, enable_post_processing=enable_post_processing,
                                post_processing_config=post_processing_config)

    except ImportError:
        # Quality scorer not available, use original method
        return generate_music(prompt, duration=duration, outfile="enhanced_output.wav", 
                            model_name=model_name, enable_post_processing=enable_post_processing,
                            post_processing_config=post_processing_config)
    except Exception as e:
        # Any other error, fallback to original method
        print(f"[generate] Quality scorer failed, using fallback: {e}")
        return generate_music(prompt, duration=duration, outfile="enhanced_output.wav", 
                            model_name=model_name, enable_post_processing=enable_post_processing,
                            post_processing_config=post_processing_config)


def generate_from_payload(payload, model_name="facebook/musicgen-small"):
    """Wrapper for payload dict input."""
    prompt = payload.get("prompt", "")
    duration = int(payload.get("duration", 8))
    enable_post_processing = payload.get("enable_post_processing", True)
    post_processing_config = payload.get("post_processing_config", None)
    
    return generate_music(prompt, duration=duration, outfile="payload_output.wav", 
                         model_name=model_name, enable_post_processing=enable_post_processing,
                         post_processing_config=post_processing_config)


def process_generated_audio(audio_file: str, output_dir: str = None,
                           effects_config: Dict[str, Any] = None) -> Dict[str, str]:
    """
    Process generated audio with full post-processing suite.
    
    Args:
        audio_file: Path to generated audio file
        output_dir: Directory for output files
        effects_config: Effects configuration
        
    Returns:
        Dictionary with paths to processed files
    """
    try:
        return process_audio_file(audio_file, output_dir, effects_config)
    except Exception as e:
        print(f"[generate] Audio processing failed: {e}")
        return {'enhanced': audio_file}


# -------------------------
# COMMAND LINE INTERFACE
# -------------------------
if __name__ == "__main__":
    import argparse
    import sys
    import os

    # Add current directory to path for imports
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    parser = argparse.ArgumentParser(description="MelodAI Music Generator with Quality Scoring and Audio Post-Processing")
    parser.add_argument("--prompt", "-p", type=str, help="Music description prompt", required=True)
    parser.add_argument("--duration", "-d", type=int, default=8, help="Duration in seconds (default: 8)")
    parser.add_argument("--model", "-m", type=str, default="facebook/musicgen-small",
                       help="Model name (default: facebook/musicgen-small)")
    parser.add_argument("--output", "-o", type=str, help="Output filename (optional)")
    parser.add_argument("--no-quality", action="store_true", help="Disable quality scoring")
    parser.add_argument("--no-post-process", action="store_true", help="Disable audio post-processing")

    args = parser.parse_args()

    print("🎵 MelodAI Music Generator with Quality Scoring and Audio Post-Processing")
    print("=" * 70)
    print(f"Prompt: {args.prompt}")
    print(f"Duration: {args.duration}s")
    print(f"Model: {args.model}")
    print(f"Quality Scoring: {'Disabled' if args.no_quality else 'Enabled'}")
    print(f"Audio Post-Processing: {'Disabled' if args.no_post_process else 'Enabled'}")
    print()

    try:
        if args.no_quality:
            # Generate without quality scoring
            print("🎵 Generating music (quality scoring disabled)...")
            output_file = generate_music(
                prompt=args.prompt,
                duration=args.duration,
                outfile=args.output or f"manual_{int(__import__('time').time())}.wav",
                model_name=args.model,
                enable_post_processing=not args.no_post_process
            )
            print(f"✅ Generated: {output_file}")
        else:
            # Generate with quality scoring
            print("🎵 Generating music with quality scoring...")
            output_file = generate_from_enhanced(
                prompt=args.prompt,
                duration=args.duration,
                model_name=args.model,
                enable_post_processing=not args.no_post_process
            )

            print(f"✅ Generated: {output_file}")

            # Score the generated music
            try:
                try:
                    from .quality_scorer import QualityScorer
                except ImportError:
                    try:
                        from backend.quality_scorer import QualityScorer
                    except ImportError:
                        import sys
                        import os
                        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                        from backend.quality_scorer import QualityScorer
                
                scorer = QualityScorer()
                report = scorer.score_audio(output_file, expected_params={'duration': args.duration})

                print()
                print("🎵 Quality Score Report")
                print("=" * 40)
                print(f"Overall Score: {report['overall_score']:.1f}/100")
                print(f"Quality Pass: {'✅ PASS' if report.get('pass', False) else '❌ FAIL'}")
                print()
                print("Detailed Scores:")
                for metric, score in report['scores'].items():
                    status = "✅" if score >= 60 else "❌"
                    print(f"  {metric.replace('_', ' ').title()}: {score:.1f} {status}")
                print()
                print("Mood Analysis:")
                mood = report.get('mood', {})
                if mood.get('tempo_bpm'):
                    print(f"  Tempo: {mood['tempo_bpm']:.1f} BPM")
                if mood.get('energy_db'):
                    print(f"  Energy: {mood['energy_db']:.1f} dB")
                if mood.get('spectral_centroid'):
                    print(f"  Spectral Centroid: {mood['spectral_centroid']:.1f} Hz")

                if not report.get('pass', False):
                    print()
                    print("⚠️  Low quality detected! Consider regenerating with different prompt.")

            except Exception as e:
                print(f"⚠️  Quality scoring failed: {e}")

    except Exception as e:
        print(f"❌ Generation failed: {e}")
        sys.exit(1)
