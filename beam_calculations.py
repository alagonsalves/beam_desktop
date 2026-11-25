from dataclasses import dataclass
import math
from math import fsum
from typing import Iterable, Sequence


STEEL_SECTIONS = (
    {"name": "W8x10", "Ix": 30.8, "Sx": 7.81, "weight": 10},
    {"name": "W10x12", "Ix": 53.8, "Sx": 10.9, "weight": 12},
    {"name": "W12x26", "Ix": 204.0, "Sx": 33.4, "weight": 26},
    {"name": "W14x22", "Ix": 199.0, "Sx": 29.0, "weight": 22},
    {"name": "W16x26", "Ix": 301.0, "Sx": 38.4, "weight": 26},
    {"name": "W18x35", "Ix": 510.0, "Sx": 57.6, "weight": 35},
    {"name": "W21x44", "Ix": 843.0, "Sx": 81.6, "weight": 44},
    {"name": "W24x55", "Ix": 1350.0, "Sx": 114.0, "weight": 55},
)

LUMBER_SECTIONS = (
    {"name": "2x8", "Ix": 47.63, "Sx": 13.14},
    {"name": "2x10", "Ix": 98.93, "Sx": 21.39},
    {"name": "2x12", "Ix": 177.98, "Sx": 31.64},
)


def normalize_span(value):
    try:
        span = float(value)
    except (TypeError, ValueError):
        raise ValueError("Span must be a number.")
    if not math.isfinite(span):
        raise ValueError("Span must be a finite number.")
    span = max(4.0, min(40.0, span))
    return round(span * 4.0) / 4.0


@dataclass(frozen=True)
class PointLoad:
    magnitude: float
    position_ft: float


@dataclass(frozen=True)
class UniformLoad:
    magnitude: float
    start_ft: float
    end_ft: float


@dataclass(frozen=True)
class BeamModel:
    support: str = "simply-supported"
    span_ft: float = 20.0
    point_loads: tuple = ()
    uniform_loads: tuple = ()
    material: str = "steel"
    section_name: str = "W12x26"
    include_self_weight: bool = False
    deflection_limit: int = 360


def sections_for(material: str) -> tuple:
    return STEEL_SECTIONS if material == "steel" else LUMBER_SECTIONS


def section_by_name(material: str, name: str) -> dict:
    for section in sections_for(material):
        if section["name"] == name:
            return dict(section)
    raise ValueError("Unknown section: " + name)


def design_to_dict(model: BeamModel) -> dict:
    return {
        "support": model.support,
        "span_ft": model.span_ft,
        "material": model.material,
        "section": model.section_name,
        "deflection_limit": model.deflection_limit,
        "include_self_weight": model.include_self_weight,
        "point_loads": [
            {"magnitude": load.magnitude, "position_ft": load.position_ft}
            for load in model.point_loads
        ],
        "uniform_loads": [
            {
                "magnitude": load.magnitude,
                "start_ft": load.start_ft,
                "end_ft": load.end_ft,
            }
            for load in model.uniform_loads
        ],
    }


