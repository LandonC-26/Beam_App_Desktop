from dataclasses import dataclass
from math import isfinite
from typing import Iterable


@dataclass(frozen=True)
class Section:
    category: str
    designation: str
    I: float
    S: float
    weight: float
    E: float


SECTIONS = (
    Section("steel", "W12x26", 204.0, 33.4, 26.0, 29000.0),
    Section("steel", "W12x22", 156.0, 29.3, 22.0, 29000.0),
    Section("steel", "W12x30", 238.0, 38.6, 30.0, 29000.0),
    Section("steel", "W10x22", 118.0, 26.0, 22.0, 29000.0),
    Section("steel", "W8x31", 110.0, 30.4, 31.0, 29000.0),
    Section("lumber", "2x8", 47.63, 13.14, 0.0, 1600.0),
    Section("lumber", "2x10", 98.93, 21.39, 0.0, 1600.0),
    Section("lumber", "2x12", 177.98, 31.64, 0.0, 1600.0),
)


@dataclass(frozen=True)
class PointLoad:
    magnitude: float
    location: float


@dataclass(frozen=True)
class Station:
    x: float
    shear: float
    moment: float
    deflection: float


@dataclass(frozen=True)
class Result:
    span_ft: float
    beam_type: str
    section: Section
    uniform: float
    points: tuple
    allowable_ksi: float
    limit: int
    stations: tuple
    reactions: dict
    max_shear: Station
    max_moment: Station
    max_deflection: Station
    bending_stress: float
    allowed_deflection: float


def validate_number(value, name, minimum=None, maximum=None):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number.")
    if not isfinite(number):
        raise ValueError(f"{name} must be a finite number.")
    if minimum is not None and number < minimum:
        raise ValueError(f"{name} must be at least {minimum:g}.")
    if maximum is not None and number > maximum:
        raise ValueError(f"{name} must be no more than {maximum:g}.")
    return number


def analyze(
    span_ft,
    beam_type,
    section,
    uniform,
    points: Iterable[PointLoad],
    allowable_ksi,
    limit,
):
    span_ft = validate_number(span_ft, "Span", 0.0001)
    uniform = validate_number(uniform, "Uniform load", 0)
    allowable_ksi = validate_number(allowable_ksi, "Allowable stress", 0.0001)
    limit = int(limit)
    if limit not in (240, 360, 480):
        raise ValueError("Deflection limit must be L/240, L/360, or L/480.")
    if beam_type not in ("simple", "cantilever"):
        raise ValueError("Beam support type is invalid.")

    point_list = []
    for point in points:
        magnitude = validate_number(point.magnitude, "Point-load magnitude", 0)
        location = validate_number(point.location, "Point-load position", 0, span_ft)
        point_list.append(PointLoad(magnitude, location))

    L = span_ft * 12.0
    EI = section.E * section.I
    reactions = {"RA": 0.0, "RB": 0.0}

    if beam_type == "simple":
        reactions["RA"] = uniform * span_ft / 2.0
        reactions["RB"] = reactions["RA"]
        for point in point_list:
            reactions["RA"] += point.magnitude * (span_ft - point.location) / span_ft
            reactions["RB"] += point.magnitude * point.location / span_ft
    else:
        reactions["RA"] = uniform * span_ft
        reactions["RA"] += sum(point.magnitude for point in point_list)

    stations = []
    for i in range(101):
        x_in = L * i / 100.0
        x_ft = x_in / 12.0
        shear = 0.0
        moment = 0.0
        deflection = 0.0

        if beam_type == "simple":
            w = uniform / 12.0
            shear = reactions["RA"] - uniform * x_ft
            moment = reactions["RA"] * x_ft - uniform * x_ft * x_ft / 2.0
            deflection = w * x_in * (L ** 3 - 2.0 * L * x_in ** 2 + x_in ** 3) / (24.0 * EI)

            for point in point_list:
                a = point.location * 12.0
                if x_in >= a:
                    shear -= point.magnitude
                    moment -= point.magnitude * (x_in - a) / 12.0
                b = L - a
                if x_in <= a:
                    deflection += point.magnitude * b * x_in * (
                        L * L - b * b - x_in * x_in
                    ) / (6.0 * L * EI)
                else:
                    deflection += point.magnitude * a * (L - x_in) * (
                        L * L - a * a - (L - x_in) * (L - x_in)
                    ) / (6.0 * L * EI)
        else:
            w = uniform / 12.0
            shear = w * (L - x_in)
            moment = -w * (L - x_in) ** 2 / 2.0
            deflection = w * x_in ** 2 * (
                6.0 * L ** 2 - 4.0 * L * x_in + x_in ** 2
            ) / (24.0 * EI)

            for point in point_list:
                a = point.location * 12.0
                if x_in < a:
                    shear += point.magnitude
                    moment -= point.magnitude * (a - x_in) / 12.0
                if x_in <= a:
                    deflection += point.magnitude * x_in ** 2 * (3.0 * a - x_in) / (6.0 * EI)
                else:
                    deflection += point.magnitude * a ** 2 * (3.0 * x_in - a) / (6.0 * EI)

        stations.append(Station(x_ft, shear, moment, deflection))

    max_shear = max(stations, key=lambda item: abs(item.shear))
    max_moment = max(stations, key=lambda item: abs(item.moment))
    max_deflection = max(stations, key=lambda item: abs(item.deflection))
    bending_stress = abs(max_moment.moment) * 12.0 / section.S
    allowed_deflection = L / limit

    return Result(
        span_ft=span_ft,
        beam_type=beam_type,
        section=section,
        uniform=uniform,
        points=tuple(point_list),
        allowable_ksi=allowable_ksi,
        limit=limit,
        stations=tuple(stations),
        reactions=reactions,
        max_shear=max_shear,
        max_moment=max_moment,
        max_deflection=max_deflection,
        bending_stress=bending_stress,
        allowed_deflection=allowed_deflection,
    )
