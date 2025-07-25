# Audio Recording with Python and Asyncio

This document explains how to record audio from system input using Python in an asyncio-compatible way.

## Overview

The audio recording functionality is implemented using **PyAudio**, which provides cross-platform audio I/O capabilities. The implementation is designed to work seamlessly with asyncio event loops.

## Key Features

- ✅ **Asyncio Compatible**: All audio operations are non-blocking
- ✅ **Cross-Platform**: Works on Linux, macOS, and Windows
- ✅ **Real-time Recording**: Captures audio in real-time using callbacks
- ✅ **Multiple Formats**: Supports various audio formats (WAV, raw PCM)
- ✅ **Device Management**: List and select audio input devices
- ✅ **Resource Management**: Proper cleanup of audio resources

## Installation

### Dependencies

The audio recording functionality requires the following dependencies:

```bash
# Install PyAudio and NumPy
poetry add pyaudio numpy
```

### System Dependencies

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get install portaudio19-dev python3-dev
```

#### macOS
```bash
brew install portaudio
```

#### Windows
PyAudio should work out of the box with pip installation.

## Usage

### Basic Audio Recording

```python
import asyncio
from voicetyping.audio import AsyncAudioRecorder

async def record_audio():
    # Create audio recorder
    recorder = AsyncAudioRecorder(
        sample_rate=16000,  # 16kHz sample rate
        channels=1,         # Mono recording
        chunk_size=1024     # Buffer size
    )

    # Start recording
    success = await recorder.start()
    if not success:
        print("Failed to start recording")
        return

    # Record for 5 seconds
    await asyncio.sleep(5)

    # Stop recording and get audio data
    audio_data = await recorder.stop()
    if audio_data:
        print(f"Captured {len(audio_data)} bytes")

        # Save to WAV file
        recorder.save_to_file(audio_data, "recording.wav")

# Run the recording
asyncio.run(record_audio())
```

### Advanced Usage

#### List Available Audio Devices

```python
recorder = AsyncAudioRecorder()
devices = recorder.list_devices()

for device in devices:
    print(f"Device {device['index']}: {device['name']}")
    print(f"  Channels: {device['channels']}")
    print(f"  Sample Rate: {device['sample_rate']}Hz")
```

#### Custom Audio Settings

```python
recorder = AsyncAudioRecorder(
    sample_rate=44100,      # CD quality
    channels=2,             # Stereo
    chunk_size=2048,        # Larger buffer
    format_type=pyaudio.paFloat32  # 32-bit float
)
```

#### Convert to NumPy Array

```python
audio_data = await recorder.stop()
if audio_data:
    # Convert to numpy array for analysis
    audio_array = recorder._recorder.convert_to_numpy(audio_data)
    print(f"Audio array shape: {audio_array.shape}")
    print(f"Duration: {len(audio_array) / 16000:.2f} seconds")
```

## Integration with DBus Service

The audio recording is integrated into the Voice Typing DBus service:

### Service Methods

- `StartRecording()` - Starts audio recording
- `StopRecording()` - Stops recording and processes audio
- `GetRecordingState()` - Returns current recording state

### Signals

- `RecordingStateChanged(is_recording: bool)` - Emitted when recording state changes
- `TranscriptionResult(text: str, confidence: float)` - Emitted when transcription is complete

## Architecture

### AudioRecorder Class

The core audio recording class that handles:

- **PyAudio Stream Management**: Opens, manages, and closes audio streams
- **Callback Handling**: Processes audio data in real-time
- **Resource Cleanup**: Ensures proper cleanup of audio resources
- **Error Handling**: Graceful error handling and recovery

### AsyncAudioRecorder Class

High-level async interface that provides:

- **Async Methods**: `start()`, `stop()` methods for asyncio compatibility
- **State Management**: Tracks recording state
- **File Operations**: Save audio data to WAV files
- **Device Discovery**: List available audio devices

## Audio Formats and Settings

### Supported Formats

- **PCM 16-bit Integer** (default): `pyaudio.paInt16`
- **PCM 32-bit Float**: `pyaudio.paFloat32`
- **PCM 24-bit Integer**: `pyaudio.paInt24`
- **PCM 8-bit Integer**: `pyaudio.paInt8`

### Recommended Settings

#### For Speech Recognition
```python
recorder = AsyncAudioRecorder(
    sample_rate=16000,  # 16kHz - optimal for speech
    channels=1,         # Mono - speech recognition typically uses mono
    chunk_size=1024,    # 64ms chunks at 16kHz
    format_type=pyaudio.paInt16
)
```

#### For High-Quality Recording
```python
recorder = AsyncAudioRecorder(
    sample_rate=44100,  # CD quality
    channels=2,         # Stereo
    chunk_size=2048,    # Larger chunks for better performance
    format_type=pyaudio.paFloat32
)
```

## Error Handling

### Common Issues and Solutions

#### 1. "No Default Input Device Available"

**Solution**: Check if microphone is connected and permissions are granted.

```python
devices = recorder.list_devices()
if not devices:
    print("No audio input devices found!")
    # Check system audio settings
