import sys
import torch
import os

print(f"Python Implementation: {sys.implementation.name}")
print(f"Python Version: {sys.version}")
print(f"Executable: {sys.executable}")
print(f"PyTorch Version: {torch.__version__}")
print(f"CUDA Available: {torch.cuda.is_available()}")
print(f"CUDA Version (Torch build): {torch.version.cuda}")
if torch.cuda.is_available():
    print(f"Device Name: {torch.cuda.get_device_name(0)}")
else:
    print("CUDA is NOT available.")

print(f"Environment: {os.environ.get('VIRTUAL_ENV', 'Not inside a virtualenv')}")
