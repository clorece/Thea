"""
Ears module for Rin - captures system audio via C# WASAPI loopback tool.
Uses external AudioCapture.exe for reliable Windows audio capture.
"""

import numpy as np
import threading
import subprocess
import tempfile
import time
import io
import wave
import os
from pathlib import Path

# Path to the AudioCapture tool
_TOOL_DIR = Path(__file__).parent.parent / "tools" / "AudioCapture" / "publish"
_AUDIO_CAPTURE_EXE = _TOOL_DIR / "AudioCapture.exe"


class Ears:
    def __init__(self, sample_rate=48000, buffer_seconds=10.0):
        # C# tool outputs 48kHz by default (system audio rate)
        self.sample_rate = sample_rate
        self.buffer_seconds = buffer_seconds
        
        # Cache of recent audio bytes (WAV format)
        self._audio_cache = None
        self._cache_time = 0
        self._cache_duration = 0
        
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        self.device_name = "Unknown"
        
        # Volume tracking
        self._last_volume = 0.0
        self._current_volume = 0.0
        
        self._init_device()

    def _init_device(self):
        """Check that the C# audio capture tool exists."""
        if not _AUDIO_CAPTURE_EXE.exists():
            print(f"[Ears] ERROR: AudioCapture.exe not found at {_AUDIO_CAPTURE_EXE}")
            print("[Ears] Audio features will be disabled.")
            return
        
        # Test the tool by listing devices
        try:
            result = subprocess.run(
                [str(_AUDIO_CAPTURE_EXE), "--list"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Parse output to find default device
            for line in result.stdout.split('\n'):
                if "[DEFAULT]" in line:
                    self.device_name = line.replace("[DEFAULT]", "").strip()
                    break
            
            if self.device_name == "Unknown":
                # Fallback: get first device name
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if line and not line.startswith("==="):
                        self.device_name = line
                        break
            
            print(f"[Ears] System default speaker: {self.device_name}")
            print(f"[Ears] Using: {self.device_name} (system default)")
            
        except Exception as e:
            print(f"[Ears] Init failed: {e}")

    def start(self):
        """Start background audio monitoring."""
        if self.running:
            return
        if not _AUDIO_CAPTURE_EXE.exists():
            print("[Ears] Cannot start - AudioCapture.exe not found")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        print("[Ears] Started listening...")
        print(f"[Ears] Recording at {self.sample_rate}Hz from {self.device_name}")

    def stop(self):
        """Stop audio monitoring."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        print("[Ears] Stopped.")

    def _monitor_loop(self):
        """Background thread to periodically capture and cache audio."""
        # Capture audio every few seconds to keep cache fresh
        capture_interval = 3.0  # seconds between captures
        capture_duration = 5    # seconds to capture each time
        
        while self.running:
            try:
                # Capture audio to temp file
                audio_bytes = self._capture_audio(capture_duration)
                if audio_bytes:
                    with self.lock:
                        self._audio_cache = audio_bytes
                        self._cache_time = time.time()
                        self._cache_duration = capture_duration
                        
                        # Calculate volume from the captured audio
                        self._update_volume_from_bytes(audio_bytes)
                        
            except Exception as e:
                print(f"[Ears] Monitor error: {e}")
            
            # Wait before next capture
            time.sleep(capture_interval)

    def _capture_audio(self, duration_seconds: int) -> bytes:
        """Capture audio using the C# tool and return WAV bytes."""
        try:
            # Create temp file for output
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tf:
                temp_path = tf.name
            
            # Run capture tool
            result = subprocess.run(
                [str(_AUDIO_CAPTURE_EXE), "--duration", str(duration_seconds), "--output", temp_path],
                capture_output=True,
                text=True,
                timeout=duration_seconds + 5
            )
            
            if result.returncode != 0:
                print(f"[Ears] Capture failed: {result.stderr}")
                return None
            
            # Read the WAV file
            if os.path.exists(temp_path):
                with open(temp_path, 'rb') as f:
                    audio_bytes = f.read()
                os.unlink(temp_path)  # Clean up
                return audio_bytes
            
            return None
            
        except subprocess.TimeoutExpired:
            print("[Ears] Capture timed out")
            return None
        except Exception as e:
            print(f"[Ears] Capture error: {e}")
            return None

    def _update_volume_from_bytes(self, audio_bytes: bytes):
        """Update volume tracking from captured audio."""
        try:
            wav_io = io.BytesIO(audio_bytes)
            with wave.open(wav_io, 'rb') as wf:
                n_frames = wf.getnframes()
                audio_data = wf.readframes(n_frames)
                bits = wf.getsampwidth() * 8
            
            # Convert based on bit depth (C# outputs 32-bit float)
            if bits == 32:
                # 32-bit float WAV
                audio_np = np.frombuffer(audio_data, dtype=np.float32)
            else:
                # 16-bit PCM
                audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Calculate RMS volume (last portion for current volume)
            chunk_size = min(len(audio_np), 48000)  # Last ~1 second
            self._current_volume = float(np.sqrt(np.mean(audio_np[-chunk_size:]**2)))
            
        except Exception as e:
            pass  # Silently fail volume updates

    def get_recent_audio_bytes(self, duration_seconds=5.0) -> bytes:
        """
        Returns a WAV file in bytes of recent audio.
        Returns None if no audio captured.
        """
        # If we have recent cache, use it
        with self.lock:
            if self._audio_cache and (time.time() - self._cache_time) < 10:
                return self._audio_cache
        
        # Otherwise capture fresh audio
        return self._capture_audio(int(duration_seconds))

    def get_current_volume(self) -> float:
        """Get approximate current volume level (0.0 to 1.0)."""
        return min(1.0, self._current_volume * 5)  # Scale up for visibility

    def get_volume_delta(self) -> tuple:
        """
        Get the change in volume since last check.
        Returns a tuple: (current_volume, delta)
        Delta > 0 means volume increased, < 0 means decreased.
        """
        current = self.get_current_volume()
        delta = current - self._last_volume
        self._last_volume = current
        return (current, delta)


# Singleton instance
ears = Ears()
