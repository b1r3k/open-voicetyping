import asyncio
import signal
from typing import Optional
from functools import partial

from dbus_next import BusType
from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface

from .logging import root_logger

logger = root_logger.getChild(__name__)


class DBusService:
    """Generic DBus service class."""

    def __init__(self, interface: ServiceInterface, bus_path: str, bus_name: str):
        self.interface: ServiceInterface = interface
        self._bus_path = bus_path
        self._bus_name = bus_name
        self.bus: Optional[MessageBus] = None
        self._shutdown_event = asyncio.Event()
        self._loop = asyncio.get_event_loop()

    async def start(self) -> None:
        """Start the DBus service."""
        # Connect to the session bus
        self.bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        self.bus.export(self._bus_path, self.interface)

        # Request the service name
        await self.bus.request_name(self._bus_name)

        logger.info("Service: %s", self._bus_name)
        logger.info("Object path: %s", self._bus_path)
        logger.info("Interface: %s", self.interface.name)

        # Set up signal handlers for graceful shutdown
        for sig in (signal.SIGINT, signal.SIGTERM):
            self._loop.add_signal_handler(sig, partial(self._signal_handler, sig, self._loop))

        # Wait for shutdown signal
        await self._shutdown_event.wait()

    async def stop(self) -> None:
        """Stop the DBus service."""
        try:
            if self.bus:
                self.bus.disconnect()
        except Exception as e:
            logger.debug(f"Error stopping DBus service: {e}")
        finally:
            logger.info("%s DBus service stopped", self.interface.name)
            self.interface.close()

    def _signal_handler(self, signum: int, loop: asyncio.AbstractEventLoop) -> None:
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self._shutdown_event.set()
