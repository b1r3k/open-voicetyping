[![CI](https://github.com/b1r3k/python-poetry-boilerplate/actions/workflows/ci.yaml/badge.svg)](https://github.com/b1r3k/python-poetry-boilerplate/actions/workflows/ci.yaml)

# Voicetyping

open-voicetyping is a Linux-first, AI-driven dictation system that turns speech into real keyboard events.
Built for GNOME and designed with privilege separation, it combines Whisper-based transcription with a hardened /dev/uinput backend.
Ideal for developers and power users who want local control, extensibility, and strong security boundaries.

## Table of Contents

- [Architecture](#architecture)
  - [Services](#services)
  - [DBus Communication](#dbus-communication)
  - [Security Model](#security-model)
- [Requirements](#requirements)
  - [System Packages Required](#system-packages-required)
    - [Audio Libraries (for pyaudio)](#audio-libraries-for-pyaudio)
    - [MP3 Encoding (for lameenc)](#mp3-encoding-for-lameenc)
    - [uinput/evdev (for python-uinput)](#uinputevdev-for-python-uinput)
- [How to install](#how-to-install)
  - [Install python backend](#install-python-backend)
  - [Install GNOME Shell extension](#install-gnome-shell-extension)
  - [Security considerations](#security-considerations)
- [Development](#development)
  - [Default logs](#default-logs)
  - [Gnome extension management](#gnome-extension-management)

## Architecture

Voicetyping uses a two-service design for security through privilege separation:

```
┌─────────────────────────────────────────────────────────────────┐
│                    GNOME Shell Extension                        │
│                   (voicetyping@cx-lab.com)                      │
│         Panel indicator, keyboard shortcut handling            │
└───────────────────────────┬─────────────────────────────────────┘
                            │ DBus (system bus)
                            │ com.cxlab.VoiceTyping
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   voicetyping-core.service                      │
│                    (runs as logged-in user)                     │
│  • Audio recording (PyAudio + LAME)                            │
│  • Transcription (OpenAI Whisper / Groq API)                   │
│  • State machine management                                     │
└───────────────────────────┬─────────────────────────────────────┘
                            │ DBus (system bus)
                            │ com.cxlab.VirtualKeyboard
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              voicetyping-keyboard@voicetyping.service           │
│                (runs as 'voicetyping' user)                     │
│  • Text → keyboard events via /dev/uinput                      │
│  • Isolated for security (input group access)                  │
└─────────────────────────────────────────────────────────────────┘
```

### Services

**voicetyping-core.service** (user service)
- Runs as the logged-in GNOME user
- Has access to audio devices (including Bluetooth)
- Handles recording, transcription, and state management
- DBus interface: `com.cxlab.VoiceTyping`

**voicetyping-keyboard@voicetyping.service** (system service)
- Runs as dedicated `voicetyping` user in `input` group
- Has write access to `/dev/uinput` for keyboard simulation
- Isolated from user session for security
- DBus interface: `com.cxlab.VirtualKeyboard`

### DBus Communication

Key methods:
- `StartRecording()` / `StopRecording()` - Control recording state
- `EmitText(text)` - Send transcribed text to keyboard service

Key signals:
- `RecordingStateChanged(boolean)` - Notifies extension of state changes
- `ErrorOccurred(category, message)` - Reports errors to extension

### Security Model

The two-service design provides privilege separation:
- `/dev/uinput` access is restricted to a dedicated system user
- The main service runs with user privileges (audio access)
- No single process has both audio capture and keyboard injection capabilities

## Requirements

 - Python >=3.12
 - GNOME Shell (for extension)

### System Packages Required

Given Debian as the target system

#### Audio Libraries (for pyaudio)

- libportaudio2 - PortAudio runtime library
- portaudio19-dev - PortAudio development files

#### MP3 Encoding (for lameenc)

- libmp3lame0 - LAME MP3 encoder runtime library
- libmp3lame-dev - LAME MP3 encoder development files

#### uinput/evdev (for python-uinput)

- libudev-dev - udev development files (needed for building)

## How to install

### Install python backend

1. Build python wheel and install it in the system

   $ poetry build

   Building voicetyping (0.2.1)
   Building sdist
   - Building sdist
   - Built voicetyping-0.2.1.tar.gz
   Building wheel
   - Building wheel
   - Built voicetyping-0.2.1-py3-none-any.whl

   $ pip3.12 install dist/voicetyping-0.2.1-py3-none-any.whl

   $ which voicetyping-server

Backend uses python-uinput for simulating keyboard from text transcript. On many linux systems `/dev/uinput` file is forbidden to be accessed without root privileges.

   $ ls -lau /dev/input
   crw------- 1 root root 10, 223 Jul 27 14:47 /dev/uinput

On the other hand it's a bit problematic to give random application access to root therefore I prefer to use group
`input` and give it write permissions to `/dev/uinput` device. Therefore, my advice is to use following setup
(tailored for Debian):

1. Load the uinput kernel module (if not already loaded):

   $ sudo modprobe uinput

   and make this permanent across reboots:

   $ echo "uinput" | sudo tee /etc/modules-load.d/uinput.conf

1. Create user who will run python backend: `sudo useradd -G input,audio -M -r voicetyping`
1. Allow input group write to `/dev/uinput` by creating `/etc/udev/rules.d/99-uinput.rules` with following contents:

```
KERNEL=="uinput", GROUP="input", MODE="0660"
```

1. sudo udevadm control --reload-rules
1. sudo udevadm trigger

   $ ls -lau /dev/uinput
   crw-rw---- 1 root input 10, 223 Jul 27 14:47 /dev/uinput

There is some DBus policy tweaking necessary to allow gnome shell extension to talk to python backend. There are two systemd services that need to be started:
  1. voicetyping-keyboard.service runs as user `voicetyping` and has access to `/dev/uinput` device.
  2. voicetyping-core.service runs as user who is logged in gnome session and has access to gnome shell DBus. More importantly it will have access to audio devices and even bluetooth ones (if "default" audio source is selected in the extension settings).

```bash
sudo cp etc/voicetyping-dbus-policy.conf /etc/dbus-1/system.d/voicetyping.conf
# !! adjust user names
sudo systemctl reload dbus
sudo cp etc/voicetyping-keyboard.service /etc/systemd/system/voicetyping-keyboard@voicetyping.service
# !! adjust python paths
sudo systemctl enable voicetyping-keyboard@voicetyping.service
sudo systemctl start voicetyping-keyboard@voicetyping.service
# run as daily driver user (logging in to gnome session):
systemctl edit --force --full voicetyping-core.service
# !! paste contents of etc/voicetyping-core.service and adjust python paths and user name
systemctl enable voicetyping-core.service
systemctl start voicetyping-core.service
```

### Install GNOME Shell extension

```
$ cd extension
$ make install
```

You probably will need to restart your GNOME session i.e. logout/login

### Security considerations

it's important to keep access to /dev/uinput very selective both for write and read permissions since that's how
malware could get access to whatever user is typing

## Development

### Default logs

```
journalctl -u voicetyping-core.service --follow
journalctl -u voicetyping-keyboard@voicetyping.service --follow
```

### Gnome extension management

```bash
gnome-extensions list
gnome-extensions disable voicetyping@cx-lab.com
gnome-extensions enable voicetyping@cx-lab.com
```
