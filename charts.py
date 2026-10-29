"""
charts.py - Biểu đồ đường vẽ bằng Canvas cho CPU và RAM.
PC Monitor Mini v1.1.0 - Sử dụng standard tkinter.Canvas trong CTkFrame.
"""

from datetime import datetime
import tkinter as tk
import customtkinter as ctk

CHART_PALETTES = {
    "Light": {
        "bg": "#FFFFFF",
        "grid": "#E8ECF2",
        "axis_text": "#556278",
        "cpu_line": "#2563EB",
        "cpu_fill": "#EFF6FF",
        "ram_line": "#8B5CF6",
        "ram_fill": "#F5F3FF",
        "dot_border": "#FFFFFF",
    },
    "Dark": {
        "bg": "#131F32",
        "grid": "#26344C",
        "axis_text": "#A5B4CC",
        "cpu_line": "#3B82F6",
        "cpu_fill": "#172A46",
        "ram_line": "#A78BFA",
        "ram_fill": "#241E3D",
        "dot_border": "#131F32",
    },
}


class ResourceChartsFrame(ctk.CTkFrame):
    """Khung chứa hai biểu đồ lịch sử tài nguyên CPU và RAM."""

    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            fg_color=("#FFFFFF", "#131F32"),
            corner_radius=16,
            border_width=1,
            border_color=("#E8ECF2", "#26344C"),
            **kwargs,
        )
        self.points = []
        self.theme = "Light"

        # Thanh tiêu đề trên của khung biểu đồ
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=16, pady=(10, 4))

        title_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        title_box.pack(side="left")

        ctk.CTkLabel(
            title_box,
            text="Lịch sử tài nguyên",
            font=("Segoe UI", 13, "bold"),
            text_color=("#182133", "#E8EEFB"),
        ).pack(side="left", padx=(0, 8))

        self.lbl_samples = ctk.CTkLabel(
            title_box,
            text="0 mẫu",
            font=("Segoe UI", 11),
            text_color=("#556278", "#A5B4CC"),
            fg_color=("#F1F5F9", "#1A273D"),
            corner_radius=8,
            padx=8,
            pady=2,
        )
        self.lbl_samples.pack(side="left")

        # Chú thích (Legend)
        legend_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        legend_box.pack(side="right")

        ctk.CTkFrame(legend_box, width=10, height=10, corner_radius=3, fg_color=("#2563EB", "#3B82F6")).pack(side="left", padx=(0, 4))
        ctk.CTkLabel(legend_box, text="CPU (%)", font=("Segoe UI", 11), text_color=("#556278", "#A5B4CC")).pack(side="left", padx=(0, 12))

        ctk.CTkFrame(legend_box, width=10, height=10, corner_radius=3, fg_color=("#8B5CF6", "#A78BFA")).pack(side="left", padx=(0, 4))
        ctk.CTkLabel(legend_box, text="RAM (%)", font=("Segoe UI", 11), text_color=("#556278", "#A5B4CC")).pack(side="left")

        # Khung chứa 2 Canvas trực tiếp (DIRECT tk.Canvas instances)
        grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        grid_frame.columnconfigure(0, weight=1, uniform="chart")
        grid_frame.columnconfigure(1, weight=1, uniform="chart")
        grid_frame.rowconfigure(0, weight=1)

        pal = CHART_PALETTES["Light"]
        self.canvas_cpu = tk.Canvas(grid_frame, bg=pal["bg"], highlightthickness=0, bd=0)
        self.canvas_cpu.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.canvas_cpu.bind("<Configure>", lambda _e: self._redraw_canvas(self.canvas_cpu, "cpu_percent", "cpu_line", "cpu_fill", "Biểu đồ CPU (%)"))

        self.canvas_ram = tk.Canvas(grid_frame, bg=pal["bg"], highlightthickness=0, bd=0)
        self.canvas_ram.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self.canvas_ram.bind("<Configure>", lambda _e: self._redraw_canvas(self.canvas_ram, "memory_percent", "ram_line", "ram_fill", "Biểu đồ RAM (%)"))

    def set_points(self, points):
        """Cập nhật danh sách điểm mẫu và vẽ lại hai biểu đồ."""
        self.points = points or []
        count = len(self.points)
        if count == 0:
            self.lbl_samples.configure(text="Đang thu thập dữ liệu…")
        elif count >= 60:
            self.lbl_samples.configure(text="60 mẫu gần nhất")
        else:
            self.lbl_samples.configure(text=f"{count} / 60 mẫu")

        self.redraw()

    def set_theme(self, mode):
        """Đổi màu chủ đề Sáng / Tối và vẽ lại biểu đồ."""
        self.theme = "Dark" if str(mode).lower() in ("dark", "tối") else "Light"
        pal = CHART_PALETTES.get(self.theme, CHART_PALETTES["Light"])
        self.canvas_cpu.configure(bg=pal["bg"])
        self.canvas_ram.configure(bg=pal["bg"])
        self.redraw()

    def redraw(self):
        """Vẽ lại cả 2 Canvas."""
        self._redraw_canvas(self.canvas_cpu, "cpu_percent", "cpu_line", "cpu_fill", "Biểu đồ CPU (%)")
        self._redraw_canvas(self.canvas_ram, "memory_percent", "ram_line", "ram_fill", "Biểu đồ RAM (%)")

    def _redraw_canvas(self, canvas, metric_key, line_key, fill_key, title):
        canvas.delete("all")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 50 or h < 50:
            return

        pal = CHART_PALETTES.get(self.theme, CHART_PALETTES["Light"])
        bg_col = pal["bg"]
        grid_col = pal["grid"]
        axis_col = pal["axis_text"]
        line_col = pal[line_key]
        fill_col = pal[fill_key]
        dot_border = pal["dot_border"]

        canvas.configure(bg=bg_col)

        left = 40
        right = 20
        top = 22
        bottom = 20
        plot_w = w - left - right
        plot_h = h - top - bottom

        if plot_w <= 0 or plot_h <= 0:
            return

        font_axis = ("Segoe UI", 8)
        font_title = ("Segoe UI", 9, "bold")

        # Tiêu đề biểu đồ
        canvas.create_text(left, 10, text=title, anchor="w", fill=line_col, font=font_title)

        # 3 đường lưới ngang: 100%, 50%, 0%
        for pct, txt in ((100.0, "100%"), (50.0, "50%"), (0.0, "0%")):
            y = top + plot_h * (1.0 - (pct / 100.0))
            canvas.create_line(left, y, w - right, y, fill=grid_col, width=1)
            canvas.create_text(left - 6, y, text=txt, anchor="e", fill=axis_col, font=font_axis)

        # Trạng thái rỗng: không có oval hay polygon
        if not self.points:
            canvas.create_text(
                left + plot_w / 2,
                top + plot_h / 2,
                text="Đang thu thập dữ liệu…",
                fill=axis_col,
                font=("Segoe UI", 11),
            )
            return

        # Chỉ có 1 mẫu: vẽ đúng 1 chấm tròn oval
        if len(self.points) == 1:
            pt = self.points[0]
            val = max(0.0, min(100.0, float(pt[metric_key])))
            cx = left + plot_w / 2
            cy = top + plot_h * (1.0 - (val / 100.0))
            r = 5
            canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=line_col, outline=dot_border, width=2)
            canvas.create_text(cx, cy - 12, text=f"{val:.1f}%", fill=line_col, font=("Segoe UI", 9, "bold"), anchor="center")
            t_str = datetime.fromtimestamp(pt["timestamp"]).strftime("%H:%M:%S")
            canvas.create_text(cx, h - 8, text=t_str, anchor="center", fill=axis_col, font=font_axis)
            return

        # Từ 2 mẫu trở lên
        t_start = self.points[0]["timestamp"]
        t_end = self.points[-1]["timestamp"]
        t_span = t_end - t_start
        if t_span <= 0:
            t_span = 1.0

        coords = []
        for pt in self.points:
            t = pt["timestamp"]
            val = max(0.0, min(100.0, float(pt[metric_key])))
            x = left + plot_w * ((t - t_start) / t_span)
            y = top + plot_h * (1.0 - (val / 100.0))
            coords.append((x, y))

        # Tô màu vùng dưới đường biểu đồ
        y_zero = top + plot_h
        poly = [coords[0][0], y_zero]
        for x, y in coords:
            poly.extend([x, y])
        poly.extend([coords[-1][0], y_zero])
        canvas.create_polygon(poly, fill=fill_col, outline="")

        # Vẽ đường nối các điểm (1 series line)
        flat_coords = []
        for x, y in coords:
            flat_coords.extend([x, y])
        canvas.create_line(flat_coords, fill=line_col, width=2, capstyle="round", joinstyle="round")

        # Điểm tròn nổi bật giá trị mới nhất
        last_x, last_y = coords[-1]
        canvas.create_oval(last_x - 4, last_y - 4, last_x + 4, last_y + 4, fill=line_col, outline=dot_border, width=2)
        last_val = self.points[-1][metric_key]
        # Neo chữ về góc phải của điểm để luôn nằm trong giới hạn canvas
        canvas.create_text(last_x, last_y - 10, text=f"{last_val:.1f}%", fill=line_col, font=("Segoe UI", 8, "bold"), anchor="e")

        # Nhãn thời gian trục hoành
        str_start = datetime.fromtimestamp(t_start).strftime("%H:%M:%S")
        str_end = datetime.fromtimestamp(t_end).strftime("%H:%M:%S")
        canvas.create_text(left, h - 8, text=str_start, anchor="w", fill=axis_col, font=font_axis)
        canvas.create_text(w - right, h - 8, text=str_end, anchor="e", fill=axis_col, font=font_axis)

        elapsed = int(round(t_span))
        if elapsed > 0:
            canvas.create_text(left + plot_w / 2, h - 8, text=f"{elapsed}s gần nhất", anchor="center", fill=axis_col, font=font_axis)
