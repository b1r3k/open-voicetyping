"""Error handling infrastructure for voicetyping.

Provides:
- Custom exception hierarchy with DBus-friendly category/code metadata
- Context variable-based error emission for deep component errors
"""

from contextvars import ContextVar
from typing import Protocol


class ErrorEmitter(Protocol):
    def __call__(self, category: str, message: str) -> None: ...


_error_handler: ContextVar[ErrorEmitter | None] = ContextVar("error_handler", default=None)


def set_error_handler(handler: ErrorEmitter) -> None:
    """Set the error handler (call from VoiceTypingInterface.__init__)."""
    _error_handler.set(handler)


def emit_error(category: str, message: str) -> None:
    """Emit an error to the DBus client. Safe to call from any component."""
    handler = _error_handler.get()
    if handler:
        handler(category, message)


class VoiceTypingError(Exception):
    """Base exception with DBus-friendly metadata."""

    def __init__(self, message: str):
        super().__init__(message)

    def emit(self) -> None:
        """Convenience: emit this error via the context handler."""
        category = self.__class__.__name__
        emit_error(category, str(self))


class RecordingError(VoiceTypingError):
    pass


class DeviceAccessError(RecordingError):
    pass


class AudioSaveError(RecordingError):
    pass


class TranscriptionError(VoiceTypingError):
    pass


class APIError(TranscriptionError):
    pass


class KeyboardError(VoiceTypingError):
    pass


class KeyboardConnectionError(KeyboardError):
    pass


class KeyboardTypingError(KeyboardError):
    pass
