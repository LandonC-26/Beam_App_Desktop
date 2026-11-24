import csv
import json
import tempfile
import unittest
from pathlib import Path

from beam_core import SECTIONS, PointLoad, Station, analyze
from beam_io import (
    export_calculation_pdf,
    export_results_csv,
    open_design_file,
    save_design_file,
    validate_design_document,
)


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

    def test_export_results_csv_for_excel(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.csv"
            stations = (
                Station(0.0, 5.0, 0.0, 0.0),
                Station(1.0, -5.0, -10.0, 0.125),
            )
            export_results_csv(path, stations)
            with path.open(encoding="utf-8-sig", newline="") as csv_file:
                rows = list(csv.reader(csv_file))
        self.assertEqual(rows[0], ["x_ft", "V_kips", "M_kip_ft", "deflection_in"])
        self.assertEqual(len(rows), len(stations) + 1)
        self.assertEqual(rows[2], ["1.0", "-5.0", "-10.0", "0.125"])

    def test_export_calculation_sheet_pdf(self):
        section = next(section for section in SECTIONS if section.designation == "W12x26")
        result = analyze(20, "simple", section, 1.0, (PointLoad(5, 10),), 24, 360)
        input_details = {
            "support": "Simply supported",
            "uniform_load": "1",
            "point_loads": "5 kip at 10 ft",
            "allowable_stress": "24 ksi",
            "self_weight": "Off",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "calculation-sheet.pdf"
            export_calculation_pdf(path, result, input_details)
            content = path.read_bytes()
        self.assertTrue(content.startswith(b"%PDF-"))
        self.assertIn(b"%%EOF", content)
        self.assertGreater(len(content), 10000)


if __name__ == "__main__":
    unittest.main()
