# Copyright (c) 2024-2026 Lukasz Jachym <lukasz.jachym@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

import uinput
import time
from uinput import _CHAR_MAP

from ..logging import root_logger

logger = root_logger.getChild(__name__)

CHAR_TO_KEY = _CHAR_MAP.copy()

CHAR_TO_KEY.update(
    {
        "'": uinput.KEY_APOSTROPHE,
        ";": uinput.KEY_SEMICOLON,
        "-": uinput.KEY_MINUS,
        "=": uinput.KEY_EQUAL,
        "`": uinput.KEY_GRAVE,
        ",": uinput.KEY_COMMA,
        ".": uinput.KEY_DOT,
        "/": uinput.KEY_SLASH,
    }
)

SHIFTED_CHARS = {
    "!": "1",
    "@": "2",
    "#": "3",
    "$": "4",
    "%": "5",
    "^": "6",
    "&": "7",
    "*": "8",
    "(": "9",
    ")": "0",
    "_": "-",
    "+": "=",
    ":": ";",
    '"': "'",
    "?": "/",
    ">": ".",
    "<": ",",
    "{": "[",
    "}": "]",
}

PL_ALT_CHARS = {
    "ą": "a",
    "ć": "c",
    "ę": "e",
    "ł": "l",
    "ń": "n",
    "ó": "o",
    "ś": "s",
    "ź": "x",
    "ż": "z",
}


class VirtualKeyboard:
    def __init__(self, emit_delay):
        self.char_to_key = CHAR_TO_KEY.copy()
        self.events = set(CHAR_TO_KEY.values())
        self.events.update(
            [uinput.KEY_LEFTSHIFT, uinput.KEY_LEFTALT, uinput.KEY_LEFTCTRL, uinput.KEY_RIGHTALT]
        )  # For shiftable/alt chars
        self.emit_delay = emit_delay
        self.device = uinput.Device(self.events)
        logger.info("Virtual keyboard initialized with emit delay: %s", self.emit_delay)

    def type_combo(self, modifiers, key, hold, gap):
        for mod in modifiers:
            self.device.emit(mod, 1)
            time.sleep(gap)

        self.device.emit(key, 1)
        time.sleep(hold)
        self.device.emit(key, 0)
        time.sleep(gap)

        for mod in reversed(modifiers):
            self.device.emit(mod, 0)
            time.sleep(gap)

        time.sleep(gap)

    def type_char(self, device, char, hold=0.025, gap=0.025):
        combo = []

        if char.isupper():
            char = char.lower()
            combo.append(uinput.KEY_LEFTSHIFT)

        if char in SHIFTED_CHARS:
            char = SHIFTED_CHARS[char]
            combo.append(uinput.KEY_LEFTSHIFT)

        if char in PL_ALT_CHARS:
            char = PL_ALT_CHARS[char]
            combo.append(uinput.KEY_RIGHTALT)

        key = self.char_to_key.get(char)

        if not key:
            return

        if combo:
            self.type_combo(combo, key, hold, gap)
        else:
            device.emit(key, 1)
            time.sleep(hold)
            device.emit(key, 0)
            time.sleep(gap)

    def type_text(self, text):
        try:
            words = text.split()
            for i, word in enumerate(words):
                for char in word:
                    self.type_char(self.device, char)
                # Only append space if not the last word
                if i < len(words) - 1:
                    self.type_char(self.device, " ")
                if self.emit_delay > 0:
                    time.sleep(self.emit_delay)
        except Exception:
            logger.exception("Error typing text")

    def close(self):
        self.device.destroy()
