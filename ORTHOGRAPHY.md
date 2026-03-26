# Karachay Transcription Guidelines

## Script

Cyrillic (Karachay-Balkar standard).

All transcriptions should follow the standard Karachay-Balkar Cyrillic orthography. A native speaker reviewer will review and correct transcriptions before final use.

## Notes Tier Usage

Use the **notes** tier to flag problem segments. Leave the **transcription** tier empty for all of the following:

| Notes value | When to use |
|---|---|
| `unclear` | You can hear speech but cannot make out the word(s) |
| `noise` | The segment contains non-speech sound only (e.g. music, cough, background noise) |
| `overlap` | Multiple speakers are talking at the same time |

If a segment is clean and audible, leave the notes tier empty and fill in the transcription normally.

## Latin Transliteration

The script `05_transliterate.py` converts Cyrillic transcriptions to Latin using the table below. Substitution is single-pass (regex alternation) — multi-character sequences are matched before their constituent letters.

### Multi-character sequences (checked first)

| Cyrillic | Latin | Notes |
|---|---|---|
| къ | q | Karachay uvular stop |
| гъ | gh | Karachay uvular fricative |
| нг | ng | velar nasal |
| дж | j | affricate |
| шч | shch | |
| ше | she | ш before е (prevents double-conversion) |
| щ | shch | |
| ч | ch | |
| ш | sh | |
| ж | zh | |
| ц | ts | |
| ё | yo | |
| ю | yu | |
| я | ya | |

### Single characters

| Cyrillic | Latin | Cyrillic | Latin | Cyrillic | Latin |
|---|---|---|---|---|---|
| а | a | й | y | с | s |
| б | b | к | k | т | t |
| в | v | л | l | у | u |
| г | g | м | m | ф | f |
| д | d | н | n | х | h |
| е | e | о | o | ы | yi |
| з | z | п | p | э | e |
| и | i | р | r | ъ | *(empty)* |
| | | | | ь | *(empty)* |

Uppercase Cyrillic maps to the capitalised Latin equivalent. Any character not in the table is preserved as-is.

## Reviewer Notes

*This section is for the native speaker reviewer. Please add any orthographic corrections, dialect notes, or transcription conventions specific to this recording below.*

---
