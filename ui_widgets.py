"""
ui_widgets.py - Các thành phần giao diện dùng chung cho PC Monitor 2.1.
Phiên bản Monochrome Mist (Trắng/Đen Mờ Ảo):
- Bảng màu Charcoal sâu thẳm / Trắng bạc thanh lịch, viền mờ tinh tế, loại bỏ hoàn toàn neon blue/cyan/purple.
- MetricCard: Thẻ số đo sắc nét, thanh đo bo cong và vòng tròn đo phần trăm (Arc Gauge) mờ ảo;
  hiệu ứng nhảy số mượt mà ~260ms trên dữ liệu thật, animate_in() tái hiện giá trị đo đạc.
- DataTable: Bọc ttk.Treeview chuẩn mực với thanh cuộn ngang/dọc, sắp xếp số thực qua bí danh,
  phản hồi chọn/hover ~150ms bằng tag animation, giữ nguyên selection và vị trí cuộn khi làm mới dữ liệu.
- NavIconCanvas: Biểu tượng vector vẽ thuần bằng Canvas không dùng Emoji.
- StatusBanner: Dải thông báo trạng thái bo cong hiện đại.
"""

import re
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk

from motion import Animator, blend

# --- BẢNG MÀU CHỦ ĐẠO MONOCHROME MIST (CHARCOAL & SILVER MIST) ---
COLOR_BG = ("#F4F4F6", "#0D0F12")             # Nền chính: Bạc sáng sương mù (Light) / Matte Charcoal sâu thẳm (Dark)
COLOR_SURFACE = ("#FFFFFF", "#14171C")        # Mặt thẻ: Trắng tinh khiết / Charcoal card cao cấp
COLOR_SURFACE_ALT = ("#EFEFF2", "#1C2027")    # Bề mặt thẻ phụ / Khung tóm tắt
COLOR_BORDER = ("#E0E0E4", "#252A34")         # Viền chuẩn mảnh mai độ tương phản thấp
COLOR_BORDER_LIGHT = ("#EBEBEF", "#1D222A")   # Viền phân cách mềm

COLOR_TEXT_MAIN = ("#111317", "#F8FAFC")      # Chữ chính: Đen sâu / Trắng tinh khiết tương phản cao
COLOR_TEXT_MUTED = ("#666B75", "#9298A4")     # Chữ phụ: Xám than chì / Màu tro sáng mờ ảo
COLOR_TEXT_SUBTLE = ("#8A909C", "#636975")    # Chữ chi tiết nhỏ

COLOR_ACCENT = ("#181A1F", "#F4F4F6")         # Màu nhấn tiền cảnh: Đen than chì (Light) / Trắng bạc (Dark)
COLOR_ACCENT_BUTTON = ("#181A1F", "#E4E4E7")  # Nền nút: Đen than chì (chữ trắng) / Bạc sáng (chữ đen)
COLOR_ACCENT_HOVER = ("#2D313A", "#D4D4D8")   # Hover nút bấm
COLOR_ACCENT_BG = ("#E8E8EC", "#232832")      # Nền highlight tab đang chọn / Pill mềm
COLOR_BUTTON_TEXT = ("#FAFAFA", "#141416")    # Chữ nút bấm tương phản cao với nền

# Màu cảnh báo ngữ nghĩa (giữ ở mức nhỏ gọn, tinh tế)
COLOR_SUCCESS = ("#15803D", "#4ADE80")
COLOR_SUCCESS_BG = ("#F0FDF4", "#13231B")

COLOR_WARNING = ("#B45309", "#FBBF24")
COLOR_WARNING_BG = ("#FFFBEB", "#261D12")

COLOR_DANGER = ("#DC2626", "#F87171")
COLOR_DANGER_BUTTON = ("#DC2626", "#DC2626")
COLOR_DANGER_HOVER = ("#B91C1C", "#B91C1C")
COLOR_DANGER_BG = ("#FEF2F2", "#2B1417")

# --- HỆ THỐNG PHÔNG CHỮ SEGOE UI ---
FONT_FAMILY = "Segoe UI"
FONT_PAGE_TITLE = (FONT_FAMILY, 20, "bold")
FONT_PAGE_SUB = (FONT_FAMILY, 12)
FONT_SECTION_TITLE = (FONT_FAMILY, 14, "bold")
FONT_CARD_TITLE = (FONT_FAMILY, 12, "bold")
FONT_METRIC_VAL = (FONT_FAMILY, 26, "bold")
FONT_BODY = (FONT_FAMILY, 12)
FONT_BODY_BOLD = (FONT_FAMILY, 12, "bold")
FONT_SMALL = (FONT_FAMILY, 11)
FONT_SMALL_BOLD = (FONT_FAMILY, 11, "bold")
FONT_MONO_SMALL = ("Consolas", 10)


