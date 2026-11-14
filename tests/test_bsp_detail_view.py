import importlib.util
import json
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


@unittest.skipUnless(importlib.util.find_spec("numpy"), "numpy is available in the nav venv")
class BspDetailViewTests(unittest.TestCase):
    def test_detail_view_preserves_stable_per_polygon_triangle_order(self):
        import numpy as np
        from eql_automation.bsp_detail_view import BspDetailMeshView
        from eql_automation.portal_surface_audit import _supported_detail_height

        with TemporaryDirectory() as directory:
            path = Path(directory) / "sample.npz"
            # Deliberately interleave polygons and overlap two triangles in
            # polygon zero. The helper's stable sort keeps both in order.
            tri0 = ((0, 0, 2), (10, 0, 2), (0, 10, 2))
            tri1 = ((0, 0, 8), (10, 0, 8), (0, 10, 8))
            tri2 = ((0, 0, 3), (10, 0, 3), (0, 10, 3))
            np.savez(path, meta=json.dumps({"format": 1, "zone": "sample"}),
                     poly_area=[63, 63], poly_nv=[3, 3],
                     detail_tris=[tri0, tri1, tri2], detail_poly=[0, 1, 0])
            view = BspDetailMeshView.load(path, zone="sample")
            self.assertEqual(view._detail_start.tolist(), [0, 2, 3])
            self.assertEqual(view._detail[:, 0, 2].tolist(), [2, 3, 8])
            self.assertEqual(view.mesh_sha256, sha256(path.read_bytes()).hexdigest())
            self.assertFalse(view._detail.flags.writeable)
            self.assertFalse(view._detail_start.flags.writeable)
            self.assertFalse(view.area.flags.writeable)
            self.assertIsNone(_supported_detail_height(view, 0, 1.0, 1.0))

    def test_detail_view_rejects_bad_polygon_reference(self):
        import numpy as np
        from eql_automation.bsp_detail_view import BspDetailMeshView

        with TemporaryDirectory() as directory:
            path = Path(directory) / "bad.npz"
            np.savez(path, meta=json.dumps({"format": 1, "zone": "sample"}),
                     poly_area=[63], poly_nv=[3],
                     detail_tris=[((0, 0, 2), (10, 0, 2), (0, 10, 2))],
                     detail_poly=[1])
            with self.assertRaisesRegex(ValueError, "invalid metadata or arrays"):
                BspDetailMeshView.load(path, zone="sample")
