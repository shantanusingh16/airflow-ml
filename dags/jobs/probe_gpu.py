"""Probe job: confirm the GPU is visible inside a gpu_job_task() container.

Prints CUDA state + a tiny matmul on the GPU; exits 0 on success.
"""
import os

import torch

print(f"probe_gpu: torch {torch.__version__} | cuda available: {torch.cuda.is_available()}")
if not torch.cuda.is_available():
    raise SystemExit("CUDA not visible — container was started without a GPU")
print(f"probe_gpu: device = {torch.cuda.get_device_name(0)}")
a = torch.randn(1024, 1024, device="cuda", dtype=torch.float32)
b = a @ a
print(f"probe_gpu: matmul on GPU ok (sum={b.sum().item():.3f})")
print(f"probe_gpu: shm = {os.path.getsize('/dev/shm')} bytes")
print("PROBE GPU OK")