import datetime
import csv
import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from beam_calculations import (
    BeamModel,
    LUMBER_SECTIONS,
    PointLoad,
    STEEL_SECTIONS,
    UniformLoad,
    calculate,
    build_results_table,
    design_from_dict,
    design_to_dict,
    find_lightest_passing,
    normalize_span,
)


class BeamDesignerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Beam Designer")
        file_menu = tk.Menu(self, tearoff=False)
        file_menu.add_command(label="Open...", accelerator="CmdOrCtrl+O",
                              command=self.open_design)
        file_menu.add_command(label="Save...", accelerator="CmdOrCtrl+S",
                              command=self.save_design)
        menu_bar = tk.Menu(self)
        menu_bar.add_cascade(label="File", menu=file_menu)
        self.config(menu=menu_bar)
        self.bind_all("<Control-o>", lambda _event: self.open_design())
        self.bind_all("<Control-s>", lambda _event: self.save_design())
        self.geometry("1180x820")
        self.minsize(760, 600)
        self.configure(bg="#f6f8fb")

        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("TFrame", background="#f6f8fb")
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("Title.TLabel", background="#f6f8fb", foreground="#172033",
                        font=("TkDefaultFont", 16, "bold"))
        style.configure("Section.TLabel", foreground="#667085",
                        font=("TkDefaultFont", 10, "bold"))

        self.support = tk.StringVar(value="simply-supported")
        self.span = tk.DoubleVar(value=20.0)
        self.material = tk.StringVar(value="steel")
        self.section_name = tk.StringVar(value="W12x26")
        self.deflection_limit = tk.IntVar(value=360)
        self.self_weight = tk.BooleanVar(value=False)
        self.point_loads = []
        self.uniform_loads = []
        self._redraw_job = None
        self._resize_job = None
        self._hover_job = None
        self._last_result_signature = None
        self._result_cache = None
        self._recommendation_signature = None
        self._recommendation_cache = None
        self._drag_point_index = None
        self.hover_window = None
        self._span_syncing = False

        self._build_ui()
        self.add_uniform_load(1.0, 0.0, 20.0)
        self.update_section_options()
        self.bind("<Configure>", lambda _event: self.schedule_resize())

    def _build_ui(self):
        header = tk.Frame(self, bg="#ffffff", height=68)
        header.pack(fill="x")
        header.pack_propagate(False)
        brand = tk.Frame(header, bg="#ffffff")
        brand.pack(side="left", padx=28, pady=14)
        tk.Label(brand, text="BD", bg="#2563eb", fg="white",
                 font=("TkDefaultFont", 12, "bold"), width=3, height=1).pack(side="left", padx=(0, 10))
        tk.Label(brand, text="Beam Designer", bg="#ffffff", fg="#172033",
                 font=("TkDefaultFont", 16, "bold")).pack(side="left")
        ttk.Button(header, text="Export Results", command=self.export_results).pack(
            side="right", padx=(0, 8), pady=16
        )
        ttk.Button(header, text="Print / Save PDF", command=self.save_pdf).pack(
            side="right", padx=28, pady=16
        )

        self.layout = tk.PanedWindow(self, orient="horizontal", sashwidth=6,
                                     sashrelief="flat", bg="#dfe6ef")
        self.layout.pack(fill="both", expand=True)

        left_outer = tk.Frame(self.layout, bg="#f6f8fb")
        self.layout.add(left_outer, minsize=290)
        left_canvas = tk.Canvas(left_outer, bg="#f6f8fb", highlightthickness=0)
        left_scroll = ttk.Scrollbar(left_outer, orient="vertical", command=left_canvas.yview)
        left_canvas.configure(yscrollcommand=left_scroll.set)
        left_scroll.pack(side="right", fill="y")
        left_canvas.pack(side="left", fill="both", expand=True)
        left = tk.Frame(left_canvas, bg="#f6f8fb")
        left_window = left_canvas.create_window((0, 0), window=left, anchor="nw")
        left.bind("<Configure>", lambda _e: left_canvas.configure(scrollregion=left_canvas.bbox("all")))
        left_canvas.bind("<Configure>",
                         lambda e: left_canvas.itemconfigure(left_window, width=e.width))

        self._build_input_panel(left)

        right = tk.Frame(self.layout, bg="#f6f8fb")
        self.layout.add(right, minsize=450)
        right_canvas = tk.Canvas(right, bg="#f6f8fb", highlightthickness=0)
        right_scroll = ttk.Scrollbar(right, orient="vertical", command=right_canvas.yview)
        right_canvas.configure(yscrollcommand=right_scroll.set)
        right_scroll.pack(side="right", fill="y")
        right_canvas.pack(side="left", fill="both", expand=True)

        right_content = tk.Frame(right_canvas, bg="#f6f8fb")
        right_window = right_canvas.create_window((0, 0), window=right_content, anchor="nw")
        right_content.bind("<Configure>",
                           lambda _e: right_canvas.configure(scrollregion=right_canvas.bbox("all")))
        right_canvas.bind("<Configure>",
                          lambda e: right_canvas.itemconfigure(right_window, width=e.width))

        self.beam_canvas = self._canvas_card(right_content, "Beam", "Loading diagram", 170)
        self.shear_canvas = self._canvas_card(right_content, "Shear", "kips", 155)
        self.moment_canvas = self._canvas_card(right_content, "Moment", "kip-ft", 155)
        self.deflection_canvas = self._canvas_card(right_content, "Deflection", "in", 155)

        checks = tk.Frame(right_content, bg="#f6f8fb")
        checks.pack(fill="x", padx=14, pady=(0, 10))
        self.bending_card = self._check_card(checks, "Bending")
        self.deflection_card = self._check_card(checks, "Deflection")

        recommendation = tk.Frame(right_content, bg="#ffffff", highlightthickness=1,
                                  highlightbackground="#e2e8f0")
        recommendation.pack(fill="x", padx=14, pady=(0, 14))
        self.recommendation_text = tk.StringVar(value="Calculating...")
        tk.Label(recommendation, textvariable=self.recommendation_text, bg="#ffffff",
                 fg="#667085", anchor="w", justify="left").pack(side="left", padx=14, pady=12)
        ttk.Button(recommendation, text="Use lightest passing",
                   command=self.use_lightest).pack(side="right", padx=14, pady=10)

        for canvas in (self.beam_canvas, self.shear_canvas,
                       self.moment_canvas, self.deflection_canvas):
            canvas.bind("<Motion>", self._hover_diagrams)
            canvas.bind("<Leave>", lambda _e: self._clear_hover())
        self.beam_canvas.bind("<ButtonPress-1>", self._start_point_drag)
        self.beam_canvas.bind("<B1-Motion>", self._drag_point_load)
        self.beam_canvas.bind("<ButtonRelease-1>", self._finish_point_drag)

    def _card(self, parent):
        frame = tk.Frame(parent, bg="#ffffff", highlightthickness=1,
                         highlightbackground="#e2e8f0")
        frame.pack(fill="x", padx=14, pady=(0, 10))
        return frame

    def _canvas_card(self, parent, title, unit, height):
        card = self._card(parent)
        heading = tk.Frame(card, bg="#ffffff")
        heading.pack(fill="x", padx=14, pady=(10, 4))
        tk.Label(heading, text=title, bg="#ffffff", fg="#172033",
                 font=("TkDefaultFont", 12, "bold")).pack(side="left")
        tk.Label(heading, text=unit, bg="#ffffff", fg="#667085").pack(side="right")
        canvas = tk.Canvas(card, height=height, bg="#ffffff", highlightthickness=1,
                           highlightbackground="#dfe6ef")
        canvas.pack(fill="x", padx=14, pady=(0, 10))
        return canvas

    def _check_card(self, parent, title):
        card = tk.Frame(parent, bg="#ffffff", highlightthickness=1,
                        highlightbackground="#e2e8f0")
        card.pack(side="left", fill="both", expand=True, padx=(0 if title == "Bending" else 5, 5))
        tk.Label(card, text=title, bg="#ffffff", fg="#172033",
                 font=("TkDefaultFont", 12, "bold")).pack(anchor="w", padx=14, pady=(10, 2))
        value = tk.StringVar(value="--")
        status = tk.StringVar(value="NOT CALCULATED")
        tk.Label(card, textvariable=value, bg="#ffffff", fg="#172033",
                 font=("TkDefaultFont", 18, "bold")).pack(anchor="w", padx=14)
        status_label = tk.Label(card, textvariable=status, bg="#ffffff", fg="#667085")
        status_label.pack(anchor="w", padx=14, pady=(2, 10))
        card.value = value
        card.status = status
        card.status_label = status_label
        return card

    def _build_input_panel(self, parent):
        setup = self._panel_section(parent, "Beam Setup")
        tk.Label(setup, text="Support type", bg="#ffffff", anchor="w").pack(fill="x")
        support = tk.Frame(setup, bg="#ffffff")
        support.pack(fill="x", pady=(4, 10))
        ttk.Radiobutton(support, text="Simply supported", value="simply-supported",
                        variable=self.support, command=lambda: self.schedule_redraw()).pack(side="left", padx=(0, 12))
        ttk.Radiobutton(support, text="Cantilever", value="cantilever",
                        variable=self.support, command=lambda: self.schedule_redraw()).pack(side="left")

        tk.Label(setup, text="Span (ft)", bg="#ffffff", anchor="w").pack(fill="x")
        span_row = tk.Frame(setup, bg="#ffffff")
        span_row.pack(fill="x", pady=(4, 0))
        self.span_scale = tk.Scale(span_row, from_=4, to=40, resolution=0.25,
                                   orient="horizontal", variable=self.span,
                                   command=self._span_slider_changed,
                                   bg="#ffffff", highlightthickness=0)
        self.span_scale.pack(side="left", fill="x", expand=True)
        self.span_entry = ttk.Entry(span_row, width=8)
        self.span_entry.insert(0, "20")
        self.span_entry.pack(side="right", padx=(8, 0))
        self.span_entry.bind("<KeyRelease>", self._span_entry_changed)
        self.span_entry.bind("<FocusOut>", self._commit_span_entry)
        self.span_entry.bind("<Return>", self._commit_span_entry)

        loads = self._panel_section(parent, "Loads")
        self.load_container = tk.Frame(loads, bg="#ffffff")
        self.load_container.pack(fill="x")
        actions = tk.Frame(loads, bg="#ffffff")
        actions.pack(fill="x", pady=(8, 0))
        ttk.Button(actions, text="+ Add point load",
                   command=lambda: self.add_point_load(1.0, self.span.get() / 2)).pack(side="left")
        ttk.Button(actions, text="+ Add uniform load",
                   command=lambda: self.add_uniform_load(1.0, 0.0, self.span.get())).pack(
                       side="right"
                   )

        section = self._panel_section(parent, "Section")
        tk.Label(section, text="Material", bg="#ffffff", anchor="w").pack(fill="x")
        self.material_combo = ttk.Combobox(section, textvariable=self.material, state="readonly",
                                           values=("steel", "lumber"))
        self.material_combo.pack(fill="x", pady=(4, 10))
        self.material_combo.bind("<<ComboboxSelected>>", self._material_changed)

        tk.Label(section, text="Section", bg="#ffffff", anchor="w").pack(fill="x")
        self.section_combo = ttk.Combobox(section, textvariable=self.section_name, state="readonly")
        self.section_combo.pack(fill="x", pady=(4, 10))
        self.section_combo.bind("<<ComboboxSelected>>", lambda _e: self.schedule_redraw())

        self.self_weight_check = ttk.Checkbutton(
            section, text="Include selected steel beam self-weight",
            variable=self.self_weight, command=lambda: self.schedule_redraw()
        )
        self.self_weight_check.pack(anchor="w")
        self.self_weight_detail = tk.StringVar(value="")
        tk.Label(section, textvariable=self.self_weight_detail, bg="#ffffff",
                 fg="#667085", anchor="w").pack(fill="x", padx=(22, 0))

        limit = self._panel_section(parent, "Deflection Limit")
        ttk.Radiobutton(limit, text="L/240", value=240,
                        variable=self.deflection_limit, command=lambda: self.schedule_redraw()).pack(anchor="w")
        ttk.Radiobutton(limit, text="L/360", value=360,
                        variable=self.deflection_limit, command=lambda: self.schedule_redraw()).pack(anchor="w")

    def _panel_section(self, parent, title):
        frame = tk.Frame(parent, bg="#ffffff", highlightthickness=1,
                         highlightbackground="#e2e8f0")
        frame.pack(fill="x", padx=10, pady=(10, 0))
        tk.Label(frame, text=title.upper(), bg="#ffffff", fg="#667085",
                 font=("TkDefaultFont", 9, "bold")).pack(anchor="w", padx=12, pady=(10, 8))
        content = tk.Frame(frame, bg="#ffffff")
        content.pack(fill="x", padx=12, pady=(0, 12))
        return content

    def _format_span(self, value):
        return f"{value:g}"

    def _sync_span(self, value, source):
        if self._span_syncing:
            return
        self._span_syncing = True
        try:
            span = normalize_span(value)
            self.span.set(span)
            entry_matches = False
            if source == "entry":
                try:
                    entry_matches = float(self.span_entry.get()) == span
                except (TypeError, ValueError):
                    entry_matches = False
            if source != "entry" or not entry_matches:
                self.span_entry.delete(0, "end")
                self.span_entry.insert(0, self._format_span(span))
            self.schedule_redraw(25)
        finally:
            self._span_syncing = False

    def _span_slider_changed(self, value):
        self._sync_span(value, "slider")

    def _span_entry_changed(self, _event):
        text = self.span_entry.get().strip()
        if not text or text.endswith("."):
            return
        try:
            value = float(text)
        except ValueError:
            return
        if value < 4.0:
            return
        self._sync_span(value, "entry")

    def _commit_span_entry(self, _event):
        text = self.span_entry.get().strip()
        try:
            value = float(text)
        except ValueError:
            value = self.span.get()
        self._sync_span(value, "entry")

    def _material_changed(self, _event):
        if self.material.get() == "lumber":
            self.self_weight.set(False)
        self.update_section_options()

    def update_section_options(self):
        if self.material.get() == "steel":
            names = [section["name"] for section in STEEL_SECTIONS]
            if self.section_name.get() not in names:
                self.section_name.set("W12x26")
            self.self_weight_check.configure(state="normal")
        else:
            names = [section["name"] for section in LUMBER_SECTIONS]
            if self.section_name.get() not in names:
                self.section_name.set("2x8")
            self.self_weight_check.configure(state="disabled")
        self.section_combo.configure(values=names)
        self.schedule_redraw()

    def add_point_load(self, magnitude=1.0, position=None):
        if position is None:
            position = self.span.get() / 2
        load = {"magnitude": tk.DoubleVar(value=magnitude),
                "position": tk.DoubleVar(value=min(position, self.span.get()))}
        self.point_loads.append(load)
        self._refresh_load_cards()

    def add_uniform_load(self, magnitude=1.0, start=0.0, end=None):
        if end is None:
            end = self.span.get()
        load = {"magnitude": tk.DoubleVar(value=magnitude),
                "start": tk.DoubleVar(value=start),
                "end": tk.DoubleVar(value=min(end, self.span.get()))}
        self.uniform_loads.append(load)
        self._refresh_load_cards()

    def _refresh_load_cards(self):
        for widget in self.load_container.winfo_children():
            widget.destroy()
        for load in self.point_loads:
            card = tk.Frame(self.load_container, bg="#fbfcfe", highlightthickness=1,
                            highlightbackground="#e2e8f0")
            card.pack(fill="x", pady=(0, 6))
            tk.Label(card, text="Point load", bg="#fbfcfe", fg="#172033",
                     font=("TkDefaultFont", 10, "bold")).grid(row=0, column=0, sticky="w", padx=8, pady=6)
            ttk.Button(card, text="x", width=3,
                       command=lambda item=load: self._remove_load(item, "point")).grid(
                           row=0, column=3, sticky="e", padx=6
                       )
            self._load_entry(card, 1, 0, "Magnitude (kips)", load["magnitude"])
            self._load_entry(card, 1, 1, "Position (ft)", load["position"])
            card.columnconfigure((0, 1, 2, 3), weight=1)
        for load in self.uniform_loads:
            card = tk.Frame(self.load_container, bg="#fbfcfe", highlightthickness=1,
                            highlightbackground="#e2e8f0")
            card.pack(fill="x", pady=(0, 6))
            tk.Label(card, text="Uniform load", bg="#fbfcfe", fg="#172033",
                     font=("TkDefaultFont", 10, "bold")).grid(row=0, column=0, columnspan=2,
                                                               sticky="w", padx=8, pady=6)
            ttk.Button(card, text="x", width=3,
                       command=lambda item=load: self._remove_load(item, "uniform")).grid(
                           row=0, column=2, sticky="e", padx=6
                       )
            self._load_entry(card, 1, 0, "Magnitude (kips/ft)", load["magnitude"])
            self._load_entry(card, 1, 1, "Start (ft)", load["start"])
            self._load_entry(card, 1, 2, "End (ft)", load["end"])
        self.schedule_redraw()

    def _load_entry(self, parent, row, column, label, variable):
        frame = tk.Frame(parent, bg="#fbfcfe")
        frame.grid(row=row, column=column, sticky="ew", padx=6, pady=(0, 8))
        tk.Label(frame, text=label, bg="#fbfcfe", fg="#667085", font=("TkDefaultFont", 9)).pack(anchor="w")
        entry = ttk.Entry(frame, textvariable=variable, width=10)
        entry.pack(fill="x")
        entry.bind("<KeyRelease>", lambda _e: self.schedule_redraw(40))

    def _remove_load(self, load, kind):
        if kind == "point":
            self.point_loads.remove(load)
        else:
            self.uniform_loads.remove(load)
        self._refresh_load_cards()

    def current_model(self):
        span = max(4.0, min(40.0, float(self.span.get())))
        points = [
            PointLoad(max(0.0, float(load["magnitude"].get())),
                      max(0.0, min(span, float(load["position"].get()))))
            for load in self.point_loads
        ]
        uniforms = []
        for load in self.uniform_loads:
            magnitude = max(0.0, float(load["magnitude"].get()))
            start = max(0.0, min(span, float(load["start"].get())))
            end = max(0.0, min(span, float(load["end"].get())))
            if start > end:
                start, end = end, start
            uniforms.append(UniformLoad(magnitude, start, end))
        include = self.material.get() == "steel" and self.self_weight.get()
        return BeamModel(
            support=self.support.get(),
            span_ft=span,
            point_loads=tuple(points),
            uniform_loads=tuple(uniforms),
            material=self.material.get(),
            section_name=self.section_name.get(),
            include_self_weight=include,
            deflection_limit=self.deflection_limit.get(),
        )

    def schedule_redraw(self, delay=35):
        if self._redraw_job is not None:
            self.after_cancel(self._redraw_job)
        self._redraw_job = self.after(delay, self._run_scheduled_redraw)

    def _run_scheduled_redraw(self):
        self._redraw_job = None
        self.redraw()

    def schedule_resize(self, delay=80):
        if self._resize_job is not None:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(delay, self._run_resize_redraw)

    def _run_resize_redraw(self):
        self._resize_job = None
        if hasattr(self, "last_model") and hasattr(self, "last_result"):
            self._draw_beam(self.last_model, self.last_result)
            self._draw_diagram(self.shear_canvas, self.last_model, self.last_result, "shear")
            self._draw_diagram(self.moment_canvas, self.last_model, self.last_result, "moment")
            self._draw_diagram(self.deflection_canvas, self.last_model, self.last_result, "deflection")

    def _model_signature(self, model):
        return (
            model.support,
            model.span_ft,
            tuple((p.magnitude, p.position_ft) for p in model.point_loads),
            tuple((u.magnitude, u.start_ft, u.end_ft) for u in model.uniform_loads),
            model.material,
            model.section_name,
            model.include_self_weight,
            model.deflection_limit,
        )

    def redraw(self):
        try:
            model = self.current_model()
            signature = self._model_signature(model)
            if signature == self._last_result_signature:
                result = self._result_cache
            else:
                result = calculate(model)
                self._last_result_signature = signature
                self._result_cache = result
        except (ValueError, tk.TclError):
            return
        self.last_model = model
        self.last_result = result
        self._draw_beam(model, result)
        self._draw_diagram(self.shear_canvas, model, result, "shear")
        self._draw_diagram(self.moment_canvas, model, result, "moment")
        self._draw_diagram(self.deflection_canvas, model, result, "deflection")
        self._update_checks(result)
        self._update_recommendation(model)
        if model.material == "steel":
            section = next(s for s in STEEL_SECTIONS if s["name"] == model.section_name)
            self.self_weight_detail.set(f"{section['name']}: {section['weight'] / 1000:.3f} kips/ft"
                                        if model.include_self_weight else "")
        else:
            self.self_weight_detail.set("")

    def _plot_geometry(self, canvas):
        width = max(400, canvas.winfo_width())
        height = max(120, canvas.winfo_height())
        return 50, width - 30, 0, height

    def _draw_beam(self, model, result):
        canvas = self.beam_canvas
        canvas.delete("all")
        width = max(400, canvas.winfo_width())
        height = max(120, canvas.winfo_height())
        left, right = 50, width - 30
        y = height * 0.48
        canvas.create_line(left, y, right, y, width=7, fill="#334155")
        span = model.span_ft

        def px(ft):
            return left + (ft / span) * (right - left)

        if model.support == "simply-supported":
            canvas.create_polygon(left - 18, y + 18, left + 18, y + 18, left, y, fill="#94a3b8")
            canvas.create_polygon(right - 18, y + 18, right + 18, y + 18, right, y, fill="#94a3b8")
        else:
            canvas.create_rectangle(left - 18, y - 38, left, y + 38, fill="#94a3b8", outline="")

        for load in model.point_loads:
            x = px(load.position_ft)
            canvas.create_line(x, y - 75, x, y - 8, arrow="last", width=2,
                               fill="#2563eb")
            canvas.create_text(x, y - 84, text=f"{load.magnitude:.2f} k",
                               fill="#2563eb", font=("TkDefaultFont", 9, "bold"))

        for load in model.uniform_loads:
            start, end = px(load.start_ft), px(load.end_ft)
            count = max(3, min(20, int(abs(end - start) / 28)))
            for i in range(count + 1):
                x = start + (end - start) * i / count
                canvas.create_line(x, y - 55, x, y - 8, arrow="last", width=1,
                                   fill="#2563eb")
            canvas.create_text((start + end) / 2, y - 64,
                               text=f"{load.magnitude:.3f} k/ft",
                               fill="#2563eb", font=("TkDefaultFont", 9, "bold"))
        if model.include_self_weight and model.material == "steel":
            section = next(s for s in STEEL_SECTIONS if s["name"] == model.section_name)
            w = section["weight"] / 1000
            count = 20
            for i in range(count + 1):
                x = left + (right - left) * i / count
                canvas.create_line(x, y - 55, x, y - 8, arrow="last", width=1,
                                   fill="#2563eb")
            canvas.create_text((left + right) / 2, y + 62,
                               text=f"Self-weight: {w:.3f} kips/ft",
                               fill="#475569", font=("TkDefaultFont", 9))

        canvas.create_text(left, height - 18, text="0 ft", fill="#667085")
        canvas.create_text(right, height - 18, text=f"{span:.2f} ft", fill="#667085")
        if model.support == "simply-supported":
            canvas.create_text(left, y + 42,
                               text=f"R_L {result['reactions']['left']:.2f} k",
                               fill="#166534", font=("TkDefaultFont", 9, "bold"))
            canvas.create_text(right, y + 42,
                               text=f"R_R {result['reactions']['right']:.2f} k",
                               fill="#166534", font=("TkDefaultFont", 9, "bold"))
        else:
            canvas.create_text(left, y + 42,
                               text=f"R {result['reactions']['left']:.2f} k",
                               fill="#166534", font=("TkDefaultFont", 9, "bold"))
            canvas.create_text(left + 100, y + 42,
                               text=f"M_fixed {result['reactions']['moment'] / 12:.2f} kip-ft",
                               fill="#166534", font=("TkDefaultFont", 9, "bold"))

    def _draw_diagram(self, canvas, model, result, kind):
        canvas.delete("all")
        width = max(400, canvas.winfo_width())
        height = max(120, canvas.winfo_height())
        left, right = 50, width - 30
        baseline = height * 0.58
        span = model.span_ft

        def px(ft):
            return left + ft / span * (right - left)

        if kind == "shear":
            xs = [i * model.span_ft / 240 for i in range(241)]
            values = [result["shear"]["at"](x * 12) for x in xs]
            scale = max(1.0, max(abs(v) for v in values))
            get_y = lambda v: baseline - v / scale * (height * 0.38)
            label = "kips"
        elif kind == "moment":
            xs = [i * model.span_ft / 240 for i in range(241)]
            values = [result["moment"]["at"](x * 12) / 12 for x in xs]
            scale = max(1.0, max(abs(v) for v in values))
            get_y = lambda v: baseline - v / scale * (height * 0.38)
            label = "kip-ft"
        else:
            xs = [i * model.span_ft / 240 for i in range(241)]
            values = [result["deflection"]["at"](x * 12) for x in xs]
            scale = max(0.001, max(abs(v) for v in values))
            get_y = lambda v: baseline - v / scale * (height * 0.38)
            label = "in"

        canvas.create_line(left, baseline, right, baseline, fill="#cbd5e1")
        points = [(px(ft), get_y(value)) for ft, value in zip(xs, values)]
        if kind == "moment":
            fill = "#2563eb"
            canvas.create_line([(p[0], p[1]) for p in points], fill=fill, width=2)
        else:
            canvas.create_line([(p[0], p[1]) for p in points], fill="#2563eb", width=2)
        canvas.create_line(left, 8, left, height - 8, fill="#f1f5f9")
        canvas.create_line(right, 8, right, height - 8, fill="#f1f5f9")

        if kind == "shear":
            extreme = result["shear"]["max"]
            loc = result["shear"]["location"] / 12
        elif kind == "moment":
            extreme = result["moment"]["max"] / 12
            loc = result["moment"]["location"] / 12
        else:
            extreme = result["deflection"]["max"]
            loc = result["deflection"]["location"] / 12
        canvas.create_text(left + 8, 12, anchor="nw",
                           text=f"max |value| {extreme:.3f} {label} at {loc:.2f} ft",
                           fill="#1d4ed8", font=("TkDefaultFont", 9, "bold"))
        canvas.create_text(left, height - 12, anchor="sw", text="0 ft", fill="#667085")
        canvas.create_text(right, height - 12, anchor="se", text=f"{span:.2f} ft", fill="#667085")

    def _update_checks(self, result):
        bending = result["bending"]
        bending_ratio = bending["actual"] / bending["allowable"]
        self.bending_card.value.set(f"{bending['actual']:.2f} ksi")
        self._set_status(self.bending_card, bending["pass"], bending_ratio)

        deflection = result["deflection_check"]
        deflection_ratio = deflection["actual"] / deflection["allowable"]
        self.deflection_card.value.set(f"{deflection['actual']:.3f} in")
        self._set_status(self.deflection_card, deflection["pass"], deflection_ratio)

    def _set_status(self, card, passed, ratio):
        card.status.set("PASS" if passed else "FAIL")
        card.status_label.configure(fg="#166534" if passed else "#b91c1c")

    def _start_point_drag(self, event):
        if not hasattr(self, "last_model") or not self.last_model.point_loads:
            return
        width = max(400, self.beam_canvas.winfo_width())
        left, right = 50, width - 30
        span = self.last_model.span_ft
        nearest_index = None
        nearest_distance = 24.0
        for index, load in enumerate(self.last_model.point_loads):
            load_x = left + load.position_ft / span * (right - left)
            distance = abs(event.x - load_x)
            if distance < nearest_distance:
                nearest_distance = distance
                nearest_index = index
        self._drag_point_index = nearest_index

    def _drag_point_load(self, event):
        if self._drag_point_index is None or not hasattr(self, "last_model"):
            return
        width = max(400, self.beam_canvas.winfo_width())
        left, right = 50, width - 30
        span = self.last_model.span_ft
        fraction = max(0.0, min(1.0, (event.x - left) / (right - left)))
        position = round(fraction * span * 4.0) / 4.0
        if self._drag_point_index < len(self.point_loads):
            self.point_loads[self._drag_point_index]["position"].set(position)
            self.schedule_redraw(20)

    def _finish_point_drag(self, _event):
        self._drag_point_index = None
        if self._redraw_job is not None:
            self.after_cancel(self._redraw_job)
        self._redraw_job = None
        self.redraw()

    def _update_recommendation(self, model):
        signature = (
            model.support,
            model.span_ft,
            tuple((p.magnitude, p.position_ft) for p in model.point_loads),
            tuple((u.magnitude, u.start_ft, u.end_ft) for u in model.uniform_loads),
            model.material,
            model.include_self_weight,
            model.deflection_limit,
        )
        if signature == self._recommendation_signature:
            recommended = self._recommendation_cache
        else:
            recommended = find_lightest_passing(model)
            self._recommendation_signature = signature
            self._recommendation_cache = recommended
        if recommended:
            self.recommendation_text.set(
                f"Lightest passing section: {recommended['name']} "
                f"(use to select this section)"
            )
            self.recommended_section = recommended["name"]
        else:
            self.recommendation_text.set("No section passes both bending and deflection checks.")
            self.recommended_section = None

    def use_lightest(self):
        if hasattr(self, "recommended_section") and self.recommended_section:
            self.section_name.set(self.recommended_section)
            self.redraw()

    def _hover_diagrams(self, event):
        if not hasattr(self, "last_model"):
            return
        if self._hover_job is not None:
            self.after_cancel(self._hover_job)

        def update_hover():
            self._hover_job = None
            canvas = event.widget
            width = max(400, canvas.winfo_width())
            left, right = 50, width - 30
            ft = max(0.0, min(self.last_model.span_ft,
                              (event.x - left) / (right - left) * self.last_model.span_ft))
            x_in = ft * 12
            shear = self.last_result["shear"]["at"](x_in)
            moment = self.last_result["moment"]["at"](x_in) / 12
            deflection = self.last_result["deflection"]["at"](x_in)
            for target in (self.shear_canvas, self.moment_canvas, self.deflection_canvas):
                target.delete("hover")
                tx = left + ft / self.last_model.span_ft * (right - left)
                target.create_line(tx, 8, tx, target.winfo_height() - 8,
                                   fill="#94a3b8", dash=(3, 3), tags=("hover",))
            if self.hover_window is None or not self.hover_window.winfo_exists():
                self.hover_window = tk.Toplevel(self)
                self.hover_window.overrideredirect(True)
                self.hover_window.configure(bg="#ffffff")
                self.hover_label = tk.Label(
                    self.hover_window, bg="#ffffff", fg="#172033", justify="left",
                    relief="solid", borderwidth=1, font=("TkDefaultFont", 9)
                )
                self.hover_label.pack(padx=1, pady=1)
            self.hover_label.configure(
                text=f"{ft:.2f} ft\nV {shear:.2f} k\nM {moment:.2f} kip-ft\ny {deflection:.3f} in"
            )
            self.hover_window.geometry(f"+{event.x_root + 12}+{event.y_root + 12}")

        self._hover_job = self.after(20, update_hover)

    def _clear_hover(self):
        if self._hover_job is not None:
            self.after_cancel(self._hover_job)
            self._hover_job = None
        if self.hover_window is not None and self.hover_window.winfo_exists():
            self.hover_window.destroy()
            self.hover_window = None

    def export_results(self):
        if not hasattr(self, "last_model") or not hasattr(self, "last_result"):
            self.redraw()
        path = filedialog.asksaveasfilename(
            title="Export Beam Results",
            defaultextension=".csv",
            filetypes=[("CSV spreadsheet", "*.csv"), ("All files", "*.*")],
            initialfile="beam-results.csv",
        )
        if not path:
            return
        try:
            rows = build_results_table(self.last_model, self.last_result)
            columns = [
                "Position x (ft)",
                "Shear V (kips)",
                "Moment M (kip-ft)",
                "Deflection (in)",
            ]
            with open(path, "w", encoding="utf-8-sig", newline="") as output:
                writer = csv.writer(output, lineterminator="\r\n")
                writer.writerow(columns)
                for row in rows:
                    writer.writerow([
                        f"{row['Position x (ft)']:.4f}",
                        f"{row['Shear V (kips)']:.12g}",
                        f"{row['Moment M (kip-ft)']:.12g}",
                        f"{row['Deflection (in)']:.12g}",
                    ])
        except (OSError, ValueError, tk.TclError) as exc:
            messagebox.showerror("Could Not Export Results",
                                 f"The results could not be exported:\n{exc}")
            return
        messagebox.showinfo("Results Exported", f"Exported results to:\n{path}")

    def save_design(self):
        path = filedialog.asksaveasfilename(
            title="Save Beam Design",
            defaultextension=".json",
            filetypes=[("Beam design JSON", "*.json"), ("All files", "*.*")],
            initialfile="beam-design.json",
        )
        if not path:
            return
        try:
            model = self.current_model()
            design = design_to_dict(model)
            with open(path, "w", encoding="utf-8") as output:
                json.dump(design, output, indent=2)
                output.write("\n")
        except (OSError, ValueError, tk.TclError) as exc:
            messagebox.showerror("Could Not Save Design",
                                 f"The design could not be saved:\n{exc}")
            return
        messagebox.showinfo("Design Saved", f"Saved design to:\n{path}")

    def open_design(self):
        path = filedialog.askopenfilename(
            title="Open Beam Design",
            filetypes=[("Beam design JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as source:
                data = json.load(source)
            model = design_from_dict(data)
        except json.JSONDecodeError as exc:
            messagebox.showerror("Invalid Design File",
                                 f"The file is not valid JSON:\n{exc}")
            return
        except (OSError, UnicodeDecodeError, ValueError, TypeError) as exc:
            messagebox.showerror("Invalid Design File",
                                 f"The design file could not be opened:\n{exc}")
            return

        self.support.set(model.support)
        self._sync_span(model.span_ft, "open")
        self.material.set(model.material)
        self.section_name.set(model.section_name)
        self.deflection_limit.set(model.deflection_limit)
        self.self_weight.set(
            model.include_self_weight if model.material == "steel" else False
        )
        self.point_loads = [
            {
                "magnitude": tk.DoubleVar(value=load.magnitude),
                "position": tk.DoubleVar(value=load.position_ft),
            }
            for load in model.point_loads
        ]
        self.uniform_loads = [
            {
                "magnitude": tk.DoubleVar(value=load.magnitude),
                "start": tk.DoubleVar(value=load.start_ft),
                "end": tk.DoubleVar(value=load.end_ft),
            }
            for load in model.uniform_loads
        ]
        self.update_section_options()
        self._refresh_load_cards()
        self.schedule_redraw(10)

    def save_pdf(self):
        if not hasattr(self, "last_model"):
            self.redraw()
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF report", "*.pdf")],
            initialfile="beam-report.pdf",
        )
        if not path:
            return
        try:
            self.write_pdf(path)
            messagebox.showinfo("Report saved", f"Saved report to:\n{path}")
        except Exception as exc:
            messagebox.showerror("Report error", str(exc))

    def write_pdf(self, path):
        model = self.last_model
        result = self.last_result
        section = result["section"]
        point_text = "\n".join(
            f"  Point: {load.magnitude:.2f} k at {load.position_ft:.2f} ft"
            for load in model.point_loads
        ) or "  Point loads: None"
        uniform_text = "\n".join(
            f"  Uniform: {load.magnitude:.3f} k/ft, {load.start_ft:.2f} to {load.end_ft:.2f} ft"
            for load in model.uniform_loads
        ) or "  Uniform loads: None"
        self_weight_text = "OFF"
        if model.include_self_weight:
            self_weight_text = (
                f"ON - {section['weight'] / 1000:.3f} kips/ft"
            )

        def escape(text):
            return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

        def text(x, y, value, font="F2", size=8, rgb="0.10 0.14 0.20"):
            commands.append(
                f"BT /{font} {size} Tf {rgb} rg 1 0 0 1 {x:.1f} {y:.1f} Tm "
                f"({escape(value)}) Tj ET"
            )

        def rect(x, y, width, height, fill="1 1 1", stroke="0.78 0.82 0.86"):
            commands.append(
                f"{fill} rg {stroke} RG {x:.1f} {y:.1f} {width:.1f} {height:.1f} re B"
            )

        def line(x1, y1, x2, y2, width=1, rgb="0.50 0.56 0.63"):
            commands.append(
                f"{rgb} RG {width:.1f} w {x1:.1f} {y1:.1f} m "
                f"{x2:.1f} {y2:.1f} l S"
            )

        commands = []
        rect(36, 748, 540, 26, "0.12 0.31 0.70", "0.12 0.31 0.70")
        text(48, 756, "BEAM DESIGNER - ENGINEERING CALCULATION SHEET",
             "F1", 13, "1 1 1")
        text(500, 756, datetime.datetime.now().strftime("%Y-%m-%d"),
             "F2", 8, "1 1 1")

        rect(36, 690, 264, 48)
        rect(312, 690, 264, 48)
        text(48, 724, "BEAM INPUTS", "F1", 9, "0.12 0.31 0.70")
        support_name = "Simply supported" if model.support == "simply-supported" else "Cantilever"
        text(48, 708, f"Support: {support_name}", "F2", 8)
        text(48, 696, f"Span: {model.span_ft:.2f} ft    Limit: L/{model.deflection_limit}",
             "F2", 8)
        text(324, 724, "SECTION PROPERTIES", "F1", 9, "0.12 0.31 0.70")
        text(324, 708, f"{model.material.title()} - {model.section_name}", "F2", 8)
        text(324, 696,
             f"Ix: {section['Ix']:.2f} in^4   Sx: {section['Sx']:.2f} in^3",
             "F2", 8)

        rect(36, 640, 540, 38)
        text(48, 664, "APPLIED LOADS", "F1", 9, "0.12 0.31 0.70")
        point_lines = point_text.split("\n")
        uniform_lines = uniform_text.split("\n")
        text(48, 650, point_lines[0], "F2", 7)
        if len(point_lines) > 1:
            text(48, 642, point_lines[1], "F2", 7)
        text(324, 650, uniform_lines[0], "F2", 7)
        if len(uniform_lines) > 1:
            text(324, 642, uniform_lines[1], "F2", 7)
        text(324, 658, f"Self-weight: {self_weight_text}", "F2", 7)

        # Beam loading diagram
        rect(36, 548, 540, 78)
        text(48, 614, "BEAM LOADING DIAGRAM", "F1", 9, "0.12 0.31 0.70")
        left, right, beam_y = 72, 540, 575
        line(left, beam_y, right, beam_y, 5, "0.20 0.25 0.31")
        if model.support == "simply-supported":
            commands.append(
                f"0.58 0.64 0.72 rg {left-12:.1f} {beam_y-12:.1f} m "
                f"{left+12:.1f} {beam_y-12:.1f} l {left:.1f} {beam_y:.1f} l h f"
            )
            commands.append(
                f"0.58 0.64 0.72 rg {right-12:.1f} {beam_y-12:.1f} m "
                f"{right+12:.1f} {beam_y-12:.1f} l {right:.1f} {beam_y:.1f} l h f"
            )
        else:
            rect(left-10, beam_y-28, 10, 56, "0.58 0.64 0.72", "0.58 0.64 0.72")

        def px(ft):
            return left + (ft / model.span_ft) * (right - left)

        for load in model.point_loads:
            x = px(load.position_ft)
            line(x, beam_y + 35, x, beam_y + 5, 1.2, "0.12 0.31 0.70")
            commands.append(
                f"0.12 0.31 0.70 RG 1.2 w {x:.1f} {beam_y+5:.1f} m "
                f"{x-4:.1f} {beam_y+11:.1f} l {x+4:.1f} {beam_y+11:.1f} l h f"
            )
            text(x-16, beam_y + 39, f"{load.magnitude:.2f} k", "F2", 6)
        for load in model.uniform_loads:
            a, b = px(load.start_ft), px(load.end_ft)
            count = max(3, min(14, int(abs(b-a)/24)))
            for i in range(count + 1):
                x = a + (b-a)*i/count
                line(x, beam_y+28, x, beam_y+5, 0.8, "0.12 0.31 0.70")
            text((a+b)/2-20, beam_y+31, f"{load.magnitude:.2f} k/ft", "F2", 6)
        text(left-5, beam_y-38, "0 ft", "F2", 7)
        text(right-24, beam_y-38, f"{model.span_ft:.2f} ft", "F2", 7)

        if model.support == "simply-supported":
            text(left-4, beam_y-25, f"RL {result['reactions']['left']:.2f} k", "F1", 7)
            text(right-40, beam_y-25, f"RR {result['reactions']['right']:.2f} k", "F1", 7)
        else:
            text(left-4, beam_y-25, f"R {result['reactions']['left']:.2f} k", "F1", 7)
            text(left+58, beam_y-25,
                 f"Mfix {result['reactions']['moment']/12:.2f} kip-ft", "F1", 7)

        def diagram(title, y, kind):
            rect(36, y-6, 540, 66)
            text(48, y+48, title, "F1", 9, "0.12 0.31 0.70")
            base = y+20
            dleft, dright = 72, 540
            line(dleft, base, dright, base, 0.7, "0.75 0.79 0.84")

            xs = [i*model.span_ft/160 for i in range(161)]
            if kind == "shear":
                values = [result["shear"]["at"](x*12) for x in xs]
                scale = max(1.0, max(abs(v) for v in values))
                unit = "kips"
            elif kind == "moment":
                values = [result["moment"]["at"](x*12)/12 for x in xs]
                scale = max(1.0, max(abs(v) for v in values))
                unit = "kip-ft"
            else:
                values = [result["deflection"]["at"](x*12) for x in xs]
                scale = max(0.001, max(abs(v) for v in values))
                unit = "in"

            for i in range(len(xs)-1):
                x1 = dleft + xs[i]/model.span_ft*(dright-dleft)
                x2 = dleft + xs[i+1]/model.span_ft*(dright-dleft)
                y1 = base - values[i]/scale*28
                y2 = base - values[i+1]/scale*28
                line(x1, y1, x2, y2, 1.2, "0.12 0.31 0.70")
            text(dleft, y+48, unit, "F2", 6)

        diagram("SHEAR DIAGRAM", 482, "shear")
        diagram("MOMENT DIAGRAM", 404, "moment")
        diagram("DEFLECTION DIAGRAM", 326, "deflection")

        rect(36, 242, 264, 66)
        rect(312, 242, 264, 66)
        bending_ratio = result["bending"]["actual"]/result["bending"]["allowable"]
        deflection_ratio = (
            result["deflection_check"]["actual"]/result["deflection_check"]["allowable"]
        )
        text(48, 294, "BENDING CHECK", "F1", 9, "0.12 0.31 0.70")
        text(48, 278,
             f"Actual: {result['bending']['actual']:.2f} ksi",
             "F2", 8)
        text(48, 266,
             f"Allowable: {result['bending']['allowable']:.2f} ksi",
             "F2", 8)
        text(48, 254,
             f"Utilization: {bending_ratio*100:.1f}%   "
             f"{'PASS' if result['bending']['pass'] else 'FAIL'}",
             "F1", 8)
        text(324, 294, "DEFLECTION CHECK", "F1", 9, "0.12 0.31 0.70")
        text(324, 278,
             f"Actual: {result['deflection_check']['actual']:.3f} in",
             "F2", 8)
        text(324, 266,
             f"Allowable: {result['deflection_check']['allowable']:.3f} in",
             "F2", 8)
        text(324, 254,
             f"Utilization: {deflection_ratio*100:.1f}%   "
             f"{'PASS' if result['deflection_check']['pass'] else 'FAIL'}",
             "F1", 8)

        rect(36, 174, 540, 54)
        text(48, 212, "MAXIMUM CALCULATED VALUES", "F1", 9, "0.12 0.31 0.70")
        text(48, 196,
             f"Shear: {result['shear']['max']:.2f} k at "
             f"{result['shear']['location']/12:.2f} ft",
             "F2", 8)
        text(210, 196,
             f"Moment: {result['moment']['max']/12:.2f} kip-ft at "
             f"{result['moment']['location']/12:.2f} ft",
             "F2", 8)
        text(390, 196,
             f"Deflection: {result['deflection']['max']:.3f} in at "
             f"{result['deflection']['location']/12:.2f} ft",
             "F2", 8)
        recommendation = getattr(self, "recommended_section", None)
        text(48, 182,
             f"Lightest passing section: {recommendation or 'No section passes'}",
             "F1", 8)

        rect(36, 72, 540, 88)
        text(48, 142, "LOADS AND REACTION SUMMARY", "F1", 9, "0.12 0.31 0.70")
        for index, line_value in enumerate(point_text.split("\n")[:3]):
            text(48, 126-index*10, line_value, "F2", 7)
        for index, line_value in enumerate(uniform_text.split("\n")[:3]):
            text(324, 126-index*10, line_value, "F2", 7)
        text(48, 84,
             f"Reactions: Left {result['reactions']['left']:.2f} k"
             f"   Right {result['reactions']['right']:.2f} k"
             f"   Fixed moment {result['reactions']['moment']/12:.2f} kip-ft",
             "F2", 7)

        line(36, 58, 576, 58, 0.7, "0.40 0.46 0.53")
        text(36, 42,
             "Educational use only. Verify calculations with a qualified engineer.",
             "F1", 7, "0.40 0.46 0.53")

        stream = ("\n".join(commands) + "\n").encode("latin-1", "replace")

        objects = []
        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
        objects.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                       b"/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>")
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode("ascii") +
                       stream + b"endstream")

        pdf = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for number, obj in enumerate(objects, start=1):
            offsets.append(len(pdf))
            pdf.extend(f"{number} 0 obj\n".encode("ascii"))
            pdf.extend(obj)
            pdf.extend(b"\nendobj\n")
        xref = len(pdf)
        pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        pdf.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
        pdf.extend(
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n".encode("ascii")
        )
        with open(path, "wb") as output:
            output.write(pdf)


if __name__ == "__main__":
    app = BeamDesignerApp()
    app.mainloop()
