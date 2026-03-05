import logging
import os
import time
from collections.abc import Generator
from pathlib import Path

from dotenv import load_dotenv
from mistralai import Mistral
from pydantic import BaseModel, Field

load_dotenv()

logger = logging.getLogger(__name__)

_CHAT_MODEL = "mistral-large-latest"

SUPPORTED_LANGUAGES = {
    "english": "English",
    "spanish": "Spanish",
    "italian": "Italian",
    "french": "French",
    "russian": "Russian",
}


class TranslationOutput(BaseModel):
    """Structured output for transcript translation."""
    language: str = Field(description="The language the transcript was translated into.")
    translated_text: str = Field(description="The full translated transcript text.")


def get_client() -> Mistral:
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError("Missing MISTRAL_API_KEY environment variable.")
    return Mistral(api_key=api_key)


def transcribe_file(
    *,
    client: Mistral,
    audio_path: Path,
    model: str = "voxtral-mini-latest",
    language: str | None = None,
    num_speakers: int | None = None,
    output_format: str | None = None,
    stream: bool = False,
) -> str | Generator[str, None, None]:
    audio_path = audio_path.expanduser().resolve()
    if not audio_path.exists() or not audio_path.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    extra_kwargs: dict = {}
    if language:
        extra_kwargs["language"] = language
    if output_format and output_format != "txt":
        extra_kwargs["response_format"] = output_format

    if stream:
        return _transcribe_stream(client, audio_path, model, extra_kwargs, num_speakers)

    logger.info(
        "STT request | model=%s | file=%s | language=%s | num_speakers=%s",
        model, audio_path.name, extra_kwargs.get("language"), num_speakers,
    )
    t0 = time.perf_counter()
    with audio_path.open("rb") as f:
        res = client.audio.transcriptions.complete(
            model=model,
            file={
                "content": f,
                "file_name": audio_path.name,
            },
            **extra_kwargs,
        )
    raw_text = res.text
    logger.info("STT response | model=%s | elapsed=%.2fs | chars=%d", model, time.perf_counter() - t0, len(raw_text))

    if num_speakers is not None and num_speakers > 1:
        return "".join(_diarize_stream(client, raw_text, num_speakers))

    return raw_text


def transcribe_raw(
    *,
    client: Mistral,
    audio_path: Path,
    model: str = "voxtral-mini-latest",
    language: str | None = None,
    num_speakers: int | None = None,
    output_format: str | None = None,
) -> str:
    """Perform the audio transcription and return the raw text (no LLM post-processing)."""
    audio_path = audio_path.expanduser().resolve()
    if not audio_path.exists() or not audio_path.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    extra_kwargs: dict = {}
    if language:
        extra_kwargs["language"] = language
    if output_format and output_format != "txt":
        extra_kwargs["response_format"] = output_format

    logger.info(
        "STT request | model=%s | file=%s | language=%s | num_speakers=%s",
        model, audio_path.name, extra_kwargs.get("language"), num_speakers,
    )
    t0 = time.perf_counter()
    with audio_path.open("rb") as f:
        res = client.audio.transcriptions.complete(
            model=model,
            file={
                "content": f,
                "file_name": audio_path.name,
            },
            **extra_kwargs,
        )
    logger.info("STT response | model=%s | elapsed=%.2fs | chars=%d", model, time.perf_counter() - t0, len(res.text))
    return res.text


def diarize_stream(
    client: Mistral,
    transcript: str,
    num_speakers: int,
) -> Generator[str, None, None]:
    """Send raw transcript to LLM and stream the diarized script."""
    yield from _diarize_stream(client, transcript, num_speakers)


def _transcribe_stream(
    client: Mistral,
    audio_path: Path,
    model: str,
    extra_kwargs: dict,
    num_speakers: int | None,
) -> Generator[str, None, None]:
    """Transcribe, optionally diarize via LLM, then yield word-by-word."""
    logger.info(
        "STT request (stream) | model=%s | file=%s | language=%s | num_speakers=%s",
        model, audio_path.name, extra_kwargs.get("language"), extra_kwargs.get("num_speakers"),
    )
    t0 = time.perf_counter()
    with audio_path.open("rb") as f:
        res = client.audio.transcriptions.complete(
            model=model,
            file={
                "content": f,
                "file_name": audio_path.name,
            },
            **extra_kwargs,
        )
    raw_text = res.text
    logger.info("STT response (stream) | model=%s | elapsed=%.2fs | chars=%d", model, time.perf_counter() - t0, len(raw_text))

    # If multiple speakers requested, run LLM diarization and stream the result
    if num_speakers is not None and num_speakers > 1:
        yield from _diarize_stream(client, raw_text, num_speakers)
        return

    # Single speaker — yield word-by-word
    words = raw_text.split(" ")
    for i, word in enumerate(words):
        yield word if i == len(words) - 1 else word + " "


def _diarize_stream(
    client: Mistral,
    transcript: str,
    num_speakers: int,
) -> Generator[str, None, None]:
    """Send the raw transcript to an LLM and stream back the diarized script."""
    system_prompt = (
        f"You are a transcript editor. "
        f"The following is a raw audio transcription of a conversation between "
        f"{num_speakers} people. "
        f"Reformat it as a clean script where each speaker's line starts with "
        f"'Speaker N:' (e.g. 'Speaker 1:', 'Speaker 2:', etc.). "
        f"Infer speaker turns from context. Do not add any commentary, "
        f"introduction, or explanation — output only the reformatted script."
    )

    logger.info(
        "LLM request | model=%s | num_speakers=%d | transcript_chars=%d",
        _CHAT_MODEL, num_speakers, len(transcript),
    )
    t0 = time.perf_counter()
    chars_out = 0
    with client.chat.stream(
        model=_CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcript},
        ],
    ) as stream:
        for event in stream:
            delta = event.data.choices[0].delta.content if event.data.choices else None
            if delta:
                chars_out += len(delta)
                yield delta
    logger.info(
        "LLM response | model=%s | elapsed=%.2fs | chars_out=%d",
        _CHAT_MODEL, time.perf_counter() - t0, chars_out,
    )


def translate_stream(
    client: Mistral,
    transcript: str,
    target_language: str,
) -> Generator[str, None, None]:
    """Translate a raw transcript into the target language and stream the result."""
    yield from _translate_stream(client, transcript, target_language)


def _translate_stream(
    client: Mistral,
    transcript: str,
    target_language: str,
) -> Generator[str, None, None]:
    """Use Mistral with structured output to translate a transcript, then stream the text."""
    lang_label = SUPPORTED_LANGUAGES.get(target_language.lower(), target_language.capitalize())

    system_prompt = (
        f"You are a professional translator. "
        f"Translate the following transcript into {lang_label}. "
        f"Preserve the original formatting and speaker labels if present. "
        f"Do not add commentary or explanation — output only the translation."
    )

    logger.info(
        "LLM translate request | model=%s | target=%s | transcript_chars=%d",
        _CHAT_MODEL, lang_label, len(transcript),
    )
    t0 = time.perf_counter()

    response = client.chat.parse(
        model=_CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcript},
        ],
        response_format=TranslationOutput,
    )

    result: TranslationOutput = response.choices[0].message.parsed
    logger.info(
        "LLM translate response | model=%s | target=%s | elapsed=%.2fs | chars_out=%d",
        _CHAT_MODEL, lang_label, time.perf_counter() - t0, len(result.translated_text),
    )

    # Stream the translated text word-by-word
    words = result.translated_text.split(" ")
    for i, word in enumerate(words):
        yield word if i == len(words) - 1 else word + " "

