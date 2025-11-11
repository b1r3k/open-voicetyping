import asyncio
import sys
import threading
import queue

from ..dbus_service import DBusService
from .dbus_interface import VirtualKeyboardInterface
from .dbus_interface import VirtualKeyboardService

from ..logging import root_logger


async def side_thread_main_loop(typing_queue, shutdown_event: threading.Event) -> None:
    virtual_kbd = VirtualKeyboardInterface(typing_queue)
    dbus_service = DBusService(virtual_kbd, "/com/cxlab/VirtualKeyboard", "com.cxlab.VirtualKeyboard", shutdown_event)

    try:
        await dbus_service.start()
    except (KeyboardInterrupt, asyncio.CancelledError):
        root_logger.info("Interrupted event loop")
    finally:
        await dbus_service.stop()


def side_thread_main(typing_queue, event_loop, shutdown_event: threading.Event) -> None:
    """Main entry point for the DBus service."""
    asyncio.set_event_loop(event_loop)
    event_loop.run_until_complete(side_thread_main_loop(typing_queue, shutdown_event))


def server() -> None:
    """CLI entry point."""
    typing_queue = queue.Queue()
    virtual_kbd_svc = VirtualKeyboardService(typing_queue)
    loop = asyncio.new_event_loop()
    shutdown_event = threading.Event()
    exit_code = 0

    t = threading.Thread(
        target=side_thread_main,
        args=(typing_queue, loop, shutdown_event),
        daemon=True,
    )

    try:
        t.start()
        # main thread: processes typing queue
        virtual_kbd_svc.process_queue()
    except KeyboardInterrupt:
        root_logger.info("Interrupted by user, exiting...")
    except Exception:
        root_logger.exception("Unhandled exception")
        exit_code = 1
    finally:
        shutdown_event.set()
        t.join(timeout=5)
        if t.is_alive():
            root_logger.warning("Thread did not exit within timeout")
        sys.exit(exit_code)
