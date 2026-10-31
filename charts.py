"""
charts.py - Biểu đồ đường Canvas hiệu năng cao cho CPU và RAM.
Phiên bản PC Monitor 2.1 - Phong cách Monochrome Mist (Trắng/Đen Mờ Ảo):
- Màu sắc chủ đạo: Charcoal sâu thẳm / Trắng bạc tinh tế, loại bỏ hoàn toàn neon cyan/violet.
- CPU: Nét vẽ liền (solid) màu trắng sáng / đen sâu nổi bật.
- RAM: Nét vẽ đứt (dashed) màu bạc / xám than chì phân biệt rõ ràng.
- Hiệu ứng animate_in(): Stroke reveal ~450ms từ trái sang phải trên dữ liệu thật, không sinh mẫu giả.
- Hỗ trợ đầy đủ Sáng / Tối, dừng animation khi ẩn hoặc tắt hiệu ứng.
"""

from datetime import datetime
import tkinter as tk
import customtkinter as ctk

from motion import Animator

CHART_PALETTES = {
    "Light": {
        "bg": "#FFFFFF",
        "frame_border": "#E0E0E4",
        "grid": "#E8E8EC",
        "grid_sub": "#F0F0F4",
        "axis_text": "#666B75",
        "cpu_line": "#111317",       # Đen than chì sắc nét
        "cpu_fill": "#EBECEF",       # Vùng phủ sương bạc nhạt
        "cpu_dash": (),              # Nét liền
        "ram_line": "#5C6270",       # Xám than chì phân biệt
        "ram_fill": "#F4F4F6",       # Vùng phủ mờ nhẹ
        "ram_dash": (4, 2),          # Nét đứt phân biệt
        "dot_border": "#FFFFFF",
        "highlight_dot": "#111317",
    },
    "Dark": {
        "bg": "#14171C",             # Nền Charcoal mờ ảo sâu thẳm
        "frame_border": "#252A34",
        "grid": "#1F242D",           # Lưới tọa độ kỹ thuật êm dịu
        "grid_sub": "#191D24",
        "axis_text": "#9298A4",       # Chữ trục màu tro sáng dễ đọc
        "cpu_line": "#FFFFFF",       # Trắng tinh khiết nổi bật
        "cpu_fill": "#20252E",       # Vùng phủ Charcoal mờ ảo
        "cpu_dash": (),              # Nét liền
        "ram_line": "#B4B9C4",       # Bạc sáng êm dịu
        "ram_fill": "#1A1E26",       # Vùng phủ mờ dịu
        "ram_dash": (4, 2),          # Nét đứt phân biệt
        "dot_border": "#14171C",
        "highlight_dot": "#FFFFFF",
    },
}


