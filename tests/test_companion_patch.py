import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from oot_trump.companion_patch import patch_companion_messages, hud_pixels, patch_runtime
from oot_trump.audio_patch import _patch_audio_heap
from oot_trump.message_patch import MessagePatchError


def message(english, message_id='0x1000'):
    return f'''DEFINE_MESSAGE({message_id}, TEXTBOX_TYPE_BLACK, TEXTBOX_POS_TOP,
MSG("Navi" SFX(NA_SE_VO_NA_HELLO_3)),
MSG({english}), MSG("Navi"), MSG("Navi"))'''


class CompanionPatchTests(unittest.TestCase):
    def test_english_only_names_cues_and_story_controls(self):
        source = message('UNSKIPPABLE SFX(NA_SE_VO_NA_HELLO_3) "Navi" BOX_BREAK UNSKIPPABLE "old" TEXTID(0x1234)')
        rows = [{'id':'0x1000','pages':[['Trump is here.'],['Follow {player}.']]}]
        patched, _ = patch_companion_messages(source, rows)
        self.assertIn('MSG("Navi" SFX(NA_SE_VO_NA_HELLO_3))',patched)
        self.assertEqual(patched.count('MSG("Navi")'),2)
        self.assertIn('NA_SE_VO_TRUMP_CUE_INTRO_HELLO',patched)
        self.assertIn('TEXTID(0x1234)',patched)
        self.assertIn('NAME',patched)
        self.assertEqual(patched.count('BOX_BREAK'),1)
        self.assertEqual(patch_companion_messages(patched,rows)[0],patched)
        with self.assertRaises(MessagePatchError):
            patch_companion_messages(source,[{'id':'0x1000','pages':[['One page']]}])

    def test_name_reference_keeps_other_speaker_and_pronoun(self):
        source=message('"Navi says listen to her!"','0x103F')
        patched,_=patch_companion_messages(source,[])
        self.assertIn('"Trump says listen to him!"',patched)
        self.assertNotIn('COLOR(LIGHTBLUE)',patched)

    def test_hud_and_facing_are_idempotent(self):
        self.assertEqual(len(hud_pixels()),128)
        with TemporaryDirectory() as directory:
            root=Path(directory)
            hud=root/'src/code/z_parameter.c'
            actor=root/'src/overlays/actors/ovl_En_Elf/z_en_elf.c'
            hud.parent.mkdir(parents=True)
            actor.parent.mkdir(parents=True)
            hud.write_text('    static void* cUpLabelTextures[] = LANGUAGE_ARRAY(gNaviCUpJPNTex, gNaviCUpENGTex, gNaviCUpENGTex, gNaviCUpENGTex);')
            actor.write_text("""        /* OOT_TRUMP_CAMERA_FACING */
        if (this->actor.params == FAIRY_NAVI) {
            Matrix_RotateY(BINANG_TO_RAD(Math_Vec3f_Yaw(&mtxMult, &play->view.eye)), MTXMODE_APPLY);
        }
        Matrix_Scale(scale, scale, scale, MTXMODE_APPLY);""")
            patch_runtime(root)
            expected=(hud.read_text(),actor.read_text())
            patch_runtime(root)
            self.assertEqual((hud.read_text(),actor.read_text()),expected)
            self.assertNotIn('play->view.eye',actor.read_text())
            self.assertIn('BINANG_TO_RAD(this->actor.shape.rot.y)',actor.read_text())
            self.assertIn('FAIRY_NAVI',actor.read_text())

    def test_permanent_fonts_reserve_extra_heap_and_support_subsets(self):
        with TemporaryDirectory() as directory:
            root=Path(directory)
            for name,text in (
                ('src/buffers/audio_heap.c','u8 gAudioHeap[0x38000];'),
                ('include/buffers.h','extern u8 gAudioHeap[0x38000];'),
                ('src/audio/game/session_init.c','#define SFX_SOUNDFONTS_SIZE (Soundfont_0_SIZE + Soundfont_1_SIZE)'),
            ):
                path=root/name
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(text)
            clips=[SimpleNamespace(font_index=i) for i in (38,39,40)]
            _patch_audio_heap(root,clips)
            _patch_audio_heap(root,clips)
            self.assertIn('0x48000',(root/'include/buffers.h').read_text())
            self.assertIn('Soundfont_40_SIZE',(root/'src/audio/game/session_init.c').read_text())
            _patch_audio_heap(root,clips[:1])
            self.assertNotIn('Soundfont_40_SIZE',(root/'src/audio/game/session_init.c').read_text())
