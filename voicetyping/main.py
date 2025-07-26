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

from dbus_next import BusType
from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface, method, signal as dbus_signal

from .logging import root_logger
from .audio import AsyncAudioRecorder
from .config import settings
from .openai_client import OpenAITranscriptionModel, OpenAIClient


class VoiceTypingInterface(ServiceInterface):
    """DBus interface for voice typing operations."""

    def __init__(self):
        super().__init__("com.cxlab.VoiceTypingInterface")
        self._is_recording = False
        self._recording_task: Optional[asyncio.Task] = None
        self._audio_recorder = AsyncAudioRecorder()
        self.openai_client = OpenAIClient(settings.OPENAI_API_KEY)
        root_logger.info("VoiceTypingInterface initialized")
        list_devices = self._audio_recorder.list_devices()
        root_logger.info(f"Available audio devices: {list_devices}")

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
            # Create a task to handle the recording process
            self._recording_task = asyncio.create_task(self._record_audio())
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
            if self._recording_task and not self._recording_task.done():
                self._recording_task.cancel()

            # Stop the audio recorder and get the audio data
            audio_data = await self._audio_recorder.stop()
            if audio_data:
                root_logger.info(f"Captured {len(audio_data)} bytes of audio")
                # generate a random filename based on mtime
                filename = f"{int(time.time())}.wav"
                audio_path = self._audio_recorder.save_to_file(audio_data, filename)
                text = await self.openai_client.create_transcription(
                    audio_path, OpenAITranscriptionModel.whisper_1, "en"
                )
                root_logger.info(f"Transcription response: {text}")

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

    async def _record_audio(self) -> None:
        """Background task to handle audio recording."""
        try:
            root_logger.info("Audio recording task started")

            # Monitor recording state
            while self._is_recording:
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting

            root_logger.info("Audio recording task completed")

        except asyncio.CancelledError:
            root_logger.info("Audio recording task cancelled")
        except Exception as e:
            root_logger.error(f"Error in audio recording task: {e}")
            self._is_recording = False
            self.RecordingStateChanged(False)


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
    except Exception as e:
        root_logger.error(f"Service error: {e}")
    finally:
        await service.stop()


def cli() -> None:
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
    cli()
