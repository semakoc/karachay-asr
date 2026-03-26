#!/usr/bin/env python3
"""
04_mms_transcribe.py  —  Run Meta MMS ASR (facebook/mms-1b-fl102) on all clips.

Produces mms_transcriptions.json: [{id, clip_file, text}, ...]
  id matches ELAN annotation IDs (a1, a2, a3 …)

Does NOT modify annotation_project.eaf. Text injection is a separate step.

First run downloads ~4 GB model to .cache/.
"""
import json
import subprocess
import sys
from pathlib import Path

CLIPS_DIR  = Path("/Users/semakoc/formosan-bank/Karachay_ASR/clips")
OUTPUT_JSON = Path("/Users/semakoc/formosan-bank/Karachay_ASR/mms_transcriptions.json")
CACHE_DIR  = Path("/Users/semakoc/formosan-bank/Karachay_ASR/.cache")
MODEL_ID   = "facebook/mms-1b-fl102"
LANG       = "krc"          # Karachay-Balkar ISO 639-3 code
TARGET_SR  = 16_000
PROGRESS_EVERY = 50


# ---------------------------------------------------------------------------
# Dependency check
# ---------------------------------------------------------------------------

def _ensure_packages() -> None:
    missing = []
    for pkg in ("transformers", "torchaudio"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"[INFO] Installing missing packages: {missing}")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet"] + missing
        )


# ---------------------------------------------------------------------------
# Audio loading helper (uses torchaudio; falls back to scipy if needed)
# ---------------------------------------------------------------------------

def _load_audio_16k_mono(path: Path):
    """Return a 1-D numpy float32 array at 16 kHz."""
    import torchaudio
    import torch

    waveform, sr = torchaudio.load(str(path))       # (channels, samples)

    if sr != TARGET_SR:
        resampler = torchaudio.transforms.Resample(orig_freq=sr, new_freq=TARGET_SR)
        waveform = resampler(waveform)

    if waveform.shape[0] > 1:                        # mix down to mono
        waveform = waveform.mean(dim=0, keepdim=True)

    return waveform.squeeze().numpy()                # 1-D float32


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    _ensure_packages()

    import torch
    from transformers import Wav2Vec2ForCTC, AutoProcessor

    # --- Collect clips ---
    clips = sorted(CLIPS_DIR.glob("clip_*.wav"))
    if not clips:
        print(f"[ERROR] No clip_*.wav files found in {CLIPS_DIR}")
        return 1
    print(f"[INFO] Found {len(clips)} clips in {CLIPS_DIR}")

    # --- Load model ---
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] Loading model {MODEL_ID}  (downloads ~4 GB on first run) …")
    print(f"[INFO] Cache: {CACHE_DIR}")

    processor = AutoProcessor.from_pretrained(MODEL_ID, cache_dir=str(CACHE_DIR))
    model = Wav2Vec2ForCTC.from_pretrained(MODEL_ID, cache_dir=str(CACHE_DIR))
    model.eval()

    # Set target language adapter for Karachay-Balkar
    processor.tokenizer.set_target_lang(LANG)
    model.load_adapter(LANG)
    print(f"[INFO] Language adapter loaded: {LANG}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    print(f"[INFO] Running on: {device}")

    # --- Transcribe ---
    results = []
    empty_count = 0
    total_chars = 0

    for idx, clip_path in enumerate(clips, start=1):
        # Derive annotation ID from filename: clip_0042.wav → a42
        stem = clip_path.stem                        # e.g. "clip_0042"
        num_str = stem.split("_")[-1]                # e.g. "0042"
        ann_id = f"a{int(num_str)}"                  # e.g. "a42"

        try:
            audio = _load_audio_16k_mono(clip_path)
            inputs = processor(
                audio,
                sampling_rate=TARGET_SR,
                return_tensors="pt",
            )
            inputs = {k: v.to(device) for k, v in inputs.items()}

            with torch.no_grad():
                logits = model(**inputs).logits

            predicted_ids = torch.argmax(logits, dim=-1)
            text = processor.decode(predicted_ids[0]).strip()

        except Exception as exc:
            print(f"[WARN] {clip_path.name}: inference failed — {exc}")
            text = ""

        results.append({
            "id":        ann_id,
            "clip_file": clip_path.name,
            "text":      text,
        })

        if not text:
            empty_count += 1
        total_chars += len(text)

        if idx % PROGRESS_EVERY == 0:
            print(f"[PROGRESS] {idx}/{len(clips)} clips transcribed …")

    # --- Save ---
    OUTPUT_JSON.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # --- Summary ---
    avg_len = total_chars / len(results) if results else 0
    print()
    print("=" * 50)
    print(f"Total clips processed  : {len(results)}")
    print(f"Empty transcriptions   : {empty_count}")
    print(f"Avg transcription len  : {avg_len:.1f} chars")
    print(f"Output written to      : {OUTPUT_JSON}")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
