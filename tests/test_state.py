"""Tests for ProcessingStateMachine listener pattern and is_recording property."""

from voicetyping.state import (
    ProcessingEvent,
    ProcessingState,
    ProcessingStateMachine,
)


class TestStateMachineListeners:
    """Test listener registration, removal, and notification."""

    def test_add_listener_and_receive_notification(self):
        """Listener receives (old_state, new_state) on transition."""
        sm = ProcessingStateMachine()
        received = []

        def listener(old_state, new_state):
            received.append((old_state, new_state))

        sm.add_listener(listener)
        sm.transition(ProcessingEvent.START_RECORDING)

        assert received == [(ProcessingState.IDLE, ProcessingState.RECORDING)]

    def test_remove_listener_stops_notifications(self):
        """Removed listener no longer receives notifications."""
        sm = ProcessingStateMachine()
        received = []

        def listener(old_state, new_state):
            received.append((old_state, new_state))

        sm.add_listener(listener)
        sm.remove_listener(listener)
        sm.transition(ProcessingEvent.START_RECORDING)

        assert received == []

    def test_listener_not_called_when_no_state_change(self):
        """Listener NOT called when state doesn't change (IDLE + STOP_RECORDING)."""
        sm = ProcessingStateMachine()
        received = []

        def listener(old_state, new_state):
            received.append((old_state, new_state))

        sm.add_listener(listener)
        sm.transition(ProcessingEvent.STOP_RECORDING)  # No-op when IDLE

        assert received == []

    def test_multiple_listeners_all_called(self):
        """All registered listeners receive notifications."""
        sm = ProcessingStateMachine()
        received1 = []
        received2 = []

        def listener1(old_state, new_state):
            received1.append((old_state, new_state))

        def listener2(old_state, new_state):
            received2.append((old_state, new_state))

        sm.add_listener(listener1)
        sm.add_listener(listener2)
        sm.transition(ProcessingEvent.START_RECORDING)

        assert received1 == [(ProcessingState.IDLE, ProcessingState.RECORDING)]
        assert received2 == [(ProcessingState.IDLE, ProcessingState.RECORDING)]

    def test_listener_receives_multiple_transitions(self):
        """Listener receives all state transitions."""
        sm = ProcessingStateMachine()
        received = []

        def listener(old_state, new_state):
            received.append((old_state, new_state))

        sm.add_listener(listener)
        sm.transition(ProcessingEvent.START_RECORDING)
        sm.transition(ProcessingEvent.STOP_RECORDING)

        assert received == [
            (ProcessingState.IDLE, ProcessingState.RECORDING),
            (ProcessingState.RECORDING, ProcessingState.IDLE),
        ]


class TestIsRecordingProperty:
    """Test is_recording property."""

    def test_is_recording_false_when_idle(self):
        """is_recording returns False in IDLE state."""
        sm = ProcessingStateMachine()
        assert sm.is_recording is False

    def test_is_recording_true_when_recording(self):
        """is_recording returns True in RECORDING state."""
        sm = ProcessingStateMachine()
        sm.transition(ProcessingEvent.START_RECORDING)
        assert sm.is_recording is True

    def test_is_recording_false_after_stop(self):
        """is_recording returns False after stopping recording."""
        sm = ProcessingStateMachine()
        sm.transition(ProcessingEvent.START_RECORDING)
        sm.transition(ProcessingEvent.STOP_RECORDING)
        assert sm.is_recording is False

    def test_is_recording_false_when_transforming(self):
        """is_recording returns False in TRANSFORMING state."""
        sm = ProcessingStateMachine()
        sm.transition(ProcessingEvent.START_RECORDING)
        sm.transition(ProcessingEvent.STOP_RECORDING)
        sm.transition(ProcessingEvent.TRANSFORM_START)
        assert sm.is_recording is False

    def test_is_recording_false_when_transcribing(self):
        """is_recording returns False in TRANSCRIBING state."""
        sm = ProcessingStateMachine()
        sm.transition(ProcessingEvent.START_RECORDING)
        sm.transition(ProcessingEvent.STOP_RECORDING)
        sm.transition(ProcessingEvent.TRANSFORM_START)
        sm.transition(ProcessingEvent.TRANSFORM_STOP)
        sm.transition(ProcessingEvent.TRANSCRIBE_START)
        assert sm.is_recording is False
