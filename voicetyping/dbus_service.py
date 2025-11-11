import asyncio
import threading
from typing import Optional

from dbus_next import BusType
from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface

from .logging import root_logger

logger = root_logger.getChild(__name__)


class DBusService:
    """Generic DBus service class."""

    def __init__(
        self, interface: ServiceInterface, bus_path: str, bus_name: str, shutdown_event: threading.Event
    ) -> None:
        self.interface: ServiceInterface = interface
        self._bus_path = bus_path
        self._bus_name = bus_name
        self.bus: Optional[MessageBus] = None
        self._shutdown_event = shutdown_event
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

        # Wait for shutdown signal by polling the threading event
        while not self._shutdown_event.is_set():
            await asyncio.sleep(1)

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
