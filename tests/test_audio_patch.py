from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from oot_trump.audio_patch import (
    _patch_audiobank_spec,
    _patch_samplebank,
    _patch_sequence,
    _patch_voice_bank_limit,
    _patch_voice_table,
    _patch_message_source,
    _patch_navi_voice_sources,
    _write_message_include,
    _write_soundfonts,
    available_clips,
)
from oot_trump.manifest import load_manifest, load_voice_cues


class AudioPatchTests(unittest.TestCase):
    def test_custom_soundfonts_are_linked_in_audiobank_spec(self) -> None:
        entries = load_manifest()
        cues = load_voice_cues()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            voice_dir = root / "voice"
            voice_dir.mkdir()
            for entry in entries:
                for page in entry.pages:
                    (voice_dir / page.voice).touch()
            for cue in cues:
                (voice_dir / cue.voice).touch()
            clips = available_clips(entries, voice_dir, require_all=True, cues=cues)
            spec = root / "spec"
            spec.write_text(
                '    include "$(BUILD_DIR)/assets/audio/soundfonts/Soundfont_37.o"\n'
                "#if OOT_VERSION >= PAL_1_0\n",
                encoding="utf-8",
            )

            _patch_audiobank_spec(spec, clips)
            first = spec.read_text(encoding="utf-8")
            _patch_audiobank_spec(spec, clips)

            for index in (38, 39, 40):
                self.assertIn(f"Soundfont_{index}.o", first)
            self.assertEqual(first.count("OOT_TRUMP_AUDIOBANK_SPEC_START"), 1)
            self.assertEqual(spec.read_text(encoding="utf-8"), first)

    def test_voice_bank_limit_is_extended_idempotently(self) -> None:
        stock = (
            "static_assert(NA_SE_VO_END - (NA_SE_VO_BASE + 1) <= 256, "
            '"Voice Bank SFX Table is limited to 256 entries due to Sequence 0");\n'
        )
        with tempfile.TemporaryDirectory() as directory:
            header = Path(directory) / "sfx.h"
            header.write_text(stock, encoding="utf-8")

            _patch_voice_bank_limit(header)
            first = header.read_text(encoding="utf-8")
            _patch_voice_bank_limit(header)

            self.assertIn("<= 512", first)
            self.assertEqual(first.count("OOT_TRUMP_VOICE_BANK_LIMIT"), 1)
            self.assertEqual(header.read_text(encoding="utf-8"), first)

    def test_catalog_is_split_across_three_64_effect_soundfonts(self) -> None:
        entries = load_manifest()
        cues = load_voice_cues()
        with tempfile.TemporaryDirectory() as directory:
            voice_dir = Path(directory)
            for entry in entries:
                for page in entry.pages:
                    (voice_dir / page.voice).touch()
            for cue in cues:
                (voice_dir / cue.voice).touch()
            clips = available_clips(entries, voice_dir, require_all=True, cues=cues)
            self.assertEqual(len(clips), 183)
            self.assertEqual({clip.font_index for clip in clips}, {38, 39, 40})
            self.assertEqual(max(clip.effect_index for clip in clips), 63)

    def test_all_stock_navi_vocal_triggers_are_replaced(self) -> None:
        entries = load_manifest()
        cues = load_voice_cues()
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            voice_dir = repo / "voice"
            voice_dir.mkdir()
            for entry in entries:
                for page in entry.pages:
                    (voice_dir / page.voice).touch()
            for cue in cues:
                (voice_dir / cue.voice).touch()
            clips = available_clips(entries, voice_dir, require_all=True, cues=cues)
            en_elf = repo / "src/overlays/actors/ovl_En_Elf/z_en_elf.c"
            parameter = repo / "src/code/z_parameter.c"
            en_elf.parent.mkdir(parents=True)
            parameter.parent.mkdir(parents=True)
            en_elf.write_text(
                "NA_SE_VO_NAVY_HELLO NA_SE_VO_NAVY_HEAR "
                "NA_SE_VO_NAVY_ENEMY NA_SE_VO_SK_LAUGH\n",
                encoding="utf-8",
            )
            parameter.write_text(
                "if (naviCallState == 0x1E) { SFX_PLAY_CENTERED(NA_SE_VO_NAVY_CALL); }\n"
                "func_800F4524(&gSfxDefaultPos, NA_SE_VO_NA_HELLO_2, 32);\n"
                "Sfx_PlaySfxCentered2(NA_SE_VO_NA_HELLO_3);\n",
                encoding="utf-8",
            )

            _patch_navi_voice_sources(repo, clips)

            patched = en_elf.read_text() + parameter.read_text()
            self.assertNotIn("NA_SE_VO_NAVY_", patched)
            self.assertNotIn("NA_SE_VO_NA_HELLO_", patched)
            self.assertNotIn("NA_SE_VO_SK_LAUGH", en_elf.read_text())
            self.assertIn("NA_SE_VO_TRUMP_CUE_CALL", patched)
            self.assertIn("NA_SE_VO_TRUMP_CUE_TALK_OPEN", patched)

    def test_generated_audio_sources_are_idempotent(self) -> None:
        entries = load_manifest()[:1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            voice_dir = root / "voice"
            voice_dir.mkdir()
            (voice_dir / entries[0].pages[0].voice).touch()
            clips = available_clips(entries, voice_dir, require_all=True)

            samplebank = root / "SampleBank_0.xml"
            samplebank.write_text("<SampleBank>\n</SampleBank>\n", encoding="utf-8")
            voice_table = root / "voicebank_table.h"
            voice_table.write_text("/* vanilla */\n", encoding="utf-8")
            sequence = root / "seq_0.prg.seq"
            sequence.write_text(
                '#include "Soundfont_1.h"\n'
                '#include "Soundfont_0.h"\n'
                ".channel voicebank_handler_1\n"
                "/* 0x5FC7 [0x64] */ ldio        IO_PORT_SFX_INDEX_LOBITS\n"
                "bgez        CHAN_5FD2\n"
                "and         127\n"
                "dyntbl      voicebank_table + 2 * 1 * 128\n"
                "rjump       CHAN_5FD5\n"
                "CHAN_5FD2:\n"
                "dyntbl      voicebank_table + 2 * 0 * 128\n"
                "CHAN_5FD5:\n"
                "SEQ_0_END:\n",
                encoding="utf-8",
            )

            for _ in range(2):
                _patch_samplebank(samplebank, clips)
                _patch_voice_table(voice_table, clips)
                _patch_sequence(sequence, clips)
                _write_soundfonts(root, clips)

            self.assertEqual(samplebank.read_text().count("SAMPLE_0_TRUMP_00E0_00"), 1)
            self.assertEqual(voice_table.read_text().count("NA_SE_VO_TRUMP_00E0_00"), 1)
            self.assertEqual(sequence.read_text().count(".channel OOT_TRUMP_CHAN_00E0_00"), 1)
            self.assertLess(
                sequence.read_text().index('#include "Soundfont_38.h"'),
                sequence.read_text().index('#include "Soundfont_1.h"'),
            )
            self.assertIn("    font 2", sequence.read_text())
            self.assertEqual(sequence.read_text().count("OOT_TRUMP_VOICE_PAGE_DISPATCH_START"), 1)
            self.assertIn("ldio IO_PORT_SFX_INDEX_HIBITS", sequence.read_text())
            soundfont = root / "assets/audio/soundfonts/Soundfont_38.xml"
            self.assertIn('Effect Name="TRUMP_00E0_00"', soundfont.read_text())

            message = root / "z_message.c"
            message.write_text(
                "void Message_CloseTextbox(PlayState* play) {\n"
                "    MessageContext* msgCtx = &play->msgCtx;\n}\n"
                "void Message_StartTextbox(PlayState* play, u16 textId, Actor* actor) {\n"
                "    play->msgCtx.ocarinaMode = OCARINA_MODE_00;\n}\n"
                "void Message_ContinueTextbox(PlayState* play, u16 textId) {\n"
                "    msgCtx->textColorAlpha = 255;\n}\n",
                encoding="utf-8",
            )
            _write_message_include(root / "oot_trump_voice.inc.c", clips)
            self.assertIn(
                "s32 OotTrump_IsVoicePlaying(void)",
                (root / "oot_trump_voice.inc.c").read_text(),
            )
            _patch_message_source(message)
            patched = message.read_text()
            self.assertLess(patched.index("OOT_TRUMP_MESSAGE_INCLUDE"), patched.index("Message_CloseTextbox"))
            self.assertIn("Message_PlayTrumpVoice(textId)", patched)
            self.assertIn("Message_StopTrumpVoice()", patched)

    def test_navi_cues_drive_talking_face_state(self) -> None:
        entries = load_manifest()[:1]
        cues = load_voice_cues()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            voice_dir = root / "voice"
            voice_dir.mkdir()
            (voice_dir / entries[0].pages[0].voice).touch()
            for cue in cues:
                (voice_dir / cue.voice).touch()
            clips = available_clips(entries, voice_dir, require_all=True, cues=cues)
            include = root / "oot_trump_voice.inc.c"

            _write_message_include(include, clips)

            generated = include.read_text()
            self.assertEqual(generated.count("Audio_IsSfxPlaying(NA_SE_VO_TRUMP_CUE_"), 6)
            self.assertIn("Audio_IsSfxPlaying(NA_SE_VO_TRUMP_CUE_CALL)", generated)


if __name__ == "__main__":
    unittest.main()
