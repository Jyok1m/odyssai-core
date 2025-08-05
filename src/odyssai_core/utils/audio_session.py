import tempfile
import textwrap
import shutil
import sounddevice as sd
import numpy as np
from pathlib import Path
from scipy.io.wavfile import write

TERMINAL_WIDTH = shutil.get_terminal_size((80, 20)).columns


class RecorderSession:
    """
    Session to handle audio recording using sounddevice.
    Suitable for start/stop triggered recording workflows.
    """

    def __init__(self):
        self.__samplerate = 44100  # Default sample rate in Hz
        self.__channels = 1  # Mono audio
        self.__dtype = "int16"  # 16-bit audio format
        self.__recording = []
        self.__stream = None
        self.is_recording = False
        self.output_path = None

    def _callback(self, indata, frames, time, status):
        self.__recording.append(indata.copy())

    def start(self):
        if self.is_recording:
            raise RuntimeError("Recording is already in progress.")

        # Clean up previous Odyssai temp files
        tmp_dir = Path(tempfile.gettempdir())
        for file in tmp_dir.glob("odyssai_*.wav"):
            file.unlink()

        self.__recording = []
        self.__stream = sd.InputStream(
            samplerate=self.__samplerate,
            channels=self.__channels,
            dtype=self.__dtype,
            callback=self._callback,
            blocksize=0,  # optimal for low-latency recording
        )
        self.__stream.start()
        self.is_recording = True

        cue = "Press Enter to STOP recording..."
        print("\n")
        print(textwrap.fill(f"AI: 🔴 {cue}", width=TERMINAL_WIDTH))

    def stop(self) -> str:
        if not self.is_recording or not self.__stream:
            raise RuntimeError("Recording is not active or stream is not initialized.")

        self.__stream.stop()
        self.__stream.close()
        self.is_recording = False

        audio_data = np.concatenate(self.__recording, axis=0)

        with tempfile.NamedTemporaryFile(
            suffix=".wav", prefix="odyssai_", delete=False
        ) as tmpfile:
            write(tmpfile.name, self.__samplerate, audio_data)
            self.output_path = tmpfile.name

        return self.output_path


# Singleton instance for session-wide access
recorder = RecorderSession()
