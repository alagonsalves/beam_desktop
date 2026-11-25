import unittest

from beam_calculations import (
    BeamModel,
    PointLoad,
    UniformLoad,
    calculate,
    design_from_dict,
    design_to_dict,
    normalize_span,
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

    def test_design_json_round_trip(self):
        model = BeamModel(
            support="cantilever",
            span_ft=18.25,
            material="steel",
            section_name="W16x26",
            deflection_limit=240,
            include_self_weight=True,
            point_loads=(PointLoad(3.5, 12.25),),
            uniform_loads=(UniformLoad(0.25, 2.0, 15.5),),
        )
        restored = design_from_dict(design_to_dict(model))
        self.assertEqual(restored.support, model.support)
        self.assertEqual(restored.span_ft, model.span_ft)
        self.assertEqual(restored.section_name, model.section_name)
        self.assertEqual(restored.deflection_limit, model.deflection_limit)
        self.assertTrue(restored.include_self_weight)
        self.assertEqual(restored.point_loads[0].position_ft, 12.25)
        self.assertEqual(restored.uniform_loads[0].end_ft, 15.5)

    def test_invalid_design_is_rejected(self):
        invalid_designs = (
            None,
            {},
            {"support": "invalid"},
            {
                "support": "simply-supported",
                "span_ft": 20,
                "material": "steel",
                "section": "W12x26",
                "deflection_limit": 360,
                "include_self_weight": True,
                "point_loads": [{"magnitude": -1, "position_ft": 5}],
                "uniform_loads": [],
            },
        )
        for data in invalid_designs:
            with self.assertRaises(ValueError):
                design_from_dict(data)

    def test_span_normalization(self):
        self.assertEqual(normalize_span(3), 4.0)
        self.assertEqual(normalize_span(40.1), 40.0)
        self.assertEqual(normalize_span(20.1), 20.0)
        self.assertEqual(normalize_span(20.25), 20.25)
        with self.assertRaises(ValueError):
            normalize_span("not-a-number")


if __name__ == "__main__":
    unittest.main()
