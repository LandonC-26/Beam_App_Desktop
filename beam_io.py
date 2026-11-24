import csv
import json

from beam_core import SECTIONS, validate_number


def validate_design_document(document):
    if not isinstance(document, dict):
        raise ValueError("The design file must contain a JSON object.")
    if type(document.get("version")) is not int or document["version"] != 1:
        raise ValueError("The design file version is not supported.")

    beam = document.get("beam")
    loads = document.get("loads")
    if not isinstance(beam, dict) or not isinstance(loads, dict):
        raise ValueError("The design file must include beam and loads objects.")

    support_type = beam.get("support_type")
    if support_type not in ("simple", "cantilever"):
        raise ValueError("The design file has an invalid support type.")

    span = validate_number(beam.get("span_ft"), "Span", 0.0001)
    material = beam.get("material")
    if material not in ("steel", "lumber"):
        raise ValueError("The design file has an invalid material.")

    section_name = beam.get("section")
    section = next(
        (item for item in SECTIONS
         if item.designation == section_name and item.category == material),
        None,
    )
    if section is None:
        raise ValueError("The design file has an invalid section for its material.")

    limit = beam.get("deflection_limit")
    if type(limit) is not int or limit not in (240, 360, 480):
        raise ValueError("The design file has an invalid deflection limit.")

    allowable = validate_number(
        beam.get("allowable_stress"), "Allowable stress", 0.0001
    )
    stress_unit = beam.get("stress_unit")
    if stress_unit not in ("ksi", "psi"):
        raise ValueError("The design file has an invalid stress unit.")

    uniform = validate_number(loads.get("uniform_kip_ft"), "Uniform load", 0)
    include_self_weight = loads.get("include_self_weight")
    if type(include_self_weight) is not bool:
        raise ValueError("The self-weight setting must be true or false.")
    if include_self_weight and material != "steel":
        raise ValueError("Self-weight can only be included for steel sections.")

    point_loads = loads.get("point_loads")
    if not isinstance(point_loads, list):
        raise ValueError("Point loads must be a list.")
    validated_points = []
    for point in point_loads:
        if not isinstance(point, dict):
            raise ValueError("Each point load must be an object.")
        magnitude = validate_number(
            point.get("magnitude_kip"), "Point-load magnitude", 0
        )
        location = validate_number(
            point.get("position_ft"), "Point-load position", 0, span
        )
        validated_points.append({
            "magnitude_kip": magnitude,
            "position_ft": location,
        })

    return {
        "version": 1,
        "beam": {
            "support_type": support_type,
            "span_ft": span,
            "material": material,
            "section": section.designation,
            "deflection_limit": limit,
            "allowable_stress": allowable,
            "stress_unit": stress_unit,
        },
        "loads": {
            "uniform_kip_ft": uniform,
            "point_loads": validated_points,
            "include_self_weight": include_self_weight,
        },
    }


def save_design_file(path, document):
    validated = validate_design_document(document)
    with open(path, "w", encoding="utf-8") as design_file:
        json.dump(validated, design_file, indent=2)
        design_file.write("\n")


def open_design_file(path):
    with open(path, "r", encoding="utf-8") as design_file:
        document = json.load(design_file)
    return validate_design_document(document)


def export_results_csv(path, stations):
    with open(path, "w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(("x_ft", "V_kips", "M_kip_ft", "deflection_in"))
        for station in stations:
            writer.writerow((
                station.x,
                station.shear,
                station.moment,
                station.deflection,
            ))