def design_from_dict(data: dict) -> BeamModel:
    if not isinstance(data, dict):
        raise ValueError("The design file must contain a JSON object.")

    required = (
        "support",
        "span_ft",
        "material",
        "section",
        "deflection_limit",
        "include_self_weight",
        "point_loads",
        "uniform_loads",
    )
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError("Missing design fields: " + ", ".join(missing))

    support = data["support"]
    if support not in ("simply-supported", "cantilever"):
        raise ValueError("Invalid support type.")

    material = data["material"]
    if material not in ("steel", "lumber"):
        raise ValueError("Invalid material.")

    section_name = data["section"]
    try:
        section_by_name(material, section_name)
    except ValueError as exc:
        raise ValueError("Invalid section for selected material.") from exc

    try:
        span_ft = float(data["span_ft"])
        deflection_limit = int(data["deflection_limit"])
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid numeric or self-weight setting.") from exc
    if isinstance(data["deflection_limit"], bool):
        raise ValueError("Deflection limit must be 240 or 360.")
    try:
        deflection_limit_value = float(data["deflection_limit"])
    except (TypeError, ValueError) as exc:
        raise ValueError("Deflection limit must be 240 or 360.") from exc
    if not math.isfinite(span_ft) or not 4.0 <= span_ft <= 40.0:
        raise ValueError("Span must be between 4 and 40 ft.")
    if deflection_limit_value not in (240.0, 360.0):
        raise ValueError("Deflection limit must be 240 or 360.")
    deflection_limit = int(deflection_limit_value)
    if not isinstance(data["include_self_weight"], bool):
        raise ValueError("include_self_weight must be true or false.")
    include_self_weight = data["include_self_weight"]
    if material == "lumber":
        include_self_weight = False

    if not isinstance(data["point_loads"], list):
        raise ValueError("Point loads must be a JSON list.")
    point_loads = []
    for load in data["point_loads"]:
        if not isinstance(load, dict) or "magnitude" not in load or "position_ft" not in load:
            raise ValueError("Invalid point load entry.")
        try:
            magnitude = float(load["magnitude"])
            position_ft = float(load["position_ft"])
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid point load values.") from exc
        if (not math.isfinite(magnitude) or not math.isfinite(position_ft)
                or magnitude < 0 or not 0.0 <= position_ft <= span_ft):
            raise ValueError("Point loads must use nonnegative magnitudes and valid positions.")
        point_loads.append(PointLoad(magnitude, position_ft))

    if not isinstance(data["uniform_loads"], list):
        raise ValueError("Uniform loads must be a JSON list.")
    uniform_loads = []
    for load in data["uniform_loads"]:
        if not isinstance(load, dict):
            raise ValueError("Invalid uniform load entry.")
        if not {"magnitude", "start_ft", "end_ft"} <= set(load):
            raise ValueError("Uniform load entries require magnitude, start_ft, and end_ft.")
        try:
            magnitude = float(load["magnitude"])
            start_ft = float(load["start_ft"])
            end_ft = float(load["end_ft"])
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid uniform load values.") from exc
        if not math.isfinite(magnitude) or not math.isfinite(start_ft) or not math.isfinite(end_ft):
            raise ValueError("Uniform load values must be finite numbers.")
        if magnitude < 0:
            raise ValueError("Uniform load magnitudes must be nonnegative.")
        start_ft = max(0.0, min(span_ft, start_ft))
        end_ft = max(0.0, min(span_ft, end_ft))
        if start_ft > end_ft:
            start_ft, end_ft = end_ft, start_ft
        uniform_loads.append(UniformLoad(magnitude, start_ft, end_ft))

    return BeamModel(
        support=support,
        span_ft=span_ft,
        point_loads=tuple(point_loads),
        uniform_loads=tuple(uniform_loads),
        material=material,
        section_name=section_name,
        include_self_weight=include_self_weight,
        deflection_limit=deflection_limit,
    )


