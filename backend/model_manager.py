# """
# Model Manager for Multi-Model MusicGen Support

# This module provides a ModelManager class that supports multiple MusicGen model variants,
# with intelligent model selection based on user preferences, duration, and quality-speed tradeoffs.
# """

# from transformers import AutoProcessor, MusicgenForConditionalGeneration
# import torch
# import numpy as np
# import warnings
# from pathlib import Path
# from typing import Dict, Optional, Tuple, Any
# import time


# class ModelManager:
#     """
#     Manages multiple MusicGen models with intelligent selection and caching.

#     Supports model variants:
#     - musicgen-small (300M params) - Fast generation
#     - musicgen-medium (1.5B params) - Balanced quality/speed
#     - musicgen-melody - Melody conditioning
#     """

#     # Model configurations
#     MODEL_CONFIGS = {
#         "facebook/musicgen-small": {
#             "params": "300M",
#             "speed": "fast",
#             "quality": "good",
#             "description": "Fast generation, good quality",
#             "recommended_duration": "< 60s"
#         },
#         "facebook/musicgen-medium": {
#             "params": "1.5B",
#             "speed": "balanced",
#             "quality": "better",
#             "description": "Balanced speed and quality",
#             "recommended_duration": "< 120s"
#         },
#         "facebook/musicgen-melody": {
#             "params": "1.5B",
#             "speed": "balanced",
#             "quality": "melody_focused",
#             "description": "Melody conditioning, balanced performance",
#             "recommended_duration": "< 120s"
#         }
#     }

#     def __init__(self):
#         """Initialize the model manager."""
#         self.models: Dict[str, Dict[str, Any]] = {}
#         self.current_model: Optional[str] = None
#         self.device = self._get_device()

#     def _get_device(self) -> torch.device:
#         """Get the best available device."""
#         if torch.cuda.is_available():
#             return torch.device("cuda")
#         try:
#             if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
#                 return torch.device("mps")
#         except Exception:
#             pass
#         return torch.device("cpu")

#     def load_model(self, model_name: str) -> None:
#         """
#         Load a specific model if not already loaded.

#         Args:
#             model_name: Name of the model to load (e.g., 'facebook/musicgen-small')
#         """
#         if model_name not in self.MODEL_CONFIGS:
#             available_models = list(self.MODEL_CONFIGS.keys())
#             raise ValueError(f"Unknown model '{model_name}'. Available models: {available_models}")

#         if model_name not in self.models:
#             print(f"[ModelManager] Loading model '{model_name}' on {self.device}...")

#             try:
#                 start_time = time.time()

#                 # Load processor and model
#                 processor = AutoProcessor.from_pretrained(model_name)
#                 model = MusicgenForConditionalGeneration.from_pretrained(model_name)

#                 # Move to device
#                 model.to(self.device)
#                 model.eval()

#                 load_time = time.time() - start_time

#                 # Cache the loaded model
#                 self.models[model_name] = {
#                     "processor": processor,
#                     "model": model,
#                     "load_time": load_time,
#                     "device": self.device
#                 }

#                 print(f"[ModelManager] Model loaded in {load_time:.2f}s")
#             except Exception as e:
#                 raise RuntimeError(f"Failed to load model '{model_name}': {e}")

#         self.current_model = model_name

#     def select_model(self, duration: int = 30, quality_priority: str = "balanced",
#                     user_preference: Optional[str] = None) -> str:
#         """
#         Intelligently select the best model based on parameters.

#         Args:
#             duration: Target duration in seconds
#             quality_priority: 'speed', 'balanced', or 'quality'
#             user_preference: Specific model name if user specified

#         Returns:
#             Selected model name
#         """
#         # If user specified a preference, use it
#         if user_preference and user_preference in self.MODEL_CONFIGS:
#             return user_preference

