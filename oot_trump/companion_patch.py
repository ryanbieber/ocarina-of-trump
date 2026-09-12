"""Complete English companion identity, story dialogue, HUD, and facing patch."""
import json
import re
from pathlib import Path

from .message_patch import DEFINE, _scan_balanced, _split_args, MessagePatchError
from .project import ROOT, ProjectError
from .title_patch import GLYPHS

CUES = {
    'NA_SE_VO_NAVY_CALL': 'NA_SE_VO_TRUMP_CUE_CALL',
    'NA_SE_VO_NA_HELLO_2': 'NA_SE_VO_TRUMP_CUE_CALL',
    'NA_SE_VO_NA_HELLO_3': 'NA_SE_VO_TRUMP_CUE_INTRO_HELLO',
    'NA_SE_VO_NAVY_HELLO': 'NA_SE_VO_TRUMP_CUE_TARGET_NPC',
    'NA_SE_VO_NAVY_HEAR': 'NA_SE_VO_TRUMP_CUE_TARGET_OBJECT',
    'NA_SE_VO_NAVY_ENEMY': 'NA_SE_VO_TRUMP_CUE_TARGET_ENEMY',
}
STRINGS = re.compile(r'"(?:\\.|[^"\\])*"')
BREAK = re.compile(r'(BOX_BREAK(?:_DELAYED\([^)]*\))?)')


def rewrites():
    return json.loads((ROOT / 'content/companion-story.en.json').read_text())['messages']


def render_page(lines, original, speaker):
    result = ['UNSKIPPABLE'] if 'UNSKIPPABLE' in original else []
    # Preserve cutscene sound triggers and all page/flow terminal controls.
    result.extend(re.findall(r'SFX\([^)]*\)', original))
    if speaker == 'Trump':
        result.append('COLOR(LIGHTBLUE)')
    for i, line in enumerate(lines):
        if len(line.replace('{player}', '12345678')) > 34:
            raise MessagePatchError('Story line exceeds conservative textbox limit: ' + line)
        if i:
            result.append('NEWLINE')
        pieces = line.split('{player}')
        for j, piece in enumerate(pieces):
            if j:
                result.append('NAME')
            if piece:
                result.append(json.dumps(piece))
    if speaker == 'Trump':
        result.append('COLOR(DEFAULT)')
    result.extend(re.findall(r'\b(?:TEXTID\([^)]*\)|FADE\([^)]*\)|FADE2\([^)]*\)|EVENT|PERSISTENT|OCARINA)\b|\b(?:TEXTID|FADE|FADE2)\([^)]*\)', original))
    return '\n'.join(result)


def patch_companion_messages(source, entries=None):
    entries = rewrites() if entries is None else entries
    by_id = {int(row['id'], 16): row for row in entries}
    found, edits, index = set(), [], []
    for match in DEFINE.finditer(source):
        if match.group(1) == 'DEFINE_MESSAGE_JPN':
            continue
        start = source.find('(', match.start())
        end = _scan_balanced(source, start)
        args = _split_args(source[start+1:end])
        if len(args) != 7:
            raise MessagePatchError('Unexpected message layout')
        message_id = int(args[0], 16)
        original = args[4]
        english = original
        row = by_id.get(message_id)
        if row:
            parts = BREAK.split(original[original.index('(')+1:original.rfind(')')])
            pages = parts[::2]
            if len(pages) != len(row['pages']):
                raise MessagePatchError(f"{row['id']}: story page count changed")
            for i, lines in enumerate(row['pages']):
                parts[2*i] = render_page(lines, pages[i], row.get('speaker', 'Trump'))
            english = 'MSG(\n' + '\n'.join(parts) + '\n)'
            found.add(message_id)
        # Only quoted English words are renamed, never identifiers or other languages.
        english = STRINGS.sub(lambda m: re.sub(r'\bNavi\b', 'Trump', m[0], flags=re.I), english)
        if message_id == 0x1017:
            english = english.replace('her words of wisdom', 'his words of wisdom')
        if message_id == 0x103F:
            english = english.replace('listen to her!', 'listen to him!')
        for old, new in CUES.items():
            english = re.sub(r'\b' + old + r'\b', new, english)
        if re.search(r'\bNavi\b', english, re.I) or any(old in english for old in CUES):
            raise MessagePatchError(f'{message_id:04X}: old companion identity remains')
        if english != original:
            args[4] = english
            edits.append((match.start(), end+1, match.group(1) + '(\n' + ',\n'.join(args) + '\n)'))
            index.append(f'0x{message_id:04X}')
    missing = set(by_id) - found
    if missing:
        raise MessagePatchError('Missing story IDs: ' + ', '.join(f'{i:04X}' for i in sorted(missing)))
    for start, end, replacement in reversed(edits):
        source = source[:start] + replacement + source[end:]
    return source, index


