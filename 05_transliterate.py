#!/usr/bin/env python3
"""
05_transliterate.py  —  Convert Cyrillic MMS transcriptions to Latin script.

Input:  mms_transcriptions.json      [{id, clip_file, text (Cyrillic)}, ...]
Output: mms_transcriptions_latin.json [{id, clip_file, text (Latin)},   ...]

Single-pass replacement via a combined regex — multi-character sequences are
tried before their constituent characters so no double-conversion occurs.
"""
import json
import re
from pathlib import Path

INPUT_JSON  = Path("/Users/semakoc/formosan-bank/Karachay_ASR/mms_transcriptions.json")
OUTPUT_JSON = Path("/Users/semakoc/formosan-bank/Karachay_ASR/mms_transcriptions_latin.json")

# ---------------------------------------------------------------------------
# Transliteration table — ORDER MATTERS.
# Multi-character sequences must come before any single character they contain.
# Within each block, more specific (longer) patterns come first.
# ---------------------------------------------------------------------------
MAPPING = [
    # ── multi-character digraphs / trigraphs ────────────────────────────────
    ("КЪ", "Q"),     ("Къ", "Q"),     ("къ", "q"),
    ("ГЪ", "GH"),    ("Гъ", "Gh"),    ("гъ", "gh"),
    ("НГ", "NG"),    ("Нг", "Ng"),    ("нг", "ng"),
    ("ДЖ", "J"),     ("Дж", "J"),     ("дж", "j"),
    ("ШЧ", "SHCH"),  ("Шч", "Shch"),  ("шч", "shch"),
    ("ШЕ", "SHE"),   ("Ше", "She"),   ("ше", "she"),   # ш before е
    ("Щ",  "Shch"),  ("щ",  "shch"),
    ("Ч",  "Ch"),    ("ч",  "ch"),
    ("Ш",  "Sh"),    ("ш",  "sh"),
    ("Ж",  "Zh"),    ("ж",  "zh"),
    ("Ц",  "Ts"),    ("ц",  "ts"),
    ("Ё",  "Yo"),    ("ё",  "yo"),
    ("Ю",  "Yu"),    ("ю",  "yu"),
    ("Я",  "Ya"),    ("я",  "ya"),
    # ── single characters ───────────────────────────────────────────────────
    ("А", "A"),  ("а", "a"),
    ("Б", "B"),  ("б", "b"),
    ("В", "V"),  ("в", "v"),
    ("Г", "G"),  ("г", "g"),
    ("Д", "D"),  ("д", "d"),
    ("Е", "E"),  ("е", "e"),
    ("З", "Z"),  ("з", "z"),
    ("И", "I"),  ("и", "i"),
    ("Й", "Y"),  ("й", "y"),
    ("К", "K"),  ("к", "k"),
    ("Л", "L"),  ("л", "l"),
    ("М", "M"),  ("м", "m"),
    ("Н", "N"),  ("н", "n"),
    ("О", "O"),  ("о", "o"),
    ("П", "P"),  ("п", "p"),
    ("Р", "R"),  ("р", "r"),
    ("С", "S"),  ("с", "s"),
    ("Т", "T"),  ("т", "t"),
    ("У", "U"),  ("у", "u"),
    ("Ф", "F"),  ("ф", "f"),
    ("Х", "H"),  ("х", "h"),
    ("Ы", "Yi"), ("ы", "yi"),
    ("Э", "E"),  ("э", "e"),
    ("Ъ", ""),   ("ъ", ""),   # hard sign — silent
    ("Ь", ""),   ("ь", ""),   # soft sign — silent
]

# Build a single combined regex. re alternation (|) tries each alternative
# left-to-right at every position, so multi-char patterns win over their
# constituent single chars without any post-processing.
_CYRILLIC_RE = re.compile("|".join(re.escape(k) for k, v in MAPPING))
_LOOKUP      = {k: v for k, v in MAPPING}

# Regex to detect any remaining Cyrillic character after conversion
_CYRILLIC_CHECK = re.compile(r"[\u0400-\u04FF]")


def transliterate(text: str) -> str:
    return _CYRILLIC_RE.sub(lambda m: _LOOKUP[m.group(0)], text)


def main() -> int:
    data = json.loads(INPUT_JSON.read_text(encoding="utf-8"))
    print(f"[INFO] Loaded {len(data)} entries from {INPUT_JSON.name}")

    results      = []
    still_cyrillic = []

    for entry in data:
        latin_text = transliterate(entry["text"])
        results.append({
            "id":        entry["id"],
            "clip_file": entry["clip_file"],
            "text":      latin_text,
        })
        if _CYRILLIC_CHECK.search(latin_text):
            still_cyrillic.append(entry["id"])

    # ── side-by-side check for first 10 entries ─────────────────────────────
    print()
    print("First 10 entries — Cyrillic → Latin:")
    print("-" * 72)
    for orig, conv in zip(data[:10], results[:10]):
        print(f"  [{orig['id']}]")
        print(f"    CYR: {orig['text']}")
        print(f"    LAT: {conv['text']}")
    print("-" * 72)

    # ── summary ─────────────────────────────────────────────────────────────
    print()
    print(f"Total converted       : {len(results)}")
    if still_cyrillic:
        print(f"Still contain Cyrillic: {len(still_cyrillic)} entries — {still_cyrillic[:10]}")
    else:
        print("Still contain Cyrillic: 0  ✓")

    OUTPUT_JSON.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Output written to     : {OUTPUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
