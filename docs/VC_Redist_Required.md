# Microsoft Visual C++ Redistributable — Required for Windows Users

Some core components used by **Transcripta Lite** (such as **PyTorch**, **PyQt5**, audio processing libraries, and several system-level DLLs) depend on Microsoft’s *Visual C++ runtime libraries*.  
Without these libraries, the application may show errors like:

- `msvcp140.dll not found`
- `vcruntime140.dll is missing`
- `The code execution cannot proceed`
- Torch / CUDA DLL initialization failures

Installing the **latest Microsoft Visual C++ Redistributable** package solves all these issues.

---

# What Is It?

**Microsoft Visual C++ Redistributable** provides essential runtime components needed by many modern applications.  
It is safe, official, and required by many Python libraries.

---

#Step-by-Step Installation Guide (Windows 10 / 11)

## 1. Download the Installer

### **Official Microsoft Link (64-bit):**  
https://aka.ms/vs/17/release/vc_redist.x64.exe

> Always download from the official Microsoft website only.

---

## 2. Run the Installer

After downloading:

1. Double-click the file:  
   **vc_redist.x64.exe**
2. Click **“I agree to the license terms and conditions”**
3. Click **Install**
4. Wait for installation to complete
5. Click **Close**

---

## 3. Restart Your Computer

A restart is **strongly recommended** so Windows can properly register all DLLs.

---

# 4. Verify Installation (Optional)

To ensure the installation succeeded:

1. Open **Control Panel**
2. Go to **Programs → Programs and Features**
3. Look for: Microsoft Visual C++ 2015-2022 Redistributable (x64)


If it's there → you're ready to use Transcripta Lite.

---

# Common Problems Solved by Installing VC++ Redist

Installing this package fixes:

| Error Message | Meaning |
|---------------|---------|
| `msvcp140.dll missing` | Missing C++ runtime library |
| `vcruntime140.dll not found` | Missing core runtime used by PyQt and Torch |
| `DLL load failed` | Runtime dependencies not found |
| PyTorch initialization error | Missing low-level MSVC runtime files |
| FFmpeg cannot run | Missing MSVC DLL dependencies |

---

# Notes

- This package is **not optional** for Windows users.  
- You only need to install it **once**.  
- It does **not** require internet after installation.  
- It is fully compatible with Python 3.10 and all Transcripta Lite dependencies.

---

# You Are Ready to Use Transcripta Lite

After installing Visual C++ Redistributable and restarting your system,  
you can run: run_transcripta.bat

or launch the application normally without DLL errors.

