from __future__ import annotations

import unittest

from oot_trump.manifest import Dialogue, Page
from oot_trump.message_patch import MessagePatchError, patch_messages, render_english


class MessagePatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.entry = Dialogue(
            message_id=0x0600,
            context="test",
            required_hint="test hint",
            pages=(
                Page(("First line", "Second line"), "trump_0600_00.wav"),
                Page(("Next page",), "trump_0600_01.wav"),
            ),
        )

    def test_render_english_uses_newline_and_box_break(self) -> None:
        rendered = render_english(self.entry)
        self.assertIn('"First line"\n        NEWLINE', rendered)
        self.assertIn("BOX_BREAK", rendered)
        self.assertIn('"Next page"', rendered)

    def test_patch_preserves_other_languages_and_is_idempotent(self) -> None:
        source = '''
DEFINE_MESSAGE(0x0600, TEXTBOX_TYPE_BLACK, TEXTBOX_POS_VARIABLE,
    MSG("Japanese"),
    MSG("Old English"),
    MSG(),
    MSG()
)
'''
        patched, found = patch_messages(source, [self.entry])
        self.assertEqual(found, {0x0600})
        self.assertIn('MSG("Japanese")', patched)
        self.assertNotIn("Old English", patched)
        self.assertIn("First line", patched)
        patched_again, found_again = patch_messages(patched, [self.entry])
        self.assertEqual(found_again, {0x0600})
        self.assertEqual(patched_again, patched)

    def test_unbalanced_macro_is_rejected(self) -> None:
        with self.assertRaises(MessagePatchError):
            patch_messages("DEFINE_MESSAGE(0x0600, MSG(\"oops\")", [self.entry])

    def test_split_language_macros_patch_only_nes(self) -> None:
        source = '''
DEFINE_MESSAGE_JPN(0x0600, TEXTBOX_TYPE_BLACK, TEXTBOX_POS_VARIABLE,
    MSG("Japanese"), MSG(), MSG(), MSG())
DEFINE_MESSAGE_NES(0x0600, TEXTBOX_TYPE_BLUE, TEXTBOX_POS_BOTTOM,
    MSG(), MSG("Old English"), MSG(), MSG())
'''
        patched, found = patch_messages(source, [self.entry])
        self.assertEqual(found, {0x0600})
        self.assertIn('DEFINE_MESSAGE_JPN(0x0600', patched)
        self.assertEqual(patched.count("First line"), 1)


if __name__ == "__main__":
    unittest.main()