#         # Duration-based selection
#         if duration > 120:
#             # Long duration - prefer smaller models for speed
#             if quality_priority == "speed":
#                 return "facebook/musicgen-small"
#             elif quality_priority == "quality":
#                 return "facebook/musicgen-small"  # Use small for speed even for quality
#             else:  # balanced
#                 return "facebook/musicgen-medium"
#         elif duration > 60:
#             # Medium duration
#             if quality_priority == "speed":
#                 return "facebook/musicgen-small"
#             else:
#                 return "facebook/musicgen-medium"
#         else:
#             # Short duration - can use any model
#             if quality_priority == "speed":
#                 return "facebook/musicgen-small"
#             elif quality_priority == "quality":
#                 return "facebook/musicgen-small"  # Use small for speed
#             else:  # balanced
#                 return "facebook/musicgen-medium"

#     def generate(self, prompt: str, params: Dict[str, Any]) -> Tuple[np.ndarray, float]:
#         """
#         Generate audio using the current model.

#         Args:
#             prompt: Text prompt for generation
#             params: Generation parameters (duration, guidance_scale, etc.)

#         Returns:
#             Tuple of (audio_array, generation_time_seconds)
#         """
#         if not self.current_model or self.current_model not in self.models:
#             raise RuntimeError("No model loaded. Call load_model() first.")

#         model_data = self.models[self.current_model]
#         processor = model_data["processor"]
#         model = model_data["model"]
#         device = model_data["device"]

#         # Extract parameters
#         duration = params.get("duration", 8)
#         guidance_scale = params.get("guidance_scale", 1.0)
#         do_sample = params.get("do_sample", True)
#         temperature = params.get("temperature", 1.0)

#         # Calculate tokens (model-specific for optimization)
#         if "small" in self.current_model:
#             TOKENS_PER_SECOND = 20
#         elif "medium" in self.current_model:
#             TOKENS_PER_SECOND = 25  # Standard for medium
#         else:
#             TOKENS_PER_SECOND = 25  # melody
#         max_new_tokens = max(20, int(duration * TOKENS_PER_SECOND))

#         print(f"[ModelManager] Generating with {self.current_model} (duration: {duration}s, tokens: {max_new_tokens})")

#         # Prepare inputs
#         inputs = processor(text=[prompt], return_tensors="pt")
#         inputs = {k: v.to(device) for k, v in inputs.items()}

#         # Generation context
#         ctx = self._get_autocast_context(device)

#         start_time = time.time()

#         with torch.inference_mode():
#             with ctx:
#                 try:
#                     # Try direct generate_audio if available
#                     if hasattr(model, "generate_audio"):
#                         audio_tensor = model.generate_audio(
#                             prompt,
#                             max_new_tokens=max_new_tokens,
#                             do_sample=do_sample,
#                             guidance_scale=guidance_scale,
#                         )
#                     else:
#                         # Fallback to standard generate
#                         gen_output = model.generate(
#                             **inputs,
#                             max_new_tokens=max_new_tokens,
#                             do_sample=do_sample,
#                             guidance_scale=guidance_scale,
#                             num_return_sequences=1,
#                         )

#                         # Extract audio from output
#                         if isinstance(gen_output, (list, tuple)):
#                             audio_tensor = gen_output[0]
#                         else:
#                             audio_tensor = gen_output

#                     # Convert to numpy
#                     if isinstance(audio_tensor, torch.Tensor):
#                         audio = audio_tensor.cpu().numpy()
#                     else:
#                         audio = np.asarray(audio_tensor)

#                 except Exception as e:
#                     # Fallback to CPU if GPU fails
#                     print(f"[ModelManager] Primary generation failed: {e}. Trying CPU fallback...")
#                     cpu_device = torch.device("cpu")

#                     try:
#                         model.to(cpu_device)
#                         inputs_cpu = processor(text=[prompt], return_tensors="pt")

#                         # For medium model, use optimized parameters on CPU too
#                         if "medium" in self.current_model:
#                             gen_output = model.generate(
#                                 **inputs_cpu,
#                                 max_new_tokens=max_new_tokens,
#                                 do_sample=False,
#                                 guidance_scale=0.3,
#                                 temperature=0.8,
#                                 num_return_sequences=1,
#                             )
#                         else:
#                             gen_output = model.generate(
#                                 **inputs_cpu,
#                                 max_new_tokens=max_new_tokens,
#                                 do_sample=do_sample,
#                                 guidance_scale=guidance_scale,
#                                 num_return_sequences=1,
#                             )

