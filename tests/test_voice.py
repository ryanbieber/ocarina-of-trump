from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from oot_trump.manifest import load_manifest
from oot_trump.voice import estimate_script, export_voice_script, generate_voice_map


class VoiceGenerationTests(unittest.TestCase):
    def test_estimate_uses_n64_vadpcm_frame_ratio(self) -> None:
        estimate = estimate_script(load_manifest(), 150)
        self.assertEqual(estimate["pages"], 176)
        self.assertEqual(estimate["words"], 2534)
        self.assertAlmostEqual(
            estimate["vadpcm_bytes"] / estimate["pcm_bytes"], 9 / 32, places=5
        )

    def test_voice_outputs_cover_every_page(self) -> None:
        entries = load_manifest()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "voice-script.json"
            source = root / "voice-map.inc.c"
            export_voice_script(entries, script)
            generate_voice_map(entries, source)
            payload = json.loads(script.read_text(encoding="utf-8"))
            expected = sum(len(entry.pages) for entry in entries)
            self.assertEqual(len(payload["clips"]), expected)
            self.assertTrue(payload["disclosure"].startswith("Fictional AI-generated"))
            self.assertEqual(source.read_text(encoding="utf-8").count("{ 0x"), expected)


if __name__ == "__main__":
    unittest.main()
