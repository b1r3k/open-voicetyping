import enum
import hashlib
import queue

from dbus_next.service import ServiceInterface, method
from pydantic import BaseModel

from ..logging import root_logger
from .virtual_keyboard import VirtualKeyboard

logger = root_logger.getChild(__name__)


class TypingEventType(enum.Enum):
    TYPING = "text"
    EXIT = "exit"


class TypingEvent(BaseModel):
    text: str
    md5_hash: str
    type: TypingEventType = TypingEventType.TYPING


class VirtualKeyboardService:
    def __init__(self, q: queue.Queue[TypingEvent]) -> None:
        self.virtual_keyboard = VirtualKeyboard(emit_delay=0.005)
        self.queue = q

    def process_queue(self):
        try:
            while True:
                event = self.queue.get()
                if event.type == TypingEventType.TYPING:
                    self.virtual_keyboard.type_text(event.text)
                    self.queue.task_done()
                else:
                    logger.info("exit command received, stopping keyboard service")
                    self.queue.task_done()
                    return
                logger.debug("Typed text with fingerprint: %s", event.md5_hash)
        except Exception as e:
            logger.error(f"Error in VoiceTypist processing queue: {e}")


class VirtualKeyboardInterface(ServiceInterface):
    """DBus interface for typing through uinput device"""

    def __init__(self, q: queue.Queue[TypingEvent]):
        super().__init__("com.cxlab.VirtualKeyboardInterface")
        self.queue = q

    @method()
    async def emit(self, text: "s") -> None:  # noqa: F821 F722
        """Start voice recording."""
        text_hash = hashlib.md5(text.encode())
        job = TypingEvent(text=text, md5_hash=text_hash.hexdigest())
        logger.debug("Received text to type, fingerprint: %s", job.md5_hash)
        self.queue.put_nowait(job)

    def close(self) -> None:
        """Cleanup resources."""
        if not self.queue.empty():
            self.queue.join()
