#!/usr/bin/env python3
"""
Voice Typing DBus Service

This module provides a DBus service that handles voice recording operations
for the GNOME Shell extension client.
"""

import asyncio
import signal
import sys
from typing import Optional
from functools import partial
import time
from pathlib import Path

from dbus_next import BusType
from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface, method, signal as dbus_signal

from .logging import root_logger
from .audio import AsyncAudioRecorder
from .config import settings
from .openai_client import OpenAITranscriptionModel, OpenAIClient
from .virtual_keyboard import VirtualKeyboard
from .gnome_settings import GNOMESettingsReader
from .const import GNOMESchemaKey


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
    def __init__(self, model: OpenAITranscriptionModel, api_key: str):
        self.openai_client = OpenAIClient(api_key)
        self.model = model
        self.queue = asyncio.Queue()

    def add_to_queue(self, audio_path: Path, language: str):
        self.queue.put_nowait((audio_path, language))

    async def process_queue(self):
        try:
            while True:
                audio_data, language = await self.queue.get()
                root_logger.info(f"Processing audio data with model {self.model} and language {language}")
                text = await self.openai_client.create_transcription(audio_data, self.model, language)
                text = text.decode("utf-8").strip()
                yield text
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
        self.transcription_srv = TranscriptionService(OpenAITranscriptionModel.whisper_1, settings.OPENAI_API_KEY)
        self.typing_srv = TypingService()
        self._processing_task = asyncio.create_task(self._processing_pipeline())
        root_logger.info("VoiceTypingInterface initialized")
        list_devices = self._audio_recorder.list_devices()
        root_logger.info(f"Available audio devices: {list_devices}")

    def close(self):
        self.typing_srv.close()
        self._processing_task.cancel()

    async def _processing_pipeline(self):
        async for text in self.transcription_srv.process_queue():
            self.typing_srv.add_to_queue(text)

    @method()
    async def StartRecording(self) -> "s":  # noqa: F821
        """Start voice recording."""

        if self._is_recording:
            root_logger.warning("Recording already in progress")
            return "already_recording"

        try:
            # Start the audio recorder
            success = await self._audio_recorder.start()
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
    async def StopRecording(self) -> "s":  # noqa: F821
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
                # generate a random filename based on mtime
                filename = f"{int(time.time())}.wav"
                audio_path = await self._audio_recorder.save_to_file(audio_data, filename)
                language = self.settings.get_key(GNOMESchemaKey.TRANSCRIPTION_LANGUAGE)
                self.transcription_srv.add_to_queue(audio_path, language)

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
        self.bus = await MessageBus(bus_type=BusType.SESSION).connect()

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
