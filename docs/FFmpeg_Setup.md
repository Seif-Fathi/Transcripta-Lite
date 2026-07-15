### Downloads

- [Windows – Official Build (Gyan.dev)](https://www.gyan.dev/ffmpeg/builds/)

- [macOS – Homebrew / Evermeet](https://evermeet.cx/ffmpeg/)

- [Linux – Official FFmpeg Downloads](https://ffmpeg.org/download.html)

# FFmpeg Setup Guide

Transcripta Lite requires **FFmpeg** for audio conversion, playback, and metadata extraction (ffprobe).
This guide explains step-by-step installation for **Windows**, **macOS**, and **Linux**, and how to add FFmpeg to your system `PATH`.



## Windows (step‑by‑step)

### 1) Download a build
- Recommended: Gyan's static builds  
  https://www.gyan.dev/ffmpeg/builds/  
- Click **"Release builds"** and download **ffmpeg-release-full.7z** .

### 2) Extract files
- Extract the ZIP to a permanent location, for example:
  ```
  C:\ffmpeg\
  ```
- After extraction you should have:
  ```
  C:\ffmpeg\bin\ffmpeg.exe
  C:\ffmpeg\bin\ffprobe.exe
  ```

### 3) Add FFmpeg to PATH (Windows 10 / 11)
1. Press `Win` and type **"Environment Variables"** → open **Edit the system environment variables**.  
2. Click **Environment Variables...**.  
3. Under **System variables**, select `Path` → **Edit...**.  
4. Click **New** and add the full path to FFmpeg `bin`, e.g.:
   ```
   C:\ffmpeg\bin
   ```
5. Click **OK** to close all dialogs.  
6. **Important:** Close and reopen any Command Prompt / PowerShell / IDE (VS Code, Spyder) to pick up the PATH change.

### 4) Verify
Open Command Prompt and run:
```bash
ffmpeg -version
ffprobe -version
```

If the commands show version info, installation succeeded.

---

## macOS (Homebrew recommended)

### 1) Install Homebrew (if not installed)
Open Terminal and run:
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

### 2) Install FFmpeg via Homebrew
```bash
brew update
brew install ffmpeg
```

Homebrew handles PATH configuration automatically.

### 3) Verify
```bash
ffmpeg -version
ffprobe -version
```

---

## Linux (Ubuntu / Debian / Fedora / Arch)

### Ubuntu / Debian
```bash
sudo apt update
sudo apt install ffmpeg
```

### Fedora
```bash
sudo dnf install ffmpeg
```

### Arch / Manjaro
```bash
sudo pacman -S ffmpeg
```

If your distribution does not provide FFmpeg in the default repositories, follow instructions at the official download page: https://ffmpeg.org/download.html

### Verify
```bash
ffmpeg -version
ffprobe -version
```

---

## Manual PATH update (if needed)

### Windows
Follow the Windows section above (Environment Variables → Path → add `...\\bin`), then restart terminal/IDE.

### macOS / Linux (bash/zsh)
If `ffmpeg` is installed in a custom location (e.g., `/opt/ffmpeg/bin`), add it to your shell profile.

For `bash` (~/.bashrc or ~/.bash_profile):
```bash
export PATH="/opt/ffmpeg/bin:$PATH"
```

For `zsh` (~/.zshrc):
```bash
export PATH="/opt/ffmpeg/bin:$PATH"
```

After editing the file, reload the shell:
```bash
source ~/.bashrc
# or
source ~/.zshrc
```

---

## Troubleshooting

- **'ffmpeg' is not recognized / command not found**  
  → Ensure the `bin` path is added to PATH and restart the terminal/IDE.

- **ffprobe missing**  
  → Use a full build (static) that includes `ffprobe`. Avoid minimal or partial builds.

- **Permission denied (Linux/macOS)**  
  → Ensure `ffmpeg` binary has execute permission:
  ```bash
  chmod +x /path/to/ffmpeg
  ```

- **Windows: long path or spaces**  
  → Use the full path without quotes when adding to PATH; subprocess calls should pass command and arguments as a list to avoid quoting issues.


---

## Quick check from Python (inside your app)
You can programmatically verify FFmpeg availability:

```python
import subprocess

def ffmpeg_available():
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        subprocess.run(["ffprobe", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception:
        return False
ffmpeg_available()
```

If this returns `False`, show a friendly message in the app pointing users to `docs/FFmpeg_Setup.md`.

---

## References
- Official FFmpeg: https://ffmpeg.org/download.html  
- Windows builds (Gyan): https://www.gyan.dev/ffmpeg/builds/  
- macOS Homebrew: https://brew.sh