def hud_pixels():
    pixels = [0] * (32 * 8)
    for i, char in enumerate('TRUMP'):
        for y, row in enumerate(GLYPHS[char]):
            for x in range(5):
                if row & (1 << (4-x)):
                    pixels[y*32 + 1 + i*6 + x] = 15  # IA4: white and opaque
    return bytes((pixels[i] << 4) | pixels[i+1] for i in range(0, len(pixels), 2))


def patch_runtime(repo):
    hud = repo / 'src/code/z_parameter.c'
    text = hud.read_text()
    old = 'LANGUAGE_ARRAY(gNaviCUpJPNTex, gNaviCUpENGTex, gNaviCUpENGTex, gNaviCUpENGTex)'
    new = 'LANGUAGE_ARRAY(gNaviCUpJPNTex, sTrumpCUpENGTex, gNaviCUpENGTex, gNaviCUpENGTex)'
    if old not in text and new not in text:
        raise ProjectError('English C-Up texture anchor missing')
    if '/* OOT_TRUMP_HUD */' not in text:
        data = hud_pixels()
        words = ',\n'.join('    0x' + data[i:i+8].hex() + 'ULL' for i in range(0,len(data),8))
        anchor = '    static void* cUpLabelTextures[] = '
        text = text.replace(anchor, '    /* OOT_TRUMP_HUD */\n    static u64 sTrumpCUpENGTex[] = {\n' + words + '\n    };\n' + anchor, 1)
    hud.write_text(text.replace(old, new))
    actor = repo / 'src/overlays/actors/ovl_En_Elf/z_en_elf.c'
    text = actor.read_text()
    anchor = '        Matrix_Scale(scale, scale, scale, MTXMODE_APPLY);'
    # Migrate existing builds as well as pristine checkouts. The stock limb
    # callback resets the matrix, so explicitly restore the actor's own yaw.
    old = """        /* OOT_TRUMP_CAMERA_FACING */
        if (this->actor.params == FAIRY_NAVI) {
            Matrix_RotateY(BINANG_TO_RAD(Math_Vec3f_Yaw(&mtxMult, &play->view.eye)), MTXMODE_APPLY);
        }
"""
    text = text.replace(old, '')
    if 'OOT_TRUMP_CAMERA_FACING' in text:
        raise ProjectError('Unrecognized old camera-facing patch')
    if '/* OOT_TRUMP_ACTOR_FACING */' not in text:
        if text.count(anchor) != 1:
            raise ProjectError('Fairy facing anchor missing')
        text = text.replace(anchor, """        /* OOT_TRUMP_ACTOR_FACING */
        if (this->actor.params == FAIRY_NAVI) {
            Matrix_RotateY(BINANG_TO_RAD(this->actor.shape.rot.y), MTXMODE_APPLY);
        }
""" + anchor)
    actor.write_text(text)


def apply_companion(repo, *, check=False):
    path = repo / 'extracted/ntsc-1.0/text/message_data.h'
    text, index = patch_companion_messages(path.read_text())
    if not check:
        path.write_text(text)
        patch_runtime(repo)
    return index
