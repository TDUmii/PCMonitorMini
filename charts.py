"""
charts.py - Biểu đồ đường Canvas hiệu năng cao cho CPU và RAM.
Thiết kế theo phong cách Dashboard Công Nghệ (Tech Dashboard):
- CPU: Cyan sáng rực rỡ (#0284C7 Light / #22D3EE Dark).
- RAM: Violet nổi bật (#7C3AED Light / #C084FC Dark).
- Nền Navy sâu thẳm, lưới tọa độ kỹ thuật sắc nét, hiển thị chính xác 60 mẫu dữ liệu thật.
"""

from datetime import datetime
import tkinter as tk
import customtkinter as ctk

CHART_PALETTES = {
    "Light": {
        "bg": "#FFFFFF",
        "frame_border": "#D5E0ED",
        "grid": "#E2E8F0",
        "grid_sub": "#EDF2F7",
        "axis_text": "#475569",
        "cpu_line": "#0284C7",       # Xanh Cyan-Blue năng động
        "cpu_fill": "#E0F2FE",       # Nền phủ Cyan mềm
        "ram_line": "#7C3AED",       # Tím Violet đậm đà
        "ram_fill": "#F3E8FF",       # Nền phủ Violet mềm
        "dot_border": "#FFFFFF",
        "highlight_dot": "#FFFFFF",
    },
    "Dark": {
        "bg": "#0F1829",             # Nền Tech Navy sâu
        "frame_border": "#1D2D44",
        "grid": "#1A2942",           # Lưới tọa độ công nghệ
        "grid_sub": "#142034",
        "axis_text": "#8EA2BE",
        "cpu_line": "#22D3EE",       # Xanh Cyan rực sáng
        "cpu_fill": "#0B2A40",       # Vùng phủ Navy-Cyan
        "ram_line": "#C084FC",       # Tím Violet công nghệ sáng
        "ram_fill": "#251842",       # Vùng phủ Navy-Violet
        "dot_border": "#0F1829",
        "highlight_dot": "#FFFFFF",
    },
}


