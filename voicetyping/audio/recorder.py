# Copyright (c) 2024-2026 Lukasz Jachym <lukasz.jachym@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

import pathlib
import os
from abc import abstractmethod
from typing import Any, TypeAlias
import hashlib

import pyaudio
import lameenc
import numpy as np

from ..logging import root_logger
from ..errors import DeviceAccessError, AudioSaveError
from .sampler import Resampler

logger = root_logger.getChild(__name__)


class AbstractAudioRecording:
    def __init__(self, stream: pyaudio.Stream, **kwargs):
        self._stream = stream
        self._data = bytearray()

    @abstractmethod
    def add_frames(self, in_data, frame_count, time_info, status):
        raise NotImplementedError

    @abstractmethod
    def save(self, path: pathlib.Path) -> pathlib.Path | None:
        raise NotImplementedError

    def save_data(self, data: bytes | bytearray, path: pathlib.Path):
        if not self._stream.is_stopped():
            raise AudioSaveError("Cannot save audio data while stream is still active")
        os.makedirs(path.parent, exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)

    def stop(self):
        if not self._stream.is_stopped():
            self._stream.stop_stream()

    def is_recording(self) -> bool:
        return not self._stream.is_stopped()

    def fingerprint(self) -> str:
        md5_hash = hashlib.md5(self._data).hexdigest()
        return md5_hash

    def cleanup(self):
        if self._stream.is_active():
            self._stream.stop_stream()
        self._stream.close()
        self._data.clear()


AudioRecording: TypeAlias = AbstractAudioRecording


class Mp3AudioRecording(AbstractAudioRecording):
    def __init__(self, stream, *, bit_rate=128, sample_rate=44100, channels=1, quality=7):
        super().__init__(stream)
        """

        :param bit_rate:
        :param sample_rate:
        :param channels:
        :param quality: 2 = high, 7 = low
        """
        self.encoder = lameenc.Encoder()
        self.encoder.set_bit_rate(bit_rate)
        self.encoder.set_in_sample_rate(sample_rate)
        self.encoder.set_channels(channels)
        self.encoder.set_quality(quality)

    def add_frames(self, in_data, frame_count, time_info, status):
        self._data.extend(self.encoder.encode(in_data))
        return None, pyaudio.paContinue

    def save(self, path: pathlib.Path) -> pathlib.Path | None:
        if path.suffix != ".mp3":
            path = path.with_suffix(".mp3")
        self._data.extend(self.encoder.flush())
        try:
            self.save_data(self._data, path)
            return path
        except Exception as e:
            raise AudioSaveError(f"Failed to save audio to {path}: {e}") from e


class AudioRecorder:
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

        logger.info(f"AudioRecorder initialized: {sample_rate}Hz, {channels}ch, {chunk_size} chunks")

    def list_devices(self) -> list[dict[str, Any]]:
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

    def get_recording_device_by_name(self, device_name: str):
        devices = self.list_devices()
        for device in devices:
            if device["name"] == device_name:
                return device
        return None

    def create_recording(self, device_name: str) -> AudioRecording | None:
        recording = None
        assert device_name is not None, "Device name is required"
        recording_device = self.get_recording_device_by_name(device_name)

        assert recording_device is not None, f"Device index not found for device name: {device_name}"
        logger.debug("Starting recording using: device name: %s", recording_device)
        device_sample_rate = int(recording_device["sample_rate"])
        logger.debug(f"Using device's native sample rate: {device_sample_rate} Hz")

        resampler = Resampler(input_rate=device_sample_rate, target_rate=self.sample_rate)

        def stream_callback(in_data, frame_count, time_info, status):
            pcm = np.frombuffer(in_data, dtype=np.int16)
            resampled_pcm = resampler.resample(pcm)
            return recording.add_frames(resampled_pcm, frame_count, time_info, status)

        try:
            stream = self._pyaudio.open(
                format=self.format_type,
                channels=self.channels,
                rate=device_sample_rate,  # Use device's native sample rate
                input=True,
                input_device_index=recording_device["index"],
                frames_per_buffer=self.chunk_size,
                stream_callback=stream_callback,
            )
            recording = Mp3AudioRecording(
                stream,
                bit_rate=128,
                sample_rate=self.sample_rate,
                channels=self.channels,
                quality=7,
            )
            logger.info("Audio recording started")
            return recording

        except Exception as e:
            raise DeviceAccessError(f"Failed to create recording: {e}") from e
