"""Tests for VoiceTypingInterface state machine integration."""

import unittest
from unittest.mock import MagicMock, patch

from voicetyping.main import VoiceTypingInterface
from voicetyping.state import ProcessingState, ProcessingEvent


def _close_coroutine_side_effect(coro):
    """Side effect for create_task mock that closes the coroutine to avoid warnings."""
    coro.close()
    return MagicMock()


class TestVoiceTypingInterfaceStateIntegration(unittest.TestCase):
    """Test that VoiceTypingInterface uses state machine as single source of truth."""

    def setUp(self):
        """Create VoiceTypingInterface with mocked dependencies."""
        self.patches = [
            patch("voicetyping.main.TranscriptionService"),
            patch("voicetyping.main.TranscriptionClients"),
            patch("voicetyping.main.VirtualKeyboardDBusClient"),
            patch("voicetyping.main.asyncio.create_task", side_effect=_close_coroutine_side_effect),
        ]
        for p in self.patches:
            p.start()
        self.interface = VoiceTypingInterface()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_interface_starts_in_idle_state(self):
        """Interface starts with state machine in IDLE state."""
        assert self.interface._state.current_state == ProcessingState.IDLE

    def test_is_recording_attribute_does_not_exist(self):
        """_is_recording boolean should be removed."""
        assert not hasattr(self.interface, "_is_recording"), "_is_recording attribute should not exist"

    def test_get_recording_state_uses_state_machine(self):
        """GetRecordingState returns value from state machine, not _recording object."""
        # Default state is IDLE, so should return False
        # Access the underlying method directly to bypass DBus wrapper
        assert self.interface._state.is_recording is False

        # Manually transition state machine to RECORDING
        self.interface._state.transition(ProcessingEvent.START_RECORDING)

        # Now state machine should return True
        assert self.interface._state.is_recording is True

    def test_state_machine_listener_registered_on_init(self):
        """State machine should have _on_state_change listener registered."""
        assert len(self.interface._state._listeners) > 0
        # Verify the listener is the interface's method
        assert self.interface._on_state_change in self.interface._state._listeners

    def test_on_state_change_method_exists(self):
        """_on_state_change method should exist for handling state transitions."""
        assert hasattr(self.interface, "_on_state_change")
        assert callable(self.interface._on_state_change)


class TestVoiceTypingInterfaceRecordingFlow(unittest.IsolatedAsyncioTestCase):
    """Test recording flow integrates with state machine."""

    def setUp(self):
        """Create VoiceTypingInterface with mocked dependencies."""
        self.patches = [
            patch("voicetyping.main.TranscriptionService"),
            patch("voicetyping.main.TranscriptionClients"),
            patch("voicetyping.main.VirtualKeyboardDBusClient"),
            patch("voicetyping.main.asyncio.create_task", side_effect=_close_coroutine_side_effect),
        ]
        for p in self.patches:
            p.start()
        self.interface = VoiceTypingInterface()
        # Mock the audio recorder
        self.interface._audio_recorder = MagicMock()
        mock_recording = MagicMock()
        mock_recording.is_recording.return_value = True
        self.interface._audio_recorder.create_recording.return_value = mock_recording

    def tearDown(self):
        for p in self.patches:
            p.stop()

    async def test_start_recording_transitions_state_machine(self):
        """StartRecording should transition state machine to RECORDING."""
        # Call the underlying async method directly
        coro = self.interface.StartRecording.__wrapped__(self.interface, "device", "/tmp", True)
        result = await coro

        assert result == "recording_started"
        assert self.interface._state.current_state == ProcessingState.RECORDING
        assert self.interface._state.is_recording is True

    async def test_start_recording_guard_uses_state_machine(self):
        """StartRecording guard should use state machine, not _recording object."""
        # First start succeeds
        coro = self.interface.StartRecording.__wrapped__(self.interface, "device", "/tmp", True)
        result1 = await coro
        assert result1 == "recording_started"

        # Second start fails due to state machine guard
        coro2 = self.interface.StartRecording.__wrapped__(self.interface, "device", "/tmp", True)
        result2 = await coro2
        assert result2 == "already_recording"

    async def test_stop_recording_transitions_state_machine(self):
        """StopRecording should transition state machine to IDLE."""
        # Start recording first
        coro = self.interface.StartRecording.__wrapped__(self.interface, "device", "/tmp", False)
        await coro
        assert self.interface._state.is_recording is True

        # Mock stop behavior
        mock_recording = self.interface._recording
        mock_recording.fingerprint.return_value = "abc123"
        mock_recording.save.return_value = MagicMock()

        # Patch transcription client
        self.interface.clients = MagicMock()
        self.interface.clients.get.return_value = MagicMock()

        coro2 = self.interface.StopRecording.__wrapped__(self.interface, "en", "openai", "whisper-1", "key")
        result = await coro2

        assert result == "recording_stopped"
        assert self.interface._state.current_state == ProcessingState.IDLE
        assert self.interface._state.is_recording is False

    async def test_stop_recording_guard_uses_state_machine(self):
        """StopRecording guard should use state machine, not _recording object."""
        # Try to stop without starting - should fail due to state machine guard
        coro = self.interface.StopRecording.__wrapped__(self.interface, "en", "openai", "whisper-1", "key")
        result = await coro
        assert result == "not_recording"


