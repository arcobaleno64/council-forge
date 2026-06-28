#!/usr/bin/env python3
from __future__ import annotations

import re
from typing import List, Sequence

# REDOS-02 fix: the paren-citation branch wrapped an overlapping required
# path-with-extension in a lazy `[^)）\n]*?` AND a greedy `[^)）\n]*` fill, and the
# bare-path branch ran `[A-Za-z0-9_./\\-]+\.ext` greedily at every search start.
# Both backtracked super-linearly on attacker-authored `## Confirmed Facts` items
# (e.g. an unclosed `(` + path-like filler: ~40 KB -> ~24 s). The paren branch now
# uses one BOUNDED lookahead to assert an inner path.ext, then a single greedy
# fill to the close paren; the bare-path run is BOUNDED to {1,256}. Both are now
# linear; accept/reject is unchanged for real citations (verified vs the prior
# pattern over the test battery + 20k fuzz strings, 0 diffs).
# NOTE: this regex MUST stay byte-identical to the copy in guard_status_validator.py
# (test_guard_units.py asserts CITATION_PATTERN.pattern equality across both).
CITATION_PATTERN = re.compile(
    r"(?:"
    r"https?://\S+"
    r"|`gh api [^`]+`"
    r"|`[^`\n]+\.(?:md|json|txt|py|ps1|csproj|ini|toml|yml|yaml|cfg|sh)[^`\n]*`"
    r"|[（(](?=[^)）\n]{0,512}[A-Za-z0-9_./\\-]\.(?:md|json|txt|py|ps1|csproj|ini|toml|yml|yaml|cfg|sh)(?::\d+)?)[^)）\n]*[)）]"
    r"|\b[A-Za-z0-9_./\\-]{1,256}\.(?:md|json|txt|py|ps1|csproj|ini|toml|yml|yaml|cfg|sh)(?::\d+)?\b"
    r")",
    re.IGNORECASE,
)

__all__ = [
    "CITATION_PATTERN",
    "_marker_present",
    "_is_v2_plan",
    "_required_markers_missing",
]

def _marker_present(text: str, marker: str) -> bool:
    """Test whether a required marker is present in `text`.

    Heading markers (starting with '#') are matched line-anchored to avoid
    false positives like '## Decision' matching '## Decision Class'. Markers
    ending in ':' allow trailing content on the same line; pure headings
    must stand alone (allowing trailing whitespace only). Non-heading markers
    (e.g. 'Task ID:', 'Artifact Type: task') keep the simple substring
    semantics used by the v1 validator.

    See docs/artifact_schema.md §5.13 for the v2 governance extension.
    """
    if marker.startswith("#"):
        if marker.endswith(":"):
            pattern = rf"^{re.escape(marker)}(\s|$)"
        else:
            pattern = rf"^{re.escape(marker)}\s*$"
        return re.search(pattern, text, re.MULTILINE) is not None
    return marker in text


def _is_v2_plan(text: str) -> bool:
    """Detect v2 governance plan format.

    v2 plans use '## Goal' / '## Approach' / '## Authorization Boundary' /
    '## Premortem' / '## Build Guarantee' / '## TAO Trace' instead of v1's
    '## Scope' / '## Proposed Changes' / '## Out of Scope' /
    '## Validation Strategy' / '## Ready For Coding'. Detection succeeds when
    any v2-only section is present, or when the v2 risk pattern (## Premortem
    without ## Validation Strategy) appears.

    See docs/artifact_schema.md §5.13 for the v2 governance extension.
    """
    if "## Authorization Boundary" in text:
        return True
    if "## TAO Trace" in text:
        return True
    return "## Premortem" in text and "## Validation Strategy" not in text


def _required_markers_missing(text: str, required: Sequence) -> List[str]:
    """Compute the list of missing markers for an artifact body.

    Each entry of `required` is either a string (single required marker) or a
    tuple of strings (any-of alternatives). For tuples, the marker is satisfied
    if at least one alternative is present. Returns human-readable labels for
    missing markers; tuple alternatives are rendered as 'A / B / C'.
    """
    missing: List[str] = []
    for marker in required:
        if isinstance(marker, tuple):
            if not any(_marker_present(text, alt) for alt in marker):
                missing.append(" / ".join(marker))
        else:
            if not _marker_present(text, marker):
                missing.append(marker)
    return missing
