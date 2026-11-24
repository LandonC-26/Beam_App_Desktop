import csv
import json

from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
from matplotlib.patches import Polygon, Rectangle

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


def export_calculation_pdf(path, result, input_details):
    figure = Figure(figsize=(11, 8.5), facecolor="white")
    figure.text(
        0.045, 0.955, "Beam Design Calculation Sheet",
        fontsize=18, fontweight="bold", color="#172033", va="top",
    )
    bending_pass = result.bending_stress <= result.allowable_ksi
    deflection_pass = (
        abs(result.max_deflection.deflection) <= result.allowed_deflection
    )
    overall_pass = bending_pass and deflection_pass
    status_text = "PASS" if overall_pass else "FAIL"
    status_color = "#15803d" if overall_pass else "#b42318"
    figure.text(
        0.955, 0.955, f"Overall: {status_text}",
        fontsize=12, fontweight="bold", color=status_color, ha="right", va="top",
    )
    figure.text(
        0.045, 0.915, "Beam analysis, strength check, and deflection check",
        fontsize=9, color="#62708a", va="top",
    )

    inputs = figure.add_axes([0.045, 0.81, 0.91, 0.09])
    inputs.set_xlim(0, 1)
    inputs.set_ylim(0, 1)
    inputs.axis("off")
    inputs.add_patch(Rectangle((0, 0), 1, 1, fill=False, edgecolor="#cbd5e1"))
    inputs.text(0.015, 0.88, "DESIGN INPUTS", fontsize=8, fontweight="bold",
                color="#475569", va="top")
    row_one = (
        f"Support: {input_details['support']}",
        f"Span: {result.span_ft:g} ft",
        f"Material: {result.section.category.title()}",
        f"Section: {result.section.designation}",
    )
    row_two = (
        f"Uniform load: {input_details['uniform_load']} kip/ft",
        f"Allowable stress: {input_details['allowable_stress']}",
        f"Deflection limit: L/{result.limit}",
        f"Self-weight: {input_details['self_weight']}",
    )
    for i, value in enumerate(row_one):
        inputs.text(0.015 + i * 0.245, 0.62, value, fontsize=8, color="#172033",
                    va="top")
    for i, value in enumerate(row_two):
        inputs.text(0.015 + i * 0.245, 0.39, value, fontsize=8, color="#172033",
                    va="top")
    inputs.text(
        0.015, 0.16, f"Point loads: {input_details['point_loads']}",
        fontsize=8, color="#172033", va="top",
    )

    metrics = (
        ("REACTIONS", f"RA {result.reactions['RA']:.2f} kips   RB {result.reactions['RB']:.2f} kips"),
        ("MAX SHEAR", f"{abs(result.max_shear.shear):.2f} kips"),
        ("MAX MOMENT", f"{abs(result.max_moment.moment):.2f} kip-ft @ {result.max_moment.x:.2f} ft"),
        ("MAX DEFLECTION", f"{abs(result.max_deflection.deflection):.3f} in @ {result.max_deflection.x:.2f} ft"),
    )
    for i, (label, value) in enumerate(metrics):
        x = 0.05 + i * 0.235
        figure.text(x, 0.775, label, fontsize=7, fontweight="bold",
                    color="#62708a", va="top")
        figure.text(x, 0.747, value, fontsize=8, fontweight="bold",
                    color="#172033", va="top")

    def add_check_card(position, passed, title, lines):
        axis = figure.add_axes(position)
        axis.set_xlim(0, 1)
        axis.set_ylim(0, 1)
        axis.axis("off")
        background = "#ecfdf3" if passed else "#fff1f0"
        foreground = "#15803d" if passed else "#b42318"
        axis.add_patch(Rectangle((0, 0), 1, 1, facecolor=background,
                                 edgecolor="#bbf7d0" if passed else "#fecaca"))
        axis.text(0.025, 0.82, f"{title}: {'PASS' if passed else 'FAIL'}",
                  fontsize=9, fontweight="bold", color=foreground, va="top")
        axis.text(0.025, 0.54, lines[0], fontsize=8, color="#172033", va="top")
        axis.text(0.025, 0.28, lines[1], fontsize=8, color="#172033", va="top")

    bending_utilization = result.bending_stress / result.allowable_ksi * 100
    deflection_utilization = (
        abs(result.max_deflection.deflection) / result.allowed_deflection * 100
    )
    add_check_card(
        [0.045, 0.655, 0.445, 0.07],
        bending_pass,
        "Bending",
        (
            f"Stress: {result.bending_stress:.2f} ksi / allowable {result.allowable_ksi:.2f} ksi",
            f"Utilization: {bending_utilization:.1f}%   Moment location: {result.max_moment.x:.2f} ft",
        ),
    )
    add_check_card(
        [0.51, 0.655, 0.445, 0.07],
        deflection_pass,
        "Deflection",
        (
            f"Actual: {abs(result.max_deflection.deflection):.3f} in / allowed {result.allowed_deflection:.3f} in",
            f"Utilization: {deflection_utilization:.1f}%   Location: {result.max_deflection.x:.2f} ft",
        ),
    )

    beam_axis = figure.add_axes([0.07, 0.525, 0.86, 0.105])
    beam_axis.set_xlim(-result.span_ft * 0.08, result.span_ft * 1.08)
    beam_axis.set_ylim(-1.15, 1.45)
    beam_axis.axis("off")
    beam_axis.plot([0, result.span_ft], [0, 0], color="#334155", linewidth=5,
                   solid_capstyle="round")
    if result.beam_type == "simple":
        beam_axis.add_patch(Polygon(
            ((-result.span_ft * 0.025, -0.75),
             (result.span_ft * 0.025, -0.75), (0, -0.08)),
            closed=True, facecolor="#dbeafe", edgecolor="#64748b",
        ))
        beam_axis.add_patch(Polygon(
            ((result.span_ft - result.span_ft * 0.025, -0.75),
             (result.span_ft + result.span_ft * 0.025, -0.75),
             (result.span_ft, -0.08)),
            closed=True, facecolor="#dbeafe", edgecolor="#64748b",
        ))
    else:
        beam_axis.plot([0, 0], [-0.8, 0.8], color="#64748b", linewidth=5)
        for y in (-0.75, -0.35, 0.05, 0.45, 0.75):
            beam_axis.plot([-result.span_ft * 0.025, 0], [y - 0.15, y],
                           color="#94a3b8", linewidth=1)
    if result.uniform > 0:
        arrows = [result.span_ft * i / 12 for i in range(13)]
        beam_axis.vlines(arrows, 0.08, 0.75, color="#2563eb", linewidth=0.8)
        beam_axis.text(result.span_ft / 2, 0.9,
                       f"{result.uniform:.3f} kip/ft uniform", ha="center",
                       fontsize=7, color="#1d4ed8")
    for point in result.points:
        beam_axis.annotate(
            "", xy=(point.location, -0.03), xytext=(point.location, 0.78),
            arrowprops={"arrowstyle": "-|>", "color": "#e11d48", "lw": 1.4},
        )
        beam_axis.text(point.location, 0.87, f"{point.magnitude:g} kip",
                       ha="center", fontsize=7, color="#b91c1c")
    beam_axis.text(0, -1.02, "0 ft", ha="center", fontsize=7)
    beam_axis.text(result.span_ft, -1.02, f"{result.span_ft:g} ft",
                   ha="center", fontsize=7)
    beam_axis.set_title("Beam and loads", fontsize=9, loc="left", pad=2)

    diagram_specs = (
        ("Shear (kips)", lambda station: station.shear, False),
        ("Moment (kip-ft)", lambda station: station.moment, False),
        ("Deflection (in, downward positive)",
         lambda station: station.deflection, True),
    )
    x_values = [station.x for station in result.stations]
    for index, (title, value_for, invert_y) in enumerate(diagram_specs):
        axis = figure.add_axes([0.055 + index * 0.305, 0.075, 0.285, 0.405])
        y_values = [value_for(station) for station in result.stations]
        axis.plot(x_values, y_values, color="#2463eb", linewidth=1.6)
        axis.axhline(0, color="#94a3b8", linewidth=0.8)
        axis.set_title(title, fontsize=9)
        axis.set_xlabel("Position (ft)", fontsize=8)
        axis.grid(True, alpha=0.25)
        axis.tick_params(labelsize=7)
        axis.set_xlim(0, result.span_ft)
        if invert_y:
            axis.invert_yaxis()

    figure.text(
        0.5, 0.025,
        "Analysis uses Euler-Bernoulli beam theory at 101 evenly spaced stations.",
        ha="center", fontsize=7, color="#62708a",
    )
    with PdfPages(path) as pdf:
        pdf.savefig(figure)
