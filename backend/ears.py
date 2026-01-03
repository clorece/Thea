"""
Ears module for Rin - captures system audio via WASAPI loopback.
Uses Windows Audio Session API directly for maximum compatibility.
"""

import numpy as np
import threading
import collections
import time
import io
import wave
import ctypes
from ctypes import wintypes

# Try different audio capture methods in order of preference
_audio_method = None


class Ears:
    def __init__(self, sample_rate=44100, buffer_seconds=10.0):
        self.sample_rate = sample_rate
        self.buffer_seconds = buffer_seconds
        
        # Ring buffer to store audio chunks (0.5s each)
        self.max_chunks = int(buffer_seconds * 2)
        self.audio_buffer = collections.deque(maxlen=self.max_chunks)
        
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        self.mic = None
        self.device_name = "Unknown"
        
        self._init_device()

    def _init_device(self):
        """Initialize the loopback audio device using soundcard with numpy fix."""
        try:
            # Apply numpy compatibility fix BEFORE importing soundcard
            if not hasattr(np, 'fromstring'):
                # Create a wrapper that handles the binary mode case
                def fromstring_compat(string, dtype=float, count=-1, sep=''):
                    if sep == '':
                        # Binary mode - use frombuffer
                        return np.frombuffer(string, dtype=dtype, count=count)
                    else:
                        # Text mode - not supported in numpy 2.0, raise clear error
                        raise ValueError("Text mode fromstring not supported")
                np.fromstring = fromstring_compat
            
            import soundcard as sc
            
            # Get default speaker
            default_speaker = sc.default_speaker()
            default_name = default_speaker.name if default_speaker else ""
            print(f"[Ears] System default speaker: {default_name}")
            
            # Get all loopback devices
            mics = sc.all_microphones(include_loopback=True)
            loopbacks = [m for m in mics if m.isloopback]
            
            # Priority: try default speaker's loopback first, then others
            sorted_loopbacks = sorted(
                loopbacks, 
                key=lambda m: 0 if (default_name and default_name in m.name) else 1
            )
            
            # Find first working device
            for mic in sorted_loopbacks:
                try:
                    # Test the device
                    with mic.recorder(samplerate=self.sample_rate) as rec:
                        test_data = rec.record(numframes=int(self.sample_rate * 0.1))
                        if len(test_data) > 0:
                            self.mic = mic
                            self.device_name = mic.name
                            is_default = default_name and default_name in mic.name
                            print(f"[Ears] Using: {mic.name}" + (" (system default)" if is_default else ""))
                            return
                except Exception as e:
                    error_str = str(e)
                    # Skip known bad devices silently
                    if "0x88890007" in error_str or "fromstring" in error_str:
                        continue
                    print(f"[Ears] Skipping {mic.name}: {e}")
            
            print("[Ears] WARNING: No working audio loopback device found.")
            print("[Ears] Audio features will be disabled.")
            self.mic = None
            
        except Exception as e:
            print(f"[Ears] Init failed: {e}")
            self.mic = None

    def start(self):
        """Start background audio capture."""
        if self.running:
            return
        if not self.mic:
            print("[Ears] Cannot start - no audio device available")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        print("[Ears] Started listening...")

    def stop(self):
        """Stop audio capture."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        print("[Ears] Stopped.")

    def _listen_loop(self):
        """Background thread to continuously record loopback audio."""
        chunk_duration = 0.5  # seconds
        chunk_size = int(self.sample_rate * chunk_duration)
        
        try:
            import soundcard as sc
            
            with self.mic.recorder(samplerate=self.sample_rate) as recorder:
                print(f"[Ears] Recording at {self.sample_rate}Hz from {self.device_name}")
                error_count = 0
                while self.running:
                    try:
                        data = recorder.record(numframes=chunk_size)
                        with self.lock:
                            self.audio_buffer.append(data)
                        error_count = 0  # Reset on success
                    except Exception as e:
                        error_count += 1
                        if error_count <= 3:
                            print(f"[Ears] Record error: {e}")
                        elif error_count == 4:
                            print("[Ears] Suppressing further errors...")
                        time.sleep(0.1)
        except Exception as e:
            print(f"[Ears] Recording failed: {e}")
            self.running = False

    def get_recent_audio_bytes(self, duration_seconds=5.0):
        """
        Returns a WAV file in bytes of the last N seconds.
        Returns None if no audio captured.
        """
        if not self.mic or not self.running:
            return None
            
        required_chunks = int(duration_seconds * 2)
        
        with self.lock:
            if not self.audio_buffer:
                return None
            chunks = list(self.audio_buffer)[-required_chunks:]
            
        if not chunks:
            return None
            
        # Concatenate
        full_data = np.concatenate(chunks, axis=0)
        
        # Convert to int16 PCM for WAV
        pcm_data = (full_data * 32767).astype(np.int16)
        
        # Write to WAV
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setnchannels(pcm_data.shape[1] if len(pcm_data.shape) > 1 else 1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(pcm_data.tobytes())
            
        return wav_buffer.getvalue()

    def get_current_volume(self):
        """Get approximate current volume level (0.0 to 1.0)."""
        with self.lock:
            if not self.audio_buffer:
                return 0.0
            last_chunk = self.audio_buffer[-1]
            return float(np.max(np.abs(last_chunk)))


# Singleton instance
ears = Ears()
