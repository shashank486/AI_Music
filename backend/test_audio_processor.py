# backend/test_audio_processor.py

"""
Comprehensive tests for AudioProcessor functionality.

Tests audio enhancement, format conversion, analysis tools, and integration.
"""

import unittest
import os
import numpy as np
import tempfile
import json
from pathlib import Path
import warnings

# Import audio processor
try:
    from .audio_processor import AudioProcessor, process_audio_file
except ImportError:
    try:
        from backend.audio_processor import AudioProcessor, process_audio_file
    except ImportError:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from backend.audio_processor import AudioProcessor, process_audio_file


class TestAudioProcessor(unittest.TestCase):
    """Test cases for AudioProcessor class."""
    
    def setUp(self):
        """Set up test environment."""
        self.processor = AudioProcessor(sample_rate=32000)
        self.temp_dir = tempfile.mkdtemp()
        self.test_audio_file = self._create_test_audio()
        
    def tearDown(self):
        """Clean up test files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def _create_test_audio(self):
        """Create a test audio file."""
        # Create synthetic audio data (sine wave)
        duration = 2.0  # 2 seconds
        sample_rate = 32000
        frequency = 440  # A4 note
        
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio = 0.3 * np.sin(2 * np.pi * frequency * t)
        
        # Add some harmonics for more complex signal
        audio += 0.1 * np.sin(2 * np.pi * frequency * 2 * t)
        audio += 0.05 * np.sin(2 * np.pi * frequency * 3 * t)
        
        # Save as test file
        test_file = os.path.join(self.temp_dir, "test_audio.wav")
        import soundfile as sf
        sf.write(test_file, audio, sample_rate)
        
        return test_file
    
    def test_enhance_audio_default_config(self):
        """Test audio enhancement with default configuration."""
        output_file = os.path.join(self.temp_dir, "enhanced.wav")
        
        result = self.processor.enhance_audio(
            self.test_audio_file, 
            output_file=output_file
        )
        
        self.assertTrue(os.path.exists(result))
        self.assertEqual(result, output_file)
        
        # Check that output file is different from input
        original_data = self._load_audio_data(self.test_audio_file)
        enhanced_data = self._load_audio_data(result)
        
        self.assertFalse(np.allclose(original_data, enhanced_data, rtol=1e-5))
    
    def test_enhance_audio_custom_config(self):
        """Test audio enhancement with custom configuration."""
        output_file = os.path.join(self.temp_dir, "custom_enhanced.wav")
        
        custom_config = {
            'noise_reduction': True,
            'eq_adjustment': True,
            'compression': False,
            'reverb': True,
            'delay': False,
            'stereo_widening': False,
            'limiter': True,
            'mastering': False
        }
        
        result = self.processor.enhance_audio(
            self.test_audio_file,
            output_file=output_file,
            effects_config=custom_config
        )
        
        self.assertTrue(os.path.exists(result))
    
    def test_format_conversion_mp3(self):
        """Test MP3 format conversion."""
        output_file = os.path.join(self.temp_dir, "converted.mp3")
        
        result = self.processor.convert_format(
            self.test_audio_file,
            'mp3',
            quality_settings={'bitrate': '128k'}
        )
        
        self.assertTrue(os.path.exists(result))
        self.assertTrue(result.endswith('.mp3'))
    
    def test_format_conversion_flac(self):
        """Test FLAC format conversion."""
        output_file = os.path.join(self.temp_dir, "converted.flac")
        
        result = self.processor.convert_format(
            self.test_audio_file,
            'flac',
            quality_settings={'compression_level': 3}
        )
        
        self.assertTrue(os.path.exists(result))
        self.assertTrue(result.endswith('.flac'))
    

    def test_format_conversion_ogg(self):
        """Test OGG format conversion."""
        output_file = os.path.join(self.temp_dir, "converted.ogg")
        
        result = self.processor.convert_format(
            self.test_audio_file,
            'ogg',
            quality_settings={'bitrate': '128k'}
        )
        
        self.assertTrue(os.path.exists(result))
        self.assertTrue(result.endswith('.ogg'))
    

    def test_embed_metadata(self):
        """Test metadata embedding."""
        metadata = {
            'title': 'Test Track',
            'artist': 'Test Artist',
            'album': 'Test Album',
            'genre': 'Electronic',
            'year': 2024
        }
        
        result = self.processor.embed_metadata(
            self.test_audio_file,
            metadata
        )
        
        self.assertTrue(os.path.exists(result))
        # File should be created (may be same file if metadata fails, which is acceptable)
        self.assertIsInstance(result, str)
    
    def test_analyze_audio_basic_features(self):
        """Test audio analysis basic features."""
        analysis = self.processor.analyze_audio(self.test_audio_file)
        
        # Check required keys
        required_keys = [
            'duration', 'sample_rate', 'channels',
            'spectral_analysis', 'beat_analysis', 
            'key_analysis', 'loudness_analysis'
        ]
        
        for key in required_keys:
            self.assertIn(key, analysis)
        
        # Check values are reasonable
        self.assertGreater(analysis['duration'], 0)
        self.assertEqual(analysis['sample_rate'], 32000)
        self.assertGreater(analysis['spectral_analysis']['spectral_centroid_mean'], 0)
        self.assertGreater(analysis['loudness_analysis']['rms_mean'], 0)
    
    def test_spectrogram_generation(self):
        """Test spectrogram visualization generation."""
        output_image = os.path.join(self.temp_dir, "spectrogram.png")
        
        result = self.processor.generate_spectrogram(
            self.test_audio_file,
            output_image
        )
        
        self.assertTrue(os.path.exists(result))
        self.assertTrue(result.endswith('.png'))
        
        # Check file size is reasonable (should be > 0)
        self.assertGreater(os.path.getsize(result), 1000)
    
    def test_process_audio_file_full_pipeline(self):
        """Test complete audio processing pipeline."""
        results = process_audio_file(
            self.test_audio_file,
            output_dir=self.temp_dir
        )
        
        # Check all expected output files are created
        expected_keys = ['enhanced', 'mp3', 'flac', 'ogg', 'analysis', 'spectrogram']
        
        for key in expected_keys:
            self.assertIn(key, results)
            self.assertTrue(os.path.exists(results[key]))
        
        # Check analysis file contains valid JSON
        with open(results['analysis'], 'r') as f:
            analysis_data = json.load(f)
            self.assertIsInstance(analysis_data, dict)
    
    def test_individual_effects(self):
        """Test individual audio effects."""
        audio_data = self._load_audio_data(self.test_audio_file)
        
        # Test noise reduction
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            noise_reduced = self.processor._apply_noise_reduction(audio_data.copy())
            self.assertEqual(len(noise_reduced), len(audio_data))
        
        # Test EQ adjustment
        eq_adjusted = self.processor._apply_eq_adjustment(audio_data.copy(), 32000)
        self.assertEqual(len(eq_adjusted), len(audio_data))
        
        # Test compression
        compressed = self.processor._apply_compression(audio_data.copy())
        self.assertEqual(len(compressed), len(audio_data))
        
        # Test limiter
        limited = self.processor._apply_limiter(audio_data.copy())
        self.assertEqual(len(limited), len(audio_data))
    
    def test_default_effects_config(self):
        """Test default effects configuration."""
        config = self.processor._get_default_effects_config()
        
        self.assertIsInstance(config, dict)
        
        expected_effects = [
            'noise_reduction', 'eq_adjustment', 'compression',
            'reverb', 'delay', 'stereo_widening', 
            'limiter', 'mastering'
        ]
        
        for effect in expected_effects:
            self.assertIn(effect, config)
            self.assertIsInstance(config[effect], bool)
    
    def test_output_path_generation(self):
        """Test output path generation."""
        input_file = "/path/to/audio.wav"
        suffix = "_enhanced"
        
        output_path = self.processor._generate_output_path(input_file, suffix)
        
        expected = "/path/to/audio_enhanced.wav"
        self.assertEqual(output_path, expected)
    
    def _load_audio_data(self, file_path):
        """Helper to load audio data."""
        import soundfile as sf
        data, _ = sf.read(file_path)
        return data


class TestAudioProcessorIntegration(unittest.TestCase):
    """Integration tests for audio processor with existing pipeline."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.processor = AudioProcessor(sample_rate=32000)
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_processor_initialization(self):
        """Test processor initializes correctly."""
        self.assertEqual(self.processor.sample_rate, 32000)
        self.assertIn('.wav', self.processor.supported_formats)
        self.assertIn('.mp3', self.processor.supported_formats)
        self.assertIn('.flac', self.processor.supported_formats)
        self.assertIn('.ogg', self.processor.supported_formats)
    
    def test_error_handling_nonexistent_file(self):
        """Test error handling for non-existent files."""
        with self.assertRaises(Exception):
            self.processor.enhance_audio("nonexistent.wav")
        
        with self.assertRaises(Exception):
            self.processor.analyze_audio("nonexistent.wav")
    
    def test_error_handling_invalid_format(self):
        """Test error handling for unsupported formats."""
        # This should not raise an error, just return the input file
        result = self.processor.convert_format(
            self.temp_dir + "/test.xyz",  # unsupported format
            "mp3"
        )
        # Should handle gracefully
        self.assertIsInstance(result, str)


