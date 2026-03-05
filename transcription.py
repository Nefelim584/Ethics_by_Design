import os
from pathlib import Path

from dotenv import load_dotenv
from mistralai import Mistral

load_dotenv()


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
    prompt: str | None = None,
    output_format: str | None = None,
) -> str:
    audio_path = audio_path.expanduser().resolve()
    if not audio_path.exists() or not audio_path.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    extra_kwargs: dict = {}
    if language:
        extra_kwargs["language"] = language
    if num_speakers is not None:
        extra_kwargs["num_speakers"] = num_speakers
    if prompt:
        extra_kwargs["prompt"] = prompt
    if output_format and output_format != "txt":
        extra_kwargs["response_format"] = output_format

    with audio_path.open("rb") as f:
        res = client.audio.transcriptions.complete(
            model=model,
            file={
                "content": f,
                "file_name": audio_path.name,
            },
            **extra_kwargs,
        )
    return res.text

