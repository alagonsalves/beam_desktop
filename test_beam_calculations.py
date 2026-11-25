import unittest

from beam_calculations import (
    BeamModel,
    PointLoad,
    UniformLoad,
    calculate,
)


class BeamCalculationValidationTests(unittest.TestCase):
    def test_default_uniform_load(self):
        model = BeamModel(
            span_ft=20,
            uniform_loads=(UniformLoad(1.0, 0.0, 20.0),),
        )
        result = calculate(model)
        self.assertAlmostEqual(result["reactions"]["left"], 10.0, places=2)
        self.assertAlmostEqual(result["reactions"]["right"], 10.0, places=2)
        self.assertAlmostEqual(result["moment"]["max"], 600.0, places=1)
        self.assertAlmostEqual(result["moment"]["location"], 120.0, places=1)
        self.assertAlmostEqual(result["bending"]["actual"], 17.96, delta=0.01)
        self.assertAlmostEqual(result["deflection"]["max"], 0.609, delta=0.001)

    def test_off_center_point_load(self):
        model = BeamModel(
            span_ft=20,
            point_loads=(PointLoad(10.0, 5.0),),
        )
        result = calculate(model)
        self.assertAlmostEqual(result["reactions"]["left"], 7.5, places=2)
        self.assertAlmostEqual(result["reactions"]["right"], 2.5, places=2)
        self.assertAlmostEqual(result["moment"]["max"] / 12, 37.5, places=2)
        self.assertAlmostEqual(result["moment"]["location"] / 12, 5.0, places=2)
        self.assertAlmostEqual(result["deflection"]["location"] / 12, 8.82, delta=0.01)

    def test_cantilever_point_load(self):
        model = BeamModel(
            support="cantilever",
            span_ft=10,
            point_loads=(PointLoad(5.0, 10.0),),
        )
        result = calculate(model)
        self.assertAlmostEqual(result["reactions"]["left"], 5.0, places=2)
        self.assertAlmostEqual(result["reactions"]["moment"], 600.0, places=2)
        self.assertAlmostEqual(result["deflection"]["location"] / 12, 10.0, places=2)
        self.assertAlmostEqual(result["deflection"]["max"], 0.487, delta=0.001)
        self.assertFalse(result["deflection_check"]["pass"])

    def test_lumber_uniform_load(self):
        model = BeamModel(
            span_ft=12,
            material="lumber",
            section_name="2x10",
            uniform_loads=(UniformLoad(0.05, 0.0, 12.0),),
        )
        result = calculate(model)
        self.assertAlmostEqual(result["moment"]["max"] / 12, 0.90, delta=0.01)
        self.assertAlmostEqual(result["bending"]["actual"], 0.505, delta=0.01)
        self.assertAlmostEqual(result["deflection"]["max"], 0.147, delta=0.001)
        self.assertTrue(result["bending"]["pass"])
        self.assertTrue(result["deflection_check"]["pass"])

    def test_steel_self_weight(self):
        model = BeamModel(
            span_ft=20,
            include_self_weight=True,
        )
        result = calculate(model)
        self.assertAlmostEqual(result["reactions"]["left"], 0.26, delta=0.01)
        self.assertAlmostEqual(result["moment"]["max"] / 12, 1.30, delta=0.01)
        self.assertAlmostEqual(result["bending"]["actual"], 0.467, delta=0.01)
        self.assertAlmostEqual(result["deflection"]["max"], 0.016, delta=0.001)

    def test_combined_external_and_self_weight(self):
        model = BeamModel(
            span_ft=20,
            uniform_loads=(UniformLoad(1.0, 0.0, 20.0),),
            include_self_weight=True,
        )
        result = calculate(model)
        self.assertAlmostEqual(result["reactions"]["left"], 10.26, delta=0.01)
        self.assertAlmostEqual(result["moment"]["max"] / 12, 51.30, delta=0.01)
        self.assertAlmostEqual(result["bending"]["actual"], 18.43, delta=0.01)
        self.assertAlmostEqual(result["deflection"]["max"], 0.624, delta=0.001)

    def test_cantilever_self_weight(self):
        model = BeamModel(
            support="cantilever",
            span_ft=10,
            include_self_weight=True,
        )
        result = calculate(model)
        self.assertAlmostEqual(result["reactions"]["left"], 0.26, delta=0.01)
        self.assertAlmostEqual(result["reactions"]["moment"] / 12, 1.30, delta=0.01)
        self.assertAlmostEqual(result["deflection"]["max"], 0.009, delta=0.001)

    def test_section_change_self_weight(self):
        w12 = calculate(BeamModel(span_ft=20, section_name="W12x26", include_self_weight=True))
        w10 = calculate(BeamModel(span_ft=20, section_name="W10x12", include_self_weight=True))
        self.assertAlmostEqual(w12["moment"]["max"] / 12, 1.30, delta=0.01)
        self.assertAlmostEqual(w12["bending"]["actual"], 0.467, delta=0.01)
        self.assertAlmostEqual(w12["deflection"]["max"], 0.016, delta=0.001)
        self.assertAlmostEqual(w10["moment"]["max"] / 12, 0.60, delta=0.01)
        self.assertAlmostEqual(w10["bending"]["actual"], 0.661, delta=0.01)
        self.assertAlmostEqual(w10["deflection"]["max"], 0.028, delta=0.001)

    def test_lumber_switch_excludes_self_weight(self):
        model = BeamModel(
            span_ft=12,
            material="lumber",
            section_name="2x10",
            uniform_loads=(UniformLoad(0.05, 0.0, 12.0),),
            include_self_weight=False,
        )
        result = calculate(model)
        self.assertAlmostEqual(result["moment"]["max"] / 12, 0.90, delta=0.01)
        self.assertAlmostEqual(result["bending"]["actual"], 0.505, delta=0.01)
        self.assertAlmostEqual(result["deflection"]["max"], 0.147, delta=0.001)


if __name__ == "__main__":
    unittest.main()
