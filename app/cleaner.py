from __future__ import annotations

import re

# Collapse 3+ blank lines down to 2, and 2+ spaces/tabs down to 1.
_MULTI_BLANK_LINES = re.compile(r"\n{3,}")
_MULTI_SPACE = re.compile(r"[ \t]{2,}")
_TRAILING_SPACE = re.compile(r"[ \t]+\n")

# Common docs-site boilerplate lines that add noise but no information.
_NOISE_LINE_PATTERNS = [
    re.compile(r"^\s*(cookie|privacy) (policy|settings)\s*$", re.IGNORECASE),
    re.compile(r"^\s*©\s*\d{4}.*$"),
    re.compile(r"^\s*was this page helpful\??\s*$", re.IGNORECASE),
    re.compile(r"^\s*(yes|no)\s*$", re.IGNORECASE),
    re.compile(r"^\s*edit this page (on github)?\s*$", re.IGNORECASE),
    re.compile(r"^\s*on this page\s*$", re.IGNORECASE),
    re.compile(r"^\s*table of contents\s*$", re.IGNORECASE),
]


def clean_text(text: str) -> str:
    """
    Normalize whitespace and strip common docs-site boilerplate lines
    from extracted page text. Deliberately conservative: it never removes
    substantive content, only obvious UI chrome noise.
    """

    if not text:
        return ""

    lines = text.split("\n")
    kept_lines = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            kept_lines.append("")
            continue

        if any(pattern.match(stripped) for pattern in _NOISE_LINE_PATTERNS):
            continue

        kept_lines.append(stripped)

    cleaned = "\n".join(kept_lines)
    cleaned = _TRAILING_SPACE.sub("\n", cleaned)
    cleaned = _MULTI_SPACE.sub(" ", cleaned)
    cleaned = _MULTI_BLANK_LINES.sub("\n\n", cleaned)

    return cleaned.strip()