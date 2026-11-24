import json
import tempfile
import unittest
from pathlib import Path

from beam_io import open_design_file, save_design_file, validate_design_document


SAMPLE_DESIGN = {
    "version": 1,
    "beam": {
        "support_type": "cantilever",
        "span_ft": 10,
        "material": "steel",
        "section": "W12x26",
        "deflection_limit": 360,
        "allowable_stress": 24,
        "stress_unit": "ksi",
    },
    "loads": {
        "uniform_kip_ft": 1,
        "point_loads": [
            {"magnitude_kip": 5, "position_ft": 10},
            {"magnitude_kip": 0, "position_ft": 4},
        ],
        "include_self_weight": True,
    },
}


class BeamIoTests(unittest.TestCase):
    def test_save_and_open_preserves_design(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "design.json"
            save_design_file(path, SAMPLE_DESIGN)
            self.assertEqual(open_design_file(path), SAMPLE_DESIGN)

    def test_invalid_point_position_is_rejected(self):
        document = json.loads(json.dumps(SAMPLE_DESIGN))
        document["loads"]["point_loads"][0]["position_ft"] = 11
        with self.assertRaisesRegex(ValueError, "Point-load position"):
            validate_design_document(document)

    def test_unknown_version_is_rejected(self):
        document = json.loads(json.dumps(SAMPLE_DESIGN))
        document["version"] = 2
        with self.assertRaisesRegex(ValueError, "version"):
            validate_design_document(document)


if __name__ == "__main__":
    unittest.main()
