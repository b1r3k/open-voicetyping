#!/usr/bin/env python3
"""
CLI for audio transcription using OpenAI Whisper models.

This module provides a command-line interface for transcribing audio files
with support for different languages and models.
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import Optional

from ..openai_client import (
    OpenAITranscriptionModel,
    GroqTranscriptionModel,
    transcription_model_from_provider,
)
from ..const import InferenceProvider
from ..transcription_client import TranscriptionClients
from ..config import settings
from ..logging import root_logger


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Transcribe audio files using OpenAI Whisper models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s audio.wav
  %(prog)s audio.mp3 --language en
  %(prog)s audio.flac --provider openai --model whisper-1 --language pl
  %(prog)s audio.wav --provider groq --model whisper-large-v3-turbo
  %(prog)s audio.wav --output transcript.txt
        """,
    )

    parser.add_argument("file", type=str, help="Path to the audio file to transcribe")

    parser.add_argument(
        "--provider",
        "-p",
        type=str,
        choices=[provider.value for provider in InferenceProvider],
        default=settings.INFERENCE_PROVIDER,
        help=f"Inference provider to use (default: {settings.INFERENCE_PROVIDER})",
    )

    parser.add_argument(
        "--language", "-l", type=str, default="en", help="Language code for transcription (default: en)"
    )

    parser.add_argument(
        "--model",
        "-m",
        type=str,
        help="Transcription model to use. Available models depend on provider. "
        f"OpenAI: {', '.join(m.value for m in OpenAITranscriptionModel)} "
        f"Groq: {', '.join(m.value for m in GroqTranscriptionModel)}",
    )

    parser.add_argument("--output", "-o", type=str, help="Output file path for transcription (default: stdout)")

    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    parser.add_argument("--version", action="version", version="%(prog)s 0.2.1")

    return parser


def validate_audio_file(file_path: str) -> Path:
    """Validate that the audio file exists and is accessible."""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    # Check if it's a supported audio format
    supported_formats = {".wav", ".mp3", ".flac", ".m4a", ".ogg", ".opus"}
    if path.suffix.lower() not in supported_formats:
        print(f"Warning: File extension '{path.suffix}' may not be supported by OpenAI API", file=sys.stderr)

    return path


async def transcribe_audio(
    file_path: Path,
    language: str,
    provider: InferenceProvider,
    model,
    api_key: str,
    output_path: Optional[str] = None,
) -> str:
    """Transcribe the audio file using the specified provider."""
    clients = TranscriptionClients()
    client = clients.get(provider, api_key)
    root_logger.info(
        f"Starting transcription of {file_path} with {provider.value}/{model.value} and language {language}"
    )
    try:
        transcription = await client.create_transcription(file_path=file_path, model=model, language=language)
    except Exception as e:
        root_logger.error(f"Transcription failed: {e}")
        raise
    else:
        if isinstance(transcription, bytes):
            text = transcription.decode("utf-8").strip()
        else:
            text = str(transcription).strip()
        root_logger.info("Transcription completed successfully")
        return text


def save_transcription(text: str, output_path: str) -> None:
    """Save transcription text to output file."""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Transcription saved to: {output_path}", file=sys.stderr)
    except Exception as e:
        print(f"Error saving transcription to {output_path}: {e}", file=sys.stderr)
        sys.exit(1)


async def main() -> None:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        root_logger.setLevel("DEBUG")
    else:
        root_logger.setLevel("INFO")

    try:
        # Validate input file
        audio_file = validate_audio_file(args.file)

        # Parse provider
        try:
            provider = InferenceProvider(args.provider)
        except ValueError:
            print(f"Error: Invalid provider '{args.provider}'", file=sys.stderr)
            sys.exit(1)

        # Get API key for provider
        if provider == InferenceProvider.OPENAI:
            api_key = settings.OPENAI_API_KEY
            default_model = OpenAITranscriptionModel.whisper_1.value
        elif provider == InferenceProvider.GROQ:
            api_key = settings.GROQ_API_KEY
            default_model = GroqTranscriptionModel.whisper_large_v3_turbo.value
        else:
            print(f"Error: Unsupported provider '{provider}'", file=sys.stderr)
            sys.exit(1)

        if not api_key:
            print(f"Error: API key not found for provider '{provider.value}'", file=sys.stderr)
            print(f"Please set {provider.value.upper()}_API_KEY in your environment or .env file", file=sys.stderr)
            sys.exit(1)

        # Parse model
        model_str = args.model if args.model else default_model
        try:
            model = transcription_model_from_provider(provider, model_str)
        except ValueError:
            print(f"Error: Invalid model '{model_str}' for provider '{provider.value}'", file=sys.stderr)
            sys.exit(1)

        # Perform transcription
        transcription_text = await transcribe_audio(
            file_path=audio_file,
            language=args.language,
            provider=provider,
            model=model,
            api_key=api_key,
            output_path=args.output,
        )

        # Output result
        if args.output:
            save_transcription(transcription_text, args.output)
        else:
            print(transcription_text)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nTranscription cancelled by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            root_logger.exception("Unexpected error occurred")
        sys.exit(1)


def transcribe() -> None:
    """CLI entry point for poetry scripts."""
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())