class ResourceChartsFrame(ctk.CTkFrame):
    """Khung chứa hai biểu đồ lịch sử tài nguyên CPU và RAM phong cách Monochrome Mist."""

    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            fg_color=("#FFFFFF", "#14171C"),
            corner_radius=16,
            border_width=1,
            border_color=("#E0E0E4", "#252A34"),
            **kwargs,
        )
        self.points = []
        self.theme = "Light"
        self.animator = Animator(self)
        self.motion_enabled = True
        self._reveal_progress = 1.0

        # Thanh tiêu đề trên của khung biểu đồ
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=16, pady=(10, 4))

        title_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        title_box.pack(side="left")

        ctk.CTkLabel(
            title_box,
            text="Lịch sử tài nguyên",
            font=("Segoe UI", 13, "bold"),
            text_color=("#111317", "#F8FAFC"),
        ).pack(side="left", padx=(0, 8))

        self.lbl_samples = ctk.CTkLabel(
            title_box,
            text="0 mẫu",
            font=("Segoe UI", 11),
            text_color=("#666B75", "#9298A4"),
            fg_color=("#F4F4F6", "#1C2027"),
            corner_radius=8,
            padx=8,
            pady=2,
        )
        self.lbl_samples.pack(side="left")

        # Chú thích màu sắc và kiểu nét (Legend)
        legend_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        legend_box.pack(side="right")

        # Badge CPU (Nét liền)
        self.cpu_legend_badge = ctk.CTkFrame(legend_box, width=12, height=4, corner_radius=2, fg_color=("#111317", "#FFFFFF"))
        self.cpu_legend_badge.pack(side="left", padx=(0, 4))
        self.lbl_cpu_legend = ctk.CTkLabel(legend_box, text="CPU (Liền)", font=("Segoe UI", 11, "bold"), text_color=("#111317", "#FFFFFF"))
        self.lbl_cpu_legend.pack(side="left", padx=(0, 14))

        # Badge RAM (Nét đứt)
        self.ram_legend_badge = ctk.CTkFrame(legend_box, width=12, height=4, corner_radius=2, fg_color=("#5C6270", "#B4B9C4"))
        self.ram_legend_badge.pack(side="left", padx=(0, 4))
        self.lbl_ram_legend = ctk.CTkLabel(legend_box, text="RAM (Đứt)", font=("Segoe UI", 11), text_color=("#5C6270", "#B4B9C4"))
        self.lbl_ram_legend.pack(side="left")

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
            lambda _e: self._redraw_canvas(self.canvas_cpu, "cpu_percent", "cpu_line", "cpu_fill", "cpu_dash", "Biểu đồ CPU (%)"),
        )

        self.canvas_ram = tk.Canvas(grid_frame, bg=pal["bg"], highlightthickness=0, bd=0)
        self.canvas_ram.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self.canvas_ram.bind(
            "<Configure>",
            lambda _e: self._redraw_canvas(self.canvas_ram, "memory_percent", "ram_line", "ram_fill", "ram_dash", "Biểu đồ RAM (%)"),
        )

    def set_motion_enabled(self, enabled):
        """Bật / tắt hiệu ứng động."""
        self.motion_enabled = bool(enabled)
        self.animator.set_enabled(self.motion_enabled)
        if not self.motion_enabled:
            self.animator.cancel_all()
            self._reveal_progress = 1.0
            self.redraw()

    def animate_in(self):
        """
        Kích hoạt hiệu ứng Stroke Reveal ~450ms từ trái sang phải
        trên chuỗi dữ liệu thực có sẵn, không thay đổi mốc tọa độ hay sinh mẫu giả.
        """
        top = self.winfo_toplevel()
        system_motion = getattr(top, "motion_enabled", True)
        if not self.motion_enabled or not system_motion or not self.winfo_ismapped() or len(self.points) < 2:
            self.animator.cancel("reveal")
            self._reveal_progress = 1.0
            self.redraw()
            return

        self.animator.cancel("reveal")
        self._reveal_progress = 0.0

        def on_tick(progress):
            self._reveal_progress = progress
            self.redraw()

        def on_done():
            self._reveal_progress = 1.0
            self.redraw()

        self.animator.animate("reveal", on_tick, duration=0.45, complete=on_done)

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

        if not self.animator.active_count:
            self._reveal_progress = 1.0
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
        self._redraw_canvas(self.canvas_cpu, "cpu_percent", "cpu_line", "cpu_fill", "cpu_dash", "Biểu đồ CPU (%)")
        self._redraw_canvas(self.canvas_ram, "memory_percent", "ram_line", "ram_fill", "ram_dash", "Biểu đồ RAM (%)")

    def _redraw_canvas(self, canvas, metric_key, line_key, fill_key, dash_key, title):
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
        dash_style = pal.get(dash_key, ())
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

        # Lưới tọa độ kỹ thuật êm dịu: 100%, 75%, 50%, 25%, 0%
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

        # Chỉ có 1 mẫu: hiển thị trung thực 1 điểm đo
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

        # Từ 2 mẫu trở lên: dựng tọa độ đường
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

        # Áp dụng Stroke Reveal: giới hạn tọa độ hiển thị theo _reveal_progress
        p = max(0.0, min(1.0, float(self._reveal_progress)))
        x_limit = left + plot_w * p

        active_coords = []
        interp_val = None
        for i in range(len(coords)):
            pt_x, pt_y = coords[i]
            if pt_x <= x_limit:
                active_coords.append((pt_x, pt_y))
            else:
                if i > 0:
                    x_prev, y_prev = coords[i - 1]
                    dx = pt_x - x_prev
                    frac = (x_limit - x_prev) / dx if dx > 0 else 0.0
                    interp_y = y_prev + (pt_y - y_prev) * frac
                    active_coords.append((x_limit, interp_y))
                    v_prev = float(self.points[i - 1][metric_key])
                    v_next = float(self.points[i][metric_key])
                    interp_val = v_prev + (v_next - v_prev) * frac
                break

        if not active_coords:
            active_coords = [coords[0]]
            interp_val = float(self.points[0][metric_key])

        # 1. Tô màu diện tích mờ ảo dưới đường biểu đồ
        y_zero = top + plot_h
        poly = [active_coords[0][0], y_zero]
        for x, y in active_coords:
            poly.extend([x, y])
        poly.extend([active_coords[-1][0], y_zero])
        canvas.create_polygon(poly, fill=fill_col, outline="")

        # 2. Vẽ đường nối các điểm mẫu
        flat_coords = []
        for x, y in active_coords:
            flat_coords.extend([x, y])

        if dash_style:
            canvas.create_line(flat_coords, fill=line_col, width=2, dash=dash_style, capstyle="round", joinstyle="round")
        else:
            canvas.create_line(flat_coords, fill=line_col, width=2.5, capstyle="round", joinstyle="round")

        # 3. Điểm tròn nổi bật giá trị đo đạc mới nhất tại đầu đường reveal
        head_x, head_y = active_coords[-1]
        canvas.create_oval(head_x - 5, head_y - 5, head_x + 5, head_y + 5, fill=line_col, outline=dot_border, width=2)
        canvas.create_oval(head_x - 2, head_y - 2, head_x + 2, head_y + 2, fill=hl_dot, outline="")

        # 4. Hiển thị số đo chính xác
        if p >= 1.0 or interp_val is None:
            last_val = self.points[-1][metric_key]
        else:
            last_val = interp_val

        anchor_mode = "e" if head_x > (left + plot_w * 0.7) else ("w" if head_x < (left + 50) else "center")
        text_x = min(w - right - 2, max(left + 20, head_x))
        canvas.create_text(text_x, head_y - 12, text=f"{last_val:.1f}%", fill=line_col, font=("Segoe UI", 9, "bold"), anchor=anchor_mode)

        # 5. Nhãn thời gian trục hoành cố định theo khoảng thời gian thật
        str_start = datetime.fromtimestamp(t_start).strftime("%H:%M:%S")
        str_end = datetime.fromtimestamp(t_end).strftime("%H:%M:%S")
        canvas.create_text(left, h - 8, text=str_start, anchor="w", fill=axis_col, font=font_axis)
        canvas.create_text(w - right, h - 8, text=str_end, anchor="e", fill=axis_col, font=font_axis)

        elapsed = int(round(t_span))
        if elapsed > 0:
            canvas.create_text(left + plot_w / 2, h - 8, text=f"{elapsed}s gần nhất", anchor="center", fill=axis_col, font=font_axis)
