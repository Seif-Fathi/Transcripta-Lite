"""
Transcripta
Copyright (c) 2025 Seif Eldeen Fathi
Licensed under a commercial one-time license.
"""

"""
App Name: Transcripta
Enhanced import section with clean structure and robust error handling.

This block:
- Loads core Python libraries.
- Imports UI frameworks (customtkinter + PyQt5).
- Safely imports optional modules (torch, whisper, docx).
- Checks system compatibility.
"""
# ---------------------------
# Standard Library Imports
# ---------------------------
from AudioRecorder import AudioRecorder
from Lang import LANG_STRINGS , APP_NAME , WHISPER_LANGS
import os
import threading
import sys
import time
import subprocess
import platform
import tempfile
import importlib
from tkinter import filedialog, messagebox

# These are standard Python libraries used for file operations, threading,
# platform detection, temporary files, and GUI dialogs.

# ---------------------------
# Third-Party Libraries
# ---------------------------

# ---------------------------
# Safe Import Function
# ---------------------------
def safe_import(module_name, alias=None, required=False, install_hint=None):
    """
    Safely import a module, showing helpful hints if missing.

    Args:
        module_name (str): The name of the module to import.
        alias (str, optional): Custom alias variable name.
        required (bool): If True, raises ImportError when not found.
        install_hint (str, optional): Command to suggest installation.

    Returns:
        module | None: The imported module, or None if not available.
    """
    try:
        module = importlib.import_module(module_name)
        return module
    except ImportError as e:
        # Module is missing — prepare a clear diagnostic message.
        msg = f"[Missing] {module_name} not found."
        
        # Add installation hint if provided.
        if install_hint:
            msg += f" Install it using: {install_hint}"
        print(msg)

        # If it's required, stop the program to avoid runtime errors.
        if required:
            raise ImportError(msg) from e

        # If optional, continue running without this module.
        return None
    

# Import Torch (for CPU/GPU acceleration in Whisper).
torch = safe_import("torch", install_hint="pip install torch")
TORCH_AVAILABLE = torch is not None


# Import Whisper (OpenAI model for speech-to-text).
whisper = safe_import("whisper", install_hint="pip install -U openai-whisper")
WHISPER_AVAILABLE = whisper is not None

# Import CustomTkinter (required for the main UI).
ctk = safe_import("customtkinter", required=True, install_hint="pip install customtkinter")

# These are external libraries for UI and data handling:
# - numpy: for handling arrays and numeric data.
# - PyQt5: for creating advanced dialogs and text editors.

from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
)
from PyQt5.QtCore import Qt

# Import python-docx (optional, for saving results as Word files).
docx_module = safe_import("docx", install_hint="pip install python-docx")
DOCX_AVAILABLE = bool(docx_module)
if DOCX_AVAILABLE:
    from docx import Document

# ---------------------------
# App Metadata
# ---------------------------
# APP_NAME = "Transcripta"
# This is the application name, used for window titles and messages.

# ---------------------------
# Environment Checks
# ---------------------------
# Check if the operating system is supported (Windows, macOS, Linux).
if platform.system() not in ["Windows", "Darwin", "Linux"]:
    print(f"[Warning] Platform {platform.system()} is not officially supported.")

# Print initialization success message.
print(f"[OK] Environment initialized successfully. Ready to start {APP_NAME}.")


# Set the default appearance mode of the app (Light, Dark, or System).
ctk.set_appearance_mode("System")

# Set the default color theme for all CustomTkinter widgets.
ctk.set_default_color_theme("blue")

import ctypes
# Attempt to enable high-DPI awareness (Windows 8.1+).
try:   
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    # Fallback for older Windows versions.
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

def configure_scaling(root, base_font_name="Segoe UI", base_font_size=11):
    """
    Adjusts UI scaling based on the system's DPI factor.

    Parameters:
        root            The main Tk instance.
        base_font_name  Default UI font family.
        base_font_size  Base font size before scaling.

    Returns:
        float: The scaling factor applied.
    """
    try:
        # Query actual DPI scaling used by Tk on the system.
        scale = float(root.tk.call('tk', 'scaling'))
    except Exception:
        scale = 1.0
        
    # Clamp scale to a safe and readable range.
    scale = max(0.8, min(scale, 3.0))
    
    # Apply scaled font size across the application.
    size = max(8, int(base_font_size * scale))
    root.option_add("*Font", (base_font_name, size))
    return scale

def get_possible_whisper_paths():
    """
   Return a list of possible directories where Whisper models may be cached.

   This function considers cross-platform paths and supports PyTorch's
   hub directory if available. It ensures compatibility with Windows, Linux,
   and macOS systems.

   Returns:
       List[str]: A list of absolute paths where Whisper model files (e.g., 
       'tiny.pt', 'base.pt') may be stored.
   
   Notes:
       - Default Whisper cache directory: ~/.cache/whisper
       - Torch hub directory (if PyTorch is installed): <torch_hub_dir>/whisper
       - Paths are returned in order of priority; the first existing path is
         usually used by Whisper.
   """
    paths = []

    # 1. Default Whisper path
    home = os.path.expanduser("~")
    paths.append(os.path.join(home, ".cache", "whisper"))

    # 2. torch.hub path (if torch installed)
    try:
        import torch
        paths.append(os.path.join(torch.hub.get_dir(), "whisper"))
    except ImportError:
        pass

    return paths
