"""
Transcripta
Copyright (c) 2025 Seif Eldeen Fathi
Licensed under a commercial one-time license.
"""
import numpy as np
import threading
import tempfile

# ---------------- Audio Recorder helper ----------------
class AudioRecorder:
    """
    A simple audio recorder class using the sounddevice library.
    
    Records audio input from the microphone in a background thread,
    stores captured frames, and saves them as a WAV, mp3 , flac file when stopped.

    Usage:
        rec = AudioRecorder()
        rec.start("temp.wav")
        ...
        rec.stop() -> returns the path to the saved file
    """
    def __init__(self, samplerate=44100, channels=1):
        """
        Initialize the audio recorder with given sample rate and channel count.

        Args:
            samplerate (int): Sampling rate in Hz. Default is 44100.
            channels (int): Number of audio channels. Default is 1 (mono).
        """
        
        self.samplerate = samplerate
        self.channels = channels
        self.recording = False
        self.frames = []
        self.thread = None
        self.filename = None
        # Initialize basic attributes for recording state and parameters.

    def start(self, filename=None):
        """
        Start recording audio from the default input device.

        Args:
            filename (str, optional): File path to save the recorded WAV audio.
                                     If not provided, a temporary file will be created.
        Returns:
            str: The file path where the audio will be saved.
        """
        # If no filename is provided, create a temporary one.
        
        if filename is None:
            filename = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
        self.filename = filename
        self.frames = []
        self.recording = True


        # Inner function to handle continuous audio recording.

        def _record():
            import sounddevice as sd
            # Open the input audio stream and collect chunks of data.
            try:
                with sd.InputStream(samplerate=self.samplerate, channels=self.channels, callback=self._callback):
                    while self.recording:
                        sd.sleep(100)
            except Exception as e:
                # If an error occurs, store it and stop recording.
                self._error = e
                self.recording = False


        # Run the recording loop in a background thread.
        self.thread = threading.Thread(target=_record, daemon=True)
        self.thread.start()
        return self.filename

    def _callback(self, indata, frames, time, status):
        """
        Callback function triggered by sounddevice for each audio chunk.

        Args:
            indata (numpy.ndarray): The recorded audio data.
            frames (int): Number of frames in this chunk.
            time (CData): Timing information.
            status (CallbackFlags): Status object with info/warnings.
        """
        
        if status:
            # Optional: log or handle sounddevice status messages.
            pass

        # If still recording, save the incoming data frame.
        if self.recording:
            self.frames.append(indata.copy())

    def stop(self):
        """
        Stop the recording process, merge frames, and save the audio file.

        Returns:
            str: The path to the final saved WAV file.
        """
        self.recording = False

        
        # Wait for the recording thread to finish properly.
        if self.thread:
            self.thread.join(timeout=1.0)

        # concatenate frames into one numpy array
        
        if len(self.frames) == 0:
             # If no audio was captured, create a short silent file.To prevent Errors
            audio = np.zeros((1, self.channels), dtype=np.float32)
        else:
            audio = np.concatenate(self.frames, axis=0)

        # write WAV (16-bit)
        import wave
        with wave.open(self.filename, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.samplerate)
            pcm = (audio * 32767).astype("int16").tobytes()
            wf.writeframes(pcm)
            
        # Return the path to the saved WAV file.
        return self.filename
