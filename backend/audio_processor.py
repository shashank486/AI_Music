# backend/audio_processor.py

"""
Advanced Audio Post-Processing Suite

Provides comprehensive audio enhancement, format conversion, and analysis tools
for music generation pipeline.
"""

import os
import numpy as np
import librosa
import soundfile as sf
import scipy.signal
from scipy.ndimage import uniform_filter1d
from pydub import AudioSegment
from pydub.effects import normalize, compress_dynamic_range
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
import warnings
from pathlib import Path
import json
from typing import Dict, List, Tuple, Optional, Union, Any
import tempfile


class AudioProcessor:
    """
    Advanced audio processing suite with effects, format conversion, and analysis.
    """
    
    def __init__(self, sample_rate: int = 32000):
        """
        Initialize AudioProcessor.
        
        Args:
            sample_rate: Default sample rate for audio processing
        """
        self.sample_rate = sample_rate
        self.supported_formats = ['.wav', '.mp3', '.flac', '.ogg', '.m4a']
        
    def enhance_audio(self, audio_file: str, 
                     output_file: Optional[str] = None,
                     effects_config: Optional[Dict[str, Any]] = None) -> str:
        """
        Main entry point for audio enhancement.
        
        Args:
            audio_file: Path to input audio file
            output_file: Path to output file (optional)
            effects_config: Dictionary of effects to apply
            
        Returns:
            Path to enhanced audio file
        """
        if effects_config is None:
            effects_config = self._get_default_effects_config()
            
        # Load audio
        audio, sr = librosa.load(audio_file, sr=self.sample_rate)
        
        # Apply effects
        enhanced_audio = self._apply_effects(audio, sr, effects_config)
        
        # Save enhanced audio
        if output_file is None:
            output_file = self._generate_output_path(audio_file, "_enhanced")
            
        sf.write(output_file, enhanced_audio, sr)
        
        return output_file
    
    def _get_default_effects_config(self) -> Dict[str, Any]:
        """Get default effects configuration."""
        return {
            'noise_reduction': True,
            'eq_adjustment': True,
            'compression': True,
            'reverb': False,
            'delay': False,
            'stereo_widening': False,
            'limiter': True,
            'mastering': True
        }
    
    def _apply_effects(self, audio: np.ndarray, sr: int, 
                      config: Dict[str, Any]) -> np.ndarray:
        """Apply configured effects to audio."""
        processed = audio.copy()
        
        # Noise Reduction
        if config.get('noise_reduction', False):
            processed = self._apply_noise_reduction(processed)
            
        # EQ Adjustment
        if config.get('eq_adjustment', False):
            processed = self._apply_eq_adjustment(processed, sr)
            
        # Compression
        if config.get('compression', False):
            processed = self._apply_compression(processed)
            
        # Reverb
        if config.get('reverb', False):
            processed = self._apply_reverb(processed, sr)
            
        # Delay
        if config.get('delay', False):
            processed = self._apply_delay(processed, sr)
            
        # Stereo Widening
        if config.get('stereo_widening', False) and len(processed.shape) > 1:
            processed = self._apply_stereo_widening(processed)
            
        # Limiter
        if config.get('limiter', False):
            processed = self._apply_limiter(processed)
            
        # Mastering
        if config.get('mastering', False):
            processed = self._apply_mastering(processed)
            
        return processed
    
    def _apply_noise_reduction(self, audio: np.ndarray) -> np.ndarray:
        """Apply noise reduction using spectral subtraction."""
        # Simple spectral subtraction
        stft = librosa.stft(audio)
        magnitude = np.abs(stft)
        phase = np.angle(stft)
        
        # Estimate noise from first 0.5 seconds
        noise_frames = int(0.5 * self.sample_rate / 512)  # hop_length default
        noise_profile = np.mean(magnitude[:, :noise_frames], axis=1, keepdims=True)
        
        # Apply spectral subtraction
        alpha = 2.0  # Over-subtraction factor
        clean_magnitude = magnitude - alpha * noise_profile
        clean_magnitude = np.maximum(clean_magnitude, 0.1 * magnitude)
        
        # Reconstruct audio
        clean_stft = clean_magnitude * np.exp(1j * phase)
        clean_audio = librosa.istft(clean_stft)
        
        return clean_audio
    
    def _apply_eq_adjustment(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """Apply EQ adjustment for better frequency balance."""
        # Simple 3-band EQ (low, mid, high)
        
        # Low shelf: boost bass slightly
        sos_low = scipy.signal.butter(2, 200, btype='low', fs=sr, output='sos')
        low_band = scipy.signal.sosfilt(sos_low, audio)
        audio = audio + 0.1 * low_band  # 10% boost
        
        # High shelf: add sparkle
        sos_high = scipy.signal.butter(2, 8000, btype='high', fs=sr, output='sos')
        high_band = scipy.signal.sosfilt(sos_high, audio)
        audio = audio + 0.05 * high_band  # 5% boost
        
        return audio
    
    def _apply_compression(self, audio: np.ndarray, 
                          threshold: float = -20.0, ratio: float = 4.0,
                          attack: float = 0.003, release: float = 0.1) -> np.ndarray:
        """Apply dynamic range compression."""
        # Convert to dB
        audio_db = 20 * np.log10(np.abs(audio) + 1e-10)
        
        # Apply compression curve
        compressed_db = np.where(
            audio_db > threshold,
            threshold + (audio_db - threshold) / ratio,
            audio_db
        )
        
        # Convert back to linear, preserving sign
        compressed_audio = np.sign(audio) * (10 ** (compressed_db / 20))
        
        return compressed_audio
    
    def _apply_reverb(self, audio: np.ndarray, sr: int, 
                     room_size: float = 0.3, damping: float = 0.5) -> np.ndarray:
        """Apply reverb effect using convolution with impulse response."""
        # Generate simple impulse response
        duration = 2.0  # 2 second reverb tail
        decay = np.exp(-damping * np.linspace(0, duration * sr, int(duration * sr)))
        impulse = np.random.normal(0, 0.1, len(decay)) * decay * room_size
        impulse[0] = 1.0  # Dry signal
        
        # Apply convolution reverb
        reverb_audio = scipy.signal.fftconvolve(audio, impulse, mode='same')
        
        # Mix dry and wet signals
        return audio + 0.3 * reverb_audio
    
    def _apply_delay(self, audio: np.ndarray, sr: int,
                    delay_time: float = 0.25, feedback: float = 0.3) -> np.ndarray:
        """Apply delay/echo effect."""
        delay_samples = int(delay_time * sr)
        delayed = np.zeros_like(audio)
        
        if len(delayed) > delay_samples:
            delayed[delay_samples:] = audio[:-delay_samples] * feedback
            delayed[:delay_samples] = 0
            
        return audio + delayed
    
    def _apply_stereo_widening(self, stereo_audio: np.ndarray) -> np.ndarray:
        """Apply stereo widening effect."""
        if stereo_audio.shape[1] < 2:
            return stereo_audio
            
        left = stereo_audio[:, 0]
        right = stereo_audio[:, 1]
        
        # Mid/Side processing for widening
        mid = (left + right) / 2
        side = (left - right) / 2
        
        # Widen side signal
        widened_side = side * 1.5
        
        # Recombine
        new_left = mid + widened_side
        new_right = mid - widened_side
        
        return np.column_stack([new_left, new_right])
    
    def _apply_limiter(self, audio: np.ndarray, threshold: float = -0.1) -> np.ndarray:
        """Apply brickwall limiter to prevent clipping."""
        # Convert to dB
        audio_db = 20 * np.log10(np.abs(audio) + 1e-10)
        
        # Apply hard limiting
        limited_db = np.minimum(audio_db, threshold)
        
        # Convert back to linear
        limited_audio = np.sign(audio) * (10 ** (limited_db / 20))
        
        return limited_audio
    
    def _apply_mastering(self, audio: np.ndarray) -> np.ndarray:
        """Apply mastering chain (EQ + compression + limiting)."""
        # Multi-band compression simulation
        # Low band
        sos_low = scipy.signal.butter(4, 250, btype='low', fs=self.sample_rate, output='sos')
        low = scipy.signal.sosfilt(sos_low, audio)
        
        # Mid band
        sos_mid = scipy.signal.butter(4, [250, 4000], btype='band', fs=self.sample_rate, output='sos')
        mid = scipy.signal.sosfilt(sos_mid, audio)
        
        # High band
        sos_high = scipy.signal.butter(4, 4000, btype='high', fs=self.sample_rate, output='sos')
        high = scipy.signal.sosfilt(sos_high, audio)
        
        # Gentle compression on each band
        low_comp = self._apply_compression(low, threshold=-15, ratio=2.0)
        mid_comp = self._apply_compression(mid, threshold=-12, ratio=3.0)
        high_comp = self._apply_compression(high, threshold=-10, ratio=2.5)
        
        # Recombine
        mastered = low_comp + mid_comp + high_comp
        
        # Final limiting
        mastered = self._apply_limiter(mastered, threshold=-1.0)
        
        return mastered
    

    def convert_format(self, input_file: str, output_format: str,
                      quality_settings: Optional[Dict[str, Any]] = None) -> str:
        """
        Convert audio to different format with quality settings.
        
        Args:
            input_file: Path to input audio file
            output_format: Target format ('mp3', 'wav', 'flac', 'ogg')
            quality_settings: Format-specific quality settings
            
        Returns:
            Path to converted file
        """
        if quality_settings is None:
            quality_settings = self._get_default_quality_settings(output_format)
            
        # Generate output filename
        input_path = Path(input_file)
        output_file = str(input_path.parent / f"{input_path.stem}_converted.{output_format}")
        
        # Check if input file exists
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
            
        # Load audio
        try:
            audio_data, sr = sf.read(input_file)
        except Exception as e:
            raise ValueError(f"Failed to read audio file {input_file}: {e}")
        
        # Apply quality settings with error handling
        try:
            if output_format.lower() == 'mp3':
                self._save_mp3(audio_data, sr, output_file, quality_settings)
            elif output_format.lower() == 'flac':
                self._save_flac(audio_data, sr, output_file, quality_settings)
            elif output_format.lower() == 'ogg':
                self._save_ogg(audio_data, sr, output_file, quality_settings)
            else:  # wav
                self._save_wav(audio_data, sr, output_file, quality_settings)
        except FileNotFoundError as e:
            if 'ffmpeg' in str(e).lower():
                raise RuntimeError(
                    f"FFmpeg is required for {output_format.upper()} conversion but not found. "
                    f"Please install FFmpeg: brew install ffmpeg (macOS) or apt-get install ffmpeg (Linux)"
                ) from e
            else:
                raise
        except Exception as e:
            raise RuntimeError(f"Failed to convert to {output_format}: {e}") from e
            
        return output_file
    
    def _get_default_quality_settings(self, format_type: str) -> Dict[str, Any]:
        """Get default quality settings for format."""
        settings = {
            'wav': {'subtype': 'PCM_16'},
            'mp3': {'bitrate': '320k'},
            'flac': {'compression_level': 5},
            'ogg': {'quality': 5}
        }
        return settings.get(format_type.lower(), {})
    

    def _save_mp3(self, audio_data: np.ndarray, sr: int, 
                  output_file: str, settings: Dict[str, Any]) -> None:
        """Save audio as MP3."""
        # Ensure audio is in the correct format for pydub
        if audio_data.dtype != np.int16:
            # Normalize and convert to int16
            audio_data = np.clip(audio_data, -1.0, 1.0)
            audio_data = (audio_data * 32767).astype(np.int16)
        
        # Determine channels
        channels = 1 if len(audio_data.shape) == 1 else audio_data.shape[1]
        
        audio_segment = AudioSegment(
            audio_data.tobytes(),
            frame_rate=sr,
            sample_width=2,  # 16-bit
            channels=channels
        )
        
        bitrate = settings.get('bitrate', '320k')
        audio_segment.export(output_file, format="mp3", bitrate=bitrate)
    


    def _save_flac(self, audio_data: np.ndarray, sr: int,
                   output_file: str, settings: Dict[str, Any]) -> None:
        """Save audio as FLAC."""
        compression_level = settings.get('compression_level', 0.5)
        # Ensure compression level is in valid range [0, 1]
        compression_level = max(0.0, min(1.0, compression_level))
        # Use correct subtype for FLAC
        sf.write(output_file, audio_data, sr, format='FLAC', 
                compression_level=compression_level)
    

    def _save_ogg(self, audio_data: np.ndarray, sr: int,
                  output_file: str, settings: Dict[str, Any]) -> None:
        """Save audio as OGG."""
        # Convert to int16 for pydub compatibility
        if audio_data.dtype != np.int16:
            audio_data = np.clip(audio_data, -1.0, 1.0)
            audio_data = (audio_data * 32767).astype(np.int16)
        
        channels = 1 if len(audio_data.shape) == 1 else audio_data.shape[1]
        
        audio_segment = AudioSegment(
            audio_data.tobytes(),
            frame_rate=sr,
            sample_width=2,  # 16-bit
            channels=channels
        )
        
        # pydub doesn't have 'quality' parameter for OGG, use bitrate instead
        bitrate = settings.get('bitrate', '128k')
        audio_segment.export(output_file, format="ogg", bitrate=bitrate)
    
    def _save_wav(self, audio_data: np.ndarray, sr: int,
                  output_file: str, settings: Dict[str, Any]) -> None:
        """Save audio as WAV."""
        subtype = settings.get('subtype', 'PCM_16')
        sf.write(output_file, audio_data, sr, subtype=subtype)
    


    def embed_metadata(self, audio_file: str, metadata: Dict[str, Any]) -> str:
        """
        Embed metadata into audio file.
        
        Args:
            audio_file: Path to audio file
            metadata: Dictionary of metadata to embed
            
        Returns:
            Path to file with embedded metadata
        """
        try:
            # Load audio data
            audio_data, sr = sf.read(audio_file)
            
            # Create output filename
            input_path = Path(audio_file)
            output_file = str(input_path.parent / f"{input_path.stem}_with_metadata{input_path.suffix}")
            
            # For WAV files, try to use soundfile's metadata support (version dependent)
            if audio_file.lower().endswith('.wav'):
                try:
                    # Try newer API first
                    sf.write(output_file, audio_data, sr, metadata=metadata)
                except TypeError:
                    # Fallback to older API - copy file and warn
                    import shutil
                    shutil.copy2(audio_file, output_file)
                    warnings.warn(f"Metadata embedding not supported in this soundfile version. Copied file without metadata.")
            else:
                # For other formats, copy the file and warn about metadata limitation
                import shutil
                shutil.copy2(audio_file, output_file)
                warnings.warn(f"Metadata embedding limited to WAV format. Copied file without metadata.")
            
            return output_file
        except Exception as e:
            warnings.warn(f"Failed to embed metadata: {e}")
            return audio_file
    
    def analyze_audio(self, audio_file: str) -> Dict[str, Any]:
        """
        Perform comprehensive audio analysis.
        
        Args:
            audio_file: Path to audio file
            
        Returns:
            Dictionary containing analysis results
        """
        # Load audio
        y, sr = librosa.load(audio_file, sr=self.sample_rate)
        
        analysis = {}
        
        # Basic features
        analysis['duration'] = len(y) / sr
        analysis['sample_rate'] = sr
        analysis['channels'] = 1 if len(y.shape) == 1 else y.shape[1]
        
        # Spectral analysis
        analysis['spectral_analysis'] = self._spectral_analysis(y, sr)
        
        # Beat detection
        analysis['beat_analysis'] = self._beat_detection(y, sr)
        
        # Key detection
        analysis['key_analysis'] = self._key_detection(y, sr)
        
        # Loudness analysis
        analysis['loudness_analysis'] = self._loudness_analysis(y)
        
        return analysis
    
    def _spectral_analysis(self, y: np.ndarray, sr: int) -> Dict[str, Any]:
        """Perform spectral analysis."""
        # Compute spectrogram
        D = librosa.stft(y)
        magnitude = np.abs(D)
        
        # Spectral features
        spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
        spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
        
        # Zero crossing rate
        zcr = librosa.feature.zero_crossing_rate(y)[0]
        
        return {
            'spectral_centroid_mean': float(np.mean(spectral_centroids)),
            'spectral_centroid_std': float(np.std(spectral_centroids)),
            'spectral_rolloff_mean': float(np.mean(spectral_rolloff)),
            'spectral_rolloff_std': float(np.std(spectral_rolloff)),
            'spectral_bandwidth_mean': float(np.mean(spectral_bandwidth)),
            'spectral_bandwidth_std': float(np.std(spectral_bandwidth)),
            'zero_crossing_rate_mean': float(np.mean(zcr)),
            'zero_crossing_rate_std': float(np.std(zcr))
        }
    
    def _beat_detection(self, y: np.ndarray, sr: int) -> Dict[str, Any]:
        """Detect beat and tempo information."""
        try:
            # Compute beat track
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
            
            return {
                'tempo': float(tempo),
                'beat_count': len(beats),
                'beat_positions': beats.tolist()
            }
        except Exception as e:
            warnings.warn(f"Beat detection failed: {e}")
            return {'tempo': 120.0, 'beat_count': 0, 'beat_positions': []}
    
    def _key_detection(self, y: np.ndarray, sr: int) -> Dict[str, Any]:
        """Detect musical key."""
        try:
            # Compute chromagram
            chroma = librosa.feature.chroma_stft(y=y, sr=sr)
            chroma_mean = np.mean(chroma, axis=1)
            
            # Key estimation (simplified)
            key_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            estimated_key = key_names[np.argmax(chroma_mean)]
            
            return {
                'estimated_key': estimated_key,
                'key_strength': float(np.max(chroma_mean) / np.mean(chroma_mean))
            }
        except Exception as e:
            warnings.warn(f"Key detection failed: {e}")
            return {'estimated_key': 'C', 'key_strength': 1.0}
    
    def _loudness_analysis(self, y: np.ndarray) -> Dict[str, Any]:
        """Analyze loudness characteristics."""
        # Compute RMS energy
        rms = librosa.feature.rms(y=y)[0]
        
        # Compute dynamic range
        dynamic_range = np.max(rms) - np.min(rms)
        
        return {
            'rms_mean': float(np.mean(rms)),
            'rms_std': float(np.std(rms)),
            'dynamic_range': float(dynamic_range),
            'peak_level': float(np.max(np.abs(y)))
        }
    
    def generate_spectrogram(self, audio_file: str, output_image: str) -> str:
        """
        Generate spectrogram visualization.
        
        Args:
            audio_file: Path to audio file
            output_image: Path to output image file
            
        Returns:
            Path to generated spectrogram image
        """
        # Load audio
        y, sr = librosa.load(audio_file, sr=self.sample_rate)
        
        # Compute spectrogram
        D = librosa.amplitude_to_db(np.abs(librosa.stft(y)), ref=np.max)
        
        # Create plot
        plt.figure(figsize=(12, 8))
        librosa.display.specshow(D, sr=sr, x_axis='time', y_axis='hz')
        plt.colorbar(format='%+2.0f dB')
        plt.title('Spectrogram')
        plt.xlabel('Time (s)')
        plt.ylabel('Frequency (Hz)')
        
        # Save plot
        plt.savefig(output_image, dpi=300, bbox_inches='tight')
        plt.close()
        
        return output_image
    
    def _generate_output_path(self, input_file: str, suffix: str) -> str:
        """Generate output file path with suffix."""
        input_path = Path(input_file)
        return str(input_path.parent / f"{input_path.stem}{suffix}{input_path.suffix}")

    def apply_effects(self, audio_path, effects, preview=False):
        """
        Apply audio effects to the given audio file.

        Args:
            audio_path (str): Path to the input audio file
            effects (dict): Dictionary of effect parameters
            preview (bool): Whether this is a preview (faster processing)

        Returns:
            str: Path to the processed audio file
        """
        try:
            # Convert effects dict to config format expected by enhance_audio
            effects_config = {
                'noise_reduction': effects.get('noise_reduction', 0.0) > 0.0,
                'eq_adjustment': any(effects.get(key, 0.0) != 0.0 for key in ['eq_low', 'eq_mid', 'eq_high']),
                'compression': effects.get('compression', 0.0) > 0.0,
                'reverb': effects.get('reverb', 0.0) > 0.0,
                'delay': effects.get('delay', 0.0) > 0.0,
                'stereo_widening': effects.get('stereo_widening', 0.0) > 0.0,
                'limiter': effects.get('limiter', 0.0) > 0.0,
                'mastering': effects.get('mastering', 0.0) > 0.0
            }

            # Create output path
            output_dir = Path("temp_audio")
            output_dir.mkdir(exist_ok=True)

            if preview:
                output_name = f"preview_{int(np.random.randint(10000, 99999))}.wav"
            else:
                output_name = f"processed_{int(np.random.randint(10000, 99999))}.wav"

            output_path = output_dir / output_name

            # Use the existing enhance_audio method
            processed_path = self.enhance_audio(
                audio_path,
                output_file=str(output_path),
                effects_config=effects_config
            )

            return processed_path

        except Exception as e:
            raise Exception(f"Failed to apply effects: {str(e)}")

    def export_audio(self, audio_path, format="wav", quality="high"):
        """
        Export audio in the specified format.

        Args:
            audio_path (str): Path to the audio file to export
            format (str): Export format ('wav', 'mp3')
            quality (str): Quality level ('high', 'medium', 'low')

        Returns:
            str: Path to the exported file
        """
        try:
            # Map quality to format-specific settings
            quality_settings = {}
            if format.lower() == 'mp3':
                if quality == 'high':
                    quality_settings['bitrate'] = '320k'
                elif quality == 'medium':
                    quality_settings['bitrate'] = '192k'
                else:  # low
                    quality_settings['bitrate'] = '128k'
            elif format.lower() == 'flac':
                if quality == 'high':
                    quality_settings['compression_level'] = 8
                elif quality == 'medium':
                    quality_settings['compression_level'] = 5
                else:  # low
                    quality_settings['compression_level'] = 0
            elif format.lower() == 'ogg':
                if quality == 'high':
                    quality_settings['bitrate'] = '256k'
                elif quality == 'medium':
                    quality_settings['bitrate'] = '128k'
                else:  # low
                    quality_settings['bitrate'] = '64k'
            # For wav, quality doesn't apply

            # Use the existing convert_format method
            exported_path = self.convert_format(
                audio_path,
                output_format=format.lower(),
                quality_settings=quality_settings
            )

            return exported_path

        except Exception as e:
            raise Exception(f"Failed to export audio: {str(e)}")


# Convenience functions for easy integration

def process_audio_file(audio_file: str, output_dir: Optional[str] = None,
                      effects_config: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """
    Process audio file with all enhancement features.
    
    Args:
        audio_file: Path to input audio file
        output_dir: Directory for output files (defaults to input directory)
        effects_config: Effects configuration
        
    Returns:
        Dictionary with paths to processed files
    """
    processor = AudioProcessor()
    
    if output_dir is None:
        output_dir = str(Path(audio_file).parent)
    
    results = {}
    
    # Enhanced audio
    enhanced_file = processor.enhance_audio(
        audio_file, 
        output_file=str(Path(output_dir) / f"{Path(audio_file).stem}_enhanced.wav"),
        effects_config=effects_config
    )
    results['enhanced'] = enhanced_file
    
    # Format conversions with default quality settings
    formats = ['mp3', 'flac', 'ogg']
    for fmt in formats:
        converted_file = processor.convert_format(
            enhanced_file, 
            output_format=fmt
        )
        results[f'{fmt}'] = converted_file
    
    # Audio analysis
    analysis = processor.analyze_audio(enhanced_file)
    analysis_file = str(Path(output_dir) / f"{Path(audio_file).stem}_analysis.json")
    with open(analysis_file, 'w') as f:
        json.dump(analysis, f, indent=2)
    results['analysis'] = analysis_file
    
    # Spectrogram
    spectrogram_file = str(Path(output_dir) / f"{Path(audio_file).stem}_spectrogram.png")
    processor.generate_spectrogram(enhanced_file, spectrogram_file)
    results['spectrogram'] = spectrogram_file
    
    return results
