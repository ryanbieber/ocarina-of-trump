"""Original pixel lettering for the title subtitle; no extracted asset data."""
from pathlib import Path
import re

from .project import ProjectError

TITLE = "OCARINA OF TRUMP"
WIDTH, HEIGHT = 96, 8
# Original 5x7 uppercase glyphs, authored as row bitmasks.
GLYPHS = {
    " ": (0, 0, 0, 0, 0, 0, 0),
    "A": (14, 17, 17, 31, 17, 17, 17),
    "C": (14, 17, 16, 16, 16, 17, 14),
    "F": (31, 16, 16, 30, 16, 16, 16),
    "I": (14, 4, 4, 4, 4, 4, 14),
    "M": (17, 27, 21, 21, 17, 17, 17),
    "N": (17, 25, 25, 21, 19, 19, 17),
    "O": (14, 17, 17, 17, 17, 17, 14),
    "P": (30, 17, 17, 30, 16, 16, 16),
    "R": (30, 17, 17, 30, 20, 18, 17),
    "T": (31, 4, 4, 4, 4, 4, 4),
    "U": (17, 17, 17, 17, 17, 17, 14),
}
ACTOR = Path("src/overlays/actors/ovl_En_Mag/z_en_mag.c")
OLD = "gTitleOcarinaOfTimeTMTextTex"
NEW = "sOotTrumpSubtitleTex"
START = "/* OOT_TRUMP_SUBTITLE_START */"
END = "/* OOT_TRUMP_SUBTITLE_END */"


def subtitle_pixels() -> bytes:
    pixels = bytearray(WIDTH * HEIGHT)
    text_width = len(TITLE) * 6 - 1
    if text_width > WIDTH:
        raise ProjectError("Title subtitle exceeds its texture width")
    left = (WIDTH - text_width) // 2
    for index, character in enumerate(TITLE):
        for y, row in enumerate(GLYPHS[character]):
            for x in range(5):
                if row & (1 << (4 - x)):
                    pixels[y * WIDTH + left + index * 6 + x] = 255
    return bytes(pixels)


def subtitle_source() -> str:
    pixels = subtitle_pixels()
    words = [f"    0x{pixels[i:i + 8].hex().upper()}ULL," for i in range(0, len(pixels), 8)]
    return "\n".join([
        START,
        '/* Original "OCARINA OF TRUMP" lettering; 96x8 I8, aligned for RDP DMA. */',
        f"static u64 {NEW}[] = {{", *words, "};", END,
    ])


def patch_title_screen(repo: Path, *, check: bool = False) -> None:
    path = repo / ACTOR
    source = path.read_text(encoding="utf-8")
    # Both shadow and foreground must retain their pinned coordinates/format.
    pattern = r"EnMag_DrawTextureI8\(&gfx, (?:" + OLD + "|" + NEW + r"), 96, 8,"
    if len(re.findall(pattern, source)) != 2:
        raise ProjectError("Expected both 96x8 title subtitle draw calls")
    patched = re.sub(pattern, f"EnMag_DrawTextureI8(&gfx, {NEW}, 96, 8,", source)
    if START in patched or END in patched:
        pattern = re.escape(START) + r".*?" + re.escape(END)
        if patched.count(START) != 1 or patched.count(END) != 1 or not re.search(pattern, patched, re.S):
            raise ProjectError("Malformed title subtitle patch markers")
        patched = re.sub(pattern, subtitle_source(), patched, flags=re.S)
    else:
        anchor = "#define FLAGS "
        if patched.count(anchor) != 1:
            raise ProjectError("Title subtitle declaration anchor not found")
        patched = patched.replace(anchor, subtitle_source() + "\n\n" + anchor, 1)
    if not check and patched != source:
        path.write_text(patched, encoding="utf-8")
