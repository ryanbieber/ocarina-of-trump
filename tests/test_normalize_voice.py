from __future__ import annotations

import unittest
from array import array

from scripts.normalize_voice_catalog import normalize


class NormalizeVoiceTests(unittest.TestCase):
    def test_dc_removal_clamps_before_gain_staging(self) -> None:
        samples = array("h", [32767] * 100 + [-32768] * 20)
        normalized = normalize(samples)
        self.assertEqual(len(normalized), len(samples))
        self.assertGreaterEqual(min(normalized), -32768)
        self.assertLessEqual(max(normalized), 32767)


if __name__ == "__main__":
    unittest.main()
