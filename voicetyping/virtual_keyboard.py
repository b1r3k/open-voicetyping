import uinput


# Mapping lowercase characters to keycodes
CHAR_TO_KEY = {
    "a": uinput.KEY_A,
    "b": uinput.KEY_B,
    "c": uinput.KEY_C,
    "d": uinput.KEY_D,
    "e": uinput.KEY_E,
    "f": uinput.KEY_F,
    "g": uinput.KEY_G,
    "h": uinput.KEY_H,
    "i": uinput.KEY_I,
    "j": uinput.KEY_J,
    "k": uinput.KEY_K,
    "l": uinput.KEY_L,
    "m": uinput.KEY_M,
    "n": uinput.KEY_N,
    "o": uinput.KEY_O,
    "p": uinput.KEY_P,
    "q": uinput.KEY_Q,
    "r": uinput.KEY_R,
    "s": uinput.KEY_S,
    "t": uinput.KEY_T,
    "u": uinput.KEY_U,
    "v": uinput.KEY_V,
    "w": uinput.KEY_W,
    "x": uinput.KEY_X,
    "y": uinput.KEY_Y,
    "z": uinput.KEY_Z,
    "0": uinput.KEY_0,
    "1": uinput.KEY_1,
    "2": uinput.KEY_2,
    "3": uinput.KEY_3,
    "4": uinput.KEY_4,
    "5": uinput.KEY_5,
    "6": uinput.KEY_6,
    "7": uinput.KEY_7,
    "8": uinput.KEY_8,
    "9": uinput.KEY_9,
    " ": uinput.KEY_SPACE,
    "\n": uinput.KEY_ENTER,
    ".": uinput.KEY_DOT,
    ",": uinput.KEY_COMMA,
    "-": uinput.KEY_MINUS,
    "=": uinput.KEY_EQUAL,
    "/": uinput.KEY_SLASH,
    "\\": uinput.KEY_BACKSLASH,
    ";": uinput.KEY_SEMICOLON,
    "'": uinput.KEY_APOSTROPHE,
    "[": uinput.KEY_LEFTBRACE,
    "]": uinput.KEY_RIGHTBRACE,
}

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


class VirtualKeyboard:
    def __init__(self):
        self.events = set(CHAR_TO_KEY.values())
        self.events.update([uinput.KEY_LEFTSHIFT])  # For shiftable chars
        self.device = uinput.Device(self.events)

    def type_char(self, char):
        shift = False

        if char.isupper():
            shift = True
            char = char.lower()

        elif char in SHIFTED_CHARS:
            shift = True
            char = SHIFTED_CHARS[char]

        key = CHAR_TO_KEY.get(char)

        if not key:
            print(f"Skipping unsupported char: '{char}'")
            return

        if shift:
            self.device.emit(uinput.KEY_LEFTSHIFT, 1)
        self.device.emit_click(key)
        if shift:
            self.device.emit(uinput.KEY_LEFTSHIFT, 0)

    def type_text(self, text):
        try:
            for char in text:
                self.type_char(char)
        except Exception as e:
            print(f"Error typing text: {e}")