#                         if isinstance(gen_output, (list, tuple)):
#                             audio_tensor = gen_output[0]
#                         else:
#                             audio_tensor = gen_output

#                         if isinstance(audio_tensor, torch.Tensor):
#                             audio = audio_tensor.cpu().numpy()
#                         else:
#                             audio = np.asarray(audio_tensor)

#                         # Move model back to original device
#                         model.to(device)

#                     except Exception as e2:
#                         raise RuntimeError(f"Generation failed on both GPU and CPU: {e2}")

#         generation_time = time.time() - start_time

#         print(f"[ModelManager] Generated audio in {generation_time:.2f}s")
#         return audio, generation_time

#     def _get_autocast_context(self, device: torch.device):
#         """Get appropriate autocast context for the device."""
#         try:
#             if device.type == "cuda":
#                 return torch.cuda.amp.autocast()
#             elif device.type == "mps":
#                 return torch.autocast("mps", dtype=torch.float16)
#         except Exception:
#             pass
#         return torch.no_grad()  # Fallback context

#     def get_available_models(self) -> Dict[str, Dict[str, str]]:
#         """Get information about available models."""
#         return self.MODEL_CONFIGS.copy()

#     def get_current_model_info(self) -> Optional[Dict[str, Any]]:
#         """Get information about the currently loaded model."""
#         if not self.current_model:
#             return None

#         info = self.MODEL_CONFIGS.get(self.current_model, {}).copy()
#         if self.current_model in self.models:
#             model_data = self.models[self.current_model]
#             info["loaded"] = True
#             info["load_time"] = model_data["load_time"]
#             info["device"] = str(model_data["device"])
#         else:
#             info["loaded"] = False

#         return info

#     def unload_model(self, model_name: str) -> None:
#         """Unload a specific model to free memory."""
#         if model_name in self.models:
#             del self.models[model_name]
#             if self.current_model == model_name:
#                 self.current_model = None
#             print(f"[ModelManager] Unloaded model '{model_name}'")

#     def clear_cache(self) -> None:
#         """Clear all loaded models from memory."""
#         self.models.clear()
#         self.current_model = None
#         print("[ModelManager] Cleared all model cache")

#     def benchmark_models(self, prompt: str = "A happy piano melody", duration: int = 8) -> Dict[str, Dict[str, Any]]:
#         """
#         Benchmark all available models with a test prompt.

#         Returns:
#             Dictionary with benchmark results for each model
#         """
#         results = {}
#         test_params = {
#             "duration": duration,
#             "guidance_scale": 1.0,
#             "do_sample": True
#         }

#         print("[ModelManager] Starting model benchmarks...")

#         for model_name in self.MODEL_CONFIGS.keys():
#             try:
#                 print(f"[ModelManager] Benchmarking {model_name}...")

#                 # Load model
#                 self.load_model(model_name)

#                 # Time the generation
#                 start_time = time.time()
#                 audio, gen_time = self.generate(prompt, test_params)
#                 total_time = time.time() - start_time

#                 # Calculate metrics
#                 audio_length = len(audio) / 32000  # Assuming 32kHz sample rate
#                 quality_estimate = len(audio) / (total_time * 1000)  # Rough quality metric

#                 results[model_name] = {
#                     "success": True,
#                     "total_time": total_time,
#                     "generation_time": gen_time,
#                     "audio_length": audio_length,
#                     "quality_metric": quality_estimate,
#                     "config": self.MODEL_CONFIGS[model_name]
#                 }

#                 print(f"[ModelManager] Benchmark completed in {total_time:.2f}s")
#             except Exception as e:
#                 results[model_name] = {
#                     "success": False,
#                     "error": str(e),
#                     "config": self.MODEL_CONFIGS[model_name]
#                 }
#                 print(f"[ModelManager] Benchmark failed for {model_name}: {e}")

#         return results


# # Global instance for easy access
# _model_manager_instance = None

# def get_model_manager() -> ModelManager:
#     """Get the global model manager instance."""
#     global _model_manager_instance
#     if _model_manager_instance is None:
#         _model_manager_instance = ModelManager()
#     return _model_manager_instance


