from backend.input_processor import InputProcessor

ip = InputProcessor(api_key=None)   # FORCE fallback mode for testing

tests = [
    "I need energetic music for my workout",
    "Something calming for meditation",
    "Happy birthday party music",
    "Sad breakup song",
    "Focus music for studying",
    "Romantic slow dance music",
    "Dark cinematic atmosphere",
    "Fast EDM festival track",
    "Lo-fi beats for coding",
    "Guitar-based emotional melody"
]

for t in tests:
    print("\nInput:", t)
    print("Output:", ip.process_input(t))
