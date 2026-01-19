# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Voicetyping is a GNOME Shell extension with a Python backend that provides voice-to-text functionality. It consists of:
- **GNOME Shell Extension** (JavaScript) - UI and keyboard shortcuts
- **Python Backend** (2 systemd services) - Audio recording and transcription via DBus

## Architecture

### Two-Service Design
The system uses two separate DBus services for security:

1. **voicetyping-core.service** (user service)
   - Runs as the logged-in GNOME user
   - Has access to audio devices (including Bluetooth)
   - Communicates with GNOME Shell via DBus
   - Entry point: `voicetyping-server` command
   - Main class: `VoiceTypingInterface` in `voicetyping/main.py`

2. **voicetyping-keyboard.service** (system service)
   - Runs as system user `voicetyping` in `input` group
   - Has write access to `/dev/uinput` for keyboard simulation
   - Entry point: `voicetyping-keyboard` command
   - Main class: `VirtualKeyboardInterface` in `voicetyping/keyboard/dbus_interface.py`

### Communication Flow
1. GNOME Extension → voicetyping-core (StartRecording/StopRecording)
2. voicetyping-core → Audio recording → OpenAI/Groq API
3. voicetyping-core → voicetyping-keyboard (EmitText)
4. voicetyping-keyboard → `/dev/uinput` (keyboard simulation)

### DBus Signals
- `RecordingStateChanged(boolean)` - emitted on state transitions (recording started/stopped)
- `ErrorOccurred(category, message)` - emitted when errors occur (category: recording, transcription, keyboard)

### State Machine
`voicetyping/state.py` implements `ProcessingStateMachine` with states:
- **IDLE** - Ready to start recording
- **RECORDING** - Audio capture in progress
- **TRANSFORMING** - Processing audio data
- **TRANSCRIBING** - Sending to transcription API

Uses observable pattern - components can subscribe to state changes via callbacks.

### Error Handling System
`voicetyping/errors.py` provides context variable-based error handling:
- **Error hierarchy**: `VoiceTypingError` → `RecordingError`, `TranscriptionError`, `KeyboardError`
- **Functions**: `emit_error()` to emit errors, `set_error_handler()` to register handlers
- Errors are propagated to the GNOME extension via `ErrorOccurred` DBus signal

### Key Components

- **Audio Recording** (`voicetyping/audio/recorder.py`): PyAudio-based recording with MP3 encoding
- **Transcription** (`voicetyping/openai_client.py`): OpenAI Whisper and Groq API clients
- **Virtual Keyboard** (`voicetyping/keyboard/virtual_keyboard.py`): Uses python-uinput for text emission
- **DBus Services** (`voicetyping/dbus_service.py`): Generic service wrapper for both services
- **State Machine** (`voicetyping/state.py`): Processing state management with observable pattern
- **Error Handling** (`voicetyping/errors.py`): Context-based error handling and propagation
- **GNOME Settings** (`voicetyping/gnome_settings.py`): GNOME settings reader for audio device selection
- **GNOME Extension** (`extension/extension.js`): Panel indicator, keyboard shortcuts, connects to `RecordingStateChanged` and `ErrorOccurred` signals (GNOME Shell 47, 48)

## Development Commands

### Python Backend

```bash
# Install dependencies
make install

# Run tests
make test

# Run tests in watch mode
make testloop

# Lint and fix
make lint-fix

# Type checking
poetry run mypy .

# Build wheel
poetry build

# Run transcription CLI (for testing)
poetry run voicetyping-transcribe <audio_file>

# Run recording CLI (for testing audio capture)
poetry run voicetyping-record <output_file>
```

### GNOME Extension

```bash
cd extension

# Install extension
make install

# Enable extension
make enable

# Disable extension
make disable

# Check status
make status

# Uninstall
make uninstall
```

After installing the extension, restart GNOME session (logout/login).

### Viewing Logs

```bash
# User service (audio recording, transcription)
journalctl --user -u voicetyping-core.service --follow

# System service (keyboard simulation)
journalctl -u voicetyping-keyboard@voicetyping.service --follow
```

## Code Style Principles

From `.cursor/rules/000-genaral.mdc`:
1. Generate minimal code to solve the request
2. Stick to instructions - don't add unrequested functionality
3. Don't refactor unless asked - suggest first instead

## Testing

Run single test:
```bash
poetry run pytest tests/test_dbus_client.py -k test_name
```

Run with specific pytest flags (defined in Makefile):
```bash
# Defaults: --failed-first -x (stop on first failure)
poetry run pytest ${PYTEST_FLAGS}
```
