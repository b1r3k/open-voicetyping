import enum
from typing import AsyncGenerator, Callable, Any
from pathlib import Path
import mimetypes
import json

from httpx import URL

from .http_client import AsyncHttpClient
from .logging import root_logger

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


class GroqTranscriptionModel(str, enum.Enum):
    whisper_large_v3_turbo = "whisper-large-v3-turbo"
    distil_whisper_large_v3_en = "distil-whisper-large-v3-en"
    whisper_large_v3 = "whisper-large-v3"


class OpenAITranscriptionModel(str, enum.Enum):
    whisper_1 = "whisper-1"
    gpt_4o = "gpt-4o-transcribe"
    gpt_4o_mini = "gpt-4o-mini-transcribe"


class OpenAIClient(AsyncHttpClient):
    HOST = "api.openai.com"
    VERSION = "v1"
    ENDPOINTS = {
        "speech": "audio/speech",
        "transcription": "audio/transcriptions",
    }

    def __init__(self, api_key: str, json_decode: Callable[[str], Any] = json.loads, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key
        self.base_url = URL(scheme="https", host=self.HOST)
        self.json_decode = json_decode

    @property
    def headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def create_speech(
        self,
        input_text: str,
        model: OpenAIModel,
        voice: OpenAIModelTTSVoice,
        output_format: OpenAIAudioFormat = OpenAIAudioFormat.OPUS,
    ):
        url = self.base_url.join("/".join([self.VERSION, self.ENDPOINTS["speech"]]))
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
        url = self.base_url.join("/".join([self.VERSION, self.ENDPOINTS["transcription"]]))
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
        url = self.base_url.join("/".join([self.VERSION, self.ENDPOINTS["transcription"]]))
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
