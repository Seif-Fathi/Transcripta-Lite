# How to Check if You Have a GPU (and Its Name)

This guide explains how to verify whether your computer has a **GPU** (graphics card) — and what its name is — on **Windows**, **macOS**, or **Linux**.  
You will also learn how to check your **CPU** model if no GPU is found.


---

## 1. Open the Terminal

### 🪟 Windows
- Press **Win + R**, type `cmd`, and press **Enter**.  
  or search for **Command Prompt** or **PowerShell** from the Start Menu.

### macOS
- Open **Launchpad → Other → Terminal**,  
  or press **Cmd + Space** → type `Terminal` → Enter.

### Linux
- Press **Ctrl + Alt + T**,  
  or open **Terminal** from your application menu.

---

## 2. Check GPU/CPU Using a System Command

Run one of the following commands depending on your operating system:

## Windows 
**copy and past this in the terminal**
```bash
wmic path win32_VideoController get name
```

- This will display your graphics cards (e.g., NVIDIA GeForce RTX 3060 or Intel UHD Graphics).

**To check your CPU:**
wmic cpu get name

## MacOS
**Gpu:**
**copy and past**
system_profiler SPDisplaysDataType | grep "Chipset Model"

**Cpu:**
sysctl -n machdep.cpu.brand_string

## Linux 
**Gpu** 
lspci | grep -i vga
**or**
nvidia-smi

**CPU**
lscpu | grep "Model name"

**If you prefer to check directly using Python, run this code from your terminal or IDE:**
```bash
python Get_Gpu_Cpu_Names.py
```

## Notes

- Transcripta Lite automatically detects your GPU at startup.
- If you see “No GPU detected,” the app will still run smoothly on CPU (just slower).
- You can re-run any of these checks anytime.