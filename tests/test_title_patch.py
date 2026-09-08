import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from oot_trump.project import ProjectError
from oot_trump.title_patch import ACTOR, NEW, START, patch_title_screen, subtitle_pixels


class TitlePatchTests(unittest.TestCase):
    def test_subtitle_size_and_blank_border(self):
        pixels = subtitle_pixels()
        self.assertEqual(len(pixels), 96 * 8)
        self.assertEqual(set(pixels), {0, 255})
        self.assertEqual(pixels[-96:], bytes(96))
        self.assertTrue(any(pixels[80:95]))  # Final word fits in the texture.

    def test_both_passes_idempotence_and_check_mode(self):
        source = '\n'.join([
            '#include "z_en_mag.h"', '#define FLAGS 0',
            'EnMag_DrawTextureI8(&gfx, gTitleTheLegendOfTextTex, 72, 8, 153, 72, 72, 8, 1024, 1024);',
            'EnMag_DrawTextureI8(&gfx, gTitleOcarinaOfTimeTMTextTex, 96, 8, 152, 127, 96, 8, 1024, 1024);',
            'EnMag_DrawTextureI8(&gfx, gTitleOcarinaOfTimeTMTextTex, 96, 8, 151, 126, 96, 8, 1024, 1024);',
        ])
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / ACTOR
            path.parent.mkdir(parents=True)
            path.write_text(source)
            patch_title_screen(root, check=True)
            self.assertEqual(path.read_text(), source)
            patch_title_screen(root)
            result = path.read_text()
            self.assertEqual(result.count(START), 1)
            self.assertEqual(result.count('EnMag_DrawTextureI8(&gfx, ' + NEW), 2)
            self.assertIn('gTitleTheLegendOfTextTex, 72, 8, 153, 72', result)
            patch_title_screen(root)
            self.assertEqual(path.read_text(), result)
            path.write_text(source.replace('96, 8, 152', '128, 8, 152'))
            before = path.read_text()
            with self.assertRaises(ProjectError):
                patch_title_screen(root)
            self.assertEqual(path.read_text(), before)
