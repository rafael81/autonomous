"""Post-process final assistant messages toward a Codex-like CLI style."""

from __future__ import annotations


def codexify_message(text: str | None) -> str | None:
    if text is None:
        return None
    normalized = text.strip()
    if not normalized:
        return normalized

    replacements = {
        "Got it - ": "",
        "Got it — ": "",
        "Done - ": "",
        "Done — ": "",
        "Sure, ": "",
        "Absolutely, ": "",
    }
    for old, new in replacements.items():
        if normalized.startswith(old):
            normalized = new + normalized[len(old) :]

    lines = [line.rstrip() for line in normalized.splitlines()]
    compact = "\n".join(line for line in lines if line or (line == "" and not _prev_blank(lines, line)))
    return compact.strip()


def _prev_blank(lines: list[str], current: str) -> bool:
    index = lines.index(current)
    if index == 0:
        return False
    return lines[index - 1] == ""
