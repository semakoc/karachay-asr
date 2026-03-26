#!/usr/bin/env python3
"""
06_inject_transcriptions.py  —  Inject Latin MMS transcriptions into annotation_project.eaf.

- Backs up annotation_project.eaf → annotation_project_backup.eaf first
- Reads mms_transcriptions_latin.json
- Sets ANNOTATION_VALUE text on the "transcription" tier only
- Leaves translation and notes tiers untouched
- Re-serialises with the same minidom + regex approach as 03_build_eaf.py
  so the ANNOTATION_DOCUMENT xmlns:xsi attributes are preserved correctly
"""
import json
import re
import shutil
from pathlib import Path
from xml.dom import minidom
from xml.etree import ElementTree as ET

EAF_PATH    = Path("/Users/semakoc/formosan-bank/Karachay_ASR/annotation_project.eaf")
BACKUP_PATH = Path("/Users/semakoc/formosan-bank/Karachay_ASR/annotation_project_backup.eaf")
JSON_PATH   = Path("/Users/semakoc/formosan-bank/Karachay_ASR/mms_transcriptions_latin.json")

# Register xsi namespace so ET doesn't emit ns0: prefixes in its output.
# (The opening tag is replaced by regex anyway, but this keeps tostring clean.)
ET.register_namespace("xsi", "http://www.w3.org/2001/XMLSchema-instance")


def _serialize(root: ET.Element, date_str: str, author_str: str) -> str:
    """Serialise the ElementTree to a well-formed EAF string.

    Uses the same minidom pretty-print + regex tag-replacement strategy as
    03_build_eaf.py so the xmlns:xsi / xsi:noNamespaceSchemaLocation
    attributes are written correctly (ElementTree cannot do this natively).
    """
    raw    = ET.tostring(root, encoding="utf-8")
    pretty = minidom.parseString(raw).toprettyxml(indent="  ")

    lines = pretty.splitlines()
    if lines and lines[0].startswith("<?xml"):
        lines = lines[1:]
    body = "\n".join(lines).strip() + "\n"

    correct_open = (
        f'<ANNOTATION_DOCUMENT AUTHOR="{author_str}" DATE="{date_str}"'
        ' FORMAT="3.0" VERSION="6.0"'
        ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        ' xsi:noNamespaceSchemaLocation="http://www.mpi.nl/tools/elan/EAFv3.0.xsd">'
    )
    body = re.sub(r"<ANNOTATION_DOCUMENT[^>]*>", correct_open, body, count=1)

    return '<?xml version="1.0" encoding="UTF-8"?>\n' + body


def main() -> int:
    # ── 1. Backup ────────────────────────────────────────────────────────────
    shutil.copy2(EAF_PATH, BACKUP_PATH)
    backup_ok = BACKUP_PATH.exists()
    print(f"Backup created        : {'yes' if backup_ok else 'NO — aborting'}")
    if not backup_ok:
        return 1

    # ── 2. Load transcriptions ───────────────────────────────────────────────
    entries = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    latin_by_id = {e["id"]: e["text"] for e in entries}
    print(f"Transcriptions loaded : {len(latin_by_id)}")

    # ── 3. Parse EAF ────────────────────────────────────────────────────────
    tree = ET.parse(EAF_PATH)
    root = tree.getroot()

    date_str   = root.get("DATE", "")
    author_str = root.get("AUTHOR", "")

    # ── 4. Find transcription tier and index its ALIGNABLE_ANNOTATIONs ──────
    transcription_tier = None
    for tier in root.iter("TIER"):
        if tier.get("TIER_ID") == "transcription":
            transcription_tier = tier
            break

    if transcription_tier is None:
        print("[ERROR] 'transcription' tier not found in EAF.")
        return 1

    # Build map: annotation_id → ANNOTATION_VALUE element
    ann_value_map: dict[str, ET.Element] = {}
    for ann in transcription_tier.findall("ANNOTATION"):
        alignable = ann.find("ALIGNABLE_ANNOTATION")
        if alignable is not None:
            ann_id    = alignable.get("ANNOTATION_ID")
            ann_value = alignable.find("ANNOTATION_VALUE")
            if ann_id and ann_value is not None:
                ann_value_map[ann_id] = ann_value

    print(f"Annotation slots found: {len(ann_value_map)}")

    # ── 5. Inject ────────────────────────────────────────────────────────────
    injected = 0
    skipped  = 0

    for ann_id, text in latin_by_id.items():
        if ann_id in ann_value_map:
            ann_value_map[ann_id].text = text if text else None
            injected += 1
        else:
            skipped += 1

    # ── 6. Serialise and write ───────────────────────────────────────────────
    out_text = _serialize(root, date_str, author_str)
    EAF_PATH.write_text(out_text, encoding="utf-8")

    # ── Summary ──────────────────────────────────────────────────────────────
    print()
    print(f"Transcriptions injected : {injected}")
    print(f"IDs skipped (not found) : {skipped}")
    print(f"Backup confirmed        : {'yes' if backup_ok else 'no'}")
    print(f"Written to              : {EAF_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
