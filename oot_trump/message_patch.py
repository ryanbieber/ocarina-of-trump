from __future__ import annotations

import re
from pathlib import Path

from .manifest import Dialogue


DEFINE = re.compile(
    r"\b(DEFINE_MESSAGE(?:_JPN|_NES)?)\s*\(\s*(0x[0-9A-Fa-f]+)"
)


class MessagePatchError(RuntimeError):
    pass


def _scan_balanced(source: str, open_index: int) -> int:
    depth = 0
    quote = False
    escaped = False
    line_comment = False
    block_comment = False
    index = open_index
    while index < len(source):
        char = source[index]
        nxt = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if char == "*" and nxt == "/":
                block_comment = False
                index += 1
        elif quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quote = False
        elif char == "/" and nxt == "/":
            line_comment = True
            index += 1
        elif char == "/" and nxt == "*":
            block_comment = True
            index += 1
        elif char == '"':
            quote = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    raise MessagePatchError("Unbalanced DEFINE_MESSAGE macro")


def _split_args(body: str) -> list[str]:
    args: list[str] = []
    start = 0
    depth = 0
    quote = False
    escaped = False
    for index, char in enumerate(body):
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quote = False
        elif char == '"':
            quote = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "," and depth == 0:
            args.append(body[start:index].strip())
            start = index + 1
    args.append(body[start:].strip())
    return args


def _c_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render_english(entry: Dialogue) -> str:
    chunks: list[str] = []
    for page_index, page in enumerate(entry.pages):
        if page_index:
            chunks.append("BOX_BREAK")
        for line_index, line in enumerate(page.lines):
            chunks.append(_c_string(line))
            if line_index + 1 < len(page.lines):
                chunks.append("NEWLINE")
    return "MSG(\n        " + "\n        ".join(chunks) + "\n    )"


def patch_messages(source: str, entries: list[Dialogue]) -> tuple[str, set[int]]:
    replacements = {entry.message_id: entry for entry in entries}
    found: set[int] = set()
    edits: list[tuple[int, int, str]] = []
    for match in DEFINE.finditer(source):
        macro = match.group(1)
        if macro == "DEFINE_MESSAGE_JPN":
            continue
        message_id = int(match.group(2), 16)
        if message_id not in replacements:
            continue
        open_index = source.find("(", match.start())
        close_index = _scan_balanced(source, open_index)
        args = _split_args(source[open_index + 1 : close_index])
        if len(args) != 7:
            raise MessagePatchError(
                f"0x{message_id:04X}: expected 7 DEFINE_MESSAGE arguments, found {len(args)}"
            )
        args[4] = render_english(replacements[message_id])
        replacement = macro + "(\n    " + ",\n    ".join(args) + "\n)"
        edits.append((match.start(), close_index + 1, replacement))
        found.add(message_id)
    for start, end, replacement in reversed(edits):
        source = source[:start] + replacement + source[end:]
    return source, found


def patch_file(path: Path, entries: list[Dialogue], check: bool = False) -> set[int]:
    original = path.read_text(encoding="utf-8")
    patched, found = patch_messages(original, entries)
    missing = {entry.message_id for entry in entries} - found
    if missing:
        raise MessagePatchError(
            "message_data.h does not contain: "
            + ", ".join(f"0x{value:04X}" for value in sorted(missing))
        )
    if not check:
        path.write_text(patched, encoding="utf-8")
    return found
