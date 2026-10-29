"""
ui_widgets.py - Các thành phần giao diện dùng chung cho PC Monitor 2.0.
Thiết kế theo phong cách Dashboard Công Nghệ (Tech Dashboard) với nền Navy sâu,
các điểm nhấn Xanh Cyan & Tím Violet nổi bật, thẻ số liệu tinh tế và bảng dữ liệu hiệu năng cao.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk

# --- BẢNG MÀU DASHBOARD CÔNG NGHỆ (TECH DASHBOARD PALETTE) ---
COLOR_BG = ("#EEF2F8", "#080E1A")             # Nền chính: Xanh lam nhạt mát mẻ (Light) / Navy sâu thẳm (Dark)
COLOR_SURFACE = ("#FFFFFF", "#0F1829")        # Mặt thẻ: Trắng tinh khiết / Tech Navy cao cấp
COLOR_SURFACE_ALT = ("#F6F9FD", "#152238")    # Mặt thẻ phụ / Khung tóm tắt
COLOR_BORDER = ("#D5E0ED", "#1D2D44")         # Viền chuẩn tinh tế
COLOR_BORDER_LIGHT = ("#E5ECF5", "#162338")   # Viền mỏng

COLOR_TEXT_MAIN = ("#0F172A", "#F1F5F9")      # Chữ chính: Slate-900 / Slate-100 tương phản cao
COLOR_TEXT_MUTED = ("#475569", "#8FA0B8")     # Chữ phụ: Slate-600 / Cool Slate-400
COLOR_TEXT_SUBTLE = ("#475569", "#8FA0B8")

COLOR_ACCENT = ("#0369A1", "#22D3EE")         # Màu nhấn công nghệ: Sky-600 / Bright Cyan
COLOR_ACCENT_BUTTON = "#0369A1"               # Nút bấm: Đậm vừa đủ để giữ chữ trắng tương phản
COLOR_ACCENT_HOVER = "#0369A1"
COLOR_ACCENT_BG = ("#E0F2FE", "#0E2A42")      # Nền nhấn mềm

COLOR_SUCCESS = ("#047857", "#34D399")        # Xanh lục công nghệ
COLOR_SUCCESS_BG = ("#ECFDF5", "#06321F")

COLOR_WARNING = ("#92400E", "#FBBF24")        # Vàng hổ phách
COLOR_WARNING_BG = ("#FFFBEB", "#382307")

COLOR_DANGER = ("#DC2626", "#F87171")         # Đỏ cảnh báo
COLOR_DANGER_BUTTON = "#DC2626"
COLOR_DANGER_HOVER = "#B91C1C"
COLOR_DANGER_BG = ("#FEF2F2", "#381318")

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
        return "", COLOR_TEXT_MUTED, ("transparent", "transparent"), ("#CBD5E1", "#334155")
    if percent < 60:
        return "Bình thường", COLOR_SUCCESS, COLOR_SUCCESS_BG, ("#059669", "#10B981")
    if percent < 85:
        return "Khá cao", COLOR_WARNING, COLOR_WARNING_BG, ("#D97706", "#F59E0B")
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
        self.color = "#475569"
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
            # 4 ô lưới bảng điều khiển phong cách tech dashboard
            self.create_rectangle(3 * f, 3 * f, 9 * f, 9 * f, fill=c, outline="")
            self.create_rectangle(11 * f, 3 * f, 17 * f, 9 * f, fill=c, outline="")
            self.create_rectangle(3 * f, 11 * f, 9 * f, 17 * f, fill=c, outline="")
            self.create_rectangle(11 * f, 11 * f, 17 * f, 17 * f, fill=c, outline="")

        elif self.icon_name == "processes":
            # Đường sóng điện tâm đồ / nhịp xung hoạt động CPU
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
            # Tia sét khởi động năng lượng cao
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
            # Hộp gói ứng dụng công nghệ
            self.create_rectangle(3 * f, 3 * f, 17 * f, 17 * f, outline=c, width=max(1, int(1.5 * f)))
            self.create_line(3 * f, 8 * f, 17 * f, 8 * f, fill=c, width=max(1, int(1.5 * f)))
            self.create_line(10 * f, 8 * f, 10 * f, 17 * f, fill=c, width=max(1, int(1.5 * f)))

        elif self.icon_name == "storage":
            # Ổ đĩa cứng với vạch đèn báo tín hiệu
            self.create_oval(3 * f, 3 * f, 17 * f, 8 * f, fill=c, outline="")
            self.create_rectangle(3 * f, 5 * f, 17 * f, 14 * f, fill=c, outline="")
            self.create_oval(3 * f, 12 * f, 17 * f, 17 * f, fill=c, outline="")
            self.create_line(5 * f, 10 * f, 9 * f, 10 * f, fill=self.bg_color, width=max(1, int(1.5 * f)))

        elif self.icon_name == "network":
            # Các cung sóng radar truyền thông và điểm nút
            self.create_arc(3 * f, 3 * f, 17 * f, 17 * f, start=45, extent=90, style="arc", outline=c, width=max(1, int(2 * f)))
            self.create_arc(6 * f, 6 * f, 14 * f, 14 * f, start=45, extent=90, style="arc", outline=c, width=max(1, int(2 * f)))
            self.create_oval(9 * f, 13 * f, 11 * f, 15 * f, fill=c, outline="")

        elif self.icon_name == "optimize":
            # Biểu tượng tia lửa tối ưu hóa 4 cánh đối xứng
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
            self.configure(fg_color=COLOR_ACCENT_BG, border_color=("#7DD3FC", "#0C4A6E"))
            self.lbl_text.configure(text=text, text_color=COLOR_ACCENT)

        self.pack(fill="x", pady=(0, 10))

    def hide(self):
        self.pack_forget()


class MetricCard(ctk.CTkFrame):
    """
    Thẻ thông số phần cứng thiết kế tinh tế kiểu dashboard công nghệ:
    - Nhãn tiêu đề rõ ràng, số đo đo đạc nổi bật, thanh tiến trình bo cong.
    - Với thẻ dung lượng/mạng có percent=None: ẩn thanh tiến trình và huy hiệu rỗng,
      chỉ hiển thị nhãn và giá trị đo được (không hiện 'Không có dữ liệu' hay thanh xám rỗng).
    - Vừa vặn hoàn hảo tại độ phân giải 1020x700.
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
            fg_color=("#E5ECF5", "#152238"),
            corner_radius=8,
            padx=8,
            pady=2,
        )
        self.lbl_badge.pack(side="right")

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

        self.prog = ctk.CTkProgressBar(
            self,
            height=6,
            corner_radius=3,
            fg_color=("#D5E0ED", "#1D2D44"),
            progress_color=COLOR_ACCENT,
        )
        self.prog.set(0.0)
        self.prog.pack(fill="x", padx=16, pady=(0, 8))

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

    def update_data(self, title, value_str, percent, detail_text, badge_text=None, badge_kind=None):
        if title:
            self.lbl_title.configure(text=title)
        self.lbl_value.configure(text=value_str)
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
                b_color, b_bg = COLOR_ACCENT, COLOR_ACCENT_BG
            else:
                b_color, b_bg = COLOR_TEXT_MUTED, ("#E5ECF5", "#152238")
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
            # percent=None và không có nhãn trạng thái: ẩn huy hiệu thay vì hiện 'Không có dữ liệu'
            self.lbl_badge.pack_forget()

        # 2. Quản lý hiển thị Thanh tiến trình (Progress Bar)
        if percent is not None:
            _, _, _, p_color = get_status_badge_colors(percent)
            self.prog.set(max(0.0, min(1.0, float(percent) / 100.0)))
            self.prog.configure(progress_color=p_color)
            if not self.prog.winfo_manager():
                self.prog.pack(fill="x", padx=16, pady=(0, 8), before=self.lbl_detail)
        else:
            # percent=None: ẩn thanh tiến trình hoàn toàn
            self.prog.pack_forget()


