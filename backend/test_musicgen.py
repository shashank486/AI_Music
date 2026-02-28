# backend/test_musicgen.py

# from backend.generate import generate_music
from backend.generate import generate_music


prompts = [
    "Happy upbeat EDM beat with synths",
    "Sad cinematic piano melody",
    "Lo-fi chill beats with vinyl crackle",
    "Epic orchestral track with drums",
    "Relaxing meditation ambient music",
    "Romantic guitar with soft background strings",
    "Dark atmospheric soundtrack",
    "Funky groove with bass and drums"
]

for i, p in enumerate(prompts, 1):
    filename = f"test_{i}.wav"
    print("\nGenerating:", p)
    generate_music(p, duration=8, outfile=filename)