# # Convenience functions for backward compatibility
# def load_model(model_name: str) -> None:
#     """Load a model using the global manager."""
#     manager = get_model_manager()
#     manager.load_model(model_name)

# def select_model(duration: int = 30, quality_priority: str = "balanced",
#                 user_preference: Optional[str] = None) -> str:
#     """Select a model using the global manager."""
#     manager = get_model_manager()
#     return manager.select_model(duration, quality_priority, user_preference)

# def generate_music(prompt: str, duration: int = 8, model_name: Optional[str] = None,
#                   **kwargs) -> Tuple[np.ndarray, float]:
#     """Generate music using the global manager."""
#     manager = get_model_manager()

#     # Auto-select model if not specified
#     if model_name is None:
#         model_name = manager.select_model(duration)

#     # Load model if needed
#     if manager.current_model != model_name:
#         manager.load_model(model_name)

#     # Prepare parameters
#     params = {
#         "duration": duration,
#         "guidance_scale": kwargs.get("guidance_scale", 1.0),
#         "do_sample": kwargs.get("do_sample", True),
#         "temperature": kwargs.get("temperature", 1.0)
#     }

#     return manager.generate(prompt, params)


# if __name__ == "__main__":
#     # Example usage and benchmarking
#     manager = get_model_manager()

#     print("Available Models:")
#     for name, config in manager.get_available_models().items():
#         print(f"  {name}: {config['description']} ({config['params']} params)")

#     print("\nRunning benchmarks...")
#     results = manager.benchmark_models()

#     print("\nBenchmark Results:")
#     for model_name, result in results.items():
#         if result["success"]:
#             print(f"  {model_name}:")
#             print(f"    Total time: {result['total_time']:.2f}s")
#             print(f"    Generation time: {result['generation_time']:.2f}s")
#         else:
#             print(f"  {model_name}: FAILED - {result['error']}")








"""
Model Manager for Multi-Model MusicGen Support

This module provides a ModelManager class that supports multiple MusicGen model variants,
with intelligent model selection based on user preferences, duration, and quality-speed tradeoffs.
"""

from transformers import AutoProcessor, MusicgenForConditionalGeneration
import torch
import numpy as np
import warnings
from pathlib import Path
from typing import Dict, Optional, Tuple, Any
import time
import threading
import queue


