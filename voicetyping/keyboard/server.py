import asyncio
import sys

from ..dbus_service import DBusService
from .dbus_interface import VirtualKeyboardInterface

from ..logging import root_logger


async def main() -> None:
    """Main entry point for the DBus service."""
    dbus_service = DBusService(VirtualKeyboardInterface(), "/com/cxlab/VirtualKeyboard", "com.cxlab.VirtualKeyboard")

    try:
        await dbus_service.start()
    except KeyboardInterrupt:
        root_logger.info("Interrupted by user")
    finally:
        await dbus_service.stop()


def server() -> None:
    """CLI entry point."""
    try:
        asyncio.run(main())
        sys.exit(0)
    except Exception:
        root_logger.exception("Unhandled exception")
        sys.exit(1)
