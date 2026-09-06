from __future__ import annotations

import tempfile
import unittest
from array import array
from pathlib import Path

from oot_trump.manifest import _voice_levels, load_manifest, validate_manifest
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
        self.assertEqual(len(entries), 176)

    def test_voice_names_are_deterministic(self) -> None:
        for entry in load_manifest():
            for index, page in enumerate(entry.pages):
                self.assertEqual(page.voice, f"trump_{entry.message_id:04x}_{index:02d}.wav")


if __name__ == "__main__":
    unittest.main()