def get_status_badge_colors(percent):
    """Xác định nhãn và màu trạng thái theo ngưỡng sử dụng tài nguyên."""
    if percent is None:
        return "", COLOR_TEXT_MUTED, ("transparent", "transparent"), ("#E0E0E4", "#252A34")
    if percent < 60:
        return "Bình thường", COLOR_SUCCESS, COLOR_SUCCESS_BG, ("#111317", "#F8FAFC")
    if percent < 85:
        return "Khá cao", COLOR_WARNING, COLOR_WARNING_BG, ("#B45309", "#FBBF24")
    return "Rất cao", COLOR_DANGER, COLOR_DANGER_BG, ("#DC2626", "#EF4444")


class NavIconCanvas(tk.Canvas):
    """
    Vẽ biểu tượng vector hình học sắc nét bằng Tkinter Canvas không dùng Emoji.
    Tự động biến đổi màu theo chủ đề Sáng / Tối và trạng thái kích hoạt.
    """

    def __init__(self, parent, icon_name, size=20, **kwargs):
        super().__init__(
            parent,
            width=size,
            height=size,
            highlightthickness=0,
            bd=0,
            **kwargs,
        )
        self.icon_name = icon_name
        self.size = size
        self.color = "#9298A4"
        self.bg_color = kwargs.get("bg", "#FFFFFF")
        self.draw()

    def update_style(self, color, bg_color):
        self.color = color
        self.bg_color = bg_color
        self.configure(bg=bg_color)
        self.draw()

    def draw(self):
        self.delete("all")
        c = self.color
        s = self.size
        f = s / 20.0

        if self.icon_name == "overview":
            # 4 ô lưới bảng điều khiển
            self.create_rectangle(3 * f, 3 * f, 9 * f, 9 * f, fill=c, outline="")
            self.create_rectangle(11 * f, 3 * f, 17 * f, 9 * f, fill=c, outline="")
            self.create_rectangle(3 * f, 11 * f, 9 * f, 17 * f, fill=c, outline="")
            self.create_rectangle(11 * f, 11 * f, 17 * f, 17 * f, fill=c, outline="")

        elif self.icon_name == "processes":
            # Đường xung nhịp hoạt động CPU
            self.create_line(
                2 * f, 10 * f,
                6 * f, 10 * f,
                9 * f, 3 * f,
                12 * f, 17 * f,
                15 * f, 10 * f,
                18 * f, 10 * f,
                fill=c, width=max(1, int(2 * f)), capstyle="round", joinstyle="round"
            )

        elif self.icon_name == "startup":
            # Tia sét khởi động
            self.create_polygon(
                11 * f, 2 * f,
                6 * f, 11 * f,
                10 * f, 11 * f,
                9 * f, 18 * f,
                15 * f, 9 * f,
                11 * f, 9 * f,
                fill=c, outline=""
            )

        elif self.icon_name == "apps":
            # Hộp gói ứng dụng
            self.create_rectangle(3 * f, 3 * f, 17 * f, 17 * f, outline=c, width=max(1, int(1.5 * f)))
            self.create_line(3 * f, 8 * f, 17 * f, 8 * f, fill=c, width=max(1, int(1.5 * f)))
            self.create_line(10 * f, 8 * f, 10 * f, 17 * f, fill=c, width=max(1, int(1.5 * f)))

        elif self.icon_name == "storage":
            # Ổ đĩa cứng với vạch đèn tín hiệu
            self.create_oval(3 * f, 3 * f, 17 * f, 8 * f, fill=c, outline="")
            self.create_rectangle(3 * f, 5 * f, 17 * f, 14 * f, fill=c, outline="")
            self.create_oval(3 * f, 12 * f, 17 * f, 17 * f, fill=c, outline="")
            self.create_line(5 * f, 10 * f, 9 * f, 10 * f, fill=self.bg_color, width=max(1, int(1.5 * f)))

        elif self.icon_name == "network":
            # Các cung sóng truyền thông và điểm nút
            self.create_arc(3 * f, 3 * f, 17 * f, 17 * f, start=45, extent=90, style="arc", outline=c, width=max(1, int(2 * f)))
            self.create_arc(6 * f, 6 * f, 14 * f, 14 * f, start=45, extent=90, style="arc", outline=c, width=max(1, int(2 * f)))
            self.create_oval(9 * f, 13 * f, 11 * f, 15 * f, fill=c, outline="")

        elif self.icon_name == "optimize":
            # Ngôi sao tối ưu 4 cánh
            self.create_line(10 * f, 2 * f, 10 * f, 18 * f, fill=c, width=max(1, int(2 * f)), capstyle="round")
            self.create_line(2 * f, 10 * f, 18 * f, 10 * f, fill=c, width=max(1, int(2 * f)), capstyle="round")
            self.create_line(4 * f, 4 * f, 16 * f, 16 * f, fill=c, width=max(1, int(1.5 * f)), capstyle="round")
            self.create_line(4 * f, 16 * f, 16 * f, 4 * f, fill=c, width=max(1, int(1.5 * f)), capstyle="round")

        elif self.icon_name == "history":
            # Mặt đồng hồ ghi nhận lịch sử
            self.create_oval(3 * f, 3 * f, 17 * f, 17 * f, outline=c, width=max(1, int(2 * f)))
            self.create_line(10 * f, 6 * f, 10 * f, 10 * f, fill=c, width=max(1, int(1.8 * f)), capstyle="round")
            self.create_line(10 * f, 10 * f, 14 * f, 10 * f, fill=c, width=max(1, int(1.8 * f)), capstyle="round")

        else:
            self.create_oval(6 * f, 6 * f, 14 * f, 14 * f, fill=c, outline="")


