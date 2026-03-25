#!/usr/bin/env python3
from pathlib import Path
import sys
import ffmpeg


def extract_and_normalize(input_media: Path, output_wav: Path) -> bool:
    try:
        if not input_media.exists():
            print(f"[ERROR] Input file does not exist: {input_media}")
            return False

        output_wav.parent.mkdir(parents=True, exist_ok=True)
        print(f"[INFO] Input: {input_media}")
        print(f"[INFO] Output: {output_wav}")
        print("[INFO] Running ffmpeg: mono, 16kHz, 16-bit PCM WAV...")

        (
            ffmpeg
            .input(str(input_media))
            .output(
                str(output_wav),
                ac=1,
                ar=16000,
                acodec="pcm_s16le",
                vn=None,
                loglevel="error",
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        print("[OK] Audio extraction and normalization completed.")
        return True
    except ffmpeg.Error as exc:
        err_text = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else str(exc)
        print("[ERROR] ffmpeg failed:")
        print(err_text)
        return False
    except Exception as exc:
        print(f"[ERROR] Unexpected failure: {exc}")
        return False


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage:")
        print("  python 01_extract_normalize_audio.py <input_media.mp4> <output_audio.wav>")
        return 1

    input_media = Path(sys.argv[1]).expanduser().resolve()
    output_wav = Path(sys.argv[2]).expanduser().resolve()
    ok = extract_and_normalize(input_media, output_wav)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
