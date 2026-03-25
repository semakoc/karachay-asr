# Karachay ASR Pipeline

Low-resource ASR data preparation pipeline for Karachay language.

## Pipeline Steps

1. **Audio extraction** — extract and normalize audio from video source to mono 16 kHz WAV
2. **VAD segmentation** — segment audio into utterances using voice activity detection, output `segments.json`
3. **ELAN annotation** — build a well-formed `.eaf` annotation file with transcription, translation, and notes tiers

## Scripts

| Script | Description |
|---|---|
| `01_extract_normalize_audio.py` | Extracts audio from a video file and normalizes it to mono, 16 kHz, 16-bit PCM WAV using ffmpeg |
| `03_build_eaf.py` | Reads `segments.json` and generates an ELAN `.eaf` annotation file with three tiers: `transcription` (alignable), `translation` (ref), and `notes` (ref) |

## Requirements

- [ffmpeg](https://ffmpeg.org/) (system install)
- [ffmpeg-python](https://github.com/kkroening/ffmpeg-python)
- [openai-whisper](https://github.com/openai/whisper)
- [pydub](https://github.com/jiaaro/pydub)

Install Python dependencies:

```bash
pip install ffmpeg-python openai-whisper pydub
```

## Notes

Audio files (`.wav`, `.mp4`) and the `clips/` folder are not included in this repository — they are too large for git.