class StatusBanner(ctk.CTkFrame):
    """Dải thông báo trạng thái hoặc lỗi nổi bật trên trang."""

    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            fg_color=COLOR_DANGER_BG,
            corner_radius=10,
            border_width=1,
            border_color=("#FCA5A5", "#781C26"),
            **kwargs,
        )
        self.lbl_text = ctk.CTkLabel(
            self,
            text="",
            font=FONT_BODY,
            text_color=COLOR_DANGER,
            anchor="w",
            justify="left",
            wraplength=800,
        )
        self.lbl_text.pack(fill="x", padx=14, pady=8)
        self.pack_forget()

    def show(self, text, kind="error"):
        if kind == "error":
            self.configure(fg_color=COLOR_DANGER_BG, border_color=("#FCA5A5", "#781C26"))
            self.lbl_text.configure(text=text, text_color=COLOR_DANGER)
        elif kind == "warning":
            self.configure(fg_color=COLOR_WARNING_BG, border_color=("#FCD34D", "#783B08"))
            self.lbl_text.configure(text=text, text_color=COLOR_WARNING)
        elif kind == "success":
            self.configure(fg_color=COLOR_SUCCESS_BG, border_color=("#86EFAC", "#0C4E2B"))
            self.lbl_text.configure(text=text, text_color=COLOR_SUCCESS)
        else:
            self.configure(fg_color=COLOR_ACCENT_BG, border_color=COLOR_BORDER)
            self.lbl_text.configure(text=text, text_color=COLOR_TEXT_MAIN)

        self.pack(fill="x", pady=(0, 10))

    def hide(self):
        self.pack_forget()


