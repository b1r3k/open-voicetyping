from typing import Optional

from dbus_next import BusType
from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface

from ..logging import root_logger

logger = root_logger.getChild(__name__)


class VirtualKeyboardDBusClient:
    """DBus client for communicating with VirtualKeyboardInterface."""

    def __init__(self):
        self.bus: Optional[MessageBus] = None
        self.proxy: Optional[ServiceInterface] = None
        self._service_name = "com.cxlab.VirtualKeyboard"
        self._object_path = "/com/cxlab/VirtualKeyboard"
        self._interface_name = "com.cxlab.VirtualKeyboardInterface"

    async def connect(self) -> bool:
        """Connect to the VirtualKeyboard DBus service."""
        try:
            self.bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
            introspection = await self.bus.introspect(self._service_name, self._object_path)
            proxy_object = self.bus.get_proxy_object(self._service_name, self._object_path, introspection)
            self.proxy = proxy_object.get_interface(self._interface_name)
            logger.info(f"Connected to VirtualKeyboard service at {self._service_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to VirtualKeyboard service: {e}")
            return False

    async def emit(self, text: str) -> bool:
        """Send text to be typed via the VirtualKeyboard service."""
        if not self.proxy:
            logger.error("Not connected to VirtualKeyboard service")
            return False

        try:
            await self.proxy.call_emit(text)
            logger.debug(f"Successfully sent text to VirtualKeyboard: {text}")
            return True
        except Exception as e:
            logger.error(f"Failed to emit text to VirtualKeyboard: {e}")
            return False

    async def disconnect(self):
        """Disconnect from the VirtualKeyboard service."""
        if self.bus:
            self.bus.disconnect()
            self.bus = None
            self.proxy = None
            logger.info("Disconnected from VirtualKeyboard service")