OS = platform.system()
# ---------- Main Application ----------
class TranscriptaApp(ctk.CTk):
    """
    Main application window for Transcripta.

    This class builds the entire GUI using CustomTkinter, manages the state
    of transcription, selected model, CPU/GPU usage, language selection,
    and all interactive UI elements such as browse, play, record and model selection.

    The class loads text strings from LANG_STRINGS based on the current language
    and updates UI elements accordingly.
    """
    
    def __init__(self):
        """Initialize the main window, UI layout, state variables and panels."""
        super().__init__()
        self.scale = configure_scaling(self, base_font_name='Segoe UI', base_font_size=11)

        # Store current UI language (key used inside LANG_STRINGS)
        self.current_language = 'English'
        self.strings = LANG_STRINGS[self.current_language]
        
        # Set main window title and size
        self.title(self.strings['app_title'])
        self.geometry("1150x720")
        self.minsize(980,600)
        
        self.ui_scaling = float(self.tk.call('tk', 'scaling'))

        # --------------- Application State Variables ---------------
        
        # Path of the selected audio file to transcribe
        self.filepath = None

        # Whether transcription is currently running
        self.transcribing = False

        # Whether to use all CPU cores when no GPU exists
        self.use_full_cpu = False

        # Total available CPU threads on the system
        self.cpu_threads = os.cpu_count() or 4

        # Default number of threads to use (half of total)
        self.selected_threads = max(1, min(self.cpu_threads, self.cpu_threads // 2))

        # Selected Whisper model (tiny/base/small)
        self.model_choice = ctk.StringVar(value="small")

        # Selected UI language (English / Arabic / etc.)
        self.lang_choice = ctk.StringVar(value=self.current_language)

        # Configure main layout sizing
        self.grid_columnconfigure(0, weight=0, minsize=int(240 * self.scale))  # left
        self.grid_columnconfigure(1, weight=1)  # center
        self.grid_columnconfigure(2, weight=0, minsize=int(260 * self.scale))  # right
        self.grid_rowconfigure(0, weight=1)

        # Build UI panels (left, center, right sections)
        self.create_left_panel()
        self.create_center_panel()
        self.create_right_panel()

        # After UI loads, detect GPU availability
        self.after(200, self.check_gpu_on_start)
        
        
    
    def _on_ctrl_key(self, event):
        """ 
        ============================================================
        Global Keyboard Shortcuts
        ============================================================
        Handles undo/redo/copy/cut/paste/Select All using hardware keycodes.
        This ensures shortcuts work even when the keyboard layout changes
        (Arabic, French, etc.) because Tkinter's symbol-based bindings
        break on non-English layouts.
        """
        key = event.keycode
    
        try: 
            if OS == "Windows":
                if key == 90:  # Ctrl + Z → Undo
                    self.text_editor.edit_undo()
                    
                elif key == 89:  # Ctrl + Y → Redo
                    self.text_editor.edit_redo()
                
                elif key == 67:  # Ctrl + C → Copy
                    self.clipboard_clear()
                    text = self.text_editor.selection_get()
                    self.clipboard_append(text)
                
                elif key == 88:  # Ctrl + X → Cut
                    self.clipboard_clear()
                    text = self.text_editor.selection_get()
                    self.clipboard_append(text)
                    self.text_editor.delete("sel.first", "sel.last")
                
                elif key == 86:  # Ctrl + V → Paste 
                    text = self.clipboard_get()
                    self.text_editor.insert("insert", text)
            
                elif key == 65:  # Ctrl + A → Select All
                    self.text_editor.tag_add("sel", "1.0", "end-1c")
    
            elif OS == "Linux":
                # Linux keycodes
                if key == 52:     # Z
                    self.text_editor.edit_undo()
                    
                elif key == 29:   # Y
                    self.text_editor.edit_redo()
                    
                elif key == 54:   # C
                    self.clipboard_clear()
                    text = self.text_editor.selection_get()
                    self.clipboard_append(text)
                    
                elif key == 53:   # X
                    self.clipboard_clear()
                    text = self.text_editor.selection_get()
                    self.clipboard_append(text)
                    self.text_editor.delete("sel.first", "sel.last")
                    
                elif key == 55:   # V
                    text = self.clipboard_get()
                    self.text_editor.insert("insert", text)
                    
                elif key == 38:   # A
                    self.text_editor.tag_add("sel", "1.0", "end-1c")
    
            elif OS == "Darwin":  # macOS
                # macOS physical key codes
                if key == 6:   # Z
                    self.text_editor.edit_undo()
                    
                elif key == 16:  # Y
                    self.text_editor.edit_redo()
                elif key == 8:   # C
                    self.clipboard_clear()
                    text = self.text_editor.selection_get()
                    self.clipboard_append(text)
                    
                elif key == 7:   # X
                    self.clipboard_clear()
                    text = self.text_editor.selection_get()
                    self.clipboard_append(text)
                    self.text_editor.delete("sel.first", "sel.last")
                    
                elif key == 9:   # V
                    text = self.clipboard_get()
                    self.text_editor.insert("insert", text)
                    
                elif key == 0:   # A
                    self.text_editor.tag_add("sel", "1.0", "end-1c")
        except:
            pass # Ignore errors such as no selection available
    
        return "break" # Prevent default Tkinter behavior for these keys

    def get_str(self, key):
        """
        Return translated UI string based on current language.

        Args:
            key (str): The text key to fetch from the language dictionary.

        Returns:
            str: Translated text for the active language or English fallback.
        """
        
        # Fetch string for the current language, fallback to English if missing.
        return LANG_STRINGS.get(self.current_language, LANG_STRINGS['English']).get(key, key)
        
    # ---------------- LEFT PANEL ----------------
    def create_left_panel(self): 
        """
        Create the left-side control panel containing 
            file browsing,
            model selection, 
            CPU settings, 
            progress bar, 
            and action buttons.
        """ 
        
        # Main container for the left panel 
        frame = ctk.CTkFrame(self, corner_radius=8) 
        frame.grid(row=0, column=0, padx=6, pady=12, sticky="nsew") 
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1) 
        current_row = 0 
        
        # --- File Selection Section --- # Container for file browsing, playback, and audio recording controls 
        browse_frame = ctk.CTkFrame(frame) 
        browse_frame.grid(row=current_row, column=0, sticky="ew", padx=8, pady=6) 
        browse_frame.grid_columnconfigure((0,1,2), weight=1) 
        current_row += 1 
        
        # Displays the currently selected file path or "No file" 
        self.file_label = ctk.CTkLabel(browse_frame, text=self.get_str('no_file'), anchor="w") 
        self.file_label.grid(row=0, column=0, columnspan=3, sticky="ew", padx=6, pady=(6, 4)) 

        # Buttons: browse, play, record 
        self.browse_button = ctk.CTkButton(browse_frame, text=self.get_str('browse'), command=self.browse_file) 
        self.browse_button.grid(row=1, column=0, sticky="ew", padx=4, pady=(0,4)) 
        self.play_button = ctk.CTkButton(browse_frame, text=self.get_str('play'), command=self.toggle_playback) 
        self.play_button.grid(row=1, column=1, sticky="ew", padx=4, pady=(0,4)) 
        self.record_button = ctk.CTkButton(browse_frame, text=self.get_str('record'), command=self.toggle_recording) 
        self.record_button.grid(row=1, column=2, sticky="ew", padx=4, pady=(0,4)) 
        
        # --- Model Selection Header --- 
        model_label = ctk.CTkLabel(frame, text=self.get_str('select_model'), anchor="w") 
        model_label.grid(row=current_row, column=0, sticky="ew", padx=8, pady=(12,4)) 
        current_row += 1 
        
        # --- Whisper Model Radio Buttons --- 
        # Allows the user to select the Whisper model size (tiny/base/small) 
        radio_frame = ctk.CTkFrame(frame, fg_color="transparent") 
        radio_frame.grid(row=current_row, column=0, sticky="ew", padx=12, pady=(0,6)) 
        radio_frame.grid_columnconfigure(0, weight=1) 
        model_row = 0 
        
        for m in ["tiny", "base", "small"]: 
            ctk.CTkRadioButton(radio_frame,
                text=m.capitalize(), 
                variable=self.model_choice, value=m, 
                command=self.update_model_description ).grid(row=model_row, 
                                                         column=0, sticky="w", pady=2) 
            model_row += 1 
        current_row += 1 
            
        # --- Model Description Textbox --- 
        # Displays the detailed description of the selected Whisper model 
        self.model_desc = ctk.CTkTextbox(frame) 
        self.model_desc.grid(row=current_row, column=0, sticky="ew", padx=8, pady=6) 
        frame.grid_rowconfigure(current_row, weight=1) 
        current_row += 1 
        self.update_model_description() 
        
        # --- Whisper Language Selector --- 
        # Create label for the audio language selection dropdown 
        audio_lang_label = ctk.CTkLabel(frame, text=self.get_str("Audio_Language"), anchor="w") 
        audio_lang_label.grid(row=current_row, column=0, sticky="nsew", padx=8, pady=(6,2)) 
        current_row += 1 
        
        # Holds selected audio language (default: auto-detect) 
        self.audio_lang_var = ctk.StringVar(value="Auto Detect") 
        
        # Create ComboBox with all languages initially 
        self.audio_lang_menu = ctk.CTkComboBox(frame, variable=self.audio_lang_var, values=list(WHISPER_LANGS.keys())) 
        self.audio_lang_menu.grid(row=current_row, column=0, sticky="ew", padx=8, pady=(0,8)) 
        current_row += 1 
        
        # Function to filter ComboBox values as user types 
        def filter_combobox(event): 
            typed = self.audio_lang_var.get().lower() 
            filtered = [lang for lang in WHISPER_LANGS.keys() if typed in lang.lower()] 
            if not filtered: 
                filtered = ["No match"] 
            self.audio_lang_menu.configure(values=filtered) 
        # Bind the function to KeyRelease event for live filtering 
        self.audio_lang_menu.bind("<KeyRelease>", filter_combobox) 
                
                
        # --- CPU Settings (Only shown if GPU is not available) --- 
        self.has_gpu = torch.cuda.is_available() 
        if not self.has_gpu: 
            # Enable/disable using all CPU threads 
            self.cpu_checkbox = ctk.CTkCheckBox(frame, text=self.get_str('use_full_cpu'), command=self.toggle_full_cpu) 
            self.cpu_checkbox.grid(row=current_row, column=0, sticky="w", padx=8, pady=(6,2)) 
            current_row += 1 
            
            # Thread slider container 
            self.thread_frame = ctk.CTkFrame(frame) 
            self.thread_frame.grid(row=current_row, column=0, sticky="ew", padx=8, pady=(4,8)) 
            self.thread_frame.grid_columnconfigure(0, weight=1) 
            
            # Displays selected vs total CPU threads 
            self.thread_label = ctk.CTkLabel( self.thread_frame, text=f"{self.get_str('threads_label')}: {self.selected_threads}/{self.cpu_threads}" ) 
            self.thread_label.grid(row=0, column=0, sticky="w", padx=6, pady=(2,4)) 
            
            # Slider to manually select number of CPU threads 
            self.thread_slider = ctk.CTkSlider( self.thread_frame, from_=1, to=self.cpu_threads, number_of_steps=max(1, self.cpu_threads-1), command=self.update_thread_label ) 
            self.thread_slider.set(self.selected_threads) 
            self.thread_slider.grid(row=1, column=0, sticky="ew", padx=6) 
            current_row += 1 
            
        # --- Progress Bar Section --- 
        progress_label = ctk.CTkLabel(frame, text=self.get_str('progress')) 
        progress_label.grid(row=current_row, column=0, sticky="w", padx=8, pady=(8,2)) 
        current_row += 1 
        # Visual transcription progress bar 
        self.progress = ctk.CTkProgressBar(frame) 
        self.progress.set(0) 
        self.progress.grid(row=current_row, column=0, sticky="ew", padx=8, pady=(0,6)) 
        current_row += 1 
        # Estimated time remaining label 
        self.eta_label = ctk.CTkLabel(frame, text=f"{self.get_str('eta')} --:--:--") 
        self.eta_label.grid(row=current_row, column=0, sticky="w", padx=8) 
        current_row += 1 
        # --- Start/Stop Action Buttons --- 
        btns = ctk.CTkFrame(frame, fg_color="transparent") 
        btns.grid(row=current_row, column=0, sticky="ew", padx=8, pady=8) 
        btns.grid_columnconfigure((0,1), weight=1) 
        ctk.CTkButton(btns, text=self.get_str('start'), command=self.start_transcription).grid(row=0, column=0, sticky="ew", padx=4) 
        ctk.CTkButton(btns, text=self.get_str('stop'), fg_color="#a12626", hover_color="#8b2222", command=self.stop_transcription).grid(row=0, column=1, sticky="ew", padx=4) 
        current_row += 1 
        # --- Appearance Mode Selector (Light/Dark) --- 
        appearance_label = ctk.CTkLabel(frame, text=self.get_str('appearance')) 
        appearance_label.grid(row=current_row, column=0, sticky="w", padx=8, pady=(10,2)) 
        current_row += 1 
        # Dropdown for selecting UI theme 
        self.appearance_option = ctk.CTkOptionMenu(frame, values=["Light","Dark"], command=self.change_appearance) 
        self.appearance_option.set(ctk.get_appearance_mode()) 
        self.appearance_option.grid(row=current_row, column=0, sticky="ew", padx=8, pady=(0,8)) 
        current_row += 1 
        # --- UI Language Selector --- 
        lang_label = ctk.CTkLabel(frame, text=self.get_str('ui_language')) 
        lang_label.grid(row=current_row, column=0, sticky="w", padx=8, pady=(4,2)) 
        current_row += 1 
        # Dropdown menu for switching interface language 
        self.lang_menu = ctk.CTkOptionMenu(frame, values=list(LANG_STRINGS.keys()), command=self.change_language) 
        self.lang_menu.set(self.current_language) 
        self.lang_menu.grid(row=current_row, column=0, sticky="ew", padx=8, pady=(0,8))

    def create_center_panel(self):
        """
        Create the center panel of the application.
    
        This panel contains:
            - The toolbar (Copy / Save / Clear / Edit buttons)
            - The main text editor area where transcription output appears
            - Global keyboard shortcuts (Undo/Redo/Copy/Cut/Paste) that work across
              all keyboard languages using hardware keycodes to ensure consistency
              even when the layout changes (e.g., Arabic , French keyboard or any other keyboard).
        """
        # Root container for the center panel
        frame = ctk.CTkFrame(self, corner_radius=8)
        frame.grid(row=0, column=1, padx=6, pady=12, sticky="nsew")
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        
        current_row = 0
    
        # ---------------------------------------------------------
        # Toolbar: contains Copy, Save, Clear, and external Editor
        # ---------------------------------------------------------
        toolbar = ctk.CTkFrame(frame, fg_color="transparent")
        toolbar.grid(row=current_row, column=0, sticky="ew", padx=8, pady=8)
        toolbar.grid_columnconfigure((0,1,2,3), weight=1)
        
        # ========== SLOGAN (Row 0) ==========
        slogan = ctk.CTkLabel(
            toolbar,
            text="Transcripta Lite • Get the Script",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="center"
        )
        slogan.grid(row=0, column=0, columnspan=4, pady=(0,4), sticky="ew")
        
        # ========== BUTTONS ROW (Row 1) ==========
        ctk.CTkButton(toolbar, text=self.get_str('copy'), command=self.copy_text).grid(row=1, column=0, sticky="ew", padx=6)
        ctk.CTkButton(toolbar, text=self.get_str('save'), command=self.save_text_dialog).grid(row=1, column=1, sticky="ew", padx=6)
        ctk.CTkButton(toolbar, text=self.get_str('clear'), command=self.clear_text).grid(row=1, column=2, sticky="ew", padx=6)
        ctk.CTkButton(toolbar, text=self.get_str('Edit'), command=self.open_pyqt_editor).grid(row=1, column=3, sticky="ew", padx=6)
        
        current_row += 1
    
        # ---------------------------------------------------------
        # Main Text Editor Area
        # ---------------------------------------------------------
        editor_frame = ctk.CTkFrame(frame)
        editor_frame.grid(row=current_row, column=0, sticky="nsew", padx=8, pady=8)
        editor_frame.grid_rowconfigure(0, weight=1)
        editor_frame.grid_columnconfigure(0, weight=1)
    
        # Textbox used to display and edit transcription output.
        # Undo/Redo enabled with unlimited history.
        self.text_editor = ctk.CTkTextbox(
            editor_frame,
            wrap="word",
            undo=True,
            autoseparators=True,
            maxundo=-1
        )
        self.text_editor.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
    
        # Bind all Ctrl+Key combinations in the text editor to the _on_ctrl_key handler.
        # This allows handling shortcuts like Ctrl+C, Ctrl+X, Ctrl+V, Ctrl+A, Ctrl+Z, and Ctrl+Y
        # in a layout-independent way, so they work across all keyboard languages and OS platforms.
        self.text_editor.bind("<Control-Key>", self._on_ctrl_key)

    def create_right_panel(self):
        """
        Create the right-side panel of the application.
    
        This panel displays:
            - A notifications title
            - A scrollable list of notification items (errors, status updates, info)
            - A button to clear all notifications
    
        Notifications allow the user to see events such as:
            - GPU detection
            - Recording started/stopped
            - File saved
            - Transcription progress messages
        """
        # Main container for the right panel
        frame = ctk.CTkFrame(self, corner_radius=8)
        frame.grid(row=0, column=2, padx=6, pady=12, sticky="nsew")
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)
    
        # ---------------------------------------------------------
        # Section Title
        # ---------------------------------------------------------
        title = ctk.CTkLabel(frame, text=self.get_str('notifications'),
                             font=ctk.CTkFont(size=14, weight="bold"))
        title.grid(row=0, column=0, pady=(8,6), sticky="ew")
    
        # ---------------------------------------------------------
        # Scrollable Frame for Notifications
        # ---------------------------------------------------------
        # This holds the vertically scrollable list of notification widgets.
        self.notif_list = ctk.CTkScrollableFrame(frame)
        self.notif_list.grid(row=1, column=0, padx=8, pady=6, sticky="nsew")
    
        # Container inside the scrollable area where individual notifications are added.
        # Using a separate frame simplifies layout management when adding/removing items dynamically.
        self.notif_items_container = ctk.CTkFrame(self.notif_list, fg_color="transparent")
        self.notif_items_container.grid(row=0, column=0, sticky="nsew")
        self.notif_items_container.grid_rowconfigure(0, weight=1)
    
        # ---------------------------------------------------------
        # Clear Notifications Button
        # ---------------------------------------------------------
        # Removes all notifications from the list.
        clear_btn = ctk.CTkButton(
            frame,
            text=f"{self.get_str('notifications')} — {self.get_str('clear')}",
            command=self.clear_notifications
        )
        clear_btn.grid(row=2, column=0, pady=6, sticky="ew")
        
    # --------------------------- Helpers ---------------------------
    def check_model_available(self, model_name):
        """
        Verifies whether the requested Whisper model is already available
        in the local cache directory.
    
        If the model is missing, a popup info dialog is displayed to inform
        the user that the model will be downloaded automatically on first use.
        """
        
        # Whisper stores downloaded models in the user's cache directory:
        for cache_dir in get_possible_whisper_paths():
            model_file = os.path.join(cache_dir, f"{model_name}.pt")
            if os.path.exists(model_file):
                return True
        
        # If the model file doesn't exist, notify the user
        if not os.path.exists(model_file):
            messagebox.showinfo(
                self.get_str('app_title'),self.get_str(
                "Whisper_model") +' '+str(model_name)+ "\n" +self.get_str("model_not_found"))

    def add_notification(self, text):
        """
        Add a timestamped notification message to the notifications panel.
    
        Args:
            text (str): The message to display inside the notifications list.
    
        This function attaches a new label containing the message along with
        a timestamp, and packs it inside the scrollable notifications container.
        """  
        # Create timestamp for the notification (HH:MM:SS)
        ts = time.strftime('%H:%M:%S')
        
        # Create label and add it to the notifications area
        lbl = ctk.CTkLabel(self.notif_items_container, text=f"[{ts}] {text}", wraplength=280, anchor='w')
        lbl.pack(fill='x', pady=4, padx=6)
        
    def clear_notifications(self):
            """
            Clear all notifications displayed in the notifications panel.
        
            This removes all child widgets from the notification container.
            """
            for child in self.notif_items_container.winfo_children():
                child.destroy()

    def update_thread_label(self, value):
        """
        Update the CPU thread count label when the user moves the slider.
    
        Args:
            value (float): The new thread value coming from the slider.
        """
        # Convert slider value to int and store it
        self.selected_threads = int(float(value))

        # Update the text label to reflect the new value
        self.thread_label.configure(text=f"{self.get_str('threads_label')}: {self.selected_threads}/{self.cpu_threads}")

    def update_model_description(self):
        """
        Update the description text shown for the selected Whisper model.
    
        Uses language keys defined in LANG_STRINGS such as:
            - model_desc_tiny
            - model_desc_base
            - model_desc_small
        """
        # Read currently selected model
        m = self.model_choice.get()

        # Dictionary mapping model name to its description key
        desc_keys = {
            'tiny': 'model_desc_tiny',
            'base': 'model_desc_base',
            'small': 'model_desc_small',
        }

        # Get the description key safely
        key = desc_keys.get(m, "")
        desc = self.get_str(key) if key else ""

        # Insert the translated model description into the textbox
        self.model_desc.delete("0.0", "end")
        self.model_desc.insert("0.0", desc)

    # ---------------- File / playback ----------------
    def browse_file(self):
        """
        Open a file dialog for selecting an audio or video file, then update
        the interface with the chosen file path.
    
        Updates:
            - self.filepath
            - the file label in the left panel
            - adds a notification showing the selected file
        """

        # Allowed file types for browsing
        filetypes = [("Audio/Video files", "*.wav *.mp3 *.m4a *.mp4 *.mov *.ogg *.opus *.flac"), ("All files", "*")]

        # Open file dialog
        path = filedialog.askopenfilename(title=self.get_str('browse'), filetypes=filetypes)

        # If the user selected a file
        if path:
            self.filepath = path
            
            # Show only filename in the UI
            self.file_label.configure(text=os.path.basename(path))

            # Add notification with full file path
            self.add_notification(self.get_str("selected_file") + "\n"+ str(path))

    def toggle_playback(self):
        """
        Toggle between starting and stopping audio playback.
    
        Playback priority:
            1. Try ffplay (fastest)
            2. Try VLC
            3. Use OS default player (Windows/Mac/Linux)
    
        The function updates:
            - Playback state (self.is_playing)
            - Button text (Play/Stop)
            - Notification messages
        """
        # Ensure playback state attributes exist
        if not hasattr(self, "is_playing"):
            self.is_playing = False
        if not hasattr(self, "player_process"):
            self.player_process = None

        # No file selected
        if not self.filepath:
            messagebox.showwarning(self.get_str('app_title'), self.get_str('no_file'))
            return
    
        # If currently playing → stop playback
        if self.is_playing:
            self.add_notification(self.get_str("stopping_playback"))
            self.play_button.configure(text=self.get_str('play'))
            self.is_playing = False

            # Try to safely terminate external player
            try:
                if self.player_process and self.player_process.poll() is None:
                    self.player_process.terminate()
            except Exception:
                pass
            return
    
        # If not playing → start playback
        def _play():
            
            # Mark as playing
            self.is_playing = True
            self.play_button.configure(text=self.get_str('stop'))
            played = False

            # Try ffplay (first option)
            try:
                self.player_process = subprocess.Popen(
                    ["ffplay", "-nodisp", "-autoexit", self.filepath],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                self.player_process.wait()
                played = True
            except Exception:
                pass

            # Try VLC (second option)
            if not played:
                try:
                    self.player_process = subprocess.Popen(
                        ["vlc", "--play-and-exit", self.filepath],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    self.player_process.wait()
                    played = True
                except Exception:
                    pass

            # Try OS default player (third option)
            if not played:
                try:
                    if platform.system() == 'Windows':
                        os.startfile(self.filepath)
                    elif platform.system() == 'Darwin':
                        subprocess.Popen(["open", self.filepath])
                    else:
                        subprocess.Popen(["xdg-open", self.filepath])
                    played = True
                except Exception:
                    played = False

            # If all playback methods failed
            if not played:
                self.add_notification("could_not_play")
    
            # Playback finished
            self.is_playing = False
            self.play_button.configure(text=self.get_str('play'))
            
        # Run playback on a background thread
        threading.Thread(target=_play, daemon=True).start()

        # Add notification for playback start
        self.add_notification(self.get_str("playing_file"))
 
    # ---------------- GPU & ETA detection ----------------
    def toggle_full_cpu(self):
        """
        Toggle between using all CPU threads or allowing manual thread selection.
    
        When enabled:
            - The slider becomes disabled
            - All CPU cores are used
    
        When disabled:
            - Slider becomes active again
            - User can manually select thread count
        """
        # Ensure slider exists before modifying it
        if hasattr(self, 'thread_slider'):  

            # If checkbox is ON → use all CPU threads
            if self.cpu_checkbox.get() == 1:
                
                self.thread_slider.configure(state="disabled")
                self.selected_threads = os.cpu_count()

                # Update UI label
                self.thread_label.configure(
                    text=f"{self.get_str('threads_label')}: {self.selected_threads}/{self.cpu_threads}"
                )

                # Notify user
                self.add_notification(self.get_str("using_all")+ str(self.selected_threads) + self.get_str("cpu_threads"))
            else:

                # Checkbox OFF → enable manual control
                self.thread_slider.configure(state="normal")
                self.selected_threads = int(self.thread_slider.get())
                self.thread_label.configure(
                    text=f"{self.get_str('threads_label')}: {self.selected_threads}/{self.cpu_threads}"
                )
                self.add_notification(self.get_str("using") + " " + str(self.selected_threads) + " " + self.get_str("cpu_threads"))
   
    def ffprobe_duration(self, path):
        """
        Get the duration of an audio/video file using ffprobe.
        Args:
            path (str): The file path.
    
        Returns:
            float or None: Duration in seconds, or None if extraction fails.
        """

        # Call ffprobe to read duration metadata
        try:
            res = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            dur = float(res.stdout.strip())
            return dur
        except Exception:
            # If extraction fails return None
            return None

    def check_gpu_on_start(self):
        """
        Detect GPU availability at startup.
    
        Displays notifications and warning messages depending on:
            - GPU available → shows GPU name and hides CPU controls
            - GPU not available → enables CPU thread controls and warns user
    
        This helps users understand expected processing speed.
        """
    
        gpu_available = False

        # Try detecting GPU using PyTorch
        try:
            import torch
            if torch.cuda.is_available():
                gpu_available = True
                gpu_name = torch.cuda.get_device_name(0)
                # Notification: GPU detected successfully
                self.add_notification(f"✅ GPU detected: {gpu_name}")
                
            else:
                # Notification: No GPU
                self.add_notification("⚠️ No GPU detected. The app will run on CPU only.")
                messagebox.showwarning("GPU Not Found", "⚠️ No GPU detected.\nThe app will run on CPU only. This may be slower.")
                
        except Exception:
            # PyTorch not available or GPU detection failed
            self.add_notification("⚠️ PyTorch not installed or no GPU detected.")
            messagebox.showwarning("GPU Not Found", "⚠️ PyTorch not installed or no GPU detected.\nThe app will run on CPU only.")
    
        # Control visibility of CPU checkbox
        try:
            if gpu_available:
                # Hide CPU options when GPU exists
                self.cpu_checkbox.grid_remove()  # يخفي العنصر بدون حذف مكانه
            else:
                # Show CPU options when GPU is missing
                self.cpu_checkbox.grid()
        except Exception as e:
            # If error occurred in CPU checkbox control
            self.add_notification(f"⚠️ CPU checkbox control error: {e}")
    
    # ---------------- Saving ----------------
    def save_text_dialog(self):
            """
            Open a Save dialog and export the current editor text as either:
                - .txt (plain text)
                - .docx (Word document)
        
            Behavior:
                - If no text exists → show warning
                - If python-docx is unavailable and the user selects .docx → fallback to .txt
                - After saving, adds a notification with the saved file path
            """
            # Retrieve text from editor
            txt = self.text_editor.get("0.0", "end-1c")

            # If editor is empty → show message
            if not txt.strip():
                messagebox.showinfo(self.get_str('app_title'), self.get_str("no_text_to_save"))
                return
                
            # Open Save As dialog
            file = filedialog.asksaveasfilename(defaultextension='.txt', filetypes=[('Text', '*.txt'), ('Word docx', '*.docx')])

            # If user cancelled the dialog
            if not file:
                return

            try:
                # ---------------- Save as DOCX ----------------
                if file.lower().endswith('.docx'):
                    
                    # If python-docx not installed → fallback to .txt
                    if not DOCX_AVAILABLE:
                        messagebox.showwarning(self.get_str('app_title'), self.get_str('saving_missing_docx'))

                        # Replace .docx with .txt
                        with open(file[:-5] + '.txt', 'w', encoding='utf-8') as f:
                            f.write(txt)
                        self.add_notification(self.get_str('saving_missing_docx'))

                    # If docx library exists → save properly
                    else:
                        doc = Document()
                        for line in txt.split('\n'):
                            doc.add_paragraph(line)
                        doc.save(file)
                        self.add_notification(self.get_str('saved_as') +"\n" + str(file))

                # ---------------- Save as TXT ----------------
                else:
                    # Save plain text file
                    with open(file, 'w', encoding='utf-8') as f:
                        f.write(txt)
                    self.add_notification(self.get_str('saved_as') +"\n" + str(file))
                    
            except Exception as e:
                # If saving failed → show error message
                messagebox.showerror('Save error', str(e))
                self.add_notification(f'Save failed: {e}')

    # ---------------- Recoeding ----------------
    def open_format_selector(self):
        """
        Open a modal window allowing the user to choose a recording format.
    
        The window displays:
            - Recommended usage text
            - Description of each format (WAV, MP3, FLAC, etc.)
            - Buttons to select the encoding format
    
        After the user selects a format, recording starts automatically.
        """
        
        win = ctk.CTkToplevel(self)
        win.title(self.get_str("choose_record_format"))
        win.geometry("560x460")
        win.grab_set() # Disable interaction with main window ,  غلق التفاعل مع نافذة التطبيق أثناء فتح النافذة الصغيرة.

        # Title
        ctk.CTkLabel(win, text=self.get_str("choose_record_format"),
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10,6))
    
        # recommendation area
        rec = self.get_str("recommendation_text")
        rec_frame = ctk.CTkFrame(win)
        rec_frame.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkLabel(rec_frame, text=rec, wraplength=500, justify="left").pack(anchor="w", padx=8, pady=8)
        
        # Format description dictionary
        options = {
            "wav": self.get_str("format_desc_wav"),
            "mp3": self.get_str("format_desc_mp3"),
            "wav->mp3": self.get_str("format_desc_wav_mp3"),
            "flac": self.get_str("format_desc_flac"),
        }

        # Callback when selecting a format
        def _select(fmt):
            win.destroy()
            self.selected_format = fmt
            self.start_recording(fmt)

        # Create UI buttons for each format
        for fmt, desc in options.items():
            frame = ctk.CTkFrame(win)
            frame.pack(fill="x", padx=14, pady=6)
            ctk.CTkLabel(frame, text=desc, wraplength=500, justify="left").pack(anchor="w", padx=8, pady=6)
            ctk.CTkButton(frame, text=f"اختيار {fmt.upper()}" if self.current_language.startswith("Arabic") else f"Select {fmt.upper()}", command=lambda f=fmt: _select(f)).pack(anchor="e", padx=8, pady=(0,8))

    def start_recording(self, fmt):
        """
        Start recording audio using AudioRecorder.
    
        Notes:
            - Always records raw audio to a temporary WAV file (.wav)
            - After stopping, the file may be converted to another format (mp3, flac, etc.)
        """
        try:
            # Ensure audio recorder exists
            if not hasattr(self, "audio_recorder") or self.audio_recorder is None:
                self.audio_recorder = AudioRecorder()
        except Exception:
            self.audio_recorder = AudioRecorder()
    
        self.selected_format = fmt
        self.recording = True

        # Update UI (button changes to "Stop")
        self.record_button.configure(text=self.get_str("stop_record"), fg_color="#a12626")

        # Temporary WAV file path
        wav_temp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
        self._current_wav = wav_temp
        
        # Start recording
        self.audio_recorder.start(wav_temp)
        self.add_notification(self.get_str("recording_started"))

    def toggle_recording(self):
        """
        Toggle recording state:
            - If not recording → open format selector
            - If recording → stop, convert, save, and set as active file
    
        Also handles:
            - User-selected file name for export
            - Conversion via ffmpeg
            - Notifications for success or failure
        """

        # Start recording if not already recording
        if not getattr(self, "recording", False):
            self.open_format_selector()
            return
    
        # Stop recording
        try:
            self.recording = False

            # Reset button appearance
            self.record_button.configure(text=self.get_str("record"), fg_color="#1f6aa5")
            wav_path = None

            # Stop the recorder
            if hasattr(self, "audio_recorder"):
                wav_path = self.audio_recorder.stop()
            else:
                wav_path = getattr(self, "_current_wav", None)
    
            if not wav_path or not os.path.exists(wav_path):
                self.add_notification(self.get_str("record_failed"))
                return

            # Ask user where to save the file
            save_path = filedialog.asksaveasfilename(
                title="Save Recording As",
                defaultextension=f".{self.selected_format}",
                filetypes=[("Audio Files", f"*.{self.selected_format}")] 
            )

            if not save_path:
                self.add_notification(self.get_str("record_cancelled"))
                return
            
            # Convert WAV to selected format
            out_path = self.convert_audio(wav_path, self.selected_format, output_path=save_path)
            if out_path:
                self.filepath = out_path
                self.file_label.configure(text=os.path.basename(out_path))
                self.add_notification(f"{self.get_str('recording_saved')}: {out_path}")
                
                #uncomment this line if u want to stard the transcription immediatly after recording
                #self.start_transcription()
            else:
                self.add_notification(self.get_str("conversion_failed"))
        except Exception as e:
            self.add_notification(f"Recording stop error: {e}")
    
    def convert_audio(self, wav_path, fmt, output_path=None):
        """
        Convert a raw WAV recording into the desired format using ffmpeg.
    
        Args:
            wav_path (str): Path to the temporary WAV file.
            fmt (str): Target format (wav, mp3, wav->mp3, flac).
            output_path (str, optional): The user-specified output file path.
    
        Returns:
            str or None: Final path if conversion succeeded, otherwise None.
        """
        try:
            # Use user-specified path if provided
            if output_path:
                out_path = output_path
                out_dir = os.path.dirname(out_path)
                os.makedirs(out_dir, exist_ok=True)
            else:
                # Default directory "recordings"
                out_dir = os.path.join(os.getcwd(), "recordings")
                os.makedirs(out_dir, exist_ok=True)
                base = os.path.splitext(os.path.basename(wav_path))[0]
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                out_path = os.path.join(out_dir, f"{base}_{timestamp}.{fmt}")
    
            # Ensure correct extension
            root, ext = os.path.splitext(out_path)
            if not out_path.lower().endswith(f".{fmt.lower()}"):
                out_path = f"{root}.{fmt}"
    
            # Handle simple copy cases (no conversion)
            if fmt == "wav":
                os.replace(wav_path, out_path)
                return out_path

            # ffmpeg conversion commands
            elif fmt == "mp3":
                cmd = ["ffmpeg", "-y", "-i", wav_path, "-codec:a", "libmp3lame", "-qscale:a", "2", out_path]
    
            elif fmt == "wav->mp3":
                cmd = ["ffmpeg", "-y", "-i", wav_path, "-codec:a", "libmp3lame", "-qscale:a", "1", out_path]
    
            elif fmt == "flac":
                cmd = ["ffmpeg", "-y", "-i", wav_path, "-c:a", "flac", out_path]
    
            else:
                # Unknown format → fallback to WAV
                os.replace(wav_path, out_path)
                return out_path

            # Execute ffmpeg
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Remove temp WAV file
            if os.path.exists(wav_path):
                os.remove(wav_path)
    
            return out_path
    
        except Exception as e:
            self.add_notification(f"Conversion error: {e}")
            return None

    # ---------------- Transcription (Whisper) ----------------
    def start_transcription(self):
        """
        Start a background transcription process using OpenAI Whisper.
    
        Flow:
            1. Validate environment (file, whisper, GPU/CPU availability)
            2. Load the selected Whisper model
            3. Estimate duration and show a dynamic progress bar + ETA
            4. Perform transcription in a background thread
            5. Display the result inside the text editor upon completion
    
        Notes:
            - Runs asynchronously to keep the UI responsive
            - Uses ffprobe for duration estimation
            - Supports both CPU and GPU processing
        """
        # Map the display name to the corresponding Whisper language code
        # (e.g., "English" → "en", "Arabic" → "ar")
        selected_display = self.audio_lang_var.get()
        self.selected_whisper_lang = WHISPER_LANGS.get(selected_display)

        # Prevent multiple transcriptions running at once
        if self.transcribing:
            messagebox.showinfo(self.get_str('app_title'), self.get_str('transcription_running'))
            return

        # Check file selection
        if not self.filepath:
            messagebox.showwarning(self.get_str('app_title'), self.get_str('no_file'))
            return

        # Ensure Whisper library is installed
        if not WHISPER_AVAILABLE:
            messagebox.showerror(self.get_str('app_title'), 'Whisper package not installed. Install with: pip install -U openai-whisper')
            return

        # Select device (GPU if available, otherwise CPU)
        device = 'cpu'
        if TORCH_AVAILABLE and torch.cuda.is_available() and getattr(self, 'cpu_checkbox', None) and not self.cpu_checkbox.get():
            device = 'cuda'

        # Apply thread limit if using CPU
        
        if device == 'cpu':
            try:
                torch.set_num_threads(self.selected_threads)
                start_time2 = time.time()
                self.add_notification(self.get_str('set_torch_threads') + str(self.selected_threads))
                
            except Exception:
                pass

        # Retrieve selected Whisper model
        model_name = self.model_choice.get()
        self.check_model_available(model_name)
        # Initialize UI and state
        self.add_notification(self.get_str('loading_model') + ": " + str(model_name) +str(" on ") + str(device))
        self.transcribing = True
        self.progress.set(0)

        # Estimate duration for progress updates
        duration = self.ffprobe_duration(self.filepath) or 0
        speed_factors = {'tiny': 0.2, 'base': 0.5, 'small': 1.0}
        speed = speed_factors.get(model_name, 0.5)
        estimated_seconds = max(5, int(duration * speed)) if duration > 0 else 20
        start_time = time.time()

        def _run_transcribe():
            """Inner thread function handling the actual Whisper transcription."""
            try:
                model = whisper.load_model(model_name, device=device)
            except Exception as e:
                # Model load failure
                self.add_notification(f'Model load failed: {e}')
                self.transcribing = False
                return

           # -------- Background progress thread --------
            def _progress_updater():
                """Continuously update progress bar and ETA while transcribing."""
                while self.transcribing:
                    elapsed = time.time() - start_time
                    if duration > 0:
                        # estimate based on estimated_seconds
                        pct = min(0.98, elapsed / max(1, estimated_seconds))
                    else:
                        pct = min(0.98, elapsed / max(1, 60))
                        
                    # Update progress bar
                    self.progress.set(pct)

                    # Calculate remaining time
                    eta = max(0, int((estimated_seconds - elapsed)))
                    self.eta_label.configure(text=f"{self.get_str('eta')} {time.strftime('%H:%M:%S', time.gmtime(eta)) if eta>0 else '--:--:--'}")
                    time.sleep(1)

            # Start background progress thread
            updater = threading.Thread(target=_progress_updater, daemon=True)
            updater.start()

            # -------- Run actual transcription --------
            try:
                
                result = model.transcribe(self.filepath , language=self.selected_whisper_lang)
                text = result.get('text', '')
                end_time2 = time.time()
                elapsed_time2 = (end_time2 - start_time2)+1
                minutes = int(elapsed_time2 // 60)
                seconds = int(elapsed_time2 % 60)
            
                if minutes > 0:
                    elapsed_str2 = f"{minutes}m {seconds}s"
                else:
                    elapsed_str2 = f"{seconds}s"

                # Insert text result into editor
                self.text_editor.insert('end', text + '\n')
                self.add_notification(self.get_str('transcription_finished') + str(elapsed_str2))
                
            except Exception as e:
                # Handle transcription failure
                self.add_notification(f'Transcription failed: {e}')
                
            finally:
                # Reset UI and state
                self.transcribing = False
                self.progress.set(1)
                self.eta_label.configure(text=f"{self.get_str('eta')} --:--:--")

        # Run transcription in background thread
        threading.Thread(target=_run_transcribe, daemon=True).start()

    def stop_transcription(self):
        """
        Stop the ongoing transcription process.
    
        Notes:
            - Whisper’s `transcribe()` cannot be forcibly interrupted cleanly.
            - This method simply sets a flag to stop progress updates
              and adds a user notification.
        """
        
        if self.transcribing:
            # there's not a clean way to stop whisper.model.transcribe in the middle; we set flag and notify
            # Stop flag (affects UI progress updater)
            self.transcribing = False
            self.add_notification(self.get_str('user_requested_stop'))
            
        else:
            # No transcription running
            self.add_notification(self.get_str('no_transcription_to_stop'))

    # ---------------- UI helpers ----------------
    def copy_text(self):
        """
        Copy the entire content of the text editor to the system clipboard.
        """
        # Get text from the editor and copy to clipboard.
        txt = self.text_editor.get("0.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(txt)
        self.add_notification(self.get_str('text_copied'))

    def clear_text(self):
        """
        Clear the text editor content and notify the user.
        """
        # Delete all text from editor and add a notification.
        self.text_editor.delete("0.0", "end")
        self.add_notification(self.get_str('editor_cleared'))

    def change_appearance(self, new):
        """
        Change the application's appearance mode (Light or Dark) and sync editor theme.
        """
        # Set CustomTkinter appearance mode and update editor colors.
        ctk.set_appearance_mode(new)
        self.sync_editor_theme()
        self.add_notification(self.get_str('appearance_set') +' ' +str(new))

    def sync_editor_theme(self):
        """
        Synchronize the text editor colors with the current appearance mode.
    
        Uses simple color pairs for Light and Dark modes to keep editor readable.
        """
        # Determine current appearance mode and choose foreground/background colors.
        mode = ctk.get_appearance_mode()
        bg, fg = ('#1f1f1f', '#ffffff') if mode == 'Dark' else ('#ffffff', '#000000')

        # Try to apply colors to the editor widget if supported.
        try:
            self.text_editor.configure(fg_color=bg, text_color=fg)
        except Exception:

            # If the editor widget does not support these options, ignore silently.
            pass

    def change_language(self, val):
        """
        Change the current UI language and rebuild visible UI panels.
    
        Args:
            val (str): Language key to switch to (must exist in LANG_STRINGS).
        """
        # Validate the requested language exists in the global LANG_STRINGS.
        if val not in LANG_STRINGS:
            return

        # Update language state and strings reference.
        self.current_language = val
        self.strings = LANG_STRINGS[val]

        # Rebuild UI panels so that all visible labels get refreshed.
        try:
            # Reset file label to localized "no file" text
            self.file_label.configure(text=self.get_str('no_file'))
            
            # For simplicity, restart the app UI by destroying and recreating panels
            # Destroy all top-level children and recreate panels
            for widget in self.winfo_children():
                widget.destroy()
            
            # Recreate panels with updated language strings
            self.create_left_panel()
            self.create_center_panel()
            self.create_right_panel()

            # Notify user about successful language switch
            self.add_notification(self.get_str("ui_lang_switched"))
        
        except Exception as e:
            # If rebuilding fails, log a notification with the error.
            self.add_notification(f'Language switch failed: {e}')

    def open_pyqt_editor(self):
        """
        Open an editable modal text dialog using PyQt5's QTextEdit.
    
        The dialog:
          - loads the current content from the main editor,
          - allows the user to edit,
          - and writes changes back to the main editor if saved.
    
        The editor's text direction is set based on the current UI language
        (Right-to-Left for Arabic, Left-to-Right otherwise).
        """
        try:
            # Ensure a single QApplication instance (required by PyQt5).
            app = QApplication.instance()
            if not app:
                app = QApplication(sys.argv)
    
             # Create modal dialog and layout
            dialog = QDialog()
            dialog.setWindowTitle("Edit Text")
            dialog.resize(700, 600)
            dialog.setWindowModality(Qt.ApplicationModal)
    
            layout = QVBoxLayout(dialog)
    
            # QTextEdit as the advanced editor
            editor = QTextEdit()
            editor.setPlainText(self.text_editor.get("0.0", "end-1c"))
    
            # Set text direction and alignment depending on language
            editor.setLayoutDirection(Qt.RightToLeft)
            editor.setAlignment(Qt.AlignRight)
            layout.addWidget(editor)
    
            # Buttons layout (Save / Cancel)
            button_layout = QHBoxLayout()
            btn_save = QPushButton("💾 Save Changes")
            btn_cancel = QPushButton("❌ Cancel")
            button_layout.addWidget(btn_save)
            button_layout.addWidget(btn_cancel)
            layout.addLayout(button_layout)
    
            # Save changes callback: copy edited text back to main editor
            def save_changes():
                new_text = editor.toPlainText()
                self.text_editor.delete("0.0", "end")
                self.text_editor.insert("0.0", new_text)
                dialog.accept()

            # Cancel callback: close dialog without modifying main editor
            def cancel_edit():
                dialog.reject()
    
            btn_save.clicked.connect(save_changes)
            btn_cancel.clicked.connect(cancel_edit)

            # Execute dialog modally
            dialog.exec_()
    
        except Exception as e:
            # Any errors opening/editing are shown as notifications.
            self.add_notification(f"Edit window error: {e}")
            
    # ---------------- END of class ----------------

if __name__ == '__main__':
    app = TranscriptaApp()
    app.mainloop()