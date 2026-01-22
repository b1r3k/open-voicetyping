# Copyright (c) 2024-2026 Lukasz Jachym <lukasz.jachym@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

from collections.abc import Callable
from enum import Enum, auto

from .logging import root_logger

StateChangeCallback = Callable[["ProcessingState", "ProcessingState"], None]

logger = root_logger.getChild(__name__)


class ProcessingState(Enum):
    IDLE = auto()
    RECORDING = auto()
    TRANSFORMING = auto()
    TRANSCRIBING = auto()


class ProcessingEvent(Enum):
    START_RECORDING = auto()
    TRANSFORM_START = auto()
    TRANSFORM_STOP = auto()
    TRANSCRIBE_START = auto()
    TRANSCRIBE_STOP = auto()
    STOP_RECORDING = auto()


class TransitionError(Exception):
    pass


class ProcessingStateMachine:
    def __init__(self):
        self._state: ProcessingState = ProcessingState.IDLE
        self._listeners: list[StateChangeCallback] = []

    def add_listener(self, callback: StateChangeCallback) -> None:
        self._listeners.append(callback)

    def remove_listener(self, callback: StateChangeCallback) -> None:
        self._listeners.remove(callback)

    def _notify_listeners(self, old_state: ProcessingState, new_state: ProcessingState) -> None:
        for listener in self._listeners:
            listener(old_state, new_state)

    def transition(self, event: ProcessingEvent) -> ProcessingState:
        old_state = self._state
        match self._state, event:
            case ProcessingState.IDLE, ProcessingEvent.START_RECORDING:
                self._state = ProcessingState.RECORDING
            case ProcessingState.RECORDING, ProcessingEvent.STOP_RECORDING:
                self._state = ProcessingState.IDLE
            case ProcessingState.IDLE, ProcessingEvent.TRANSFORM_START:
                self._state = ProcessingState.TRANSFORMING
            case ProcessingState.TRANSFORMING, ProcessingEvent.TRANSFORM_STOP:
                self._state = ProcessingState.IDLE
            case ProcessingState.IDLE, ProcessingEvent.TRANSCRIBE_START:
                self._state = ProcessingState.TRANSCRIBING
            case ProcessingState.TRANSCRIBING, ProcessingEvent.TRANSCRIBE_STOP:
                self._state = ProcessingState.IDLE
            # edge cases
            case ProcessingState.IDLE, ProcessingEvent.STOP_RECORDING:
                logger.warning("Can't stop if not recording")
            case _:
                msg = f"Unknown transition from: {self._state} on event: {event}"
                raise TransitionError(msg)
        if old_state != self._state:
            self._notify_listeners(old_state, self._state)
        return self._state

    @property
    def current_state(self) -> ProcessingState:
        return self._state

    @property
    def is_recording(self) -> bool:
        return self._state == ProcessingState.RECORDING
