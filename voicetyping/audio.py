"""
Audio recording module for voice typing service.

This module provides asyncio-compatible audio recording functionality
using PyAudio for cross-platform compatibility.
"""

import asyncio
import wave
from typing import Optional, Callable, Any
import numpy as np
import pyaudio

from .logging import root_logger


class AudioRecorder:
    """Asyncio-compatible audio recorder using PyAudio."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 1024,
        format_type: int = pyaudio.paInt16,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.format_type = format_type

        self._pyaudio = pyaudio.PyAudio()
        self._stream: Optional[pyaudio.Stream] = None
        self._is_recording = False
        self._audio_frames: list[bytes] = []
        self._recording_task: Optional[asyncio.Task] = None

        root_logger.info(f"AudioRecorder initialized: {sample_rate}Hz, {channels}ch, {chunk_size} chunks")

    def __del__(self):
        """Cleanup PyAudio resources."""
        self._cleanup()

    def _cleanup(self):
        """Clean up PyAudio resources."""
        if self._stream:
            self._stream.close()
            self._stream = None
        if self._pyaudio:
            self._pyaudio.terminate()

    async def start_recording(self) -> bool:
        """Start recording audio asynchronously."""
        if self._is_recording:
            root_logger.warning("Recording already in progress")
            return False

        try:
            # Open audio stream
            self._stream = self._pyaudio.open(
                format=self.format_type,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback,
            )

            self._is_recording = True
            self._audio_frames = []

            # Start the recording task
            self._recording_task = asyncio.create_task(self._recording_loop())

            root_logger.info("Audio recording started")
            return True

        except Exception as e:
            root_logger.error(f"Failed to start recording: {e}")
            self._cleanup()
            return False

    async def stop_recording(self) -> Optional[bytes]:
        """Stop recording and return the recorded audio data."""
        if not self._is_recording:
            root_logger.warning("No recording in progress")
            return None

        try:
            self._is_recording = False

            # Cancel the recording task
            if self._recording_task and not self._recording_task.done():
                self._recording_task.cancel()
                try:
                    await self._recording_task
                except asyncio.CancelledError:
                    pass

            # Close the stream
            if self._stream:
                self._stream.stop_stream()
                self._stream.close()
                self._stream = None

            # Combine all audio frames
            if self._audio_frames:
                audio_data = b"".join(self._audio_frames)
                root_logger.info(f"Recording stopped. Captured {len(audio_data)} bytes")
                return audio_data
            else:
                root_logger.warning("No audio data captured")
                return None

        except Exception as e:
            root_logger.error(f"Failed to stop recording: {e}")
            return None

    def _audio_callback(self, in_data: bytes, frame_count: int, time_info: dict, status: int) -> tuple[bytes, int]:
        """Callback for PyAudio stream to capture audio data."""
        if self._is_recording:
            self._audio_frames.append(in_data)
        return (in_data, pyaudio.paContinue)

    async def _recording_loop(self) -> None:
        """Main recording loop that runs while recording is active."""
        try:
            while self._is_recording:
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
        except asyncio.CancelledError:
            root_logger.debug("Recording loop cancelled")
        except Exception as e:
            root_logger.error(f"Error in recording loop: {e}")

    def get_recording_state(self) -> bool:
        """Get current recording state."""
        return self._is_recording

    def get_audio_duration(self) -> float:
        """Get the duration of recorded audio in seconds."""
        if not self._audio_frames:
            return 0.0

        total_bytes = sum(len(frame) for frame in self._audio_frames)
        bytes_per_sample = self._pyaudio.get_sample_size(self.format_type)
        total_samples = total_bytes // bytes_per_sample
        return total_samples / self.sample_rate

    def save_audio_to_wav(self, audio_data: bytes, filename: str) -> bool:
        """Save audio data to a WAV file."""
        try:
            with wave.open(filename, "wb") as wav_file:
                wav_file.setnchannels(self.channels)
                wav_file.setsampwidth(self._pyaudio.get_sample_size(self.format_type))
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(audio_data)
            root_logger.info(f"Audio saved to {filename}")
            return True
        except Exception as e:
            root_logger.error(f"Failed to save audio to {filename}: {e}")
            return False

    def convert_to_numpy(self, audio_data: bytes) -> np.ndarray:
        """Convert audio data to numpy array."""
        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            return audio_array
        except Exception as e:
            root_logger.error(f"Failed to convert audio to numpy: {e}")
            return np.array([])

    def list_audio_devices(self) -> list[dict[str, Any]]:
        """List available audio input devices."""
        devices = []
        for i in range(self._pyaudio.get_device_count()):
            device_info = self._pyaudio.get_device_info_by_index(i)
            if device_info["maxInputChannels"] > 0:  # Only input devices
                devices.append(
                    {
                        "index": i,
                        "name": device_info["name"],
                        "channels": device_info["maxInputChannels"],
                        "sample_rate": device_info["defaultSampleRate"],
                    }
                )
        return devices


class AsyncAudioRecorder:
    """High-level async interface for audio recording."""

    def __init__(self, **kwargs):
        self._recorder = AudioRecorder(**kwargs)
        self._on_audio_ready: Optional[Callable[[bytes], None]] = None

    async def start(self) -> bool:
        """Start recording."""
        return await self._recorder.start_recording()

    async def stop(self) -> Optional[bytes]:
        """Stop recording and return audio data."""
        return await self._recorder.stop_recording()

    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._recorder.get_recording_state()

    def set_audio_ready_callback(self, callback: Callable[[bytes], None]) -> None:
        """Set callback for when audio is ready."""
        self._on_audio_ready = callback

    def list_devices(self) -> list[dict[str, Any]]:
        """List available audio devices."""
        return self._recorder.list_audio_devices()

    def save_to_file(self, audio_data: bytes, filename: str) -> bool:
        """Save audio data to file."""
        return self._recorder.save_audio_to_wav(audio_data, filename)