class ModelManager:
    """
    Manages multiple MusicGen models with intelligent selection and caching.

    Supports model variants:
    - musicgen-small (300M params) - Fast generation
    - musicgen-medium (1.5B params) - Balanced quality/speed
    - musicgen-melody - Melody conditioning
    """

    # Model configurations
    MODEL_CONFIGS = {
        "facebook/musicgen-small": {
            "params": "300M",
            "speed": "fast",
            "quality": "good",
            "description": "Fast generation, good quality",
            "recommended_duration": "< 60s"
        },
        "facebook/musicgen-medium": {
            "params": "1.5B",
            "speed": "balanced",
            "quality": "better",
            "description": "Balanced speed and quality",
            "recommended_duration": "< 120s"
        },
        "facebook/musicgen-melody": {
            "params": "1.5B",
            "speed": "balanced",
            "quality": "melody_focused",
            "description": "Melody conditioning, balanced performance",
            "recommended_duration": "< 120s"
        }
    }

    def __init__(self):
        """Initialize the model manager."""
        self.models: Dict[str, Dict[str, Any]] = {}
        self.current_model: Optional[str] = None
        self.device = self._get_device()

    def _get_device(self) -> torch.device:
        """Get the best available device."""
        if torch.cuda.is_available():
            return torch.device("cuda")
        try:
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return torch.device("mps")
        except Exception:
            pass
        return torch.device("cpu")

    def load_model(self, model_name: str) -> None:
        """
        Load a specific model if not already loaded.
        
        **FIX IMPLEMENTED:** Adds conversion to half-precision (float16/bfloat16) 
        for large models on GPU/MPS to prevent Out-of-Memory (OOM) errors 
        that cause generation hangs.

        Args:
            model_name: Name of the model to load (e.g., 'facebook/musicgen-small')
        """
        if model_name not in self.MODEL_CONFIGS:
            available_models = list(self.MODEL_CONFIGS.keys())
            raise ValueError(f"Unknown model '{model_name}'. Available models: {available_models}")

        if model_name not in self.models:
            print(f"[ModelManager] Loading model '{model_name}' on {self.device}...")

            try:
                start_time = time.time()

                # Load processor and model
                processor = AutoProcessor.from_pretrained(model_name)
                # Use torch_dtype='auto' to let Hugging Face attempt to load in half precision if memory is tight
                model = MusicgenForConditionalGeneration.from_pretrained(model_name, torch_dtype="auto")

                # Move to device
                model.to(self.device)
                
                # --- START OF FIX ---
                # Enforce half-precision (float16/bfloat16) for large models on CUDA/MPS 
                # to save VRAM and prevent OOM/hang issues.
                if self.device.type in ["cuda", "mps"] and ("medium" in model_name or "melody" in model_name):
                    try:
                        # Prioritize bfloat16 for modern CUDA cards (better numerical stability)
                        if self.device.type == "cuda" and torch.cuda.is_bf16_supported():
                            model.to(torch.bfloat16)
                            print(f"[ModelManager] Model converted to bfloat16 for memory efficiency.")
                        else:
                            # Fallback to float16
                            model.half()
                            print(f"[ModelManager] Model converted to float16 for memory efficiency.")
                    except Exception as e:
                        warnings.warn(f"Failed to convert model to half-precision: {e}")
                # --- END OF FIX ---

                model.eval()

                load_time = time.time() - start_time

                # Cache the loaded model
                self.models[model_name] = {
                    "processor": processor,
                    "model": model,
                    "load_time": load_time,
                    "device": self.device
                }

                print(f"[ModelManager] Model loaded in {load_time:.2f}s")
            except Exception as e:
                raise RuntimeError(f"Failed to load model '{model_name}': {e}")

        self.current_model = model_name

    def select_model(self, duration: int = 30, quality_priority: str = "balanced",
                    user_preference: Optional[str] = None) -> str:
        """
        Intelligently select the best model based on parameters.

        Args:
            duration: Target duration in seconds
            quality_priority: 'speed', 'balanced', or 'quality'
            user_preference: Specific model name if user specified

        Returns:
            Selected model name
        """
        # If user specified a preference, use it
        if user_preference and user_preference in self.MODEL_CONFIGS:
            return user_preference

        # Duration-based selection
        if duration > 120:
            # Long duration - prefer smaller models for speed
            if quality_priority == "speed":
                return "facebook/musicgen-small"
            elif quality_priority == "quality":
                return "facebook/musicgen-small"  # Use small for speed even for quality
            else:  # balanced
                return "facebook/musicgen-medium"
        elif duration > 60:
            # Medium duration
            if quality_priority == "speed":
                return "facebook/musicgen-small"
            else:
                return "facebook/musicgen-medium"
        else:
            # Short duration - can use any model
            if quality_priority == "speed":
                return "facebook/musicgen-small"
            elif quality_priority == "quality":
                return "facebook/musicgen-medium" # Changed to medium for short quality segments
            else:  # balanced
                return "facebook/musicgen-medium"

    def _generate_with_timeout(self, model, prompt, inputs, max_new_tokens, do_sample, guidance_scale, device, ctx, timeout_queue):
        """Helper method to run generation with timeout monitoring."""
        try:
            with torch.inference_mode():
                with ctx:
                    # Try direct generate_audio if available
                    if hasattr(model, "generate_audio"):
                        audio_tensor = model.generate_audio(
                            prompt,
                            max_new_tokens=max_new_tokens,
                            do_sample=do_sample,
                            guidance_scale=guidance_scale,
                        )
                    else:
                        # Fallback to standard generate
                        gen_output = model.generate(
                            **inputs,
                            max_new_tokens=max_new_tokens,
                            do_sample=do_sample,
                            guidance_scale=guidance_scale,
                            num_return_sequences=1,
                        )

                        # Extract audio from output
                        if isinstance(gen_output, (list, tuple)):
                            audio_tensor = gen_output[0]
                        else:
                            audio_tensor = gen_output

                    # Convert to numpy
                    if isinstance(audio_tensor, torch.Tensor):
                        audio = audio_tensor.cpu().numpy()
                    else:
                        audio = np.asarray(audio_tensor)

                    timeout_queue.put(("success", audio))

        except Exception as e:
            timeout_queue.put(("error", e))

    def generate(self, prompt: str, params: Dict[str, Any]) -> Tuple[np.ndarray, float]:
        """
        Generate audio using the current model with automatic fallback.

        **FALLBACK IMPLEMENTED:** If medium model takes >5 minutes or encounters memory issues,
        automatically switches to small model and retries generation.

        Args:
            prompt: Text prompt for generation
            params: Generation parameters (duration, guidance_scale, etc.)

        Returns:
            Tuple of (audio_array, generation_time_seconds)
        """
        if not self.current_model or self.current_model not in self.models:
            raise RuntimeError("No model loaded. Call load_model() first.")

        original_model = self.current_model
        fallback_used = False

        # Check if we should use fallback for medium model
        if "medium" in self.current_model:
            print(f"[ModelManager] Medium model detected. Will fallback to small if generation takes >5 minutes or encounters memory issues.")

        model_data = self.models[self.current_model]
        processor = model_data["processor"]
        model = model_data["model"]
        device = model_data["device"]

        # Extract parameters
        duration = params.get("duration", 8)
        guidance_scale = params.get("guidance_scale", 1.0)
        do_sample = params.get("do_sample", True)
        temperature = params.get("temperature", 1.0)

        # Calculate tokens (model-specific for optimization)
        TOKENS_PER_SECOND = 25 # Standard rate for MusicGen models
        if "small" in self.current_model:
            TOKENS_PER_SECOND = 20
        max_new_tokens = max(20, int(duration * TOKENS_PER_SECOND))

        print(f"[ModelManager] Generating with {self.current_model} (duration: {duration}s, tokens: {max_new_tokens})")

        # Prepare inputs
        inputs = processor(text=[prompt], return_tensors="pt")
        inputs = {k: v.to(device) for k, v in inputs.items()}

        # Generation context
        ctx = self._get_autocast_context(device)

        start_time = time.time()
        generation_timeout = 300  # 5 minutes timeout for medium model

        # For medium model, use threading with timeout
        if "medium" in self.current_model:
            timeout_queue = queue.Queue()
            generation_thread = threading.Thread(
                target=self._generate_with_timeout,
                args=(model, prompt, inputs, max_new_tokens, do_sample, guidance_scale, device, ctx, timeout_queue)
            )

            generation_thread.start()
            generation_thread.join(timeout=generation_timeout)

            if generation_thread.is_alive():
                # Timeout occurred - kill the thread and fallback
                print(f"[ModelManager] Medium model timed out after {generation_timeout}s. Falling back to small model...")
                # Note: In Python, we can't forcefully kill threads, but the fallback will proceed
                # First unload the medium model to free memory
                self.unload_model("facebook/musicgen-medium")
                self.load_model("facebook/musicgen-small")
                fallback_used = True
                return self.generate(prompt, params)

            # Check if generation completed successfully
            if not timeout_queue.empty():
                result = timeout_queue.get()
                if result[0] == "success":
                    audio = result[1]
                    generation_time = time.time() - start_time
                    print(f"[ModelManager] Generated audio in {generation_time:.2f}s")
                    return audio, generation_time
                else:
                    # Exception occurred
                    e = result[1]
                    print(f"[ModelManager] Medium model failed with error: {e}")
                    print("[ModelManager] Falling back to small model...")
                    self.load_model("facebook/musicgen-small")
                    fallback_used = True
                    return self.generate(prompt, params)
            else:
                # Should not happen, but fallback anyway
                print("[ModelManager] Medium model generation failed unexpectedly. Falling back to small model...")
                # First unload the medium model to free memory
                self.unload_model("facebook/musicgen-medium")
                self.load_model("facebook/musicgen-small")
                fallback_used = True
                return self.generate(prompt, params)

        # For non-medium models, use normal generation
        with torch.inference_mode():
            with ctx:
                try:
                    # Try direct generate_audio if available
                    if hasattr(model, "generate_audio"):
                        audio_tensor = model.generate_audio(
                            prompt,
                            max_new_tokens=max_new_tokens,
                            do_sample=do_sample,
                            guidance_scale=guidance_scale,
                        )
                    else:
                        # Fallback to standard generate
                        gen_output = model.generate(
                            **inputs,
                            max_new_tokens=max_new_tokens,
                            do_sample=do_sample,
                            guidance_scale=guidance_scale,
                            num_return_sequences=1,
                        )

                        # Extract audio from output
                        if isinstance(gen_output, (list, tuple)):
                            audio_tensor = gen_output[0]
                        else:
                            audio_tensor = gen_output

                    # Convert to numpy
                    if isinstance(audio_tensor, torch.Tensor):
                        audio = audio_tensor.cpu().numpy()
                    else:
                        audio = np.asarray(audio_tensor)

                except Exception as e:
                    # Fallback to CPU if GPU fails
                    print(f"[ModelManager] Primary generation failed: {e}. Trying CPU fallback...")
                    cpu_device = torch.device("cpu")

                    try:
                        # Temporarily move model and inputs to CPU for fallback
                        model.to(cpu_device)
                        inputs_cpu = processor(text=[prompt], return_tensors="pt")

                        gen_output = model.generate(
                            **inputs_cpu,
                            max_new_tokens=max_new_tokens,
                            do_sample=do_sample,
                            guidance_scale=guidance_scale,
                            num_return_sequences=1,
                        )

                        if isinstance(gen_output, (list, tuple)):
                            audio_tensor = gen_output[0]
                        else:
                            audio_tensor = gen_output

                        if isinstance(audio_tensor, torch.Tensor):
                            audio = audio_tensor.cpu().numpy()
                        else:
                            audio = np.asarray(audio_tensor)

                        # Move model back to original device
                        model.to(device)

                    except Exception as e2:
                        raise RuntimeError(f"Generation failed on both GPU and CPU: {e2}")

        generation_time = time.time() - start_time

        if fallback_used:
            print(f"[ModelManager] Successfully generated with fallback model in {generation_time:.2f}s")
        else:
            print(f"[ModelManager] Generated audio in {generation_time:.2f}s")

        return audio, generation_time

    def _get_autocast_context(self, device: torch.device):
        """Get appropriate autocast context for the device."""
        try:
            if device.type == "cuda":
                # Ensure autocast uses bfloat16 if available and model is bfloat16
                if torch.cuda.is_bf16_supported() and self.current_model and "medium" in self.current_model:
                    return torch.cuda.amp.autocast(dtype=torch.bfloat16)
                return torch.cuda.amp.autocast()
            elif device.type == "mps":
                return torch.autocast("mps", dtype=torch.float16)
        except Exception:
            pass
        return torch.no_grad()  # Fallback context

    def get_available_models(self) -> Dict[str, Dict[str, str]]:
        """Get information about available models."""
        return self.MODEL_CONFIGS.copy()

    def get_current_model_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the currently loaded model."""
        if not self.current_model:
            return None

        info = self.MODEL_CONFIGS.get(self.current_model, {}).copy()
        if self.current_model in self.models:
            model_data = self.models[self.current_model]
            info["loaded"] = True
            info["load_time"] = model_data["load_time"]
            info["device"] = str(model_data["device"])
        else:
            info["loaded"] = False

        return info

    def unload_model(self, model_name: str) -> None:
        """Unload a specific model to free memory."""
        if model_name in self.models:
            del self.models[model_name]
            # Attempt to clear CUDA cache if possible
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            if self.current_model == model_name:
                self.current_model = None
            print(f"[ModelManager] Unloaded model '{model_name}'")

    def clear_cache(self) -> None:
        """Clear all loaded models from memory."""
        self.models.clear()
        self.current_model = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        print("[ModelManager] Cleared all model cache")

    def benchmark_models(self, prompt: str = "A happy piano melody", duration: int = 8) -> Dict[str, Dict[str, Any]]:
        """
        Benchmark all available models with a test prompt.

        Returns:
            Dictionary with benchmark results for each model
        """
        results = {}
        test_params = {
            "duration": duration,
            "guidance_scale": 1.0,
            "do_sample": True
        }

        print("[ModelManager] Starting model benchmarks...")

        for model_name in self.MODEL_CONFIGS.keys():
            # Clear cache before each benchmark to ensure clean start
            if model_name in self.models:
                self.unload_model(model_name)
            
            try:
                print(f"[ModelManager] Benchmarking {model_name}...")

                # Load model
                self.load_model(model_name)

                # Time the generation
                start_time = time.time()
                # Run twice: once for warm-up, second for measurement
                _, _ = self.generate(prompt, test_params)
                audio, gen_time = self.generate(prompt, test_params)
                total_time = time.time() - start_time

                # Calculate metrics
                # Note: MusicGen sample rate is 32kHz
                SAMPLE_RATE = 32000 
                audio_length = len(audio[0]) / SAMPLE_RATE if len(audio.shape) > 1 else len(audio) / SAMPLE_RATE 
                # Rough quality metric: generated seconds per total computation second
                quality_estimate = audio_length / gen_time if gen_time > 0 else float('inf') 

                results[model_name] = {
                    "success": True,
                    "total_time": total_time,
                    "generation_time": gen_time,
                    "audio_length": audio_length,
                    "generation_speed_ratio": quality_estimate,
                    "config": self.MODEL_CONFIGS[model_name]
                }

                print(f"[ModelManager] Benchmark completed in {total_time:.2f}s")
            except Exception as e:
                results[model_name] = {
                    "success": False,
                    "error": str(e),
                    "config": self.MODEL_CONFIGS[model_name]
                }
                print(f"[ModelManager] Benchmark failed for {model_name}: {e}")
            finally:
                # Unload the model after benchmarking to free up memory for the next one
                self.unload_model(model_name)

        return results


# Global instance for easy access
_model_manager_instance = None

def get_model_manager() -> ModelManager:
    """Get the global model manager instance."""
    global _model_manager_instance
    if _model_manager_instance is None:
        _model_manager_instance = ModelManager()
    return _model_manager_instance


# Convenience functions for backward compatibility
def load_model(model_name: str) -> None:
    """Load a model using the global manager."""
    manager = get_model_manager()
    manager.load_model(model_name)

def select_model(duration: int = 30, quality_priority: str = "balanced",
                user_preference: Optional[str] = None) -> str:
    """Select a model using the global manager."""
    manager = get_model_manager()
    return manager.select_model(duration, quality_priority, user_preference)

def generate_music(prompt: str, duration: int = 8, model_name: Optional[str] = None,
                  **kwargs) -> Tuple[np.ndarray, float]:
    """Generate music using the global manager."""
    manager = get_model_manager()

    # Auto-select model if not specified
    if model_name is None:
        model_name = manager.select_model(duration)

    # Load model if needed
    if manager.current_model != model_name:
        manager.load_model(model_name)

    # Prepare parameters
    params = {
        "duration": duration,
        "guidance_scale": kwargs.get("guidance_scale", 1.0),
        "do_sample": kwargs.get("do_sample", True),
        "temperature": kwargs.get("temperature", 1.0)
    }

    return manager.generate(prompt, params)


if __name__ == "__main__":
    # Example usage and benchmarking
    manager = get_model_manager()

    print("Available Models:")
    for name, config in manager.get_available_models().items():
        print(f"  {name}: {config['description']} ({config['params']} params)")

    print("\nRunning benchmarks...")
    results = manager.benchmark_models()

    print("\nBenchmark Results:")
    for model_name, result in results.items():
        if result["success"]:
            print(f"  {model_name}:")
            print(f"    Total time: {result['total_time']:.2f}s")
            print(f"    Generation time: {result['generation_time']:.2f}s")
            print(f"    Speed Ratio (Secs Gen / Secs Compute): {result['generation_speed_ratio']:.2f}")
        else:
            print(f"  {model_name}: FAILED - {result['error']}")