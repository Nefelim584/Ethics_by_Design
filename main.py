import argparse
from pathlib import Path

from transcription import get_client, transcribe_file


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Transcribe an audio file with Mistral (Voxtral) and save to .txt"
    )
    p.add_argument("audio_path", help="Path to an audio file (mp3, wav, m4a, ...)")
    p.add_argument(
        "-o",
        "--out",
        dest="out_path",
        default=None,
        help="Output .txt path (default: <audio_basename>.txt next to the audio)",
    )
    p.add_argument(
        "--model",
        default="voxtral-mini-latest",
        help='Transcription model (default: "voxtral-mini-latest")',
    )
    p.add_argument(
        "--language",
        default=None,
        help='Optional language hint (e.g. "en", "de"). If omitted, auto-detect.',
    )
    return p


def transcribe_file(*, client: Mistral, audio_path: Path, model: str, language: str | None) -> str:
    # Backwards-compatible wrapper around the shared implementation.
    return transcribe_file(
        client=client,
        audio_path=audio_path,
        model=model,
        language=language,
    )


def main() -> int:
    args = _build_arg_parser().parse_args()

    audio_path = Path(args.audio_path).expanduser().resolve()

    out_path = (
        Path(args.out_path).expanduser().resolve()
        if args.out_path
        else audio_path.with_suffix(".txt")
    )

    client = get_client()
    try:
        text = transcribe_file(
            client=client,
            audio_path=audio_path,
            model=args.model,
            language=args.language,
        )
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    print(f"Wrote transcript to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
