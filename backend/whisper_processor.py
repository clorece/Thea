"""
Whisper Processor for Rin - Local audio transcription.
Uses OpenAI Whisper for converting audio bytes to text.
"""

import io
import wave
import numpy as np
from typing import Optional

# Whisper will be loaded lazily to avoid slow startup
_whisper_model = None
_whisper_available = False

def _load_whisper():
    """Lazily load whisper model on first use."""
    global _whisper_model, _whisper_available
    
    if _whisper_model is not None:
        return _whisper_model
    
    try:
        import whisper
        # Use 'base' model - good balance of speed and accuracy
        # Runs well on CPU with Ryzen 7 5800X3D
        print("[Whisper] Loading base model (this may take a moment)...")
        _whisper_model = whisper.load_model("base")
        _whisper_available = True
        print("[Whisper] Model loaded successfully")
        return _whisper_model
    except ImportError:
        print("[Whisper] openai-whisper not installed. Audio transcription disabled.")
        print("[Whisper] Install with: pip install openai-whisper")
        _whisper_available = False
        return None
    except Exception as e:
        print(f"[Whisper] Failed to load model: {e}")
        _whisper_available = False
        return None


class WhisperProcessor:
    """Local audio transcription using OpenAI Whisper."""
    
    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model = None
    
    @property
    def model(self):
        """Lazy-load the whisper model."""
        if self._model is None:
            self._model = _load_whisper()
        return self._model
    
    @property
    def is_available(self) -> bool:
        """Check if whisper is available."""
        # Try to load if not yet attempted
        if self._model is None and not _whisper_available:
            self._model = _load_whisper()
        return self._model is not None
    
    def transcribe(self, audio_bytes: bytes) -> Optional[str]:
        """
        Transcribe audio bytes (WAV format) to text.
        
        Args:
            audio_bytes: WAV file as bytes (supports 16-bit PCM or 32-bit float)
            
        Returns:
            Transcribed text or None if transcription failed
        """
        if not self.is_available:
            return None
        
        if not audio_bytes:
            return None
        
        try:
            # Parse WAV header manually to handle 32-bit float format
            # Standard wave module doesn't handle IEEE float well
            import struct
            
            wav_io = io.BytesIO(audio_bytes)
            
            # Read RIFF header
            riff = wav_io.read(4)
            if riff != b'RIFF':
                print("[Whisper] Not a valid WAV file")
                return None
            
            wav_io.read(4)  # file size
            wave_id = wav_io.read(4)
            if wave_id != b'WAVE':
                print("[Whisper] Not a valid WAV file")
                return None
            
            # Find fmt chunk
            sample_rate = 48000
            n_channels = 2
            bits_per_sample = 32
            is_float = False
            
            while True:
                chunk_id = wav_io.read(4)
                if len(chunk_id) < 4:
                    break
                chunk_size = struct.unpack('<I', wav_io.read(4))[0]
                
                if chunk_id == b'fmt ':
                    fmt_data = wav_io.read(chunk_size)
                    audio_format = struct.unpack('<H', fmt_data[0:2])[0]
                    n_channels = struct.unpack('<H', fmt_data[2:4])[0]
                    sample_rate = struct.unpack('<I', fmt_data[4:8])[0]
                    bits_per_sample = struct.unpack('<H', fmt_data[14:16])[0]
                    # Format 3 = IEEE float, Format 1 = PCM
                    is_float = (audio_format == 3)
                elif chunk_id == b'data':
                    audio_data = wav_io.read(chunk_size)
                    break
                else:
                    wav_io.read(chunk_size)  # Skip unknown chunks
            
            # Convert to float32 numpy array based on format
            if is_float and bits_per_sample == 32:
                # 32-bit float (from C# WASAPI capture)
                audio_np = np.frombuffer(audio_data, dtype=np.float32)
            elif bits_per_sample == 16:
                # 16-bit PCM
                audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            elif bits_per_sample == 24:
                # 24-bit PCM - convert manually
                n_samples = len(audio_data) // 3
                audio_np = np.zeros(n_samples, dtype=np.float32)
                for i in range(n_samples):
                    sample = int.from_bytes(audio_data[i*3:(i+1)*3], 'little', signed=True)
                    audio_np[i] = sample / 8388608.0  # 2^23
            else:
                print(f"[Whisper] Unsupported bit depth: {bits_per_sample}")
                return None
            
            # If stereo, convert to mono
            if n_channels == 2:
                audio_np = audio_np.reshape(-1, 2).mean(axis=1)
            elif n_channels > 2:
                audio_np = audio_np.reshape(-1, n_channels).mean(axis=1)
            
            # Resample to 16kHz if needed (Whisper expects 16kHz)
            if sample_rate != 16000:
                # Simple resampling using numpy
                duration = len(audio_np) / sample_rate
                target_length = int(duration * 16000)
                indices = np.linspace(0, len(audio_np) - 1, target_length).astype(int)
                audio_np = audio_np[indices]
            
            # Check for silence (skip transcription if too quiet)
            rms = np.sqrt(np.mean(audio_np**2))
            if rms < 0.01:  # Silence threshold
                return None
            
            # Transcribe
            result = self.model.transcribe(
                audio_np,
                language="en",  # Default to English, can be made configurable
                fp16=False,     # Use FP32 for CPU compatibility
                verbose=False
            )
            
            text = result.get("text", "").strip()
            
            # Skip if empty or just noise/music detected
            if not text or text.lower() in ["[music]", "(music)", "[silence]", ""]:
                return None
            
            print(f"[Whisper] Transcribed: {text[:50]}...")
            return text
            
        except Exception as e:
            print(f"[Whisper] Transcription failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def describe_audio(self, audio_bytes: bytes) -> Optional[str]:
        """
        Get a description of the audio content.
        Returns transcription if speech, or a description if music/ambient.
        """
        transcription = self.transcribe(audio_bytes)
        
        if transcription:
            return f"Audio: {transcription}"
        
        # If no speech detected, check if there's audio at all
        if audio_bytes:
            try:
                # Use same WAV parsing as transcribe
                import struct
                wav_io = io.BytesIO(audio_bytes)
                
                # Skip RIFF header
                wav_io.read(12)
                
                # Parse chunks to find format and data
                is_float = False
                bits_per_sample = 16
                audio_data = b''
                
                while True:
                    chunk_id = wav_io.read(4)
                    if len(chunk_id) < 4:
                        break
                    chunk_size = struct.unpack('<I', wav_io.read(4))[0]
                    
                    if chunk_id == b'fmt ':
                        fmt_data = wav_io.read(chunk_size)
                        audio_format = struct.unpack('<H', fmt_data[0:2])[0]
                        bits_per_sample = struct.unpack('<H', fmt_data[14:16])[0]
                        is_float = (audio_format == 3)
                    elif chunk_id == b'data':
                        audio_data = wav_io.read(chunk_size)
                        break
                    else:
                        wav_io.read(chunk_size)
                
                # Convert based on format
                if is_float and bits_per_sample == 32:
                    audio_np = np.frombuffer(audio_data, dtype=np.float32)
                else:
                    audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                
                rms = np.sqrt(np.mean(audio_np**2))
                
                if rms > 0.05:
                    return "Audio: Non-speech audio detected (music or ambient sounds)"
                elif rms > 0.01:
                    return "Audio: Quiet audio detected"
            except:
                pass
        
        return None


# Singleton instance
whisper_processor = WhisperProcessor()
