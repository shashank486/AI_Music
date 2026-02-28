from backend.input_processor import InputProcessor
from backend.generate import generate_from_payload

ip = InputProcessor()

user_text = "calming music with piano for meditation"

print("Extracting parameters...")
params = ip.process_input(user_text)
print(params)

payload = {
    "prompt": f"{params['mood']} {params['style']} music with {', '.join(params['instruments'])}",
    "duration": 8,
    "outfile": "test_full_pipeline.wav"
}

print("Generating audio...")
path = generate_from_payload(payload)
print("Saved:", path)
