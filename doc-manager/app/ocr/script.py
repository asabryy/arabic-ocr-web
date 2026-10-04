"""Script and direction detection shared by both conversion paths.

Extracted from ``pipeline.py`` unchanged so the digital path and the Gemini path
resolve direction identically — two implementations of bidi would drift, and the
difference would show up as documents that read correctly on one route and not
the other.
"""

import unicodedata

# Arabic (+ supplements and presentation forms), Hebrew, Syriac, Thaana, N'Ko:
# everything Word must lay out right-to-left.
RTL_RANGES = (
    (0x0590, 0x05FF),  # Hebrew
    (0x0600, 0x06FF),  # Arabic
    (0x0700, 0x074F),  # Syriac
    (0x0750, 0x077F),  # Arabic Supplement
    (0x0780, 0x07BF),  # Thaana
    (0x07C0, 0x07FF),  # N'Ko
    (0x0860, 0x08FF),  # Syriac Supplement / Arabic Extended-A
    (0xFB1D, 0xFDFF),  # Hebrew + Arabic Presentation Forms-A
    (0xFE70, 0xFEFF),  # Arabic Presentation Forms-B
)

# The legacy block holding one codepoint per CONTEXTUAL SHAPE of an Arabic
# letter. A PDF storing these renders correctly and is broken for everything
# else — search, spellcheck, copy-paste, and Word's own shaping.
PRESENTATION_RANGES = ((0xFB50, 0xFDFF), (0xFE70, 0xFEFF))

# Tashkeel and the tatweel used to pad justified text.
TASHKEEL = frozenset(range(0x064B, 0x0653)) | {0x0670}
TATWEEL = "ـ"


def _in(cp: int, ranges: tuple[tuple[int, int], ...]) -> bool:
    return any(lo <= cp <= hi for lo, hi in ranges)


def is_rtl_char(ch: str) -> bool:
    return bool(ch) and _in(ord(ch), RTL_RANGES)


def is_presentation_char(ch: str) -> bool:
    return bool(ch) and _in(ord(ch), PRESENTATION_RANGES)


def is_latin_char(ch: str) -> bool:
    if not ch or not ch.isalpha():
        return False
    cp = ord(ch)
    return (0x41 <= cp <= 0x5A) or (0x61 <= cp <= 0x7A) or (0x00C0 <= cp <= 0x024F)


def is_combining_mark(ch: str) -> bool:
    """A mark that belongs to the letter before it and must never move alone."""
    return bool(ch) and (ord(ch) in TASHKEEL or unicodedata.combining(ch) != 0)


def char_script(ch: str) -> str | None:
    """'rtl', 'ltr', or None for a neutral character (space, digit, punctuation)."""
    if is_rtl_char(ch):
        # Combining marks inherit the direction of what they sit on, and here they
        # only ever sit on Arabic letters, so counting them as RTL is safe.
        return "rtl"
    if is_latin_char(ch):
        return "ltr"
    return None


def is_rtl_text(text: str, default: bool = True) -> bool:
    """True when a string is majority right-to-left.

    Counted per WORD — each token takes the direction of its first strong
    character — not per character: Arabic words are markedly shorter than their
    Latin equivalents, so a character count flips "نص Smith" to left-to-right on
    spelling alone. Text with no strong characters at all (a numeric table cell, a
    date) falls back to ``default``, the surrounding direction, rather than being
    forced left-to-right.
    """
    rtl = ltr = 0
    for token in text.split():
        for ch in token:
            script = char_script(ch)
            if script == "rtl":
                rtl += 1
                break
            if script == "ltr":
                ltr += 1
                break
    if rtl == ltr:
        return default
    return rtl > ltr


def segment_by_script(text: str, default_rtl: bool) -> list[tuple[str, bool]]:
    """Split text into (chunk, is_rtl) runs at strong-direction boundaries.

    Neutral characters attach to the chunk that precedes them (or to the first
    strong chunk when they lead), so "قال Smith في 1998" becomes an RTL run, an LTR
    run and an RTL run — each of which can then carry (or not carry) ``<w:rtl/>``.
    """
    if not text:
        return []
    chunks: list[list] = []  # [text, is_rtl|None]
    for ch in text:
        script = char_script(ch)
        want = None if script is None else (script == "rtl")
        if chunks and (want is None or chunks[-1][1] in (None, want)):
            chunks[-1][0] += ch
            if chunks[-1][1] is None and want is not None:
                chunks[-1][1] = want
        else:
            chunks.append([ch, want])
    return [(t, default_rtl if d is None else d) for t, d in chunks]


def normalise_presentation_forms(text: str) -> str:
    """Expand Arabic presentation forms to real letters, and nothing else.

    NFKC is applied PER CHARACTER and only to the presentation blocks. Running it
    over the whole string also rewrites digits, ligatures and compatibility
    characters elsewhere in the text, which is a silent corruption of content the
    document actually meant.
    """
    return "".join(
        unicodedata.normalize("NFKC", c) if is_presentation_char(c) else c
        for c in text
    )
