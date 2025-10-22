import asyncio
import hashlib
from typing import Optional

from dbus_next.service import ServiceInterface, method
from pydantic import BaseModel

from ..logging import root_logger
from .virtual_keyboard import VirtualKeyboard

logger = root_logger.getChild(__name__)


class TypingJob(BaseModel):
    text: str
    md5_hash: str


class VirtualKeyboardService:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.virtual_keyboard = VirtualKeyboard(emit_delay=0.005)
        self.processing_task: Optional[asyncio.Task] = None

    async def start(self):
        self.processing_task = asyncio.create_task(self.process_queue())

    def add_to_queue(self, typing_job: TypingJob):
        self.queue.put_nowait(typing_job)

    async def process_queue(self):
        try:
            while True:
                job = await self.queue.get()
                await asyncio.to_thread(self.virtual_keyboard.type_text, job.text)
                logger.debug("Typed text with fingerprint: %s", job.md5_hash)
        except asyncio.CancelledError:
            logger.debug("VoiceTypist processing queue cancelled")
        except Exception as e:
            logger.error(f"Error in VoiceTypist processing queue: {e}")

    def close(self):
        self.virtual_keyboard.close()
        if self.processing_task:
            self.processing_task.cancel()
            self.processing_task = None


class VirtualKeyboardInterface(ServiceInterface):
    """DBus interface for typing through uinput device"""

    def __init__(self):
        super().__init__("com.cxlab.VirtualKeyboardInterface")
        self.typing_service = VirtualKeyboardService()

    def close(self):
        self.typing_service.close()

    @method()
    async def emit(self, text: "s") -> None:  # noqa: F821 F722
        """Start voice recording."""
        text_hash = hashlib.md5(text.encode())
        job = TypingJob(text=text, md5_hash=text_hash.hexdigest())
        logger.debug("Received text to type, fingerprint: %s", job.md5_hash)
        if not self.typing_service.processing_task:
            await self.typing_service.start()
        self.typing_service.add_to_queue(job)
