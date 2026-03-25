#!/usr/bin/env python3
from pathlib import Path
import json
import re
import sys
import datetime
from xml.etree import ElementTree as ET
from xml.dom import minidom


SEGMENTS_JSON = Path("/Users/semakoc/formosan-bank/Karachay_ASR/segments.json")
MEDIA_WAV_PATH = Path("/Users/semakoc/formosan-bank/Karachay_ASR/audio_16k_mono.wav")
OUTPUT_EAF = Path("/Users/semakoc/formosan-bank/Karachay_ASR/annotation_project.eaf")

MEDIA_URL = "file:///Users/semakoc/formosan-bank/Karachay_ASR/audio_16k_mono.wav"
MEDIA_TYPE = "audio/x-wav"


def _ms_from_seconds(value) -> int:
    return int(round(float(value) * 1000.0))


def _pretty_print_xml(elem: ET.Element) -> str:
    raw = ET.tostring(elem, encoding="utf-8")
    pretty = minidom.parseString(raw).toprettyxml(indent="  ")
    lines = pretty.splitlines()
    if lines and lines[0].startswith("<?xml"):
        lines = lines[1:]
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    try:
        print("[INFO] Building ELAN .eaf from segments.json ...")

        if not SEGMENTS_JSON.exists():
            print(f"[ERROR] Missing segments.json: {SEGMENTS_JSON}")
            return 1

        try:
            segments = json.loads(SEGMENTS_JSON.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"[ERROR] Invalid JSON in segments.json: {exc}")
            return 1

        if not isinstance(segments, list):
            print("[ERROR] segments.json must be a JSON array.")
            return 1
        if len(segments) == 0:
            print("[ERROR] segments.json is empty; nothing to write.")
            return 1

        created_dt = datetime.datetime.now(datetime.timezone.utc)
        created_str = created_dt.isoformat(timespec="seconds").replace("+00:00", "Z")

        root = ET.Element(
            "ANNOTATION_DOCUMENT",
            attrib={
                "AUTHOR": "",
                "DATE": created_str,
                "FORMAT": "3.0",
                "VERSION": "6.0",
            },
        )

        header = ET.SubElement(
            root,
            "HEADER",
            attrib={
                "MEDIA_FILE": "",          # fix 4: ELAN expects empty string here
                "TIME_UNITS": "milliseconds",
            },
        )

        media_desc = ET.SubElement(
            header,
            "MEDIA_DESCRIPTOR",
            attrib={
                "MEDIA_URL": MEDIA_URL,
                "MIME_TYPE": MEDIA_TYPE,
                "RELATIVE_MEDIA_URL": "",  # fix 3: must be empty string, not "false"
            },
        )
        _ = media_desc  # keep for clarity; no other use

        # BUG 1 FIX: LINGUISTIC_TYPE belongs at document level, AFTER </HEADER>, not inside it.
        ET.SubElement(
            root,
            "LINGUISTIC_TYPE",
            attrib={
                "GRAPHIC_REFERENCES": "false",
                "LINGUISTIC_TYPE_ID": "default-lt",
                "TIME_ALIGNABLE": "true",
            },
        )

        time_order = ET.SubElement(root, "TIME_ORDER")

        # Exactly 3 tiers with required structure
        tier_transcription = ET.SubElement(
            root,
            "TIER",
            attrib={
                "LINGUISTIC_TYPE_REF": "default-lt",
                "TIER_ID": "transcription",
            },
        )
        tier_translation = ET.SubElement(
            root,
            "TIER",
            attrib={
                "LINGUISTIC_TYPE_REF": "default-lt",
                "PARENT_REF": "transcription",
                "TIER_ID": "translation",
            },
        )
        tier_notes = ET.SubElement(
            root,
            "TIER",
            attrib={
                "LINGUISTIC_TYPE_REF": "default-lt",
                "PARENT_REF": "transcription",
                "TIER_ID": "notes",
            },
        )

        time_slot_id = 1
        alignable_count = 0
        ref_count = 0

        for i, seg in enumerate(segments, start=1):
            try:
                start_s = float(seg["start"])
                end_s = float(seg["end"])
            except Exception:
                continue
            if end_s <= start_s:
                continue

            start_ms = _ms_from_seconds(start_s)
            end_ms = _ms_from_seconds(end_s)

            ts1 = f"ts{time_slot_id}"
            time_slot_id += 1
            ts2 = f"ts{time_slot_id}"
            time_slot_id += 1

            ET.SubElement(
                time_order,
                "TIME_SLOT",
                attrib={"TIME_SLOT_ID": ts1, "TIME_VALUE": str(start_ms)},
            )
            ET.SubElement(
                time_order,
                "TIME_SLOT",
                attrib={"TIME_SLOT_ID": ts2, "TIME_VALUE": str(end_ms)},
            )

            # transcription tier: ALIGNABLE_ANNOTATION (a*)
            a_id = f"a{i}"
            ann_a = ET.SubElement(tier_transcription, "ANNOTATION")
            alignable = ET.SubElement(
                ann_a,
                "ALIGNABLE_ANNOTATION",
                attrib={"ANNOTATION_ID": a_id, "TIME_SLOT_REF1": ts1, "TIME_SLOT_REF2": ts2},
            )
            ET.SubElement(alignable, "ANNOTATION_VALUE").text = ""
            alignable_count += 1

            # translation tier: REF_ANNOTATION (b*) referencing a*
            b_id = f"b{i}"
            ann_b = ET.SubElement(tier_translation, "ANNOTATION")
            ref_b = ET.SubElement(
                ann_b,
                "REF_ANNOTATION",
                attrib={"ANNOTATION_ID": b_id, "ANNOTATION_REF": a_id},
            )
            ET.SubElement(ref_b, "ANNOTATION_VALUE").text = ""
            ref_count += 1

            # notes tier: REF_ANNOTATION (c*) referencing a*
            c_id = f"c{i}"
            ann_c = ET.SubElement(tier_notes, "ANNOTATION")
            ref_c = ET.SubElement(
                ann_c,
                "REF_ANNOTATION",
                attrib={"ANNOTATION_ID": c_id, "ANNOTATION_REF": a_id},
            )
            ET.SubElement(ref_c, "ANNOTATION_VALUE").text = ""
            ref_count += 1

            if i % 500 == 0:
                print(f"[PROGRESS] Built annotations for {i}/{len(segments)} segments ...")

        total_time_slots = time_slot_id - 1

        pretty_body = _pretty_print_xml(root)

        # fix 1: no <!DOCTYPE ...> line
        # fix 2: inject xmlns:xsi / xsi:noNamespaceSchemaLocation via string replacement
        # because ElementTree cannot write these namespace attributes cleanly.
        correct_open_tag = (
            f'<ANNOTATION_DOCUMENT AUTHOR="" DATE="{created_str}" FORMAT="3.0" VERSION="6.0"'
            ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            ' xsi:noNamespaceSchemaLocation="http://www.mpi.nl/tools/elan/EAFv3.0.xsd">'
        )
        pretty_body = re.sub(
            r"<ANNOTATION_DOCUMENT[^>]*>",
            correct_open_tag,
            pretty_body,
            count=1,
        )
        xml_header = '<?xml version="1.0" encoding="UTF-8"?>\n'
        out_text = xml_header + pretty_body

        OUTPUT_EAF.write_text(out_text, encoding="utf-8")

        media_ok = False
        try:
            media_ok = MEDIA_URL in OUTPUT_EAF.read_text(encoding="utf-8")
        except Exception:
            media_ok = False

        print(f"Total TIME_SLOTs: {total_time_slots}")
        print(f"Total ALIGNABLE_ANNOTATIONs: {alignable_count}")
        print(f"Total REF_ANNOTATIONs: {ref_count}")
        print(f"MEDIA_URL confirmed: {media_ok}")
        print(f"[OK] Wrote ELAN file: {OUTPUT_EAF}")
        return 0
    except Exception as exc:
        print(f"[ERROR] 03_build_eaf.py failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

