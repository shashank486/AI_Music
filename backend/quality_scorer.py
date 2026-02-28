# backend/quality_scorer.py
"""
Quality Scorer for generated audio (Task 3.1)

Provides:
- QualityScorer class with score_audio(audio_file, expected_params)
- evaluate_and_maybe_retry(...) helper to auto-retry generation when score < threshold
- generate_batch_report(...) to score multiple files and save a report

Metrics computed (each mapped to 0-100):
- audio_quality (clipping detection)
- duration_accuracy (matches requested duration ±2s)
- silence_detection (penalize long silent sections)
- dynamic_range (RMS variation / crest factor)
- frequency_balance (spectral centroid spread)
- mood_alignment: tempo, energy, spectral centroid => informational

Overall score is a weighted aggregation of metrics.
"""

from dataclasses import dataclass, asdict
import json
import math
import os
import time
from typing import Dict, Tuple, Optional, Callable, List

# Numerical libs
import numpy as np

# Audio libs
try:
    import soundfile as sf
except Exception as e:
    raise ImportError("soundfile is required (pip install soundfile) — " + str(e))

try:
    import librosa
except Exception:
    librosa = None  # we'll check and raise only if used functions require it

# Optional helper to call generator if provided
try:
    from backend.generate import generate_from_enhanced  # used as fallback generator in auto-retry
except Exception:
    generate_from_enhanced = None


@dataclass
class QualityConfig:
    min_overall_score: float = 65.0  # threshold to accept generation
    max_retries: int = 2
    duration_tolerance_s: float = 2.0  # ± seconds tolerance
    max_silence_sec: float = 1.5  # maximum allowed contiguous silence length before penalty
    silence_threshold_db: float = -40.0  # dB relative threshold considered silence
    clipping_threshold: float = 0.995  # normalized amplitude above which considered clipped
    dynamic_range_min: float = 6.0  # dB minimum dynamic range expected (lower => flat)
    sample_rate_resample: int = 22050  # librosa default processing rate


