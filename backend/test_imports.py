# backend/test_imports.py
try:
    import torch, torchaudio, audiocraft, soundfile, music21, pretty_midi
    print("All imports OK")
except Exception as e:
    print("Import error:", e)