class MetricCard(ctk.CTkFrame):
    """
    Thẻ thông số phần cứng thiết kế tinh tế kiểu Monochrome Mist:
    - Nhãn tiêu đề rõ ràng, số đo lớn nổi bật, thanh tiến trình bo cong và vòng tròn đo (Arc Gauge).
    - Hiệu ứng nhảy số mượt mà ~260ms trên dữ liệu thật, animate_in() đếm từ 0 đến giá trị đo gần nhất.
    - Với thẻ có percent=None: ẩn thanh tiến trình, vòng tròn đo và huy hiệu rỗng.
    - Tương thích 100% với các thuộc tính widget hiện hành.
    """

    def __init__(self, parent, default_title, **kwargs):
        super().__init__(
            parent,
            fg_color=COLOR_SURFACE,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_BORDER,
            **kwargs,
        )
        self.animator = Animator(self)
        self.motion_enabled = True

        self._target_title = default_title
        self._target_value_str = "--"
        self._target_percent = None
        self._target_detail = "--"
        self._target_badge_text = None
        self._target_badge_kind = None

        self._current_num = None
        self._current_percent = None
        self._num_info = None
        self._active_progress_color = ("#111317", "#F8FAFC")

        # Top row: Tiêu đề + Huy hiệu trạng thái
        self.top_row = ctk.CTkFrame(self, fg_color="transparent")
        self.top_row.pack(fill="x", padx=16, pady=(12, 4))

        self.lbl_title = ctk.CTkLabel(
            self.top_row,
            text=default_title,
            font=FONT_CARD_TITLE,
            text_color=COLOR_TEXT_MAIN,
            anchor="w",
        )
        self.lbl_title.pack(side="left")

        self.lbl_badge = ctk.CTkLabel(
            self.top_row,
            text="--",
            font=FONT_SMALL_BOLD,
            text_color=COLOR_TEXT_MUTED,
            fg_color=("#EAEAEF", "#1C2027"),
            corner_radius=8,
            padx=8,
            pady=2,
        )
        self.lbl_badge.pack(side="right")

        # Mid row: Số đo lớn + Vòng tròn đo tỷ lệ (Arc Gauge)
        self.mid_row = ctk.CTkFrame(self, fg_color="transparent")
        self.mid_row.pack(fill="x", padx=16, pady=(2, 6))

        self.lbl_value = ctk.CTkLabel(
            self.mid_row,
            text="--",
            font=FONT_METRIC_VAL,
            text_color=COLOR_TEXT_MAIN,
            anchor="w",
        )
        self.lbl_value.pack(side="left")

        self.gauge = tk.Canvas(
            self.mid_row,
            width=32,
            height=32,
            bg="#FFFFFF",
            highlightthickness=0,
            bd=0,
        )
        # Ẩn mặc định, chỉ đóng gói khi percent != None

        # Thanh tiến trình ngang (Progress Bar)
        self.prog = ctk.CTkProgressBar(
            self,
            height=6,
            corner_radius=3,
            fg_color=("#E0E0E4", "#20252F"),
            progress_color=COLOR_ACCENT,
        )
        self.prog.set(0.0)
        self.prog.pack(fill="x", padx=16, pady=(0, 8))

        # Dòng chi tiết phụ bên dưới
        self.lbl_detail = ctk.CTkLabel(
            self,
            text="--",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_MUTED,
            justify="left",
            anchor="w",
            wraplength=220,
        )
        self.lbl_detail.pack(fill="x", padx=16, pady=(0, 12))

    @staticmethod
    def _is_dark():
        return ctk.get_appearance_mode().lower() == "dark"

    @staticmethod
    def _parse_number(val_str):
        if not val_str:
            return None
        s = str(val_str).strip()
        match = re.match(r"^([+-]?\d+(?:\.\d+)?)(.*)$", s)
        if match:
            raw_num = float(match.group(1))
            raw_unit = match.group(2)
            has_dot = "." in match.group(1)
            decimals = len(match.group(1).split(".")[1]) if has_dot else 0
            return raw_num, raw_unit, decimals
        return None

    def _draw_gauge(self, percent, color):
        self.gauge.delete("all")
        if percent is None:
            return
        is_dark = self._is_dark()
        bg_col = "#14171C" if is_dark else "#FFFFFF"
        track_col = "#252A34" if is_dark else "#E5E5EB"
        self.gauge.configure(bg=bg_col)

        # Đường tròn khung viền
        self.gauge.create_oval(3, 3, 29, 29, outline=track_col, width=3)

        # Cung tròn tiến trình quay theo chiều kim đồng hồ từ đỉnh
        pct = max(0.0, min(100.0, float(percent)))
        if pct > 0:
            extent = -pct * 3.6
            self.gauge.create_arc(3, 3, 29, 29, start=90, extent=extent, style="arc", outline=color, width=3)

    def set_motion_enabled(self, enabled):
        """Bật / tắt hiệu ứng động."""
        self.motion_enabled = bool(enabled)
        self.animator.set_enabled(self.motion_enabled)
        if not self.motion_enabled:
            self.animator.cancel_all()
            self.lbl_value.configure(text=self._target_value_str)
            if self._target_percent is not None and self.prog.winfo_manager():
                self.prog.set(max(0.0, min(1.0, float(self._target_percent) / 100.0)))
                is_dark = self._is_dark()
                c = self._active_progress_color[1] if is_dark else self._active_progress_color[0]
                self._draw_gauge(self._target_percent, c)
            if self._num_info:
                self._current_num = self._num_info[0]
            self._current_percent = self._target_percent

    def animate_in(self):
        """Tái hiện hiệu ứng đếm số từ 0 đến giá trị đo gần nhất khi chuyển tab."""
        top = self.winfo_toplevel()
        system_motion = getattr(top, "motion_enabled", True)
        if not self.motion_enabled or not system_motion or not self.winfo_ismapped() or not self._num_info:
            self.animator.cancel("count_in")
            self.lbl_value.configure(text=self._target_value_str)
            if self._target_percent is not None and self.prog.winfo_manager():
                self.prog.set(max(0.0, min(1.0, float(self._target_percent) / 100.0)))
                is_dark = self._is_dark()
                c = self._active_progress_color[1] if is_dark else self._active_progress_color[0]
                self._draw_gauge(self._target_percent, c)
            return

        target_num, unit, decimals = self._num_info
        target_pct = self._target_percent

        def on_tick(progress):
            cur_n = target_num * progress
            if decimals > 0:
                txt = f"{cur_n:.{decimals}f}{unit}"
            else:
                txt = f"{round(cur_n)}{unit}"
            self.lbl_value.configure(text=txt)

            if target_pct is not None and self.prog.winfo_manager():
                cur_p = target_pct * progress
                self.prog.set(max(0.0, min(1.0, cur_p / 100.0)))
                is_d = self._is_dark()
                c = self._active_progress_color[1] if is_d else self._active_progress_color[0]
                self._draw_gauge(cur_p, c)

        def on_done():
            self.lbl_value.configure(text=self._target_value_str)
            if target_pct is not None and self.prog.winfo_manager():
                self.prog.set(max(0.0, min(1.0, float(target_pct) / 100.0)))
                is_d = self._is_dark()
                c = self._active_progress_color[1] if is_d else self._active_progress_color[0]
                self._draw_gauge(target_pct, c)
            self._current_num = target_num
            self._current_percent = target_pct

        self.animator.animate("count_in", on_tick, duration=0.26, complete=on_done)

    def update_data(self, title, value_str, percent, detail_text, badge_text=None, badge_kind=None):
        if title:
            self.lbl_title.configure(text=title)
            self._target_title = title
        self._target_value_str = value_str
        self._target_percent = percent
        self._target_detail = detail_text
        self._target_badge_text = badge_text
        self._target_badge_kind = badge_kind
        self.lbl_detail.configure(text=detail_text)

        # 1. Quản lý hiển thị Huy hiệu (Badge)
        if badge_text is not None and str(badge_text).strip() != "":
            if badge_kind == "danger":
                b_color, b_bg = COLOR_DANGER, COLOR_DANGER_BG
            elif badge_kind == "warning":
                b_color, b_bg = COLOR_WARNING, COLOR_WARNING_BG
            elif badge_kind == "success":
                b_color, b_bg = COLOR_SUCCESS, COLOR_SUCCESS_BG
            elif str(badge_text).strip().lower() == "live":
                b_color, b_bg = COLOR_TEXT_MAIN, COLOR_ACCENT_BG
            else:
                b_color, b_bg = COLOR_TEXT_MUTED, ("#EAEAEF", "#1C2027")
            self.lbl_badge.configure(text=badge_text, text_color=b_color, fg_color=b_bg)
            if not self.lbl_badge.winfo_manager():
                self.lbl_badge.pack(side="right")
        elif percent is not None:
            b_text, b_color, b_bg, _ = get_status_badge_colors(percent)
            if badge_kind == "danger":
                b_color, b_bg = COLOR_DANGER, COLOR_DANGER_BG
            self.lbl_badge.configure(text=b_text, text_color=b_color, fg_color=b_bg)
            if not self.lbl_badge.winfo_manager():
                self.lbl_badge.pack(side="right")
        else:
            self.lbl_badge.pack_forget()

        # 2. Quản lý hiển thị Thanh tiến trình & Gauge
        if percent is not None:
            _, _, _, p_color = get_status_badge_colors(percent)
            self._active_progress_color = p_color
            self.prog.configure(progress_color=p_color)
            if not self.prog.winfo_manager():
                self.prog.pack(fill="x", padx=16, pady=(0, 8), before=self.lbl_detail)
            if not self.gauge.winfo_manager():
                self.gauge.pack(side="right", padx=(8, 0))
        else:
            self.prog.pack_forget()
            self.gauge.pack_forget()

        # 3. Cập nhật số đo (có animation nếu thỏa điều kiện)
        parsed = self._parse_number(value_str)
        self._num_info = parsed

        top = self.winfo_toplevel()
        system_motion = getattr(top, "motion_enabled", True)
        can_animate = (
            self.motion_enabled
            and system_motion
            and self.winfo_ismapped()
            and self._current_num is not None
            and parsed is not None
        )

        if can_animate:
            start_num = self._current_num
            target_num, unit, decimals = parsed
            start_pct = self._current_percent if self._current_percent is not None else (percent or 0.0)
            target_pct = percent if percent is not None else 0.0

            def on_tick(progress):
                cur_n = start_num + (target_num - start_num) * progress
                if decimals > 0:
                    txt = f"{cur_n:.{decimals}f}{unit}"
                else:
                    txt = f"{round(cur_n)}{unit}"
                self.lbl_value.configure(text=txt)

                if percent is not None:
                    cur_p = start_pct + (target_pct - start_pct) * progress
                    self.prog.set(max(0.0, min(1.0, cur_p / 100.0)))
                    is_d = self._is_dark()
                    c = self._active_progress_color[1] if is_d else self._active_progress_color[0]
                    self._draw_gauge(cur_p, c)

            def on_done():
                self.lbl_value.configure(text=value_str)
                if percent is not None:
                    self.prog.set(max(0.0, min(1.0, float(percent) / 100.0)))
                    is_d = self._is_dark()
                    c = self._active_progress_color[1] if is_d else self._active_progress_color[0]
                    self._draw_gauge(percent, c)
                self._current_num = target_num
                self._current_percent = percent

            self.animator.animate("update_num", on_tick, duration=0.26, complete=on_done)
        else:
            self.animator.cancel("update_num")
            self.animator.cancel("count_in")
            self.lbl_value.configure(text=value_str)
            if percent is not None:
                self.prog.set(max(0.0, min(1.0, float(percent) / 100.0)))
                is_dark = self._is_dark()
                c = self._active_progress_color[1] if is_dark else self._active_progress_color[0]
                self._draw_gauge(percent, c)
            if parsed:
                self._current_num = parsed[0]
            else:
                self._current_num = None
            self._current_percent = percent