class ResourceChartsFrame(ctk.CTkFrame):
    """Khung chứa hai biểu đồ lịch sử tài nguyên CPU và RAM phong cách Tech Dashboard."""

    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            fg_color=("#FFFFFF", "#0F1829"),
            corner_radius=16,
            border_width=1,
            border_color=("#D5E0ED", "#1D2D44"),
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
            text_color=("#0F172A", "#F1F5F9"),
        ).pack(side="left", padx=(0, 8))

        self.lbl_samples = ctk.CTkLabel(
            title_box,
            text="0 mẫu",
            font=("Segoe UI", 11),
            text_color=("#475569", "#8FA0B8"),
            fg_color=("#F1F5F9", "#152238"),
            corner_radius=8,
            padx=8,
            pady=2,
        )
        self.lbl_samples.pack(side="left")

        # Chú thích màu sắc (Legend) đồng bộ với màu đường vẽ
        legend_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        legend_box.pack(side="right")

        ctk.CTkFrame(legend_box, width=10, height=10, corner_radius=3, fg_color=("#0284C7", "#22D3EE")).pack(side="left", padx=(0, 4))
        ctk.CTkLabel(legend_box, text="CPU (%)", font=("Segoe UI", 11, "bold"), text_color=("#0284C7", "#22D3EE")).pack(side="left", padx=(0, 14))

        ctk.CTkFrame(legend_box, width=10, height=10, corner_radius=3, fg_color=("#7C3AED", "#C084FC")).pack(side="left", padx=(0, 4))
        ctk.CTkLabel(legend_box, text="RAM (%)", font=("Segoe UI", 11, "bold"), text_color=("#7C3AED", "#C084FC")).pack(side="left")

        # Khung chứa 2 Canvas trực tiếp
        grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        grid_frame.columnconfigure(0, weight=1, uniform="chart")
        grid_frame.columnconfigure(1, weight=1, uniform="chart")
        grid_frame.rowconfigure(0, weight=1)

        pal = CHART_PALETTES["Light"]
        self.canvas_cpu = tk.Canvas(grid_frame, bg=pal["bg"], highlightthickness=0, bd=0)
        self.canvas_cpu.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.canvas_cpu.bind(
            "<Configure>",
            lambda _e: self._redraw_canvas(self.canvas_cpu, "cpu_percent", "cpu_line", "cpu_fill", "Biểu đồ CPU (%)"),
        )

        self.canvas_ram = tk.Canvas(grid_frame, bg=pal["bg"], highlightthickness=0, bd=0)
        self.canvas_ram.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self.canvas_ram.bind(
            "<Configure>",
            lambda _e: self._redraw_canvas(self.canvas_ram, "memory_percent", "ram_line", "ram_fill", "Biểu đồ RAM (%)"),
        )

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
        grid_sub = pal["grid_sub"]
        axis_col = pal["axis_text"]
        line_col = pal[line_key]
        fill_col = pal[fill_key]
        dot_border = pal["dot_border"]
        hl_dot = pal.get("highlight_dot", "#FFFFFF")

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

        # Đường lưới kỹ thuật: 100%, 75%, 50%, 25%, 0%
        for pct, txt, is_major in ((100.0, "100%", True), (75.0, "", False), (50.0, "50%", True), (25.0, "", False), (0.0, "0%", True)):
            y = top + plot_h * (1.0 - (pct / 100.0))
            if is_major:
                canvas.create_line(left, y, w - right, y, fill=grid_col, width=1)
                canvas.create_text(left - 6, y, text=txt, anchor="e", fill=axis_col, font=font_axis)
            else:
                canvas.create_line(left, y, w - right, y, fill=grid_sub, width=1, dash=(2, 4))

        # Trạng thái rỗng: không có mẫu
        if not self.points:
            canvas.create_text(
                left + plot_w / 2,
                top + plot_h / 2,
                text="Đang thu thập dữ liệu…",
                fill=axis_col,
                font=("Segoe UI", 11),
            )
            return

        # Chỉ có 1 mẫu: vẽ đúng 1 chấm tròn
        if len(self.points) == 1:
            pt = self.points[0]
            val = max(0.0, min(100.0, float(pt[metric_key])))
            cx = left + plot_w / 2
            cy = top + plot_h * (1.0 - (val / 100.0))
            r = 5
            canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=line_col, outline=dot_border, width=2)
            canvas.create_oval(cx - 2, cy - 2, cx + 2, cy + 2, fill=hl_dot, outline="")
            canvas.create_text(cx, cy - 12, text=f"{val:.1f}%", fill=line_col, font=("Segoe UI", 9, "bold"), anchor="center")
            t_str = datetime.fromtimestamp(pt["timestamp"]).strftime("%H:%M:%S")
            canvas.create_text(cx, h - 8, text=t_str, anchor="center", fill=axis_col, font=font_axis)
            return

        # Từ 2 mẫu trở lên: vẽ đường diện tích và chuỗi dữ liệu
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

        # Tô màu diện tích dưới đường biểu đồ
        y_zero = top + plot_h
        poly = [coords[0][0], y_zero]
        for x, y in coords:
            poly.extend([x, y])
        poly.extend([coords[-1][0], y_zero])
        canvas.create_polygon(poly, fill=fill_col, outline="")

        # Vẽ đường nối các điểm mẫu (Strokes)
        flat_coords = []
        for x, y in coords:
            flat_coords.extend([x, y])
        canvas.create_line(flat_coords, fill=line_col, width=2.5, capstyle="round", joinstyle="round")

        # Điểm tròn nổi bật giá trị đo đạc mới nhất (có tâm neon trắng)
        last_x, last_y = coords[-1]
        canvas.create_oval(last_x - 5, last_y - 5, last_x + 5, last_y + 5, fill=line_col, outline=dot_border, width=2)
        canvas.create_oval(last_x - 2, last_y - 2, last_x + 2, last_y + 2, fill=hl_dot, outline="")

        last_val = self.points[-1][metric_key]
        anchor_mode = "e" if last_x > (left + plot_w * 0.7) else "center"
        text_x = min(w - right - 2, max(left + 20, last_x))
        canvas.create_text(text_x, last_y - 12, text=f"{last_val:.1f}%", fill=line_col, font=("Segoe UI", 9, "bold"), anchor=anchor_mode)

        # Nhãn thời gian trục hoành
        str_start = datetime.fromtimestamp(t_start).strftime("%H:%M:%S")
        str_end = datetime.fromtimestamp(t_end).strftime("%H:%M:%S")
        canvas.create_text(left, h - 8, text=str_start, anchor="w", fill=axis_col, font=font_axis)
        canvas.create_text(w - right, h - 8, text=str_end, anchor="e", fill=axis_col, font=font_axis)

        elapsed = int(round(t_span))
        if elapsed > 0:
            canvas.create_text(left + plot_w / 2, h - 8, text=f"{elapsed}s gần nhất", anchor="center", fill=axis_col, font=font_axis)