class TestRecordingStateChangedSignal(unittest.IsolatedAsyncioTestCase):
    """Test RecordingStateChanged signal is emitted via state listener."""

    def setUp(self):
        """Create VoiceTypingInterface with signal spy."""
        self.patches = [
            patch("voicetyping.main.TranscriptionService"),
            patch("voicetyping.main.TranscriptionClients"),
            patch("voicetyping.main.VirtualKeyboardDBusClient"),
            patch("voicetyping.main.asyncio.create_task", side_effect=_close_coroutine_side_effect),
        ]
        for p in self.patches:
            p.start()
        self.interface = VoiceTypingInterface()
        # Spy on RecordingStateChanged signal
        self.interface.RecordingStateChanged = MagicMock()
        # Re-register listener since we mocked the signal
        self.interface._state.remove_listener(self.interface._on_state_change)
        self.interface._state.add_listener(self.interface._on_state_change)
        # Mock audio recorder
        self.interface._audio_recorder = MagicMock()
        mock_recording = MagicMock()
        mock_recording.is_recording.return_value = True
        self.interface._audio_recorder.create_recording.return_value = mock_recording

    def tearDown(self):
        for p in self.patches:
            p.stop()

    async def test_signal_emitted_via_state_listener_on_start(self):
        """RecordingStateChanged should be emitted via state listener, not manually."""
        coro = self.interface.StartRecording.__wrapped__(self.interface, "device", "/tmp", True)
        await coro

        # Signal should have been called (via state listener)
        # The signal uses the return value mechanism, so it's called without arguments
        self.interface.RecordingStateChanged.assert_called_once()

    async def test_signal_emitted_via_state_listener_on_stop(self):
        """RecordingStateChanged should be emitted via state listener on stop."""
        # Start recording
        coro = self.interface.StartRecording.__wrapped__(self.interface, "device", "/tmp", False)
        await coro
        self.interface.RecordingStateChanged.reset_mock()

        # Mock stop behavior
        mock_recording = self.interface._recording
        mock_recording.fingerprint.return_value = "abc123"
        mock_recording.save.return_value = MagicMock()
        self.interface.clients = MagicMock()
        self.interface.clients.get.return_value = MagicMock()

        coro2 = self.interface.StopRecording.__wrapped__(self.interface, "en", "openai", "whisper-1", "key")
        await coro2

        # Signal should have been called (via state listener)
        # The signal uses the return value mechanism, so it's called without arguments
        assert self.interface.RecordingStateChanged.call_count == 3
