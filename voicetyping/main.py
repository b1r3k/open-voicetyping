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
from typing import Optional, AsyncGenerator, Callable
from functools import partial
from datetime import datetime
from pathlib import Path

from dbus_next import BusType
from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface, method, signal as dbus_signal

from .logging import root_logger
from .audio.recorder import AudioRecorder, AudioRecording
from .errors import set_error_handler, emit_error, VoiceTypingError
from .openai_client import (
    OpenAITranscriptionModel,
    GroqTranscriptionModel,
    TranscriptionModel,
    transcription_model_from_provider,
    BaseAIClient,
)
from .const import InferenceProvider
from .keyboard.dbus_client import VirtualKeyboardDBusClient
from .transcription_client import TranscriptionClients
from .state import ProcessingEvent, ProcessingState, ProcessingStateMachine


class TranscriptionTask:
    def __init__(
        self,
        audio_path: Path,
        language: str,
        provider: InferenceProvider,
        model: TranscriptionModel,
        client: BaseAIClient,
        store_transcripts: bool,
        on_start_callback: Callable,
        on_finish_callback: Callable,
    ):
        self.audio_path = audio_path
        self.provider = provider
        self.model = model
        self.language = language
        self.client = client
        self.store_transcripts = store_transcripts
        self.on_start_callback = on_start_callback
        self.on_finish_callback = on_finish_callback


class TranscriptionService:
    def __init__(self):
        self.queue = asyncio.Queue()

    def add_to_queue(self, task: TranscriptionTask):
        self.queue.put_nowait(task)

    async def process_queue(self) -> AsyncGenerator[TranscriptionTask, None]:
        while True:
            try:
                transcription_task = await self.queue.get()
                transcription_task.on_start_callback()

                # Nested try-except for transcription errors only
                try:
                    root_logger.info(
                        f"Processing audio data with model {transcription_task.provider}/{transcription_task.model} and language {transcription_task.language}"
                    )
                    text = await transcription_task.client.create_transcription(
                        transcription_task.audio_path, transcription_task.model, transcription_task.language
                    )
                    text = text.decode("utf-8").strip()
                    transcription_task.transcription = text
                except VoiceTypingError as e:
                    e.emit()
                    transcription_task.transcription = None  # Mark as failed
                except Exception as e:
                    emit_error("TranscriptionService", f"Unexpected error in TranscriptionService: {str(e)}")
                    transcription_task.transcription = None  # Mark as failed
                finally:
                    # Always call finish callback and yield, even on error
                    transcription_task.on_finish_callback()

                yield transcription_task  # ALWAYS YIELD - success or failure

            except asyncio.CancelledError:
                root_logger.info("TranscriptionService cancelled")
                break


