"""
Transcripta
Copyright (c) 2025 Eldeen Seif Fathi
Licensed under a commercial one-time license.
"""


import platform, subprocess

print("=== System Hardware Check ===")
try:
    import torch
    if torch.cuda.is_available():
        print("GPU Detected ✔")
        print("Device Name:", torch.cuda.get_device_name(0))
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        print("Apple GPU (Metal/MPS) Detected ✔")
    else:
        print("No GPU detected.")
except Exception:
    print("Torch not installed or GPU not accessible. Checking system info...")

# Show CPU Commercial name
#print("CPU:", platform.processor() or 'unkown')


#Show CPU Technical Name
def get_cpu_name():
    system = platform.system()
    try:
        if system == "Windows":
            out = subprocess.check_output("wmic cpu get Name", shell=True).decode(errors="ignore").split("\n")[1].strip()
            return out or platform.processor()
        elif system == "Linux":
            out = subprocess.check_output("lscpu | grep 'Model name'", shell=True).decode(errors="ignore")
            return out.split(":")[1].strip()
        elif system == "Darwin":  # macOS
            out = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"]).decode().strip()
            return out
        else:
            return platform.processor()
    except Exception:
        return platform.processor() or "Unknown"
    
print("CPU:", get_cpu_name())
input("Press Enter to exit...")
