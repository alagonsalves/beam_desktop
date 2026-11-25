import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from beam_calculations import BeamModel, PointLoad, UniformLoad, calculate


def rounded(value, places=3):
    return round(value, places)


cases = []


def evaluate(name, model):
    result = calculate(model)
    cases.append((name, model, result))
    return result


r1 = evaluate("1. Simply supported uniform 1 kip/ft", BeamModel(
    span_ft=20, uniform_loads=(UniformLoad(1.0, 0.0, 20.0),)
))
r2 = evaluate("2. Simply supported point load", BeamModel(
    span_ft=20, point_loads=(PointLoad(10.0, 5.0),)
))
r3 = evaluate("3. Cantilever point load", BeamModel(
    support="cantilever", span_ft=10, point_loads=(PointLoad(5.0, 10.0),)
))
r4 = evaluate("4. Lumber uniform 0.05 kip/ft", BeamModel(
    span_ft=12, material="lumber", section_name="2x10",
    uniform_loads=(UniformLoad(0.05, 0.0, 12.0),),
))
r5 = evaluate("5. Steel self-weight", BeamModel(
    span_ft=20, include_self_weight=True,
))
r6 = evaluate("6. Combined external and self-weight", BeamModel(
    span_ft=20, uniform_loads=(UniformLoad(1.0, 0.0, 20.0),),
    include_self_weight=True,
))
r7 = evaluate("7. Cantilever steel self-weight", BeamModel(
    support="cantilever", span_ft=10, include_self_weight=True,
))
r8w12 = evaluate("8. W12x26 with self-weight", BeamModel(
    span_ft=20, section_name="W12x26", include_self_weight=True,
))
r8w10 = evaluate("8. W10x12 with self-weight", BeamModel(
    span_ft=20, section_name="W10x12", include_self_weight=True,
))
r9 = evaluate("9. Lumber switch; no steel self-weight", BeamModel(
    span_ft=12, material="lumber", section_name="2x10",
    uniform_loads=(UniformLoad(0.05, 0.0, 12.0),),
    include_self_weight=False,
))


def status(expected, actual, tolerance):
    return "PASS" if abs(expected - actual) <= tolerance else "FAIL"


rows = [
    ("1", "Left reaction", 10.0, r1["reactions"]["left"], 0.01, "k"),
    ("1", "Right reaction", 10.0, r1["reactions"]["right"], 0.01, "k"),
    ("1", "Max shear", 10.0, r1["shear"]["max"], 0.01, "k"),
    ("1", "Max moment", 50.0, r1["moment"]["max"] / 12, 0.01, "kip-ft"),
    ("1", "Bending stress", 17.96, r1["bending"]["actual"], 0.01, "ksi"),
    ("1", "Deflection", 0.609, r1["deflection"]["max"], 0.001, "in"),
    ("2", "Left reaction", 7.5, r2["reactions"]["left"], 0.01, "k"),
    ("2", "Right reaction", 2.5, r2["reactions"]["right"], 0.01, "k"),
    ("2", "Max moment", 37.5, r2["moment"]["max"] / 12, 0.01, "kip-ft"),
    ("2", "Deflection location", 8.82, r2["deflection"]["location"] / 12, 0.01, "ft"),
    ("2", "Bending stress", 13.47, r2["bending"]["actual"], 0.01, "ksi"),
    ("2", "Deflection", 0.340, r2["deflection"]["max"], 0.001, "in"),
    ("3", "Reaction", 5.0, r3["reactions"]["left"], 0.01, "k"),
    ("3", "Fixed-end moment", 50.0, r3["reactions"]["moment"] / 12, 0.01, "kip-ft"),
    ("3", "Deflection", 0.487, r3["deflection"]["max"], 0.001, "in"),
    ("3", "Deflection limit", 0.333, r3["deflection_check"]["allowable"], 0.001, "in"),
    ("4", "Max moment", 0.90, r4["moment"]["max"] / 12, 0.01, "kip-ft"),
    ("4", "Bending stress", 0.505, r4["bending"]["actual"], 0.01, "ksi"),
    ("4", "Deflection", 0.147, r4["deflection"]["max"], 0.001, "in"),
    ("5", "Left reaction", 0.26, r5["reactions"]["left"], 0.01, "k"),
    ("5", "Right reaction", 0.26, r5["reactions"]["right"], 0.01, "k"),
    ("5", "Max moment", 1.30, r5["moment"]["max"] / 12, 0.01, "kip-ft"),
    ("5", "Bending stress", 0.467, r5["bending"]["actual"], 0.01, "ksi"),
    ("5", "Deflection", 0.016, r5["deflection"]["max"], 0.001, "in"),
    ("6", "Left reaction", 10.26, r6["reactions"]["left"], 0.01, "k"),
    ("6", "Right reaction", 10.26, r6["reactions"]["right"], 0.01, "k"),
    ("6", "Max moment", 51.30, r6["moment"]["max"] / 12, 0.01, "kip-ft"),
    ("6", "Bending stress", 18.43, r6["bending"]["actual"], 0.01, "ksi"),
    ("6", "Deflection", 0.624, r6["deflection"]["max"], 0.001, "in"),
    ("7", "Reaction", 0.26, r7["reactions"]["left"], 0.01, "k"),
    ("7", "Fixed-end moment", 1.30, r7["reactions"]["moment"] / 12, 0.01, "kip-ft"),
    ("7", "Deflection", 0.009, r7["deflection"]["max"], 0.001, "in"),
    ("8", "W12 moment", 1.30, r8w12["moment"]["max"] / 12, 0.01, "kip-ft"),
    ("8", "W12 stress", 0.467, r8w12["bending"]["actual"], 0.01, "ksi"),
    ("8", "W12 deflection", 0.016, r8w12["deflection"]["max"], 0.001, "in"),
    ("8", "W10 moment", 0.60, r8w10["moment"]["max"] / 12, 0.01, "kip-ft"),
    ("8", "W10 stress", 0.661, r8w10["bending"]["actual"], 0.01, "ksi"),
    ("8", "W10 deflection", 0.028, r8w10["deflection"]["max"], 0.001, "in"),
    ("9", "Max moment", 0.90, r9["moment"]["max"] / 12, 0.01, "kip-ft"),
    ("9", "Bending stress", 0.505, r9["bending"]["actual"], 0.01, "ksi"),
    ("9", "Deflection", 0.147, r9["deflection"]["max"], 0.001, "in"),
]

failed = []
for case, metric, expected, actual, tolerance, unit in rows:
    if status(expected, actual, tolerance) == "FAIL":
        failed.append((case, metric, expected, actual, tolerance, unit))

print("Validation cases:", len(rows))
print("Failures:", len(failed))
for failure in failed:
    print(failure)