class VoiceTypingInterface(ServiceInterface):
    """DBus interface for voice typing operations."""

    @property
    def audio_recorder(self):
        if not self._audio_recorder:
            self._audio_recorder = AudioRecorder()
        return self._audio_recorder

    def __init__(self):
        super().__init__("com.cxlab.VoiceTypingInterface")
        self._state = ProcessingStateMachine()
        self._state.add_listener(self._on_state_change)
        self._recording_task: Optional[asyncio.Task] = None
        self._audio_recorder: Optional[AudioRecorder] = None
        self._recording: Optional[AudioRecording] = None
        self.transcription_srv = TranscriptionService()
        self.clients = TranscriptionClients()
        self.keyboard_client = VirtualKeyboardDBusClient()
        self._processing_task = asyncio.create_task(self._processing_pipeline())
        # Set up context variable-based error handler for deep components
        set_error_handler(self._emit_error)
        root_logger.info("VoiceTypingInterface initialized")

    def _emit_error(self, category: str, message: str) -> None:
        """Helper to emit error signal."""
        root_logger.error(f"Error [{category}]: {message}")
        self.ErrorOccurred(category, message)

    def _on_state_change(self, old_state: ProcessingState, new_state: ProcessingState) -> None:
        """Handle state machine transitions by emitting DBus signal."""
        self.RecordingStateChanged()

    async def close(self):
        await self.keyboard_client.disconnect()
        self._processing_task.cancel()

    async def _processing_pipeline(self):
        # Connect to the keyboard service
        if not await self.keyboard_client.connect():
            root_logger.error("Failed to connect to VirtualKeyboard service")
            self._emit_error("keyboard", "Keyboard service unavailable")
            return

        async for transcription_task in self.transcription_srv.process_queue():
            if transcription_task.transcription and transcription_task.store_transcripts:
                transcritption_md5 = hashlib.md5(transcription_task.transcription.encode("utf-8")).hexdigest()
                transcription_path = (transcription_task.audio_path.parent / transcritption_md5).with_suffix(".txt")
                with open(transcription_path, "w", encoding="utf-8") as f:
                    f.write(transcription_task.transcription)
                # Send text to VirtualKeyboard via DBus
                await self.keyboard_client.emit(transcription_task.transcription)
            else:
                root_logger.error(f"Failed to transcribe {transcription_task.audio_path}")
                self._emit_error("transcription", "Failed to transcribe audio")
            if not transcription_task.store_transcripts and transcription_task.audio_path.exists():
                try:
                    root_logger.debug(f"Cleaning up audio file {transcription_task.audio_path}")
                    transcription_task.audio_path.unlink(missing_ok=True)
                    transcription_task.audio_path.parent.rmdir()
                except Exception as e:
                    root_logger.error(f"Failed to delete audio file {transcription_task.audio_path}: {e}")

    @method()
    async def StartRecording(self, device_name: "s", transcript_path: "s", store_transcripts: "b") -> "s":  # noqa: F821
        """Start voice recording."""

        if self._state.is_recording:
            root_logger.warning("Recording already in progress")
            return "already_recording"

        self.transcript_path = transcript_path
        self.store_transcripts = store_transcripts
        try:
            # Start the audio recorder with the selected device
            self._recording = self.audio_recorder.create_recording(device_name)
            self._state.transition(ProcessingEvent.START_RECORDING)
            root_logger.info("Started voice recording")
            return "recording_started"
        except Exception as e:
            root_logger.error(f"Failed to start recording: {e}")
            return "recording_failed"

    @method()
    async def StopRecording(self, language: "s", provider: "s", model: "s", api_key: "s") -> "s":  # noqa: F821
        """Stop voice recording."""
        if not self._state.is_recording:
            root_logger.warning("No recording in progress")
            return "not_recording"

        try:
            self._recording.stop()
            self._state.transition(ProcessingEvent.STOP_RECORDING)
            root_logger.info("Stopped voice recording")
            # generate filename in format YYYY-MM-DD_HH-MM-SS
            now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            self._state.transition(ProcessingEvent.TRANSFORM_START)
            md5_hash = self._recording.fingerprint()
            filename = Path(self.transcript_path) / now_str / md5_hash
            root_logger.info("Saving audio to %s", filename.resolve())
            audio_path = self._recording.save(filename)
            provider = InferenceProvider(provider)
            model = transcription_model_from_provider(provider, model)
            client = self.clients.get(provider, api_key)
            self._state.transition(ProcessingEvent.TRANSFORM_STOP)
            self.transcription_srv.add_to_queue(
                TranscriptionTask(
                    audio_path,
                    language,
                    provider,
                    model,
                    client,
                    self.store_transcripts,
                    lambda: self._state.transition(ProcessingEvent.TRANSCRIBE_START),
                    lambda: self._state.transition(ProcessingEvent.TRANSCRIBE_STOP),
                )
            )
            return "recording_stopped"
        except Exception as e:
            root_logger.error(f"Failed to stop recording: {e}")
            self._emit_error("internal", f"Failed to stop recording: {e}")
            return "stop_failed"
        finally:
            self._recording.cleanup()
            self._recording = None

    @method()
    def GetRecordingState(self) -> "b":  # noqa: F821
        """Get current recording state."""
        return self._state.is_recording

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
        devices = self.audio_recorder.list_devices()
        root_logger.info("Fetching audio sources: %s", devices)
        # Return device names in order, the index will be the position in the list
        return [device["name"] for device in devices]

    @dbus_signal()
    def RecordingStateChanged(self) -> "b":  # noqa: F821 F722
        """Signal emitted when recording state changes."""
        return self._state.is_recording

    @dbus_signal()
    def ErrorOccurred(self, category: "s", message: "s") -> "ss":  # noqa: F821 F722
        """Signal emitted when an error occurs. Returns (category, code, message)."""
        return [category, message]


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
            if self.interface and self.interface._state.is_recording:
                self.interface.StopRecording()

            if self.bus:
                self.bus.disconnect()
        except Exception as e:
            root_logger.debug(f"Error stopping DBus service: {e}")
        finally:
            root_logger.info("Voice Typing DBus service stopped")
            if self.interface:
                await self.interface.close()

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
        root_logger.error(f"Server error: {e}")
        sys.exit(1)
    finally:
        sys.exit(0)


if __name__ == "__main__":
    server()
