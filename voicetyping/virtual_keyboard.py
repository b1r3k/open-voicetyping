import uinput
import time
from uinput import _CHAR_MAP

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

ALTERNATE_CHARS = {
    "ą": "a",
    "ć": "c",
    "ę": "e",
    "ł": "l",
    "ń": "n",
    "ó": "o",
    "ś": "s",
    "ź": "z",
    "ż": "z",
}


class VirtualKeyboard:
    def __init__(self, emit_delay=0.025):
        self.events = set(CHAR_TO_KEY.values())
        self.events.update([uinput.KEY_LEFTSHIFT, uinput.KEY_LEFTALT])  # For shiftable/alt chars
        self.emit_delay = emit_delay
        self.device = uinput.Device(self.events)

    def type_char(self, device, char):
        combo = []

        if char.isupper():
            char = char.lower()
            combo.append(uinput.KEY_LEFTSHIFT)

        if char in SHIFTED_CHARS:
            char = SHIFTED_CHARS[char]
            combo.append(uinput.KEY_LEFTSHIFT)

        if char in ALTERNATE_CHARS:
            char = ALTERNATE_CHARS[char]
            combo.append(uinput.KEY_LEFTALT)

        key = CHAR_TO_KEY.get(char)

        if not key:
            print(f"Skipping unsupported char: '{char}'")
            return

        if combo:
            device.emit_combo(combo + [key])
        else:
            device.emit_click(key)

    def type_text(self, text):
        try:
            for char in text:
                self.type_char(self.device, char)
                if self.emit_delay > 0:
                    time.sleep(self.emit_delay)
        except Exception as e:
            print(f"Error typing text: {e}")

    def close(self):
        self.device.destroy()