class DataTable(ctk.CTkFrame):
    """
    Bảng dữ liệu mạnh mẽ bọc ttk.Treeview cho phong cách Monochrome Mist:
    - Bề mặt Charcoal mờ ảo trong Dark mode, Trắng bạc trong Light mode.
    - Sắp xếp cột chuẩn xác theo giá trị số thực bên dưới (numeric sort aliases).
    - Cập nhật tăng dần (incremental updates) bảo toàn vị trí cuộn và dòng được chọn.
    - Phản hồi chọn / hover nhanh mượt ~150ms mà không re-animate các dòng giữ nguyên khi làm mới.
    - Hỗ trợ đầy đủ cuộn dọc và cuộn ngang.
    """

    def __init__(self, parent, columns, id_column="id", on_select=None, **kwargs):
        super().__init__(
            parent,
            fg_color=COLOR_SURFACE,
            corner_radius=12,
            border_width=1,
            border_color=COLOR_BORDER,
            **kwargs,
        )
        self.columns = columns  # danh sách tuple (col_id, title, width, anchor, sort_type)
        self.id_column = id_column
        self.on_select = on_select
        self.theme = "Light"
        self.animator = Animator(self)
        self.motion_enabled = True

        self._raw_data = []
        self._filtered_data = []
        self._sort_col = None
        self._sort_reverse = False
        self._filter_query = ""
        self._selected_id = None
        self._last_animated_selection = None
        self._hovered_row_id = None

        # Container bảng + scrollbars
        self.table_box = ctk.CTkFrame(self, fg_color="transparent")
        self.table_box.pack(fill="both", expand=True, padx=2, pady=2)
        self.table_box.rowconfigure(0, weight=1)
        self.table_box.columnconfigure(0, weight=1)

        col_ids = [c[0] for c in self.columns]
        self._style_name = f"PCMonitor{id(self)}.Treeview"
        self.tree = ttk.Treeview(
            self.table_box,
            columns=col_ids,
            show="headings",
            selectmode="browse",
            style=self._style_name,
        )

        for col_id, title, width, anchor, _ in self.columns:
            self.tree.heading(col_id, text=title, command=lambda c=col_id: self._on_header_click(c))
            self.tree.column(col_id, width=width, anchor=anchor, stretch=True)

        self.scrollbar = ctk.CTkScrollbar(
            self.table_box,
            orientation="vertical",
            command=self.tree.yview,
            width=12,
            corner_radius=6,
        )
        self.tree.configure(yscrollcommand=self.scrollbar.set)

        self.x_scrollbar = ctk.CTkScrollbar(
            self.table_box,
            orientation="horizontal",
            command=self.tree.xview,
            height=12,
            corner_radius=6,
        )
        self.tree.configure(xscrollcommand=self.x_scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns", padx=(2, 4))
        self.x_scrollbar.grid(row=1, column=0, sticky="ew")

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Motion>", self._on_tree_mouse_motion)
        self.tree.bind("<Leave>", self._on_tree_mouse_leave)

        # Label hiển thị trạng thái rỗng hoặc đang đọc
        self.lbl_empty = ctk.CTkLabel(
            self,
            text="Không có dữ liệu để hiển thị",
            font=FONT_BODY,
            text_color=COLOR_TEXT_MUTED,
        )

        self.apply_theme("Light")

    def set_motion_enabled(self, enabled):
        """Bật / tắt hiệu ứng động."""
        self.motion_enabled = bool(enabled)
        self.animator.set_enabled(self.motion_enabled)
        if not self.motion_enabled:
            self.animator.cancel_all()
            if self._hovered_row_id and self.tree.exists(self._hovered_row_id):
                tags = [t for t in self.tree.item(self._hovered_row_id, "tags") if t != "hover"]
                self.tree.item(self._hovered_row_id, tags=tags)

    def apply_theme(self, theme):
        self.animator.cancel_all()
        self.theme = "Dark" if str(theme).lower() in ("dark", "tối") else "Light"
        is_dark = self.theme == "Dark"

        bg = "#14171C" if is_dark else "#FFFFFF"
        fg = "#F8FAFC" if is_dark else "#111317"
        heading_bg = "#1C2027" if is_dark else "#F4F4F6"
        heading_fg = "#D1D5DB" if is_dark else "#111317"
        heading_active = "#252A34" if is_dark else "#EAEAEF"
        sel_bg = "#2A303C" if is_dark else "#E2E4E9"
        sel_fg = "#FFFFFF" if is_dark else "#111317"
        hover_bg = "#1B2028" if is_dark else "#F7F7FA"

        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            self._style_name,
            background=bg,
            foreground=fg,
            fieldbackground=bg,
            rowheight=32,
            font=(FONT_FAMILY, 10),
            borderwidth=0,
            relief="flat",
            bordercolor=bg,
            lightcolor=bg,
            darkcolor=bg,
        )
        style.map(
            self._style_name,
            background=[("selected", sel_bg)],
            foreground=[("selected", sel_fg)],
        )

        style.configure(
            self._style_name + ".Heading",
            background=heading_bg,
            foreground=heading_fg,
            font=(FONT_FAMILY, 10, "bold"),
            relief="flat",
            borderwidth=0,
            padding=(6, 6),
        )
        style.map(
            self._style_name + ".Heading",
            background=[("active", heading_active)],
            foreground=[("active", heading_fg)],
        )

        self.tree.tag_configure("hover", background=hover_bg)

    def set_data(self, data_list):
        """Cập nhật dữ liệu nguồn cho bảng và duy trì lựa chọn hiện thời."""
        self._raw_data = data_list or []
        self._apply_filter_and_sort()

    def set_filter(self, query):
        """Lọc dữ liệu theo chuỗi tìm kiếm."""
        self._filter_query = (query or "").strip().lower()
        self._apply_filter_and_sort()

    def get_selected_item(self):
        """Trả về dictionary của dòng đang chọn, hoặc None."""
        sel = self.tree.selection()
        if not sel:
            return None
        item_id = sel[0]
        for row in self._raw_data:
            if str(row.get(self.id_column)) == str(item_id):
                return row
        return None

    def select_item_by_id(self, item_id):
        """Chọn dòng có id tương ứng."""
        str_id = str(item_id)
        if self.tree.exists(str_id):
            self.tree.selection_set(str_id)
            self.tree.see(str_id)
            self._selected_id = str_id

    def set_empty_message(self, text):
        self.lbl_empty.configure(text=text)

    def _on_header_click(self, col_id):
        if self._sort_col == col_id:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_col = col_id
            self._sort_reverse = False
        self._apply_filter_and_sort()

    def _apply_filter_and_sort(self):
        # 1. Lọc
        q = self._filter_query
        if not q:
            filtered = list(self._raw_data)
        else:
            filtered = []
            for row in self._raw_data:
                matched = False
                for val in row.values():
                    if val is not None and q in str(val).lower():
                        matched = True
                        break
                if matched:
                    filtered.append(row)

        # 2. Sắp xếp với bí danh giá trị số nguyên bản
        if self._sort_col:
            sort_type = "str"
            for col_id, _, _, _, stype in self.columns:
                if col_id == self._sort_col:
                    sort_type = stype
                    break

            def sort_key(row):
                val = row.get(self._sort_col)
                numeric_fields = {
                    "cpu_str": "cpu_percent",
                    "mem_str": "memory_bytes",
                    "speed_str": "speed_mbps",
                    "recv_str": "bytes_recv",
                    "sent_str": "bytes_sent",
                }
                if self._sort_col == "size_str":
                    val = row.get("size_bytes", row.get("bytes"))
                elif self._sort_col in numeric_fields:
                    val = row.get(numeric_fields[self._sort_col])

                if val is None:
                    return (-1, 0) if sort_type in ("int", "float", "bytes") else (-1, "")
                if sort_type == "int":
                    try:
                        return (1, int(val))
                    except (ValueError, TypeError):
                        return (0, 0)
                elif sort_type == "float":
                    try:
                        return (1, float(val))
                    except (ValueError, TypeError):
                        return (0, 0.0)
                elif sort_type == "bytes":
                    try:
                        return (1, int(val))
                    except (ValueError, TypeError):
                        return (0, 0)
                return (1, str(val).lower())

            filtered.sort(key=sort_key, reverse=self._sort_reverse)

        self._filtered_data = filtered

        # 3. Ghi nhớ ID đang chọn và vị trí cuộn
        selection = self.tree.selection()
        target_id = selection[0] if selection else self._selected_id
        scroll_position = self.tree.yview()[0] if self.tree.get_children() else 0.0

        # 4. Cập nhật tăng dần (Incremental updates) tránh giật nháy
        wanted = {str(row.get(self.id_column, "")) for row in filtered}
        for item_id in self.tree.get_children():
            if item_id not in wanted:
                self.tree.delete(item_id)

        if not self._filtered_data:
            self.lbl_empty.place(relx=0.5, rely=0.5, anchor="center")
        else:
            self.lbl_empty.place_forget()
            col_ids = [c[0] for c in self.columns]
            for index, row in enumerate(self._filtered_data):
                row_id = str(row.get(self.id_column, ""))
                values = [row.get(cid, "--") for cid in col_ids]
                formatted_values = []
                for v in values:
                    if v is None:
                        formatted_values.append("--")
                    else:
                        formatted_values.append(v)

                if self.tree.exists(row_id):
                    self.tree.item(row_id, values=formatted_values)
                    self.tree.move(row_id, "", index)
                else:
                    self.tree.insert("", "end", iid=row_id, values=formatted_values)

            # 5. Phục hồi lựa chọn và vị trí cuộn
            if target_id and self.tree.exists(str(target_id)):
                self.tree.selection_set(str(target_id))
                self._selected_id = str(target_id)
            else:
                self.tree.selection_remove(*self.tree.selection())
                self._selected_id = None
            self.tree.yview_moveto(scroll_position)

    def _on_tree_mouse_motion(self, event):
        row_id = self.tree.identify_row(event.y)
        if row_id != self._hovered_row_id:
            if self._hovered_row_id and self.tree.exists(self._hovered_row_id):
                current_tags = [t for t in self.tree.item(self._hovered_row_id, "tags") if t != "hover"]
                self.tree.item(self._hovered_row_id, tags=current_tags)
            self._hovered_row_id = row_id
            if row_id and self.tree.exists(row_id) and row_id != self._selected_id:
                current_tags = list(self.tree.item(row_id, "tags"))
                if "hover" not in current_tags:
                    current_tags.append("hover")
                    self.tree.item(row_id, tags=current_tags)
                    is_dark = self.theme == "Dark"
                    start = "#14171C" if is_dark else "#FFFFFF"
                    end = "#1B2028" if is_dark else "#F7F7FA"
                    self.animator.animate(
                        "hover", lambda progress: self.tree.tag_configure("hover", background=blend(start, end, progress)),
                        duration=0.12,
                    )

    def _on_tree_mouse_leave(self, _event):
        self.animator.cancel("hover")
        if self._hovered_row_id and self.tree.exists(self._hovered_row_id):
            current_tags = [t for t in self.tree.item(self._hovered_row_id, "tags") if t != "hover"]
            self.tree.item(self._hovered_row_id, tags=current_tags)
        self._hovered_row_id = None

    def _on_tree_select(self, _event):
        sel = self.tree.selection()
        if sel:
            selected_id = sel[0]
            if selected_id != self._last_animated_selection:
                self._last_animated_selection = selected_id
                top = self.winfo_toplevel()
                system_motion = getattr(top, "motion_enabled", True)
                if self.motion_enabled and system_motion and self.winfo_ismapped():
                    is_dark = self.theme == "Dark"
                    flash_start = "#424855" if is_dark else "#CBD0D8"
                    flash_end = "#2A303C" if is_dark else "#E2E4E9"

                    def tick(progress):
                        if self.tree.exists(selected_id):
                            col = blend(flash_start, flash_end, progress)
                            ttk.Style(self.tree).map(self._style_name, background=[("selected", col)])

                    def done():
                        ttk.Style(self.tree).map(self._style_name, background=[("selected", flash_end)])

                    self.animator.animate("select_pulse", tick, duration=0.15, complete=done)

            self._selected_id = selected_id
            if self.on_select:
                item = self.get_selected_item()
                if item is not None:
                    self.on_select(item)
        else:
            self._selected_id = None
            self._last_animated_selection = None
            if self.on_select:
                self.on_select(None)