class DataTable(ctk.CTkFrame):
    """
    Bảng dữ liệu mạnh mẽ bọc ttk.Treeview cho Dashboard công nghệ:
    - Màu sắc Navy sâu trong Dark mode, Trắng thanh lịch trong Light mode.
    - Sắp xếp cột chuẩn xác theo giá trị số thực bên dưới (numeric sort aliases).
    - Cập nhật tăng dần (incremental updates) bảo toàn vị trí cuộn và dòng được chọn.
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

        self._raw_data = []
        self._filtered_data = []
        self._sort_col = None
        self._sort_reverse = False
        self._filter_query = ""
        self._selected_id = None

        # Container bảng + scrollbars
        self.table_box = ctk.CTkFrame(self, fg_color="transparent")
        self.table_box.pack(fill="both", expand=True, padx=2, pady=2)
        self.table_box.rowconfigure(0, weight=1)
        self.table_box.columnconfigure(0, weight=1)

        col_ids = [c[0] for c in self.columns]
        self.tree = ttk.Treeview(
            self.table_box,
            columns=col_ids,
            show="headings",
            selectmode="browse",
            style="Modern.Treeview",
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

        # Label hiển thị trạng thái rỗng hoặc đang đọc
        self.lbl_empty = ctk.CTkLabel(
            self,
            text="Không có dữ liệu để hiển thị",
            font=FONT_BODY,
            text_color=COLOR_TEXT_MUTED,
        )

        self.apply_theme("Light")

    def apply_theme(self, theme):
        self.theme = "Dark" if str(theme).lower() in ("dark", "tối") else "Light"
        is_dark = self.theme == "Dark"

        bg = "#0F1829" if is_dark else "#FFFFFF"
        fg = "#F1F5F9" if is_dark else "#0F172A"
        heading_bg = "#152238" if is_dark else "#F1F5F9"
        heading_fg = "#93C5FD" if is_dark else "#0F172A"
        heading_active = "#1E2F4C" if is_dark else "#E2E8F0"
        sel_bg = "#0284C7" if is_dark else "#0284C7"
        sel_fg = "#FFFFFF"

        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Modern.Treeview",
            background=bg,
            foreground=fg,
            fieldbackground=bg,
            rowheight=32,
            font=(FONT_FAMILY, 10),
            borderwidth=0,
        )
        style.map(
            "Modern.Treeview",
            background=[("selected", sel_bg)],
            foreground=[("selected", sel_fg)],
        )

        style.configure(
            "Modern.Treeview.Heading",
            background=heading_bg,
            foreground=heading_fg,
            font=(FONT_FAMILY, 10, "bold"),
            relief="flat",
            borderwidth=0,
            padding=(6, 6),
        )
        style.map(
            "Modern.Treeview.Heading",
            background=[("active", heading_active)],
            foreground=[("active", heading_fg)],
        )

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
        if not self.tree.get_children():
            self.lbl_empty.place(relx=0.5, rely=0.5, anchor="center")

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

        # 4. Cập nhật tăng dần (Incremental updates) tránh nhấp nháy
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

    def _on_tree_select(self, _event):
        sel = self.tree.selection()
        if sel:
            self._selected_id = sel[0]
            if self.on_select:
                item = self.get_selected_item()
                if item is not None:
                    self.on_select(item)
        else:
            self._selected_id = None
            if self.on_select:
                self.on_select(None)
