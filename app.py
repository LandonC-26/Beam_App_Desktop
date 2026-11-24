import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from beam_core import SECTIONS, PointLoad, analyze, validate_number
from beam_io import open_design_file, save_design_file


class BeamApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Beam Designer")
        self.geometry("1400x900")
        self.minsize(1000, 700)
        self.configure(bg="#eef3f8")
        self._build_menu()

        header = tk.Frame(self, bg="#172033", height=62)
        header.pack(fill="x")
        tk.Label(header, text="Beam Designer", bg="#172033", fg="white",
                 font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=24, pady=(10, 0))
        tk.Label(header, text="Shear, moment, deflection, and strength check",
                 bg="#172033", fg="#bdc7d8", font=("Segoe UI", 10)).pack(anchor="w", padx=24)

        body = tk.Frame(self, bg="#eef3f8")
        body.pack(fill="both", expand=True, padx=16, pady=16)
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self.controls = tk.Frame(body, bg="white", width=320, relief="solid", bd=1)
        self.controls.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.output = tk.Frame(body, bg="#eef3f8")
        self.output.grid(row=0, column=1, sticky="nsew")
        self.output.columnconfigure(0, weight=1)

        self._build_controls()
        self._build_output()
        self.update_sections()
        self.calculate()

    def _build_menu(self):
        menu_bar = tk.Menu(self)
        file_menu = tk.Menu(menu_bar, tearoff=False)
        file_menu.add_command(label="Save", command=self.save_design, accelerator="Ctrl+S")
        file_menu.add_command(label="Open", command=self.open_design, accelerator="Ctrl+O")
        menu_bar.add_cascade(label="File", menu=file_menu)
        self.configure(menu=menu_bar)
        self.bind("<Control-s>", lambda event: self.save_design())
        self.bind("<Control-o>", lambda event: self.open_design())

    def _section(self, title, parent):
        frame = ttk.LabelFrame(parent, text=title)
        frame.pack(fill="x", padx=8, pady=(5, 2))
        return frame

    def _build_controls(self):
        beam = self._section("Beam", self.controls)
        tk.Label(beam, text="Support type", font=("Segoe UI", 9)).pack(anchor="w", padx=6)
        self.beam_type = ttk.Combobox(beam, values=("Simply supported", "Cantilever"),
                                      state="readonly")
        self.beam_type.set("Simply supported")
        self.beam_type.pack(fill="x", padx=6, pady=(0, 4))
        tk.Label(beam, text="Span (ft)", font=("Segoe UI", 9)).pack(anchor="w", padx=6)
        self.span = tk.Entry(beam)
        self.span.insert(0, "20")
        self.span.pack(fill="x", padx=6, pady=(0, 4))

        loads = self._section("Loads", self.controls)
        tk.Label(loads, text="Uniform load (kip/ft)", font=("Segoe UI", 9)).pack(anchor="w", padx=6)
        self.uniform = tk.Entry(loads)
        self.uniform.insert(0, "1")
        self.uniform.pack(fill="x", padx=6, pady=(0, 4))
        self.point_rows = tk.Frame(loads)
        self.point_rows.pack(fill="x", padx=6)
        tk.Button(loads, text="+ Add point load", command=self.add_point_load,
                  bg="#eff6ff", fg="#2463eb", relief="groove").pack(fill="x", padx=6, pady=4)
        self.self_weight = tk.BooleanVar(value=False)
        self.self_weight_check = tk.Checkbutton(loads, text="Include steel self-weight",
                                                variable=self.self_weight,
                                                font=("Segoe UI", 9))
        self.self_weight_check.pack(anchor="w", padx=6, pady=(0, 4))

        section = self._section("Section", self.controls)
        tk.Label(section, text="Material", font=("Segoe UI", 9)).pack(anchor="w", padx=6)
        self.material = ttk.Combobox(section, values=("Steel", "Lumber"), state="readonly")
        self.material.set("Steel")
        self.material.bind("<<ComboboxSelected>>", lambda event: self.update_sections())
        self.material.pack(fill="x", padx=6, pady=(0, 4))

        tk.Label(section, text="Section", font=("Segoe UI", 9)).pack(anchor="w", padx=6)
        self.section_choice = ttk.Combobox(section, values=(), state="readonly")
        self.section_choice.pack(fill="x", padx=6, pady=(0, 4))

        stress_row = tk.Frame(section)
        stress_row.pack(fill="x", padx=6, pady=(0, 4))
        tk.Label(stress_row, text="Allowable stress", font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w")
        tk.Label(stress_row, text="Stress unit", font=("Segoe UI", 9)).grid(row=0, column=1, sticky="w")
        self.allowable = tk.Entry(stress_row)
        self.allowable.insert(0, "24")
        self.allowable.grid(row=1, column=0, sticky="ew", padx=(0, 5))
        self.stress_unit = ttk.Combobox(stress_row, values=("ksi", "psi"), state="readonly")
        self.stress_unit.set("ksi")
        self.stress_unit.grid(row=1, column=1, sticky="ew")
        stress_row.columnconfigure(0, weight=1)
        stress_row.columnconfigure(1, weight=1)

        tk.Label(section, text="Deflection limit", font=("Segoe UI", 9)).pack(anchor="w", padx=6)
        self.deflection_limit = ttk.Combobox(section, values=("L/240", "L/360", "L/480"),
                                             state="readonly")
        self.deflection_limit.set("L/360")
        self.deflection_limit.pack(fill="x", padx=6, pady=(0, 4))

        self.calculate_button = tk.Button(
            self.controls, text="Calculate beam", command=self.calculate,
            bg="#2463eb", fg="white", activebackground="#194ba8",
            activeforeground="white", relief="flat", font=("Segoe UI", 10, "bold"),
            height=1
        )
        self.calculate_button.pack(fill="x", padx=8, pady=(5, 4))
        self.error = tk.Label(self.controls, text="", fg="#b42318",
                              wraplength=290, justify="left")
        self.error.pack(fill="x", padx=8)

    def update_sections(self):
        is_steel = self.material.get() == "Steel"
        categories = "steel" if is_steel else "lumber"
        choices = [section.designation for section in SECTIONS if section.category == categories]
        self.section_choice.configure(values=choices)
        self.section_choice.set("W12x26" if is_steel else "2x8")
        self.allowable.delete(0, "end")
        self.allowable.insert(0, "24" if is_steel else "900")
        self.stress_unit.set("ksi" if is_steel else "psi")
        self.self_weight_check.configure(state="normal" if is_steel else "disabled")
        if not is_steel:
            self.self_weight.set(False)

    def add_point_load(self, magnitude="10", location="10"):
        row = tk.Frame(self.point_rows)
        row.pack(fill="x", pady=3)
        left = tk.Frame(row)
        left.pack(side="left", fill="x", expand=True)
        tk.Label(left, text="Load (kip)", font=("Segoe UI", 9)).pack(anchor="w")
        load_entry = tk.Entry(left)
        load_entry.insert(0, magnitude)
        load_entry.pack(fill="x")
        right = tk.Frame(row)
        right.pack(side="left", fill="x", expand=True, padx=(5, 0))
        tk.Label(right, text="Position (ft)", font=("Segoe UI", 9)).pack(anchor="w")
        location_entry = tk.Entry(right)
        location_entry.insert(0, location)
        location_entry.pack(fill="x")
        tk.Button(row, text="x", width=3, command=lambda: row.destroy()).pack(
            side="left", padx=(5, 0), pady=(18, 0)
        )
        row.load_entry = load_entry
        row.location_entry = location_entry

    def _build_output(self):
        stats = tk.Frame(self.output, bg="#eef3f8")
        stats.grid(row=0, column=0, sticky="ew")
        for i in range(4):
            stats.columnconfigure(i, weight=1)
        self.stat_labels = []
        for i, title in enumerate(("Moment", "Shear", "Deflection", "Section")):
            card = tk.Frame(stats, bg="white", relief="solid", bd=1)
            card.grid(row=0, column=i, sticky="ew", padx=(0, 8 if i < 3 else 0),
                      pady=(0, 5), ipady=3)
            tk.Label(card, text=f"{title}: ", bg="white", fg="#62708a",
                     font=("Segoe UI", 9)).pack(side="left", padx=(8, 0), pady=4)
            value = tk.Label(card, text="-", bg="white", fg="#172033",
                             font=("Segoe UI", 11, "bold"))
            value.pack(side="left", pady=4)
            self.stat_labels.append(value)

        self.checks = tk.Frame(self.output, bg="#eef3f8")
        self.checks.grid(row=1, column=0, sticky="ew")
        self.checks.columnconfigure(0, weight=1)
        self.checks.columnconfigure(1, weight=1)
        self.bending_card = tk.Frame(self.checks)
        self.bending_card.grid(row=0, column=0, sticky="ew", padx=(0, 5), pady=(0, 5))
        self.deflection_card = tk.Frame(self.checks)
        self.deflection_card.grid(row=0, column=1, sticky="ew", padx=(5, 0), pady=(0, 5))
        self.overall_card = tk.Frame(self.checks)
        self.overall_card.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 5))

        plot_container = tk.Frame(self.output, bg="#eef3f8")
        plot_container.grid(row=2, column=0, sticky="nsew")
        self.output.rowconfigure(2, weight=1)
        plot_container.columnconfigure(0, weight=1)

        self.canvas_frames = []
        self.canvases = []
        names = ("Beam and loads", "Shear (kips)", "Moment (kip-ft)",
                 "Deflection (in, downward positive)")
        for row, name in enumerate(names):
            frame = tk.Frame(plot_container, bg="white", relief="solid", bd=1)
            frame.grid(row=row, column=0, sticky="nsew", pady=(0, 7))
            plot_container.rowconfigure(row, weight=1)
            tk.Label(frame, text=name, bg="white", fg="#475569",
                     font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(4, 0))
            fig = Figure(figsize=(8, 1.35), dpi=100, facecolor="white")
            canvas = FigureCanvasTkAgg(fig, master=frame)
            canvas.get_tk_widget().pack(fill="both", expand=True)
            self.canvas_frames.append(frame)
            self.canvases.append(canvas)

    def _selected_section(self):
        designation = self.section_choice.get()
        return next(section for section in SECTIONS if section.designation == designation)

    def calculate(self):
        self.error.configure(text="")
        try:
            span = validate_number(self.span.get(), "Span", 0.0001)
            uniform = validate_number(self.uniform.get(), "Uniform load", 0)
            section = self._selected_section()
            if section.category == "steel" and self.self_weight.get():
                uniform += section.weight / 1000.0

            points = []
            for row in self.point_rows.winfo_children():
                magnitude = validate_number(row.load_entry.get(), "Point-load magnitude", 0)
                location = validate_number(row.location_entry.get(), "Point-load position",
                                          0, span)
                if magnitude > 0:
                    points.append(PointLoad(magnitude, location))

            allowable = validate_number(self.allowable.get(), "Allowable stress", 0.0001)
            if self.stress_unit.get() == "psi":
                allowable /= 1000.0
            limit = int(self.deflection_limit.get().split("/")[1])
            beam_type = "simple" if self.beam_type.get() == "Simply supported" else "cantilever"

            result = analyze(span, beam_type, section, uniform, points, allowable, limit)
            self._render(result)
        except (ValueError, StopIteration) as exc:
            self.error.configure(text=str(exc))

    def save_design(self):
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Save Beam Design",
            defaultextension=".json",
            filetypes=(("Beam design files", "*.json"), ("All files", "*.*")),
        )
        if not path:
            return

        self.calculate()
        error = self.error.cget("text")
        if error:
            messagebox.showerror("Cannot save design", error, parent=self)
            return

        try:
            document = {
                "version": 1,
                "beam": {
                    "support_type": (
                        "simple" if self.beam_type.get() == "Simply supported"
                        else "cantilever"
                    ),
                    "span_ft": validate_number(self.span.get(), "Span", 0.0001),
                    "material": (
                        "steel" if self.material.get() == "Steel" else "lumber"
                    ),
                    "section": self.section_choice.get(),
                    "deflection_limit": int(
                        self.deflection_limit.get().split("/")[1]
                    ),
                    "allowable_stress": validate_number(
                        self.allowable.get(), "Allowable stress", 0.0001
                    ),
                    "stress_unit": self.stress_unit.get(),
                },
                "loads": {
                    "uniform_kip_ft": validate_number(
                        self.uniform.get(), "Uniform load", 0
                    ),
                    "point_loads": [
                        {
                            "magnitude_kip": validate_number(
                                row.load_entry.get(), "Point-load magnitude", 0
                            ),
                            "position_ft": validate_number(
                                row.location_entry.get(), "Point-load position",
                                0, validate_number(self.span.get(), "Span", 0.0001)
                            ),
                        }
                        for row in self.point_rows.winfo_children()
                    ],
                    "include_self_weight": self.self_weight.get(),
                },
            }
            save_design_file(path, document)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Save failed", str(exc), parent=self)

    def open_design(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Open Beam Design",
            filetypes=(("Beam design files", "*.json"), ("All files", "*.*")),
        )
        if not path:
            return

        try:
            document = open_design_file(path)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Open failed", str(exc), parent=self)
            return

        beam = document["beam"]
        loads = document["loads"]
        self.beam_type.set(
            "Simply supported" if beam["support_type"] == "simple" else "Cantilever"
        )
        self.span.delete(0, "end")
        self.span.insert(0, str(beam["span_ft"]))
        self.material.set("Steel" if beam["material"] == "steel" else "Lumber")
        self.update_sections()
        self.section_choice.set(beam["section"])
        self.allowable.delete(0, "end")
        self.allowable.insert(0, str(beam["allowable_stress"]))
        self.stress_unit.set(beam["stress_unit"])
        self.deflection_limit.set(f"L/{beam['deflection_limit']}")
        self.uniform.delete(0, "end")
        self.uniform.insert(0, str(loads["uniform_kip_ft"]))
        self.self_weight.set(loads["include_self_weight"])
        for row in self.point_rows.winfo_children():
            row.destroy()
        for point in loads["point_loads"]:
            self.add_point_load(
                str(point["magnitude_kip"]),
                str(point["position_ft"]),
            )
        self.calculate()

    def _clear_card(self, card):
        for widget in card.winfo_children():
            widget.destroy()

    def _set_check_card(self, card, passed, title, lines):
        self._clear_card(card)
        card.configure(bg="#ecfdf3" if passed else "#fff1f0",
                       relief="solid", bd=1)
        header = tk.Frame(card, bg=card.cget("bg"))
        header.pack(fill="x", padx=8, pady=(3, 1))
        tk.Label(header, text=title, bg=card.cget("bg"), fg="#172033",
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Label(header, text="PASS" if passed else "FAIL", bg=card.cget("bg"),
                 fg="#15803d" if passed else "#b42318",
                 font=("Segoe UI", 9, "bold")).pack(side="right")
        tk.Label(card, text="  |  ".join(lines[:2]), bg=card.cget("bg"),
                 fg="#172033", font=("Segoe UI", 8)).pack(anchor="w", padx=8)
        tk.Label(card, text="  |  ".join(lines[2:]), bg=card.cget("bg"),
                 fg="#172033", font=("Segoe UI", 8)).pack(anchor="w", padx=8, pady=(0, 3))

    def _render(self, result):
        self.result = result
        self.stat_labels[0].configure(
            text=f"{abs(result.max_moment.moment):.2f} kip-ft")
        self.stat_labels[1].configure(
            text=f"{abs(result.max_shear.shear):.2f} kips")
        self.stat_labels[2].configure(
            text=f"{abs(result.max_deflection.deflection):.3f} in")
        self.stat_labels[3].configure(text=result.section.designation)

        bending_pass = result.bending_stress <= result.allowable_ksi
        deflection_pass = abs(result.max_deflection.deflection) <= result.allowed_deflection
        bending_util = result.bending_stress / result.allowable_ksi * 100.0
        deflection_util = abs(result.max_deflection.deflection) / result.allowed_deflection * 100.0
        self._set_check_card(
            self.bending_card, bending_pass, "Bending",
            [f"Stress: {result.bending_stress:.2f} ksi",
             f"Allowable: {result.allowable_ksi:.2f} ksi",
             f"Utilization: {bending_util:.1f}%",
             f"Moment location: {result.max_moment.x:.2f} ft"])
        self._set_check_card(
            self.deflection_card, deflection_pass, "Deflection",
            [f"Deflection: {abs(result.max_deflection.deflection):.3f} in",
             f"Allowed: {result.allowed_deflection:.3f} in (L/{result.limit})",
             f"Utilization: {deflection_util:.1f}%",
             f"Deflection location: {result.max_deflection.x:.2f} ft"])

        overall_pass = bending_pass and deflection_pass
        self._clear_card(self.overall_card)
        self.overall_card.configure(
            bg="#ecfdf3" if overall_pass else "#fff1f0",
            relief="solid", bd=1)
        failures = []
        if not bending_pass:
            failures.append("bending strength")
        if not deflection_pass:
            failures.append("deflection stiffness")
        summary = ("Congratulations - the beam passes!" if overall_pass
                   else f"The beam does not pass. Fails: {' and '.join(failures)}.")
        tk.Label(self.overall_card, text=summary, bg=self.overall_card.cget("bg"),
                 fg="#15803d" if overall_pass else "#b42318",
                 font=("Segoe UI", 9, "bold")).pack(pady=4)

        self._draw_beam(result)
        self._draw_diagram(1, "shear", lambda station: station.shear,
                           "kips", "#2463eb")
        self._draw_diagram(2, "moment", lambda station: station.moment,
                           "kip-ft", "#2463eb")
        self._draw_diagram(3, "deflection", lambda station: station.deflection,
                           "in", "#2463eb")

    def _draw_beam(self, result):
        canvas = self.canvases[0]
        fig = canvas.figure
        fig.clear()
        ax = fig.subplots()
        ax.set_xlim(-1, result.span_ft + 1)
        ax.set_ylim(-2.5, 2.5)
        ax.axis("off")
        ax.plot([0, result.span_ft], [0, 0], color="#334155", linewidth=8,
                solid_capstyle="round")

        if result.beam_type == "simple":
            ax.plot([0, 0], [-0.15, -1.2], color="#64748b", linewidth=2)
            ax.plot([result.span_ft, result.span_ft], [-0.15, -1.2],
                    color="#64748b", linewidth=2)
            ax.plot([0, -0.6, 0.6, 0], [-1.2, -2.0, -2.0, -1.2],
                    color="#64748b", linewidth=1)
            ax.plot([result.span_ft, result.span_ft - 0.6, result.span_ft + 0.6,
                     result.span_ft], [-1.2, -2.0, -2.0, -1.2],
                    color="#64748b", linewidth=1)
        else:
            ax.fill_between([-0.8, 0], -1.5, 1.5, color="#94a3b8")

        if result.uniform > 0:
            arrow_x = [i * result.span_ft / 12 for i in range(13)]
            ax.vlines(arrow_x, 0.15, 1.15, color="#2563eb", linewidth=1)
            ax.text(result.span_ft / 2, 1.45,
                    f"{result.uniform:.3f} kip/ft", ha="center", color="#1d4ed8",
                    fontweight="bold")

        for point in result.points:
            ax.annotate("", xy=(point.location, -0.05), xytext=(point.location, 1.1),
                        arrowprops={"arrowstyle":"-|>", "color":"#e11d48", "lw":2})
            ax.text(point.location, 1.25, f"{point.magnitude:g} k",
                    ha="center", va="bottom", color="#b91c1c", fontweight="bold")
        ax.text(0, -2.25, "0 ft", ha="center")
        ax.text(result.span_ft, -2.25, f"{result.span_ft:g} ft", ha="center")
        fig.tight_layout(pad=0.5)
        canvas.draw()

    def _draw_diagram(self, index, title, accessor, unit, color):
        canvas = self.canvases[index]
        fig = canvas.figure
        fig.clear()
        ax = fig.subplots()
        xs = [station.x for station in self.result.stations]
        ys = [accessor(station) for station in self.result.stations]
        ax.plot(xs, ys, color=color, linewidth=2)
        ax.axhline(0, color="#94a3b8", linewidth=1)
        ax.set_xlim(0, result_span := self.result.span_ft)
        ax.set_xlabel("Position (ft)", fontsize=8)
        ax.set_ylabel(unit, fontsize=8)
        ax.grid(True, alpha=0.25)
        ax.tick_params(labelsize=8)
        fig.tight_layout(pad=0.6)
        canvas.draw()


if __name__ == "__main__":
    app = BeamApp()
    app.mainloop()
