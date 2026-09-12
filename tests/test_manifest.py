from __future__ import annotations

import tempfile
import unittest
from array import array
from pathlib import Path

from oot_trump.manifest import (
    _voice_levels,
    load_manifest,
    load_voice_cues,
    validate_manifest,
    validate_voice_cues,
)
from oot_trump.project import ProjectConfig


class ManifestTests(unittest.TestCase):
    def test_voice_level_measurement_detects_active_level_and_peak(self) -> None:
        # A constant active frame makes both measurements exactly -20 dBFS.
        samples = array("h", [round(32768 * 0.1)] * 320)
        active_db, peak_db = _voice_levels(samples.tobytes(), 16000)
        self.assertAlmostEqual(active_db, -20.0, places=2)
        self.assertAlmostEqual(peak_db, -20.0, places=2)

    def test_checked_in_manifest_has_complete_supported_coverage(self) -> None:
        entries = load_manifest()
        with tempfile.TemporaryDirectory() as directory:
            errors = validate_manifest(
                entries, ProjectConfig.load(), Path(directory), allow_missing_audio=True
            )
        self.assertEqual(errors, [])
        self.assertEqual(len(entries), 177)
        self.assertIn(0x00E2, {entry.message_id for entry in entries})

    def test_navi_non_text_voice_cues_are_complete(self) -> None:
        cues = load_voice_cues()
        with tempfile.TemporaryDirectory() as directory:
            errors, _size = validate_voice_cues(
                cues,
                ProjectConfig.load(),
                Path(directory),
                allow_missing_audio=True,
            )
        self.assertEqual(errors, [])
        self.assertEqual(len(cues), 6)
        replaced = {name for cue in cues for name in cue.replaces}
        for stock in (
            "NA_SE_VO_NAVY_CALL",
            "NA_SE_VO_NAVY_HELLO",
            "NA_SE_VO_NAVY_HEAR",
            "NA_SE_VO_NAVY_ENEMY",
            "NA_SE_VO_NA_HELLO_2",
        ):
            self.assertIn(stock, replaced)

    def test_voice_names_are_deterministic(self) -> None:
        for entry in load_manifest():
            for index, page in enumerate(entry.pages):
                self.assertEqual(page.voice, f"trump_{entry.message_id:04x}_{index:02d}.wav")


if __name__ == "__main__":
    unittest.main()
