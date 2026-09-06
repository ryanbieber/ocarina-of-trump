from __future__ import annotations

import unittest
from pathlib import Path

from oot_trump.cli import build
from oot_trump.project import ProjectError


class CliTests(unittest.TestCase):
    def test_full_build_requires_complete_voice_inputs(self) -> None:
        with self.assertRaisesRegex(ProjectError, "missing 175 voice WAVs"):
            build(Path("/unused"))


if __name__ == "__main__":
    unittest.main()
