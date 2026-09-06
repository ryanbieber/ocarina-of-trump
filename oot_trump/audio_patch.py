from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from .manifest import Dialogue
from .project import ProjectConfig, ProjectError, ROOT
from .voice import _symbol


FONT_SIZE = 64
FONT_INDICES = (38, 39, 40)


@dataclass(frozen=True)
class Clip:
    message_id: int
    page_index: int
    filename: str
    symbol: str
    font_index: int
    effect_index: int

    @property
    def stem(self) -> str:
        return Path(self.filename).stem.upper()

    @property
    def sample(self) -> str:
        return f"SAMPLE_0_{self.stem}"

    @property
    def effect(self) -> str:
        return f"TRUMP_{self.message_id:04X}_{self.page_index:02d}"

    @property
    def channel(self) -> str:
        return f"OOT_TRUMP_CHAN_{self.message_id:04X}_{self.page_index:02d}"


def available_clips(entries: list[Dialogue], voice_dir: Path, require_all: bool) -> list[Clip]:
    found: list[tuple[int, int, str, str]] = []
    missing: list[str] = []
    for entry in sorted(entries, key=lambda item: item.message_id):
        for page_index, page in enumerate(entry.pages):
            if (voice_dir / page.voice).is_file():
                found.append((entry.message_id, page_index, page.voice, _symbol(entry, page_index)))
            else:
                missing.append(page.voice)
    if require_all and missing:
        raise ProjectError(f"missing {len(missing)} voice WAVs (first: {', '.join(missing[:3])})")
    if not found:
        raise ProjectError(f"no voice WAVs found in {voice_dir}")
    if any(page_index != 0 for _message_id, page_index, _filename, _symbol_name in found):
        raise ProjectError("multi-page voice messages need an explicit page-advance hook")
    if len(found) > FONT_SIZE * len(FONT_INDICES):
        raise ProjectError(
            f"voice catalog exceeds the {len(FONT_INDICES)}-soundfont "
            f"{FONT_SIZE * len(FONT_INDICES)}-clip capacity"
        )
    return [
        Clip(*item, FONT_INDICES[index // FONT_SIZE], index % FONT_SIZE)
        for index, item in enumerate(found)
    ]


def _markers(name: str) -> tuple[str, str]:
    return (f"/* OOT_TRUMP_{name}_START */", f"/* OOT_TRUMP_{name}_END */")


def _replace_block(text: str, block: str, name: str) -> str:
    start, end = _markers(name)
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    if pattern.search(text):
        return pattern.sub(block, text)
    return text


def _insert_before(text: str, marker: str, block: str, name: str) -> str:
    start, _end = _markers(name)
    if start in text:
        return _replace_block(text, block, name)
    if marker not in text:
        raise ProjectError(f"audio patch anchor not found: {marker}")
    return text.replace(marker, block + "\n" + marker, 1)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _patch_samplebank(path: Path, clips: list[Clip]) -> None:
    text = path.read_text(encoding="utf-8")
    start, end = _markers("SAMPLEBANK")
    lines = [start]
    for clip in clips:
        lines.append(
            f'    <Sample Name="{clip.sample}" '
            f'Path="$(BUILD_DIR)/assets/audio/samples/SampleBank_0/{Path(clip.filename).stem}.aifc"/>'
        )
    lines.append(end)
    _write(path, _insert_before(text, "</SampleBank>", "\n".join(lines), "SAMPLEBANK"))


def _write_soundfonts(repo: Path, clips: list[Clip]) -> None:
    directory = repo / "assets/audio/soundfonts"
    for font_index in FONT_INDICES:
        subset = [clip for clip in clips if clip.font_index == font_index]
        path = directory / f"Soundfont_{font_index}.xml"
        if not subset:
            if path.exists():
                path.unlink()
            continue
        lines = [
            f'<Soundfont Name="Soundfont_{font_index}" Index="{font_index}" Medium="MEDIUM_CART" '
            'CachePolicy="CACHE_LOAD_TEMPORARY" '
            'SampleBank="$(BUILD_DIR)/assets/audio/samplebanks/SampleBank_0.xml">',
            "    <Samples>",
        ]
        lines.extend(f'        <Sample Name="{clip.sample}"/>' for clip in subset)
        lines.extend(["    </Samples>", "    <Effects>"])
        lines.extend(
            f'        <Effect Name="{clip.effect}" Sample="{clip.sample}"/>' for clip in subset
        )
        lines.extend(["    </Effects>", "</Soundfont>", ""])
        _write(path, "\n".join(lines))


def _patch_voice_table(path: Path, clips: list[Clip]) -> None:
    text = path.read_text(encoding="utf-8")
    start, end = _markers("VOICE_TABLE")
    lines = [start, "/* Trump-as-Navi message voice-over. */"]
    for offset, clip in enumerate(clips):
        lines.append(
            f"/* 0x{0x6880 + offset:04X} */ DEFINE_SFX({clip.channel}, {clip.symbol}, "
            "0x70, 0, 0, SFX_FLAG_5)"
        )
    lines.append(end)
    if start in text:
        text = _replace_block(text, "\n".join(lines), "VOICE_TABLE")
    else:
        text = text.rstrip() + "\n\n" + "\n".join(lines) + "\n"
    _write(path, text)


def _patch_sequence(path: Path, clips: list[Clip]) -> None:
    text = path.read_text(encoding="utf-8")
    include_start, include_end = _markers("SEQUENCE_INCLUDES")
    include_lines = [include_start]
    # Zelda's sequence font operands index the reversed dependency list. Keep
    # vanilla fonts 0 and 1 at operands 0 and 1 by including additions first,
    # in descending order. Custom fonts then occupy operands 2 onward.
    include_lines.extend(
        f'#include "Soundfont_{index}.h"'
        for index in sorted({c.font_index for c in clips}, reverse=True)
    )
    include_lines.append(include_end)
    if include_start in text:
        text = _replace_block(text, "", "SEQUENCE_INCLUDES")
    anchor = '#include "Soundfont_1.h"'
    if anchor not in text:
        raise ProjectError("sequence-0 soundfont include anchor not found")
    text = text.replace(anchor, "\n".join(include_lines) + "\n" + anchor, 1)

    reset = "/* OOT_TRUMP_STOCK_FONT_RESET */\n    font Soundfont_0_ID"
    dispatch_start, dispatch_end = _markers("VOICE_PAGE_DISPATCH")
    if dispatch_start not in text and "OOT_TRUMP_STOCK_FONT_RESET" not in text:
        anchor = "/* 0x5FC7 [0x64                    ] */ ldio        IO_PORT_SFX_INDEX_LOBITS"
        if anchor not in text:
            anchor = "ldio        IO_PORT_SFX_INDEX_LOBITS"
        pos = text.find(anchor, text.find(".channel voicebank_handler_1"))
        if pos < 0:
            raise ProjectError("sequence-0 voice handler anchor not found")
        text = text[:pos] + reset + "\n" + text[pos:]

    # The stock voice handler only selects two 128-entry pages from the low
    # byte of the SFX index. Full Navi coverage extends the voice table past
    # index 255, so mirror the enemy-bank handler and also consult IO port 5.
    stock_start = text.find("/* OOT_TRUMP_STOCK_FONT_RESET */")
    stock_end_label = "CHAN_5FD5:"
    stock_end = text.find(stock_end_label, stock_start)
    if stock_start >= 0 and stock_end >= 0:
        stock_end += len(stock_end_label)
        dispatch = "\n".join(
            [
                dispatch_start,
                "    font Soundfont_0_ID",
                "    ldio IO_PORT_SFX_INDEX_HIBITS",
                "    sub 1",
                "    rbeqz OOT_TRUMP_VOICE_PAGE_2",
                "    ldio IO_PORT_SFX_INDEX_LOBITS",
                "    bgez OOT_TRUMP_VOICE_PAGE_0",
                "    and 127",
                "    dyntbl voicebank_table + 2 * 1 * 128",
                "    rjump OOT_TRUMP_VOICE_DISPATCH_DONE",
                "OOT_TRUMP_VOICE_PAGE_2:",
                "    dyntbl voicebank_table + 2 * 2 * 128",
                "    ldio IO_PORT_SFX_INDEX_LOBITS",
                "    bgez OOT_TRUMP_VOICE_DISPATCH_DONE",
                "    and 127",
                "    dyntbl voicebank_table + 2 * 3 * 128",
                "    rjump OOT_TRUMP_VOICE_DISPATCH_DONE",
                "OOT_TRUMP_VOICE_PAGE_0:",
                "    dyntbl voicebank_table + 2 * 0 * 128",
                "OOT_TRUMP_VOICE_DISPATCH_DONE:",
                dispatch_end,
            ]
        )
        text = text[:stock_start] + dispatch + text[stock_end:]

    channel_start, channel_end = _markers("SEQUENCE_CHANNELS")
    lines = [channel_start, "/* One-shot channels; effect numbers are local to each 64-entry font. */"]
    for clip in clips:
        lines.extend(
            [
                f".channel {clip.channel}",
                f"    font {2 + FONT_INDICES.index(clip.font_index)}",
                f"    stseq (ASEQ_OP_LAYER_NOTEDV | SF{clip.font_index}_{clip.effect}), "
                "LAYER_612D + STSEQ_NOTEDV_OPCODE_PITCH",
                "    rjump CHAN_6125",
                "",
            ]
        )
    lines.append(channel_end)
    text = _insert_before(text, "SEQ_0_END:", "\n".join(lines), "SEQUENCE_CHANNELS")
    _write(path, text)


def _write_message_include(path: Path, clips: list[Clip]) -> None:
    lines = [
        "/* Generated by oot-trump install-voice; included only by z_message.c. */",
        "static u16 sTrumpVoiceSfxId = NA_SE_NONE;",
        "",
        "static void Message_StopTrumpVoice(void) {",
        "    if (sTrumpVoiceSfxId != NA_SE_NONE) {",
        "        Audio_StopSfxById(sTrumpVoiceSfxId);",
        "        sTrumpVoiceSfxId = NA_SE_NONE;",
        "    }",
        "}",
        "",
        "static void Message_PlayTrumpVoice(u16 textId) {",
        "    Message_StopTrumpVoice();",
        "    switch (textId) {",
    ]
    for clip in clips:
        if clip.page_index == 0:
            lines.append(f"        case 0x{clip.message_id:04X}: sTrumpVoiceSfxId = {clip.symbol}; break;")
    lines.extend(
        [
            "        default: return;",
            "    }",
            "    SFX_PLAY_CENTERED(sTrumpVoiceSfxId);",
            "}",
            "",
        ]
    )
    _write(path, "\n".join(lines))


def _patch_message_source(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    include = '#include "oot_trump_voice.inc.c" /* OOT_TRUMP_MESSAGE_INCLUDE */'
    # The stop hook appears much earlier than Message_StartTextbox in z_message.c,
    # so keep the generated static functions above Message_CloseTextbox.
    text = text.replace(include + "\n\n", "")
    first_hook = text.find("void Message_CloseTextbox")
    if first_hook < 0:
        raise ProjectError("Message_CloseTextbox not found")
    text = text[:first_hook] + include + "\n\n" + text[first_hook:]

    for function, anchor, call in (
        ("Message_StartTextbox", "play->msgCtx.ocarinaMode = OCARINA_MODE_00;", "Message_PlayTrumpVoice(textId);"),
        ("Message_ContinueTextbox", "msgCtx->textColorAlpha = 255;", "Message_PlayTrumpVoice(textId);"),
        ("Message_CloseTextbox", "MessageContext* msgCtx = &play->msgCtx;", "Message_StopTrumpVoice();"),
    ):
        marker = f"/* OOT_TRUMP_{function.upper()} */"
        if marker in text:
            continue
        start = text.find(f"void {function}")
        pos = text.find(anchor, start)
        if start < 0 or pos < 0:
            raise ProjectError(f"{function} patch anchor not found")
        end = pos + len(anchor)
        text = text[:end] + f"\n    {call} {marker}" + text[end:]
    _write(path, text)


def install_audio_backend(
    repo: Path, entries: list[Dialogue], config: ProjectConfig, require_all: bool = True
) -> int:
    voice_dir = ROOT / "content/voice"
    clips = available_clips(entries, voice_dir, require_all)
    extracted = repo / "extracted" / config.version / "assets/audio"
    samplebank = extracted / "samplebanks/SampleBank_0.xml"
    sequence = repo / "assets/audio/sequences/seq_0.prg.seq"
    voice_table = repo / "include/tables/sfx/voicebank_table.h"
    message_source = repo / "src/code/z_message.c"
    for path in (samplebank, sequence, voice_table, message_source):
        if not path.is_file():
            raise ProjectError(f"missing ZeldaRET build input {path}; run make setup first")

    sample_dir = repo / "assets/audio/samples/SampleBank_0"
    sample_dir.mkdir(parents=True, exist_ok=True)
    wanted = {clip.filename for clip in clips}
    for stale in sample_dir.glob("trump_*.wav"):
        if stale.name not in wanted:
            stale.unlink()
    for clip in clips:
        shutil.copy2(voice_dir / clip.filename, sample_dir / clip.filename)

    _patch_samplebank(samplebank, clips)
    _write_soundfonts(repo, clips)
    _patch_voice_table(voice_table, clips)
    _patch_sequence(sequence, clips)
    _write_message_include(repo / "include/oot_trump_voice.inc.c", clips)
    _patch_message_source(message_source)
    return len(clips)
