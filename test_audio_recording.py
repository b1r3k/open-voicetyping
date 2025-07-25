#!/usr/bin/env python3
"""
Test script for audio recording functionality.

This script demonstrates how to use the AsyncAudioRecorder class
to record audio from system input in an asyncio-compatible way.
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voicetyping.audio import AsyncAudioRecorder


async def test_audio_recording():
    """Test the audio recording functionality."""
    print("Testing Audio Recording...")

    # Create audio recorder
    recorder = AsyncAudioRecorder(sample_rate=16000, channels=1, chunk_size=1024)

    # List available audio devices
    print("\nAvailable audio devices:")
    devices = recorder.list_devices()
    for device in devices:
        print(f"  {device['index']}: {device['name']} ({device['channels']} channels, {device['sample_rate']}Hz)")

    if not devices:
        print("No audio input devices found!")
        return False

    # Test recording
    print("\nStarting recording... (speak into your microphone)")
    print("Press Ctrl+C to stop recording")

    try:
        # Start recording
        success = await recorder.start()
        if not success:
            print("Failed to start recording!")
            return False

        print("Recording started! Speak now...")

        # Record for 5 seconds
        await asyncio.sleep(5)

        # Stop recording
        print("Stopping recording...")
        audio_data = await recorder.stop()

        if audio_data:
            print(f"Recording completed! Captured {len(audio_data)} bytes")

            # Save to file
            output_file = "test_recording.wav"
            if recorder.save_to_file(audio_data, output_file):
                print(f"Audio saved to {output_file}")

            # Convert to numpy for analysis
            audio_array = recorder._recorder.convert_to_numpy(audio_data)
            if len(audio_array) > 0:
                print(f"Audio converted to numpy array with {len(audio_array)} samples")
                print(f"Audio duration: {len(audio_array) / 16000:.2f} seconds")

            return True
        else:
            print("No audio data captured!")
            return False

    except KeyboardInterrupt:
        print("\nRecording interrupted by user")
        await recorder.stop()
        return False
    except Exception as e:
        print(f"Error during recording: {e}")
        return False


async def test_continuous_recording():
    """Test continuous recording with multiple start/stop cycles."""
    print("\nTesting Continuous Recording...")

    recorder = AsyncAudioRecorder()

    try:
        for i in range(3):
            print(f"\nRecording session {i + 1}/3")

            # Start recording
            success = await recorder.start()
            if not success:
                print("Failed to start recording!")
                continue

            print("Recording... (speak for 2 seconds)")
            await asyncio.sleep(2)

            # Stop recording
            audio_data = await recorder.stop()
            if audio_data:
                print(f"Session {i + 1}: Captured {len(audio_data)} bytes")

                # Save to file
                output_file = f"recording_session_{i + 1}.wav"
                recorder.save_to_file(audio_data, output_file)
            else:
                print(f"Session {i + 1}: No audio captured")

        print("Continuous recording test completed!")
        return True

    except Exception as e:
        print(f"Error during continuous recording: {e}")
        return False


async def main():
    """Main test function."""
    print("Audio Recording Test")
    print("=" * 50)

    # Test basic recording
    success1 = await test_audio_recording()

    # Test continuous recording
    success2 = await test_continuous_recording()

    if success1 and success2:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")
        return 1

    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Test error: {e}")
        sys.exit(1)