class QualityScorer:
    def __init__(self, config: Optional[QualityConfig] = None):
        self.config = config or QualityConfig()

    # -------------------------
    # Low-level audio helpers
    # -------------------------
    def _load_audio(self, path: str) -> Tuple[np.ndarray, int]:
        """Load audio file using soundfile (fallback) and librosa for resampling if available."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Audio file not found: {path}")

        # Use soundfile to read raw audio and its samplerate
        data, sr = sf.read(path, dtype='float32')
        # Convert to mono for analysis
        if data.ndim > 1:
            data = np.mean(data, axis=1)
        # Optionally resample for consistent analysis
        target_sr = self.config.sample_rate_resample
        if librosa is not None and sr != target_sr:
            # librosa.resample expects shape (n,)
            try:
                data = librosa.resample(data, orig_sr=sr, target_sr=target_sr)
                sr = target_sr
            except Exception:
                # if resample fails, keep original sr
                pass
        return data.astype(np.float32), sr

    def _rms_db(self, y: np.ndarray) -> float:
        rms = np.sqrt(np.mean(np.square(y))) + 1e-12
        return 20.0 * math.log10(rms)

    # -------------------------
    # Metric checks
    # -------------------------
    def _check_clipping(self, y: np.ndarray) -> float:
        """Return clipping score (0-100). 100 = no clipping, 0 = heavily clipped."""
        # Norm max to 1 range
        peak = float(np.max(np.abs(y))) if y.size else 0.0
        if peak <= 0:
            return 0.0
        # If peak exceeds clipping threshold, penalize
        if peak >= self.config.clipping_threshold:
            # map from [clipping_threshold..1.0] to [60..0]
            t = (peak - self.config.clipping_threshold) / (1.0 - self.config.clipping_threshold + 1e-9)
            score = max(0.0, 60.0 * (1.0 - t))  # allow some partial score
        else:
            score = 100.0
        return float(score)

    def _check_duration(self, y: np.ndarray, sr: int, expected_duration: float) -> float:
        """Score based on closeness to expected duration ± tolerance."""
        actual = len(y) / sr if sr > 0 else 0.0
        tol = self.config.duration_tolerance_s
        diff = abs(actual - expected_duration)
        if diff <= tol:
            return 100.0
        # linear penalty up to 3x tolerance
        penalty = min(1.0, (diff - tol) / max(tol, 1e-9))
        score = max(0.0, 100.0 * (1.0 - penalty))
        return float(score)

    def _check_silence(self, y: np.ndarray, sr: int) -> float:
        """Detect long silent intervals. Penalize if contiguous silence > max_silence_sec."""
        # Convert amplitude to short-time energy and threshold
        frame_len = int(0.05 * sr)  # 50 ms
        hop = int(frame_len / 2)
        # compute RMS per frame
        if len(y) < frame_len:
            # short audio: compute global RMS
            db = self._rms_db(y)
            if db < self.config.silence_threshold_db:
                # mostly silence
                return 0.0
            return 100.0
        rms_frames = []
        for i in range(0, len(y) - frame_len + 1, hop):
            frame = y[i:i + frame_len]
            rms_frames.append(self._rms_db(frame))
        rms_frames = np.array(rms_frames)
        silence_mask = rms_frames < self.config.silence_threshold_db
        # find longest contiguous silence (in frames)
        if silence_mask.sum() == 0:
            return 100.0
        # Find runs of True
        max_run = 0
        run = 0
        for s in silence_mask:
            if s:
                run += 1
                max_run = max(max_run, run)
            else:
                run = 0
        longest_silence_sec = (max_run * hop) / sr if sr > 0 else 0.0
        if longest_silence_sec <= self.config.max_silence_sec:
            return 100.0
        # penalty proportional to exceeded silence
        excess = longest_silence_sec - self.config.max_silence_sec
        penalty = min(1.0, excess / max(1.0, self.config.max_silence_sec))
        score = max(0.0, 100.0 * (1.0 - penalty))
        return float(score)

    def _check_dynamic_range(self, y: np.ndarray) -> float:
        """
        Estimate dynamic range by comparing loud vs quiet frames (RMS dB difference).
        Higher difference => larger dynamic range.
        """
        if len(y) == 0:
            return 0.0
        # compute frame RMS (50ms hop)
        # reuse sample rate independent approach: slice into frames of 50ms
        # assume previously resampled to target sr
        fs = self.config.sample_rate_resample
        frame_len = int(0.05 * fs)
        hop = int(frame_len / 2) if frame_len > 1 else 1
        rms_vals = []
        for i in range(0, len(y) - frame_len + 1, hop):
            frame = y[i:i + frame_len]
            rms_vals.append(self._rms_db(frame))
        if not rms_vals:
            return 0.0
        rms_vals = np.array(rms_vals)
        # dynamic range estimate = difference between 90th and 10th percentile
        high = np.percentile(rms_vals, 90)
        low = np.percentile(rms_vals, 10)
        dyn_range_db = float(high - low)
        # Score mapping: if dyn_range_db >= configured min -> 100, if 0 -> 0
        target = self.config.dynamic_range_min
        score = np.clip((dyn_range_db / (target + 1e-6)) * 100.0, 0.0, 100.0)
        return float(score)

    def _check_frequency_balance(self, y: np.ndarray, sr: int) -> float:
        """
        Evaluate frequency balance using spectral centroid and spectral rolloff spread.
        The function expects musical balance roughly centered.
        Returns 0-100 score; 100 = pleasing balanced spectrum.
        """
        if librosa is None:
            # Rough fallback: use FFT centroid
            N = len(y)
            if N == 0:
                return 0.0
            freqs = np.fft.rfftfreq(N, d=1.0 / sr)
            spectrum = np.abs(np.fft.rfft(y))
            centroid = np.sum(freqs * spectrum) / (np.sum(spectrum) + 1e-9)
            # map centroid around typical music centroid (e.g., 1500-3500 Hz)
            ideal_low, ideal_high = 800.0, 4000.0
            if centroid < ideal_low:
                score = max(0.0, 100.0 - (ideal_low - centroid) / ideal_low * 60.0)
            elif centroid > ideal_high:
                score = max(0.0, 100.0 - (centroid - ideal_high) / ideal_high * 60.0)
            else:
                score = 100.0
            return float(score)

        # with librosa compute spectral centroid and rolloff
        try:
            S = np.abs(librosa.stft(y, n_fft=2048))
            centroid = librosa.feature.spectral_centroid(S=S, sr=sr).mean()
            rolloff = librosa.feature.spectral_rolloff(S=S, sr=sr, roll_percent=0.85).mean()
            # prefer centroid in midrange typical for music
            ideal_center = 2000.0  # heuristic
            spread = abs(centroid - ideal_center) / max(1.0, ideal_center)
            # rolloff penalty if too low or too high
            score = max(0.0, 100.0 - spread * 80.0)
            # additional slight penalty if rolloff too low/high
            if rolloff < 1000:
                score *= 0.9
            return float(np.clip(score, 0.0, 100.0))
        except Exception:
            return 50.0

    # -------------------------
    # Mood / music features
    # -------------------------
    def _analyze_mood(self, y: np.ndarray, sr: int) -> Dict[str, float]:
        """Return simple mood-like metrics: tempo (BPM), energy (RMS), spectral centroid."""
        out = {"tempo_bpm": None, "energy_db": None, "spectral_centroid": None}
        try:
            if librosa is None:
                # fallback crude tempo estimate via autocorrelation on envelope — return None
                out["tempo_bpm"] = None
            else:
                tempo = librosa.beat.tempo(y=y, sr=sr)
                out["tempo_bpm"] = float(tempo[0]) if isinstance(tempo, (list, np.ndarray)) and len(tempo) > 0 else float(tempo)
            out["energy_db"] = float(self._rms_db(y))
            if librosa is not None:
                centroid = librosa.feature.spectral_centroid(y=y, sr=sr).mean()
                out["spectral_centroid"] = float(centroid)
            else:
                out["spectral_centroid"] = None
        except Exception:
            pass
        return out

    # -------------------------
    # Overall scoring
    # -------------------------
    def _calculate_overall_score(self, scores: Dict[str, float]) -> float:
        """
        Weighted aggregation. The weights can be tuned.
        """
        # Default weights
        weights = {
            "audio_quality": 0.20,
            "duration_accuracy": 0.20,
            "silence_detection": 0.20,
            "dynamic_range": 0.20,
            "frequency_balance": 0.20,
        }
        total = 0.0
        wsum = 0.0
        for k, w in weights.items():
            v = float(scores.get(k, 0.0))
            total += v * w
            wsum += w
        overall = float(total / (wsum + 1e-9))
        return overall

    # -------------------------
    # Public API
    # -------------------------
    def score_audio(self, audio_file: str, expected_params: Optional[Dict] = None) -> Dict:
        """
        Score an audio file and return detailed report.
        expected_params may include {'duration': seconds}.
        Returns a dict with per-metric scores (0-100) and overall score & mood metrics.
        """
        report = {
            "file": audio_file,
            "timestamp": time.time(),
            "scores": {},
            "mood": {},
            "notes": []
        }
        expected_duration = None
        if expected_params and isinstance(expected_params, dict):
            expected_duration = expected_params.get("duration")

        try:
            y, sr = self._load_audio(audio_file)
        except Exception as e:
            report["notes"].append(f"load_error: {e}")
            # return immediate failure report
            report["scores"] = {
                "audio_quality": 0.0,
                "duration_accuracy": 0.0,
                "silence_detection": 0.0,
                "dynamic_range": 0.0,
                "frequency_balance": 0.0,
            }
            report["overall_score"] = 0.0
            return report

        # compute metrics
        try:
            audio_quality = self._check_clipping(y)
            duration_accuracy = self._check_duration(y, sr, expected_duration if expected_duration is not None else (len(y) / sr))
            silence_detection = self._check_silence(y, sr)
            dynamic_range = self._check_dynamic_range(y)
            freq_balance = self._check_frequency_balance(y, sr)
            mood = self._analyze_mood(y, sr)
        except Exception as e:
            report["notes"].append(f"analysis_error: {e}")
            # in case of analysis error, return partial
            audio_quality = audio_quality if 'audio_quality' in locals() else 0.0
            duration_accuracy = duration_accuracy if 'duration_accuracy' in locals() else 0.0
            silence_detection = silence_detection if 'silence_detection' in locals() else 0.0
            dynamic_range = dynamic_range if 'dynamic_range' in locals() else 0.0
            freq_balance = freq_balance if 'freq_balance' in locals() else 0.0
            mood = mood if 'mood' in locals() else {}

        report["scores"] = {
            "audio_quality": float(np.clip(audio_quality, 0.0, 100.0)),
            "duration_accuracy": float(np.clip(duration_accuracy, 0.0, 100.0)),
            "silence_detection": float(np.clip(silence_detection, 0.0, 100.0)),
            "dynamic_range": float(np.clip(dynamic_range, 0.0, 100.0)),
            "frequency_balance": float(np.clip(freq_balance, 0.0, 100.0)),
        }
        overall = self._calculate_overall_score(report["scores"])
        report["overall_score"] = float(np.clip(overall, 0.0, 100.0))
        report["mood"] = mood

        # quick pass/fail
        report["pass"] = report["overall_score"] >= self.config.min_overall_score

        return report

    # -------------------------
    # Retry loop utility
    # -------------------------
    def evaluate_and_maybe_retry(
        self,
        generate_callable: Optional[Callable[[str, int, str], str]],
        base_prompt: str,
        duration: int,
        model_name: Optional[str] = None,
        expected_params: Optional[Dict] = None,
    ) -> Tuple[Dict, List[str]]:
        """
        Try initial generation via generate_callable(base_prompt, duration, model_name).
        Score it. If overall_score < threshold, auto-retry up to max_retries.
        generate_callable must return path to generated audio file.

        If generate_callable is None and backend.generate.generate_from_enhanced is available,
        it will be used with enhanced prompt flow omitted (caller can pass a wrapper).

        Returns (final_report, list_of_generated_paths)
        """
        if generate_callable is None:
            # fallback to backend.generate.generate_from_enhanced if available
            if generate_from_enhanced is None:
                raise ValueError("No generation callable provided and backend.generate.generate_from_enhanced not available.")
            # create thin wrapper that accepts (prompt, duration, model_name)
            def _gen(prompt, dur, mdl):
                return generate_from_enhanced(prompt, dur, model_name=mdl)
            generate_callable = _gen

        paths = []
        attempts = 0
        final_report = None

        while attempts <= self.config.max_retries:
            attempts += 1
            try:
                p = generate_callable(base_prompt, duration, model_name)
                paths.append(p)
            except Exception as e:
                final_report = {"error": f"generation_failed: {e}"}
                break

            # Score
            rpt = self.score_audio(p, expected_params={"duration": duration} if expected_params is None else expected_params)
            final_report = rpt
            if rpt.get("overall_score", 0.0) >= self.config.min_overall_score:
                # Accept
                break
            # else retry if allowed
            if attempts > self.config.max_retries:
                break

        return final_report, paths

    # -------------------------
    # Batch scoring / reporting
    # -------------------------
    def generate_batch_report(self, sample_files: List[str], expected_params_list: Optional[List[Dict]] = None, out_file: Optional[str] = None) -> Dict:
        """
        Score a list of audio files and return a dictionary report summarizing each file.
        Optionally writes JSON to out_file.
        expected_params_list: list aligned to sample_files with expected params dicts (or None).
        """
        reports = []
        for idx, f in enumerate(sample_files):
            exp = None
            if expected_params_list and idx < len(expected_params_list):
                exp = expected_params_list[idx]
            rpt = self.score_audio(f, expected_params=exp)
            reports.append(rpt)

        summary = {
            "generated_at": time.time(),
            "n_samples": len(sample_files),
            "min_score": min([r["overall_score"] for r in reports]) if reports else None,
            "max_score": max([r["overall_score"] for r in reports]) if reports else None,
            "avg_score": float(np.mean([r["overall_score"] for r in reports])) if reports else None,
            "reports": reports
        }

        if out_file:
            try:
                with open(out_file, "w", encoding="utf-8") as fh:
                    json.dump(summary, fh, indent=2, ensure_ascii=False)
            except Exception:
                pass

        return summary


# -------------------------
# Quick test/demo (not run on import)
# -------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Quality Scorer demo")
    parser.add_argument("--files", nargs="+", help="Audio files to score", required=True)
    parser.add_argument("--out", help="Output JSON report path", default="quality_report.json")
    args = parser.parse_args()
    scorer = QualityScorer()
    report = scorer.generate_batch_report(args.files, out_file=args.out)
    print(f"Saved report to {args.out}")