def calculate(model: BeamModel) -> dict:
    if model.support not in ("simply-supported", "cantilever"):
        raise ValueError("Unknown support type")

    L = model.span_ft * 12.0
    point_loads = [(float(p.magnitude), float(p.position_ft) * 12.0) for p in model.point_loads]
    uniform_loads = [
        (float(u.magnitude) / 12.0, float(u.start_ft) * 12.0, float(u.end_ft) * 12.0)
        for u in model.uniform_loads
    ]

    section = section_by_name(model.material, model.section_name)
    if model.include_self_weight and model.material == "steel":
        uniform_loads.append((section["weight"] / 1000.0 / 12.0, 0.0, L))

    total_point = fsum(p for p, _ in point_loads)
    total_uniform = fsum(w * (end - start) for w, start, end in uniform_loads)

    if model.support == "cantilever":
        left_reaction = total_point + total_uniform
        right_reaction = 0.0
        fixed_moment = fsum(p * a for p, a in point_loads)
        fixed_moment += fsum(w * (end * end - start * start) / 2.0 for w, start, end in uniform_loads)
    else:
        left_reaction = fsum(p * (L - a) / L for p, a in point_loads)
        fixed_moment = 0.0
        left_terms = [p * (L - a) / L for p, a in point_loads]
        left_terms.extend(
            w * (end - start) * (L - (start + end) / 2.0) / L
            for w, start, end in uniform_loads
        )
        left_reaction = fsum(left_terms)
        right_reaction = total_point + total_uniform - left_reaction

    def shear_at(x: float) -> float:
        if model.support == "cantilever":
            result = left_reaction
            for p, a in point_loads:
                if a <= x:
                    result -= p
            for w, start, end in uniform_loads:
                overlap = min(end, x) - start
                if overlap > 0:
                    result -= w * overlap
            return result
        result = left_reaction
        for p, a in point_loads:
            if a <= x:
                result -= p
        for w, start, end in uniform_loads:
            overlap = min(end, x) - start
            if overlap > 0:
                result -= w * overlap
        return result

    def moment_at(x: float) -> float:
        if model.support == "cantilever":
            result = 0.0
            for p, a in point_loads:
                if a >= x:
                    result -= p * (a - x)
            for w, start, end in uniform_loads:
                segment_start = max(start, x)
                if end > segment_start:
                    result -= w * (
                        (end - x) * (end - x) - (segment_start - x) * (segment_start - x)
                    ) / 2.0
            return result
        result = left_reaction * x
        for p, a in point_loads:
            if x >= a:
                result -= p * (x - a)
        for w, start, end in uniform_loads:
            if x > start:
                right = min(x, end)
                if right > start:
                    length = right - start
                    result -= w * length * length / 2.0
        return result

    breakpoints = {0.0, L}
    for _, a in point_loads:
        breakpoints.add(a)
    for _, start, end in uniform_loads:
        breakpoints.add(start)
        breakpoints.add(end)
    breakpoints = sorted(breakpoints)

    shear_candidates = set(breakpoints)
    step = 3.0
    x = 0.0
    while x <= L:
        shear_candidates.add(min(x, L))
        x += step
    shear_candidates = sorted(shear_candidates)

    max_shear = max((abs(shear_at(x)) for x in shear_candidates), default=0.0)
    max_shear_location = next(
        x for x in shear_candidates if abs(abs(shear_at(x)) - max_shear) < 1e-7
    )

    moment_candidates = set(shear_candidates)
    for x in shear_candidates:
        moment_candidates.add(x)
    moment_candidates = sorted(moment_candidates)
    max_moment = max((abs(moment_at(x)) for x in moment_candidates), default=0.0)
    max_moment_location = next(
        x for x in moment_candidates if abs(abs(moment_at(x)) - max_moment) < 1e-7
    )

    E = 29000.0 if model.material == "steel" else 1600.0
    EI = E * section["Ix"]
    deflection_step = 0.25
    raw_points = [(0.0, 0.0, 0.0)]
    x = 0.0
    prev_y = 0.0
    prev_slope = 0.0
    while x < L:
        next_x = min(x + deflection_step, L)
        if model.support == "cantilever":
            curvature_left = -moment_at(x) / EI
            curvature_right = -moment_at(next_x) / EI
        else:
            curvature_left = moment_at(x) / EI
            curvature_right = moment_at(next_x) / EI
        next_slope = prev_slope + (curvature_left + curvature_right) * (next_x - x) / 2.0
        next_y = prev_y + (prev_slope + next_slope) * (next_x - x) / 2.0
        raw_points.append((next_x, next_y, next_slope))
        x = next_x
        prev_y = next_y
        prev_slope = next_slope

    if model.support == "simply-supported":
        boundary_slope = -raw_points[-1][1] / L
        points = [(px, py + boundary_slope * px, ps + boundary_slope) for px, py, ps in raw_points]
    else:
        points = raw_points

    def deflection_and_slope(x: float) -> tuple:
        low_index = int(x // deflection_step)
        if low_index >= len(points) - 1:
            low_index = len(points) - 2
        low_index = max(0, low_index)
        x1, y1, s1 = points[low_index]
        x2, y2, s2 = points[low_index + 1]
        fraction = (x - x1) / (x2 - x1) if x2 != x1 else 0.0
        y = y1 + (y2 - y1) * fraction
        slope = s1 + (s2 - s1) * fraction
        return y, slope

    candidates = {0.0, L}
    for _, a in point_loads:
        candidates.add(a)
    for _, start, end in uniform_loads:
        candidates.add(start)
        candidates.add(end)

    for px, _, ps in points:
        candidates.add(px)

    def bisect_slope(left: float, right: float) -> float:
        for _ in range(50):
            mid = (left + right) / 2.0
            _, left_slope = deflection_and_slope(left)
            _, mid_slope = deflection_and_slope(mid)
            if (left_slope >= 0 and mid_slope >= 0) or (left_slope <= 0 and mid_slope <= 0):
                left = mid
            else:
                right = mid
        return (left + right) / 2.0

    slope_roots = []
    ordered_points = [p[0] for p in points]
    for i in range(len(ordered_points) - 1):
        xa = ordered_points[i]
        xb = ordered_points[i + 1]
        _, sa = deflection_and_slope(xa)
        _, sb = deflection_and_slope(xb)
        if abs(sa) < 1e-10:
            slope_roots.append(xa)
        if sa * sb < 0:
            slope_roots.append(bisect_slope(xa, xb))
    for root in list(slope_roots):
        candidates.add(root)

    max_deflection = 0.0
    max_deflection_location = 0.0
    for x in sorted(candidates):
        y, _ = deflection_and_slope(x)
        if abs(y) > abs(max_deflection) + 1e-12:
            max_deflection = y
            max_deflection_location = x
        elif abs(abs(y) - abs(max_deflection)) <= 1e-12:
            if x < max_deflection_location:
                max_deflection = y
                max_deflection_location = x

    max_moment_kip_in = abs(moment_at(max_moment_location))
    bending_stress = max_moment_kip_in / section["Sx"]
    allowable_bending = 30.0 if model.material == "steel" else 0.9
    allowable_deflection = L / model.deflection_limit
    max_deflection_abs = abs(max_deflection)

    return {
        "reactions": {
            "left": left_reaction,
            "right": right_reaction,
            "moment": fixed_moment,
        },
        "shear": {
            "max": max_shear,
            "location": max_shear_location,
            "at": shear_at,
        },
        "moment": {
            "max": max_moment,
            "location": max_moment_location,
            "at": moment_at,
        },
        "deflection": {
            "max": max_deflection_abs,
            "location": max_deflection_location,
            "signed": max_deflection,
            "at": lambda x: deflection_and_slope(x)[0],
            "points": [{"x": p[0], "y": p[1], "slope": p[2]} for p in points],
        },
        "bending": {
            "actual": bending_stress,
            "allowable": allowable_bending,
            "pass": bending_stress <= allowable_bending,
        },
        "deflection_check": {
            "actual": max_deflection_abs,
            "allowable": allowable_deflection,
            "pass": max_deflection_abs <= allowable_deflection,
        },
        "section": section,
        "model": model,
    }


def evaluate_section(model: BeamModel, section: dict) -> dict:
    candidate = BeamModel(
        support=model.support,
        span_ft=model.span_ft,
        point_loads=model.point_loads,
        uniform_loads=model.uniform_loads,
        material=model.material,
        section_name=section["name"],
        include_self_weight=model.include_self_weight,
        deflection_limit=model.deflection_limit,
    )
    return calculate(candidate)


def find_lightest_passing(model: BeamModel) -> dict | None:
    passing = []
    for section in sections_for(model.material):
        result = evaluate_section(model, section)
        if result["bending"]["pass"] and result["deflection_check"]["pass"]:
            passing.append(section)
    if not passing:
        return None
    if model.material == "steel":
        return sorted(passing, key=lambda s: (s["weight"], -s["Ix"]))[0]
    return passing[0]


def build_results_table(model: BeamModel, result: dict) -> list:
    positions = {0.0, model.span_ft}
    for load in model.point_loads:
        positions.add(load.position_ft)
    for load in model.uniform_loads:
        positions.add(load.start_ft)
        positions.add(load.end_ft)

    step = 0.25
    position = 0.0
    while position < model.span_ft:
        positions.add(round(position * 4.0) / 4.0)
        position += step

    ordered = sorted(positions)
    rows = []
    for position_ft in ordered:
        x_in = position_ft * 12.0
        rows.append({
            "Position x (ft)": position_ft,
            "Shear V (kips)": result["shear"]["at"](x_in),
            "Moment M (kip-ft)": result["moment"]["at"](x_in) / 12.0,
            "Deflection (in)": result["deflection"]["at"](x_in),
        })

    shear_locations = sorted(
        set(location for location in (
            *[load.position_ft for load in model.point_loads],
            *[load.start_ft for load in model.uniform_loads],
            *[load.end_ft for load in model.uniform_loads],
        ))
    )
    for location in shear_locations:
        if 0.0 < location < model.span_ft:
            eps = 1e-7
            left_ft = location - eps
            right_ft = location + eps
            if left_ft >= 0.0:
                left_x = left_ft * 12.0
                rows.append({
                    "Position x (ft)": left_ft,
                    "Shear V (kips)": result["shear"]["at"](left_x),
                    "Moment M (kip-ft)": result["moment"]["at"](left_x) / 12.0,
                    "Deflection (in)": result["deflection"]["at"](left_x),
                })
            if right_ft <= model.span_ft:
                right_x = right_ft * 12.0
                rows.append({
                    "Position x (ft)": right_ft,
                    "Shear V (kips)": result["shear"]["at"](right_x),
                    "Moment M (kip-ft)": result["moment"]["at"](right_x) / 12.0,
                    "Deflection (in)": result["deflection"]["at"](right_x),
                })

    unique = {}
    for row in rows:
        key = round(row["Position x (ft)"], 7)
        unique[key] = row
    return [unique[key] for key in sorted(unique)]