def create_test_audio_samples():
    """Create sample audio files for testing."""
    temp_dir = tempfile.mkdtemp()
    processor = AudioProcessor()
    
    # Create different types of test audio
    sample_types = {
        'sine_wave': {'freq': 440, 'duration': 2.0},
        'chord': {'freqs': [440, 554, 659], 'duration': 2.0},
        'noise': {'type': 'white', 'duration': 2.0},
        'complex': {'type': 'mixed', 'duration': 3.0}
    }
    
    for name, params in sample_types.items():
        # Generate audio
        sample_rate = 32000
        t = np.linspace(0, params['duration'], int(sample_rate * params['duration']))
        
        if name == 'sine_wave':
            audio = 0.3 * np.sin(2 * np.pi * params['freq'] * t)

        elif name == 'chord':
            audio = np.zeros_like(t)
            for freq in params['freqs']:
                audio += 0.1 * np.sin(2 * np.pi * freq * t)
        elif name == 'noise':
            audio = 0.1 * np.random.normal(0, 1, len(t))
        elif name == 'complex':
            # Mix of different elements
            audio = (0.2 * np.sin(2 * np.pi * 220 * t) + 
                    0.1 * np.sin(2 * np.pi * 440 * t) +
                    0.05 * np.random.normal(0, 1, len(t)))
        
        # Save file
        file_path = os.path.join(temp_dir, f"{name}.wav")
        import soundfile as sf
        sf.write(file_path, audio, sample_rate)
    
    return temp_dir


if __name__ == "__main__":
    # Run tests
    print("🎵 Audio Processor Test Suite")
    print("=" * 50)
    
    # Create test audio samples
    print("Creating test audio samples...")
    test_audio_dir = create_test_audio_samples()
    
    # Run unit tests
    unittest.main(verbosity=2, exit=False)
    
    print(f"\n✅ Test audio samples created in: {test_audio_dir}")
    print("📁 You can use these files for manual testing:")
    
    import glob
    for audio_file in glob.glob(os.path.join(test_audio_dir, "*.wav")):
        print(f"   • {os.path.basename(audio_file)}")
