#!/usr/bin/env python3
"""
Test client for Voice Typing DBus Service

This script tests the DBus service functionality by connecting to it
and calling its methods.
"""

import asyncio
import sys

from dbus_next import BusType
from dbus_next.aio import MessageBus


async def test_dbus_service():
    """Test the DBus service functionality."""
    try:
        # Connect to the session bus
        bus = await MessageBus(bus_type=BusType.SESSION).connect()

        # Get the remote object
        introspection = await bus.introspect("com.cxlab.VoiceTyping", "/com/cxlab/VoiceTyping")
        obj = bus.get_proxy_object("com.cxlab.VoiceTyping", "/com/cxlab/VoiceTyping", introspection)

        # Get the interface
        interface = obj.get_interface("com.cxlab.VoiceTypingInterface")

        print("Testing Voice Typing DBus Service...")

        # Test GetRecordingState
        print("\n1. Testing GetRecordingState...")
        state = await interface.call_get_recording_state()
        print(f"   Current recording state: {state}")

        # Test StartRecording
        print("\n2. Testing StartRecording...")
        result = await interface.call_start_recording()
        print(f"   StartRecording result: {result}")

        # Check state again
        state = await interface.call_get_recording_state()
        print(f"   Recording state after start: {state}")

        # Wait a bit
        await asyncio.sleep(2)

        # Test StopRecording
        print("\n3. Testing StopRecording...")
        result = await interface.call_stop_recording()
        print(f"   StopRecording result: {result}")

        # Check final state
        state = await interface.call_get_recording_state()
        print(f"   Recording state after stop: {state}")

        # Test starting again when already stopped
        print("\n4. Testing StartRecording again...")
        result = await interface.call_start_recording()
        print(f"   StartRecording result: {result}")

        # Test stopping again when already recording
        print("\n5. Testing StopRecording again...")
        result = await interface.call_stop_recording()
        print(f"   StopRecording result: {result}")

        print("\nAll tests completed successfully!")

    except Exception as e:
        print(f"Error testing DBus service: {e}")
        return False

    finally:
        bus.disconnect()

    return True


async def main():
    """Main entry point."""
    print("Voice Typing DBus Service Test Client")
    print("=" * 40)

    success = await test_dbus_service()

    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
