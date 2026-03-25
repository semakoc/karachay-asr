#!/usr/bin/env python3
from pathlib import Path
import json
import statistics
import sys
import tempfile

import whisper
import ffmpeg


INPUT_WAV = Path("/Users/semakoc/formosan-bank/Karachay_ASR/audio_16k_mono.wav")
OUTPUT_JSON = Path("/Users/semakoc/formosan-bank/Karachay_ASR/segments.json")
OUTPUT_CLIPS_DIR = Path("/Users/semakoc/formosan-bank/Karachay_ASR/clips")

MODEL_NAME = "small"
MIN_DURATION_SEC = 1.5
LONG_THRESHOLD_SEC = 15.0
WHISPER_WINDOW_SEC = 600.0


def _get_wav_duration_sec(wav_path):
    try:
        probe = ffmpeg.probe(str(wav_path))
        return float(probe["format"]["duration"])
    except Exception as exc:
        raise RuntimeError(f"Unable to read WAV duration via ffprobe: {exc}") from exc


def _export_wav_slice(input_wav, output_wav, start_sec, end_sec):
    duration = max(0.0, end_sec - start_sec)
    if duration <= 0:
        raise ValueError("Slice duration must be > 0")
    (
        ffmpeg
        .input(str(input_wav), ss=start_sec, t=duration)
        .output(
            str(output_wav),
            ac=1,
            ar=16000,
            acodec="pcm_s16le",
            loglevel="error",
        )
        .overwrite_output()
        .run(capture_stdout=True, capture_stderr=True)
    )


def _clean_segments(raw_segments):
    cleaned = []
    for seg in raw_segments:
        try:
            start = float(seg["start"])
            end = float(seg["end"])
            if end <= start:
                continue
            cleaned.append({"start": start, "end": end})
        except Exception:
            continue
    cleaned.sort(key=lambda x: x["start"])
    return cleaned


def _merge_short_segments(segments, min_duration_sec):
    if not segments:
        return []

    merged = [dict(s) for s in segments]
    i = 0
    while i < len(merged):
        start = merged[i]["start"]
        end = merged[i]["end"]
        duration = end - start

        if duration >= min_duration_sec:
            i += 1
            continue

        if len(merged) == 1:
            break

        prev_idx = i - 1 if i > 0 else None
        next_idx = i + 1 if i < len(merged) - 1 else None

        if prev_idx is None:
            target = next_idx
        elif next_idx is None:
            target = prev_idx
        else:
            gap_prev = abs(start - merged[prev_idx]["end"])
            gap_next = abs(merged[next_idx]["start"] - end)
            target = prev_idx if gap_prev <= gap_next else next_idx

        if target < i:
            merged[target]["start"] = min(merged[target]["start"], start)
            merged[target]["end"] = max(merged[target]["end"], end)
            del merged[i]
            i = max(0, target)
        else:
            merged[target]["start"] = min(merged[target]["start"], start)
            merged[target]["end"] = max(merged[target]["end"], end)
            del merged[i]
            i = max(0, i - 1)

    merged.sort(key=lambda x: x["start"])
    return merged


def main():
    try:
        print("[INFO] Starting VAD-style segmentation from Whisper timestamps.")
        print("[WARN] This may take several minutes for long audio.")
        print("[WARN] Whisper model download may fail without internet on first run.")

        if not INPUT_WAV.exists():
            print(f"[ERROR] Input WAV not found: {INPUT_WAV}")
            return 1

        OUTPUT_CLIPS_DIR.mkdir(parents=True, exist_ok=True)

        print(f"[INFO] Loading Whisper model: {MODEL_NAME}")
        model = whisper.load_model(MODEL_NAME)

        print("[INFO] Running Whisper transcribe in 10-minute windows for progress...")
        total_sec = _get_wav_duration_sec(INPUT_WAV)
        total_windows = int((total_sec + WHISPER_WINDOW_SEC - 1) // WHISPER_WINDOW_SEC)
        raw_segments = []

        for window_idx in range(total_windows):
            start_sec = window_idx * WHISPER_WINDOW_SEC
            end_sec = min((window_idx + 1) * WHISPER_WINDOW_SEC, total_sec)

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp_file:
                _export_wav_slice(INPUT_WAV, Path(tmp_file.name), start_sec, end_sec)
                result = model.transcribe(
                    tmp_file.name,
                    language=None,
                    task="transcribe",
                    verbose=False,
                )

            offset_sec = start_sec
            for seg in result.get("segments", []):
                try:
                    seg_start = float(seg["start"]) + offset_sec
                    seg_end = float(seg["end"]) + offset_sec
                    raw_segments.append({"start": seg_start, "end": seg_end})
                except Exception:
                    continue

            print(
                "[PROGRESS] Processed 10-minute chunk "
                f"{window_idx + 1}/{total_windows} "
                f"({start_sec:.1f}s to {end_sec:.1f}s)"
            )

        print(f"[INFO] Raw segments from Whisper windows: {len(raw_segments)}")

        segments = _clean_segments(raw_segments)
        print(f"[INFO] Valid segments after cleanup: {len(segments)}")

        segments = _merge_short_segments(segments, MIN_DURATION_SEC)
        print(
            f"[INFO] Segments after merging clips < {MIN_DURATION_SEC:.1f}s: {len(segments)}"
        )

        final_segments = []
        durations = []
        long_count = 0

        for idx, seg in enumerate(segments, start=1):
            start = round(seg["start"], 3)
            end = round(seg["end"], 3)
            duration = round(end - start, 3)
            is_long = duration > LONG_THRESHOLD_SEC
            if is_long:
                long_count += 1

            final_segments.append(
                {
                    "id": idx,
                    "start": start,
                    "end": end,
                    "duration": duration,
                    "long": is_long,
                }
            )
            durations.append(duration)

        total = len(final_segments)
        for i, seg in enumerate(final_segments, start=1):
            start_sec = float(seg["start"])
            end_sec = float(seg["end"])
            clip_name = f"clip_{i:04d}.wav"
            clip_path = OUTPUT_CLIPS_DIR / clip_name
            _export_wav_slice(INPUT_WAV, clip_path, start_sec, end_sec)

            if i % 50 == 0 or i == total:
                print(f"[PROGRESS] Exported clips: {i}/{total}")

        with OUTPUT_JSON.open("w", encoding="utf-8") as f:
            json.dump(final_segments, f, ensure_ascii=False, indent=2)

        if durations:
            shortest = min(durations)
            longest = max(durations)
            mean_duration = round(statistics.mean(durations), 3)
        else:
            shortest = 0.0
            longest = 0.0
            mean_duration = 0.0

        print(f"Total segments: {len(final_segments)}")
        print(f"Shortest clip duration: {shortest:.3f}")
        print(f"Longest clip duration: {longest:.3f}")
        print(f"Mean clip duration: {mean_duration:.3f}")
        print(f"Count of clips flagged as long (over 15 seconds): {long_count}")
        return 0

    except Exception as exc:
        print(f"[ERROR] 02_vad_segment.py failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
