# backend/test_full_pipeline.py

from backend.full_pipeline import run_music_pipeline

print(run_music_pipeline(
    "Create calm ambient music with soft pads and piano for meditation.",
    "test_pipeline.wav"
))
