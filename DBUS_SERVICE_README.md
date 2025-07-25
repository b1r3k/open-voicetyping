# Voice Typing DBus Service

This directory contains a Python DBus service that provides voice recording functionality for the GNOME Shell extension.

## Overview

The DBus service implements the `com.cxlab.VoiceTypingInterface` interface with the following methods:

- `StartRecording()` - Starts voice recording
- `StopRecording()` - Stops voice recording
- `GetRecordingState()` - Returns current recording state

And signals:
- `RecordingStateChanged(is_recording: bool)` - Emitted when recording state changes
- `TranscriptionResult(text: str, confidence: float)` - Emitted when transcription is complete

## Installation

1. Install dependencies:
```bash
poetry install
```

2. Make the service executable:
```bash
chmod +x voicetyping/main.py
```

## Running the Service

### Method 1: Direct execution
```bash
poetry run python -m voicetyping.main
```

### Method 2: Using the CLI entry point
```bash
poetry run app-cli
```

### Method 3: As a systemd user service

1. Copy the service file to your systemd user directory:
```bash
cp voicetyping.service ~/.config/systemd/user/
```

2. Enable and start the service:
```bash
systemctl --user enable voicetyping.service
systemctl --user start voicetyping.service
```

3. Check service status:
```bash
systemctl --user status voicetyping.service
```

## Testing the Service

Run the test client to verify the service is working:

```bash
python test_dbus_client.py
```

This will test all the DBus methods and verify the service responds correctly.

## DBus Interface Details

### Service Name
`com.cxlab.VoiceTyping`

### Object Path
`/com/cxlab/VoiceTyping`

### Interface
`com.cxlab.VoiceTypingInterface`

### Methods

#### StartRecording()
- **Returns**: `str` - Status message ("recording_started", "already_recording", "recording_failed")
- **Description**: Starts voice recording if not already recording

#### StopRecording()
- **Returns**: `str` - Status message ("recording_stopped", "not_recording", "stop_failed")
- **Description**: Stops voice recording if currently recording

#### GetRecordingState()
- **Returns**: `bool` - Current recording state
- **Description**: Returns whether recording is currently active

### Signals

#### RecordingStateChanged(is_recording: bool)
- **Description**: Emitted whenever the recording state changes

#### TranscriptionResult(text: str, confidence: float)
- **Description**: Emitted when transcription processing is complete

## Integration with GNOME Shell Extension

The GNOME Shell extension connects to this service using Gio.DBusProxy:

```javascript
this._dbusProxy = new DBusProxy('com.cxlab.VoiceTyping', '/com/cxlab/VoiceTyping', 'com.cxlab.VoiceTypingInterface');
```

The extension calls:
- `StartRecording()` when the user presses the shortcut to start recording
- `StopRecording()` when the user releases the shortcut to stop recording

## Development

### Adding New Methods

To add new methods to the DBus interface:

1. Add the method to the `VoiceTypingInterface` class in `voicetyping/main.py`
2. Use the `@method()` decorator
3. Update the GNOME Shell extension to call the new method

### Adding New Signals

To add new signals:

1. Add the signal to the `VoiceTypingInterface` class
2. Use the `@signal()` decorator
3. Emit the signal when appropriate using `self.SignalName(args)`

### Logging

The service uses structured logging with configurable log levels. Logs are output to stdout and can be viewed with:

```bash
journalctl --user -u voicetyping.service -f
```

## Troubleshooting

### Service won't start
- Check if the service name is already taken: `dbus-send --session --dest=org.freedesktop.DBus --type=method_call /org/freedesktop/DBus org.freedesktop.DBus.ListNames`
- Verify Python dependencies are installed: `poetry install`
- Check logs: `journalctl --user -u voicetyping.service`

### Extension can't connect
- Ensure the service is running: `systemctl --user status voicetyping.service`
- Check DBus service availability: `dbus-send --session --dest=com.cxlab.VoiceTyping --type=method_call /com/cxlab/VoiceTyping com.cxlab.VoiceTypingInterface.GetRecordingState`

### Permission issues
- Make sure the service file has correct permissions
- Check that the user has access to the session bus
