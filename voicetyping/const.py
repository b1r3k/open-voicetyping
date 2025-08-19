import enum


class InferenceProvider(enum.Enum):
    OPENAI = "openai"
    GROQ = "groq"


class GNOMESchema:
    VOICETYPING = "org.gnome.shell.extensions.voicetyping"


class GNOMESchemaKey:
    OPENAI_API_KEY = "openai-api-key"
    OPENAI_API_URL = "openai-api-url"
    GROQ_API_KEY = "groq-api-key"
    GROQ_API_URL = "groq-api-url"
    SHORTCUT_START_STOP = "shortcut-start-stop"
    TRANSCRIPTION_LANGUAGE = "transcription-language"
    INFERENCE_PROVIDER = "inference-provider"
    INFERENCE_MODEL = "inference-model"
