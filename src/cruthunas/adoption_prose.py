from __future__ import annotations

import re


FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
BLOCK_START = re.compile(
    r"^ {0,3}(?:#{1,6}(?:\s|$)|(?:[-+*]|\d+[.)])\s+|>|\|)"
)
STANDALONE = re.compile(
    r"^ {0,3}(?:#{1,6}(?:\s|$)|(?:[-*_]\s*){3,}$|=+\s*$)"
)
INLINE_LINK = re.compile(r"\[([^\]\n]+)\]\((?:[^()\n]|\([^()\n]*\))*\)")
INLINE_IMAGE = re.compile(r"!\[[^\]\n]*\]\((?:[^()\n]|\([^()\n]*\))*\)")
HTML_COMMENT = re.compile(r"<!--[\s\S]*?-->")
UNDERSCORE_EMPHASIS = re.compile(r"(?<!\w)(__?)(?=\S)([^\n]*?\S)\1(?!\w)")
STAR_EMPHASIS = re.compile(r"(?<!\\)(\*{1,3})(?=\S)([^\n]*?\S)\1")


def _mask_range(chars: list[str], start: int, end: int) -> None:
    for index in range(start, end):
        if chars[index] not in "\r\n":
            chars[index] = " "


def _mask_inline_code(text: str) -> str:
    chars = list(text)
    index = 0
    while index < len(text):
        if text[index] != "`":
            index += 1
            continue
        run_end = index + 1
        while run_end < len(text) and text[run_end] == "`":
            run_end += 1
        marker = text[index:run_end]
        close = -1
        search_at = run_end
        while search_at < len(text):
            candidate = text.find("`", search_at)
            if candidate < 0:
                break
            candidate_end = candidate + 1
            while candidate_end < len(text) and text[candidate_end] == "`":
                candidate_end += 1
            if candidate_end - candidate == len(marker):
                close = candidate
                break
            search_at = candidate_end
        if close < 0:
            index = run_end
            continue
        _mask_range(chars, index, close + len(marker))
        index = close + len(marker)
    return "".join(chars)


def _visible_markup(text: str) -> str:
    chars = list(text)
    for match in HTML_COMMENT.finditer(text):
        _mask_range(chars, match.start(), match.end())
    masked = _mask_inline_code("".join(chars))
    chars = list(masked)
    for match in INLINE_IMAGE.finditer(masked):
        _mask_range(chars, match.start(), match.end())
    for match in INLINE_LINK.finditer(masked):
        _mask_range(chars, match.start(), match.start(1))
        _mask_range(chars, match.end(1), match.end())
    for match in UNDERSCORE_EMPHASIS.finditer("".join(chars)):
        _mask_range(chars, match.start(1), match.end(1))
        closing_start = match.end() - len(match.group(1))
        _mask_range(chars, closing_start, match.end())
    for match in STAR_EMPHASIS.finditer("".join(chars)):
        _mask_range(chars, match.start(1), match.end(1))
        closing_start = match.end() - len(match.group(1))
        _mask_range(chars, closing_start, match.end())
    return "".join(chars)


def prose_blocks(text: str, *, markdown: bool = True) -> tuple[str, ...]:
    """Return the visible prose blocks in the supported Markdown subset."""
    if not markdown:
        return (text,) if text.strip() else ()
    blocks: list[str] = []
    current: list[str] = []
    fence_char = ""
    fence_length = 0

    def flush() -> None:
        if current:
            visible = _visible_markup("".join(current))
            if visible.strip():
                blocks.append(visible)
            current.clear()

    for line in text.splitlines(keepends=True):
        if fence_char:
            closing = re.match(rf"^ {{0,3}}{re.escape(fence_char)}{{{fence_length},}}\s*$", line)
            if closing:
                fence_char = ""
                fence_length = 0
            continue
        opening = FENCE_OPEN.match(line)
        if opening:
            flush()
            marker = opening.group(1)
            fence_char, fence_length = marker[0], len(marker)
            continue
        if not line.strip():
            flush()
            continue
        if line.startswith("    ") and not current:
            continue
        starts_block = bool(BLOCK_START.match(line))
        if starts_block:
            flush()
        current.append(line)
        if STANDALONE.match(line) or line.lstrip().startswith("|"):
            flush()
    flush()
    return tuple(blocks)
