#!/usr/bin/env python3
"""
Voice Typing DBus Service

This module provides a DBus service that handles voice recording operations
for the GNOME Shell extension client.
"""

import asyncio
import hashlib
import signal
import sys
from typing import Optional, AsyncGenerator
from functools import partial
from datetime import datetime
from pathlib import Path

from dbus_next import BusType
from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface, method, signal as dbus_signal

from .logging import root_logger
from .audio import AsyncAudioRecorder
from .openai_client import (
    OpenAITranscriptionModel,
    OpenAIClient,
    GroqTranscriptionModel,
    TranscriptionModel,
    transcription_model_from_provider,
    GroqClient,
    BaseAIClient,
)
from .virtual_keyboard import VirtualKeyboard
from .gnome_settings import GNOMESettingsReader
from .const import InferenceProvider


class TranscriptionClients:
    def __init__(self):
        self.clients = {}

    def get(self, provider: InferenceProvider, api_key: str) -> BaseAIClient:
        if not api_key:
            raise ValueError(f"API key not found for provider {provider}")

        match provider:
            case InferenceProvider.OPENAI:
                return self.clients.setdefault(provider, OpenAIClient(api_key))
            case InferenceProvider.GROQ:
                return self.clients.setdefault(provider, GroqClient(api_key))


class TranscriptionTask:
    def __init__(
        self,
        audio_path: Path,
        language: str,
        provider: InferenceProvider,
        model: TranscriptionModel,
        client: BaseAIClient,
    ):
        self.audio_path = audio_path
        self.provider = provider
        self.model = model
        self.language = language
        self.client = client


class TypingService:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.virtual_keyboard = VirtualKeyboard(emit_delay=0.005)
        self.processing_task = asyncio.create_task(self.process_queue())

    def add_to_queue(self, text: str):
        self.queue.put_nowait(text)

    async def process_queue(self):
        try:
            while True:
                text = await self.queue.get()
                await asyncio.to_thread(self.virtual_keyboard.type_text, text)
        except asyncio.CancelledError:
            root_logger.info("VoiceTypist processing queue cancelled")
        except Exception as e:
            root_logger.error(f"Error in VoiceTypist processing queue: {e}")

    def close(self):
        self.virtual_keyboard.close()


class TranscriptionService:
    def __init__(self):
        self.queue = asyncio.Queue()

    def add_to_queue(self, task: TranscriptionTask):
        self.queue.put_nowait(task)

    async def process_queue(self) -> AsyncGenerator[TranscriptionTask, None]:
        try:
            while True:
                transcription_task = await self.queue.get()
                root_logger.info(
                    f"Processing audio data with model {transcription_task.provider}/{transcription_task.model} and language {transcription_task.language}"
                )
                text = await transcription_task.client.create_transcription(
                    transcription_task.audio_path, transcription_task.model, transcription_task.language
                )
                text = text.decode("utf-8").strip()
                transcription_task.transcription = text
                yield transcription_task
        except asyncio.CancelledError:
            root_logger.info("TranscriptionService processing queue cancelled")
        except Exception as e:
            root_logger.error(f"Error in TranscriptionService processing queue: {e}")


