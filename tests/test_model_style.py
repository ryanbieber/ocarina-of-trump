"""Geometry/color regressions that do not require a Blender installation."""
import ast
import math
from collections import Counter
import unittest
from pathlib import Path
from types import SimpleNamespace


def load_helper(name, **context):
    script = Path(__file__).resolve().parents[1] / 'scripts/build_fairy_model.py'
    tree = ast.parse(script.read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(script), 'exec'), context)
    return context[name]


class ModelStyleTests(unittest.TestCase):
    def test_sampled_skin_is_linear_and_rejects_transparent_cheeks(self):
        texture = SimpleNamespace(size=(32, 32), pixels=[0.8, 0.5, 0.3, 1.0] * 1024)
        helper = load_helper('sample_face_skin', bpy=SimpleNamespace(data=SimpleNamespace(
            images=SimpleNamespace(load=lambda *a, **k: texture))), log=lambda message: None)
        color = helper('face.png')
        for actual, expected in zip(color, (0.603827, 0.214041, 0.073239)):
            self.assertAlmostEqual(actual, expected, places=5)
        texture.pixels = [0.8, 0.5, 0.3, 0.0] * 1024
        with self.assertRaisesRegex(RuntimeError, 'opaque cheek'):
            helper('face.png')

    def test_mirrored_wings_and_lapels_face_forward(self):
        for name in ('add_wing', 'add_lapel'):
            helper = load_helper(name, add_flat_mesh=lambda name, vertices, faces, material: (vertices, faces))
            for side in (-1, 1):
                vertices, faces = helper('part', side, None)
                for face in faces:
                    a, b, c = [vertices[index] for index in face]
                    normal_y = (b[2]-a[2])*(c[0]-a[0]) - (b[0]-a[0])*(c[2]-a[2])
                    self.assertLess(normal_y, 0, (name, side, face))

    def test_head_is_closed_with_shared_skin_boundary_and_outward_normals(self):
        vertices, faces, uvs, materials = load_helper('head_geometry', math=math)()
        edges = Counter(tuple(sorted((face[i], face[(i+1) % len(face)])))
                        for face in faces for i in range(len(face)))
        self.assertTrue(all(count == 2 for count in edges.values()))
        self.assertEqual(len(vertices) - len(edges) + len(faces), 2)
        self.assertTrue(all(0 <= u <= 1 and 0 <= v <= 1 for u, v in uvs))
        self.assertEqual(set(materials), {0, 1})
        for face in faces:
            a,b,c = [vertices[i] for i in face[:3]]
            ab,ac = [b[i]-a[i] for i in range(3)], [c[i]-a[i] for i in range(3)]
            normal=(ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0])
            self.assertGreater(sum(normal[i]*(a[i]-(2.67 if i==2 else 0)) for i in range(3)),0)
