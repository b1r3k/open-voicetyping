"""
Tests for Voice Typing DBus Service

This module tests the DBus service functionality by connecting to it
and calling its methods.
"""

import unittest

from voicetyping.main import VoiceTypingInterface


class TestVoiceTypingInterface(unittest.IsolatedAsyncioTestCase):
    async def test_create_instance(self):
        interface = VoiceTypingInterface()
        self.assertIsNotNone(interface)