```

#### 2. "PortAudio Error: Invalid device"

**Solution**: Use a specific device index.

```python
# List devices first
devices = recorder.list_devices()
if devices:
    # Use the first available device
    device_index = devices[0]['index']
    # Modify the recorder to use specific device
```

#### 3. "Audio Stream Already Open"

**Solution**: Ensure proper cleanup between recordings.

```python
# Always stop recording before starting a new one
await recorder.stop()
await recorder.start()
```

## Performance Considerations

### Memory Usage

- **Chunk Size**: Smaller chunks (512-1024) use less memory but more CPU
- **Buffer Management**: Audio frames are stored in memory during recording
- **Cleanup**: Always call `stop()` to free audio resources

### CPU Usage

- **Sample Rate**: Higher sample rates use more CPU
- **Channels**: Stereo uses more CPU than mono
- **Format**: Float32 uses more CPU than Int16

### Latency

- **Chunk Size**: Smaller chunks reduce latency but increase CPU usage
- **Buffer Size**: Larger buffers reduce CPU usage but increase latency

## Testing

### Run the Test Script

```bash
python test_audio_recording.py
```

This will:
1. List available audio devices
2. Test basic recording functionality
3. Test continuous recording with multiple start/stop cycles
4. Save test recordings to WAV files

### Manual Testing

```python
import asyncio
from voicetyping.audio import AsyncAudioRecorder

async def test():
    recorder = AsyncAudioRecorder()

    # Test device listing
    devices = recorder.list_devices()
    print(f"Found {len(devices)} audio devices")

    # Test recording
    await recorder.start()
    await asyncio.sleep(3)  # Record for 3 seconds
    audio_data = await recorder.stop()

    if audio_data:
        print(f"Successfully recorded {len(audio_data)} bytes")

asyncio.run(test())
```

## Troubleshooting

### Linux Issues

#### ALSA Errors
```bash
# Install ALSA development libraries
sudo apt-get install libasound2-dev
```

#### PulseAudio Issues
```bash
# Check PulseAudio status
pulseaudio --check
# Restart PulseAudio if needed
pulseaudio --kill && pulseaudio --start
```

### macOS Issues

#### Permission Issues
- Go to System Preferences > Security & Privacy > Privacy > Microphone
- Add your Python application to the allowed list

#### PortAudio Issues
```bash
# Reinstall PortAudio
brew uninstall portaudio
brew install portaudio
```

### Windows Issues

#### PyAudio Installation
```bash
# Install Visual C++ Build Tools first
# Then install PyAudio
pip install pyaudio
```

#### Device Access
- Check Windows privacy settings for microphone access
- Ensure microphone is set as default input device

## Best Practices

1. **Always Clean Up**: Call `stop()` to free audio resources
2. **Handle Errors**: Wrap audio operations in try-catch blocks
3. **Check Devices**: List devices before attempting to record
4. **Use Appropriate Settings**: Choose sample rate and format based on your use case
5. **Monitor Resources**: Check memory usage for long recording sessions

## Integration Examples

### With OpenAI Whisper

```python
import openai
from voicetyping.audio import AsyncAudioRecorder

async def record_and_transcribe():
    recorder = AsyncAudioRecorder()

    # Record audio
    await recorder.start()
    await asyncio.sleep(5)
    audio_data = await recorder.stop()

    if audio_data:
        # Save to temporary file
        recorder.save_to_file(audio_data, "temp_audio.wav")

        # Send to OpenAI Whisper
        with open("temp_audio.wav", "rb") as audio_file:
            transcript = openai.Audio.transcribe("whisper-1", audio_file)
            print(f"Transcription: {transcript['text']}")
```

### With WebSocket Streaming

```python
import websockets
from voicetyping.audio import AsyncAudioRecorder

async def stream_audio():
    recorder = AsyncAudioRecorder()

    async with websockets.connect('ws://localhost:8080') as websocket:
        await recorder.start()

        while recorder.is_recording():
            # Stream audio chunks
            await websocket.send(audio_chunk)
            await asyncio.sleep(0.1)

        await recorder.stop()
```

This implementation provides a robust, asyncio-compatible solution for audio recording that can be easily integrated into your voice typing application.