class VoiceTypingInterface(ServiceInterface):
    """DBus interface for voice typing operations."""

    def __init__(self):
        super().__init__("com.cxlab.VoiceTypingInterface")
        self._is_recording = False
        self._recording_task: Optional[asyncio.Task] = None
        self._audio_recorder = AsyncAudioRecorder()
        self.settings = GNOMESettingsReader("org.gnome.shell.extensions.voicetyping")
        self.transcription_srv = TranscriptionService()
        self.clients = TranscriptionClients()
        self.typing_srv = TypingService()
        self._processing_task = asyncio.create_task(self._processing_pipeline())
        root_logger.info("VoiceTypingInterface initialized")
        list_devices = self._audio_recorder.list_devices()
        root_logger.info(f"Available audio devices: {list_devices}")

    def close(self):
        self.typing_srv.close()
        self._processing_task.cancel()

    async def _processing_pipeline(self):
        async for transcription_task in self.transcription_srv.process_queue():
            if transcription_task.transcription:
                transcritption_md5 = hashlib.md5(transcription_task.transcription.encode("utf-8")).hexdigest()
                transcription_path = (transcription_task.audio_path.parent / transcritption_md5).with_suffix(".txt")
                with open(transcription_path, "w", encoding="utf-8") as f:
                    f.write(transcription_task.transcription)
                self.typing_srv.add_to_queue(transcription_task.transcription)
            else:
                root_logger.error(f"Failed to transcribe {transcription_task.audio_path}")

    @method()
    async def StartRecording(self, device_name: "s") -> "s":  # noqa: F821
        """Start voice recording."""

        if self._is_recording:
            root_logger.warning("Recording already in progress")
            return "already_recording"

        try:
            # Start the audio recorder with the selected device
            success = await self._audio_recorder.start(device_name)
            if not success:
                return "recording_failed"

            self._is_recording = True
            root_logger.info("Started voice recording")
            self.RecordingStateChanged(True)
            return "recording_started"
        except Exception as e:
            root_logger.error(f"Failed to start recording: {e}")
            self._is_recording = False
            return "recording_failed"

    @method()
    async def StopRecording(self, language: "s", provider: "s", model: "s", api_key: "s") -> "s":  # noqa: F821
        """Stop voice recording."""
        if not self._is_recording:
            root_logger.warning("No recording in progress")
            return "not_recording"

        try:
            self._is_recording = False

            # Stop the audio recorder and get the audio data
            audio_data = await self._audio_recorder.stop()
            if audio_data:
                root_logger.info(f"Captured {len(audio_data)} bytes of audio")
                # generate filename in format YYYY-MM-DD_HH-MM-SS.wav
                now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                md5_hash = hashlib.md5(audio_data).hexdigest()
                filename = (Path.cwd() / Path("recordings") / now_str / md5_hash).with_suffix(".wav")
                root_logger.info("Saving audio to %s", filename.resolve())
                audio_path = await self._audio_recorder.save_to_file(audio_data, filename)
                provider = InferenceProvider(provider)
                model = transcription_model_from_provider(provider, model)
                client = self.clients.get(provider, api_key)
                self.transcription_srv.add_to_queue(TranscriptionTask(audio_path, language, provider, model, client))

            root_logger.info("Stopped voice recording")
            self.RecordingStateChanged(False)
            return "recording_stopped"
        except Exception as e:
            root_logger.error(f"Failed to stop recording: {e}")
            return "stop_failed"

    @method()
    def GetRecordingState(self) -> "b":  # noqa: F821
        """Get current recording state."""
        return self._is_recording

    @method()
    def GetAvailableInferenceProviders(self) -> "as":  # noqa: F821 F722
        """Get list of available inference providers."""
        providers = list(provider.value for provider in InferenceProvider)
        return providers

    @method()
    def GetAvailableProviderModels(self, provider: "s") -> "as":  # noqa: F821 F722
        """Get list of available inference providers."""
        match InferenceProvider(provider):
            case InferenceProvider.OPENAI:
                return [model.value for model in OpenAITranscriptionModel]
            case InferenceProvider.GROQ:
                return [model.value for model in GroqTranscriptionModel]

    @method()
    def GetAvailableAudioSources(self) -> "as":  # noqa: F821 F722
        """Get list of available audio sources for recording."""
        devices = self._audio_recorder.list_devices()
        # Return device names in order, the index will be the position in the list
        return [device["name"] for device in devices]

    @dbus_signal()
    def RecordingStateChanged(self, is_recording: bool) -> None:
        """Signal emitted when recording state changes."""
        pass


class VoiceTypingService:
    """Main DBus service class."""

    def __init__(self):
        self.bus: Optional[MessageBus] = None
        self.interface: Optional[VoiceTypingInterface] = None
        self._shutdown_event = asyncio.Event()
        self._loop = asyncio.get_event_loop()

    async def start(self) -> None:
        """Start the DBus service."""
        # Connect to the session bus
        self.bus = await MessageBus(bus_type=BusType.SYSTEM).connect()

        # Create and export the interface
        self.interface = VoiceTypingInterface()
        self.bus.export("/com/cxlab/VoiceTyping", self.interface)

        # Request the service name
        await self.bus.request_name("com.cxlab.VoiceTyping")

        root_logger.info("Voice Typing DBus service started successfully")
        root_logger.info("Service: com.cxlab.VoiceTyping")
        root_logger.info("Object path: /com/cxlab/VoiceTyping")
        root_logger.info("Interface: com.cxlab.VoiceTypingInterface")

        # Set up signal handlers for graceful shutdown
        for sig in (signal.SIGINT, signal.SIGTERM):
            self._loop.add_signal_handler(sig, partial(self._signal_handler, sig, self._loop))

        # Wait for shutdown signal
        await self._shutdown_event.wait()

    async def stop(self) -> None:
        """Stop the DBus service."""
        try:
            if self.interface and self.interface._is_recording:
                self.interface.StopRecording()

            if self.bus:
                self.bus.disconnect()
        except Exception as e:
            root_logger.debug(f"Error stopping DBus service: {e}")
        finally:
            root_logger.info("Voice Typing DBus service stopped")
            self.interface.close()

    def _signal_handler(self, signum: int, loop: asyncio.AbstractEventLoop) -> None:
        """Handle shutdown signals."""
        root_logger.info(f"Received signal {signum}, shutting down...")
        self._shutdown_event.set()


async def main() -> None:
    """Main entry point for the DBus service."""
    service = VoiceTypingService()

    try:
        await service.start()
    except KeyboardInterrupt:
        root_logger.info("Interrupted by user")
    except Exception:
        root_logger.exception("Service error:")
    finally:
        await service.stop()


def server() -> None:
    """CLI entry point."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        root_logger.info("Service interrupted")
    except Exception as e:
        root_logger.error(f"CLI error: {e}")
        sys.exit(1)
    finally:
        sys.exit(0)


if __name__ == "__main__":
    server()
