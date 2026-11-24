import unittest

from beam_core import SECTIONS, PointLoad, analyze


class BeamCoreTests(unittest.TestCase):
    def test_default_example(self):
        section = next(section for section in SECTIONS if section.designation == "W12x26")
        result = analyze(20, "simple", section, 1.0, (), 24.0, 360)
        self.assertAlmostEqual(abs(result.max_moment.moment), 50.0, places=2)
        self.assertAlmostEqual(abs(result.max_deflection.deflection), 0.609, places=2)

    def test_simple_point_load_reactions(self):
        section = next(section for section in SECTIONS if section.designation == "W12x26")
        result = analyze(20, "simple", section, 0.0,
                         (PointLoad(10, 10),), 24.0, 360)
        self.assertAlmostEqual(result.reactions["RA"], 5.0)
        self.assertAlmostEqual(result.reactions["RB"], 5.0)

    def test_cantilever_end_load(self):
        section = next(section for section in SECTIONS if section.designation == "W12x26")
        result = analyze(10, "cantilever", section, 0.0,
                         (PointLoad(5, 10),), 24.0, 360)
        self.assertAlmostEqual(abs(result.reactions["RA"]), 5.0)
        self.assertAlmostEqual(abs(result.max_moment.moment), 50.0, places=2)

    def test_cantilever_uniform_load(self):
        section = next(section for section in SECTIONS if section.designation == "W12x26")
        result = analyze(10, "cantilever", section, 1.0, (), 24.0, 360)
        self.assertAlmostEqual(result.reactions["RA"], 10.0)
        self.assertAlmostEqual(abs(result.max_shear.shear), 10.0)
        self.assertAlmostEqual(abs(result.max_moment.moment), 50.0, places=2)
        self.assertAlmostEqual(result.bending_stress, 50.0 * 12.0 / section.S, places=2)
        self.assertAlmostEqual(abs(result.max_deflection.deflection), 0.365112, places=5)

    def test_point_load_position_validation(self):
        section = next(section for section in SECTIONS if section.designation == "W12x26")
        with self.assertRaises(ValueError):
            analyze(20, "simple", section, 1.0,
                    (PointLoad(10, 21),), 24.0, 360)


if __name__ == "__main__":
    unittest.main()
