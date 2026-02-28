# backend/verify_env.py
import sys
import torch

print("Python:", sys.version.split()[0])
print("Torch version:", getattr(torch, "__version__", "not installed"))
print("CUDA available:", torch.cuda.is_available())
try:
    import audiocraft
    print("audiocraft imported:", audiocraft.__version__)
except Exception as e:
    print("audiocraft import error:", e)
