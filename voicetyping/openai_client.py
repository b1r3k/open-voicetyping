import enum
from typing import AsyncGenerator, Callable, Any, TypeAlias
from pathlib import Path
import mimetypes
import json
from abc import ABC, abstractmethod

from httpx import URL

from .http_client import AsyncHttpClient
from .logging import root_logger
from .const import InferenceProvider

logger = root_logger.getChild(__name__)

print("logger.getEffectiveLevel()", logger.getEffectiveLevel())
print("logger.level", logger.level)
print("logger.handlers", logger.handlers)

mimetypes.init()


class OpenAIAudioFormat(enum.Enum):
    OPUS = "opus"
    WAV = "wav"
    MP3 = "mp3"
    FLAC = "flac"
    AAC = "aac"
    PCM = "pcm"


class OpenAIModel(str, enum.Enum):
    tts1 = "tts-1"
    tts_hd = "tts-1-hd"
    gpt_4o = "gpt-4o-mini-tts"


class OpenAIModelTTSVoice(str, enum.Enum):
    alloy = "alloy"
    ash = "ash"
    ballad = "ballad"
    coral = "coral"
    echo = "echo"
    fable = "fable"
    onyx = "onyx"
    nova = "nova"
    sage = "sage"
    shimmer = "shimmer"
    verse = "verse"


TranscriptionModel: TypeAlias = enum.StrEnum


class GroqTranscriptionModel(TranscriptionModel):
    whisper_large_v3_turbo = "whisper-large-v3-turbo"
    distil_whisper_large_v3_en = "distil-whisper-large-v3-en"
    whisper_large_v3 = "whisper-large-v3"


class OpenAITranscriptionModel(TranscriptionModel):
    whisper_1 = "whisper-1"
    gpt_4o = "gpt-4o-transcribe"
    gpt_4o_mini = "gpt-4o-mini-transcribe"


def transcription_model_from_provider(provider: InferenceProvider, model_str: str) -> TranscriptionModel:
    match provider:
        case InferenceProvider.OPENAI:
            return OpenAITranscriptionModel(model_str)
        case InferenceProvider.GROQ:
            return GroqTranscriptionModel(model_str)


class BaseAIClient(AsyncHttpClient, ABC):
    """Abstract base class for AI service clients."""

    @abstractmethod
    def __init__(
        self,
        api_key: str,
        json_decode: Callable[[str], Any] = json.loads,
        host: str = "",
        version: str = "",
        base_path: str = "",
        **kwargs,
    ):
        super().__init__(**kwargs)
        assert api_key, "API key is required"
        assert host, "Host is required"
        assert version, "Version is required"
        assert base_path is not None, "Base path is required"

        self.host = host
        self.version = version
        self.base_path = base_path
        self.api_key = api_key
        self.base_url = URL(scheme="https", host=self.host)
        self.json_decode = json_decode

    @property
    @abstractmethod
    def headers(self):
        """Return the headers for API requests."""
        pass

    @abstractmethod
    def get_url(self, endpoint: str) -> URL:
        """Construct the URL for a given endpoint."""
        pass

    @abstractmethod
    async def create_speech(
        self,
        input_text: str,
        model: OpenAIModel,
        voice: OpenAIModelTTSVoice,
        output_format: OpenAIAudioFormat = OpenAIAudioFormat.OPUS,
    ):
        """Create speech from text using TTS."""
        pass

    @abstractmethod
    async def create_transcription(
        self,
        file_path: Path,
        model: TranscriptionModel,
        language: str,
    ) -> str:
        """Create transcription from audio file."""
        pass

    @abstractmethod
    async def stream_transcription(
        self,
        file_path: Path,
        model: TranscriptionModel,
        language: str,
    ) -> AsyncGenerator[Any, None]:
        """Stream transcription from audio file."""
        pass


class OpenAIClient(BaseAIClient):
    ENDPOINTS = {
        "speech": "audio/speech",
        "transcription": "audio/transcriptions",
    }

    def __init__(
        self,
        api_key: str,
        json_decode: Callable[[str], Any] = json.loads,
        host="api.openai.com",
        version="v1",
        base_path="",
        **kwargs,
    ):
        super().__init__(api_key, json_decode, host, version, base_path, **kwargs)

    @property
    def headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def get_url(self, endpoint: str) -> URL:
        return self.base_url.join("/".join([self.base_path, self.version, self.ENDPOINTS[endpoint]]))

    async def create_speech(
        self,
        input_text: str,
        model: OpenAIModel,
        voice: OpenAIModelTTSVoice,
        output_format: OpenAIAudioFormat = OpenAIAudioFormat.OPUS,
    ):
        url = self.get_url("speech")
        payload = {
            "model": model,
            "voice": voice,
            "input": input_text,
            "response_format": output_format,
        }
        response = await self.post(url, json=payload, headers=self.headers, stream=True)
        return response

    async def create_transcription(
        self,
        file_path: Path,
        model: OpenAITranscriptionModel,
        language: str,
    ) -> str:
        url = self.get_url("transcription")
        headers = self.headers.copy()
        del headers["Content-Type"]
        try:
            mime_type = mimetypes.guess_type(file_path.absolute())[0]
        except Exception as e:
            logger.error(f"Error guessing MIME type for {file_path}: {e}")
            raise e
        try:
            file_obj = open(file_path.absolute(), "rb")
        except Exception as e:
            logger.error(f"Error opening {file_path}: {e}")
            raise e

        files = {
            "file": (file_path.name, file_obj, mime_type),
        }

        fields = {
            "model": model.value,
            "language": language,
            "response_format": "text",
            "temperature": "0.0",
        }
        response = await self.post(url, headers=headers, data=fields, files=files)
        content = await response.aread()
        return content

    async def stream_transcription(
        self,
        file_path: Path,
        model: OpenAITranscriptionModel,
        language: str,
    ) -> AsyncGenerator[Any, None]:
        """
        Streams the transcription of a file.
        For streaming when size of the recording is not known real-time API needs to be used.

        Args:
            file_path: The path to the file to transcribe.
            model: The model to use for transcription.
            language: The language of the file.
        """
        url = self.get_url("transcription")
        headers = self.headers.copy()
        del headers["Content-Type"]
        headers["Accept"] = "text/event-stream"

        mime_type = mimetypes.guess_type(file_path)[0]
        fields = {
            "file": (file_path.name, open(file_path, "rb"), mime_type),
            "model": model.value,
            "language": language,
            "response_format": "text",
            "temperature": 0.0,
            "stream": True,
        }
        async with self.session.stream("POST", url, headers=headers, files=fields) as response:
            async for chunk in response.aiter_lines():
                if chunk and chunk.startswith("data:"):
                    data = chunk[5:].strip()
                    if data == "":
                        continue
                    json_data = self.json_decode(data)
                    yield json_data


class GroqClient(OpenAIClient):
    def __init__(
        self,
        api_key: str,
        json_decode: Callable[[str], Any] = json.loads,
        host="api.groq.com",
        version="v1",
        base_path="openai",
        **kwargs,
    ):
        super().__init__(api_key, json_decode, host, version, base_path, **kwargs)
