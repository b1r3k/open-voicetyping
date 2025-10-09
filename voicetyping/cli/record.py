#!/usr/bin/env python3
"""
CLI for audio recording.

This module provides a command-line interface for recording audio
from input devices and saving to MP3 files.
"""

import argparse
import sys
import signal
import time
from pathlib import Path
from typing import Optional

from ..audio.recorder import AudioRecorder
from ..logging import root_logger


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Record audio from input devices",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list-devices
  %(prog)s --device "Default" --output recording.mp3
  %(prog)s -d "Default" -o recording.mp3 --duration 10
        """,
    )

    parser.add_argument("--device", "-d", type=str, help="Audio device name to use for recording")

    parser.add_argument("--output", "-o", type=str, help="Output file path for recording (will save as MP3)")

    parser.add_argument(
        "--list-devices",
        "-l",
        action="store_true",
        help="List available audio input devices and exit",
    )

    parser.add_argument(
        "--duration",
        "-t",
        type=float,
        help="Recording duration in seconds (default: record until Ctrl+C)",
    )

    parser.add_argument(
        "--sample-rate",
        type=int,
        default=16000,
        help="Sample rate in Hz (default: 16000)",
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    return parser


def list_devices(recorder: AudioRecorder) -> None:
    """List available audio input devices."""
    devices = recorder.list_devices()

    if not devices:
        print("No audio input devices found", file=sys.stderr)
        return

    print("\nAvailable audio input devices:")
    print("-" * 80)
    for device in devices:
        print(f"Name: {device['name']}")
        print(f"  Index: {device['index']}")
        print(f"  Channels: {device['channels']}")
        print(f"  Sample Rate: {device['sample_rate']} Hz")
        print()


def validate_output_path(output_path: str) -> Path:
    """Validate and prepare output path."""
    path = Path(output_path)

    # Ensure parent directory exists
    if path.parent != Path(".") and not path.parent.exists():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ValueError(f"Cannot create output directory: {e}")

    # Ensure .mp3 extension
    if path.suffix.lower() != ".mp3":
        path = path.with_suffix(".mp3")

    return path


def record_audio(
    recorder: AudioRecorder,
    device_name: str,
    output_path: Path,
    duration: Optional[float] = None,
) -> None:
    """Record audio from the specified device."""
    recording = None
    interrupted = False

    def signal_handler(signum, frame):
        """Handle Ctrl+C gracefully."""
        nonlocal interrupted
        root_logger.info("Recording interrupted by user")
        interrupted = True

    # Set up signal handler
    original_handler = signal.signal(signal.SIGINT, signal_handler)

    try:
        # Create recording
        root_logger.info(f"Starting recording from device: {device_name}")
        recording = recorder.create_recording(device_name)

        if not recording or recording is False:
            raise RuntimeError("Failed to create recording")

        if duration:
            print(f"Recording for {duration} seconds... Press Ctrl+C to stop early")
            start_time = time.time()
            while time.time() - start_time < duration and not interrupted:
                time.sleep(0.1)
            if not interrupted:
                root_logger.info(f"Recording completed after {duration} seconds")
        else:
            print("Recording... Press Ctrl+C to stop")
            while not interrupted:
                time.sleep(0.1)

        # Stop recording (but don't close the stream yet)
        root_logger.info("Stopping recording...")
        recording.stop()

        # Save to file
        root_logger.info(f"Saving recording to {output_path}")
        saved_path = recording.save(output_path)

        if saved_path:
            print(f"\nRecording saved to: {saved_path}")
        else:
            raise RuntimeError("Failed to save recording")

    except Exception as e:
        root_logger.error(f"Recording failed: {e}")
        if recording and recording.is_recording():
            recording.stop()
        raise
    finally:
        recording.cleanup()
        signal.signal(signal.SIGINT, original_handler)


def main() -> None:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        root_logger.setLevel("DEBUG")
    else:
        root_logger.setLevel("INFO")

    try:
        # Initialize recorder
        recorder = AudioRecorder(sample_rate=args.sample_rate)

        # List devices if requested
        if args.list_devices:
            list_devices(recorder)
            sys.exit(0)

        # Validate required arguments for recording
        if not args.device:
            print("Error: --device is required for recording\n", file=sys.stderr)
            list_devices(recorder)
            sys.exit(1)

        if not args.output:
            print("Error: --output is required for recording\n", file=sys.stderr)
            sys.exit(1)

        # Check if device exists
        device = recorder.get_recording_device_by_name(args.device)
        if device is None:
            print(f"Error: Device '{args.device}' not found\n", file=sys.stderr)
            list_devices(recorder)
            sys.exit(1)

        # Validate output path
        output_path = validate_output_path(args.output)

        # Start recording
        record_audio(
            recorder=recorder,
            device_name=args.device,
            output_path=output_path,
            duration=args.duration,
        )

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nRecording cancelled by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            root_logger.exception("Unexpected error occurred")
        sys.exit(1)


def record() -> None:
    """CLI entry point for poetry scripts."""
    main()


if __name__ == "__main__":
    main()
