"""
ui_pages.py - Triển khai đầy đủ 8 màn hình của PC Monitor 2.1.
1. Tổng quan (Overview)
2. Đang chạy (Processes)
3. Khởi động (Startup)
4. Ứng dụng (Apps)
5. Dung lượng (Storage)
6. Mạng (Network)
7. Tối ưu (Optimize)
8. Lịch sử (History)

Tuân thủ nghiêm ngặt API contract trong ANTIGRAVITY_V2_BRIEF.md.
Dùng trực tiếp backend từ system_service, không dùng fallback giả.
"""

from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from system_service import format_bytes, format_duration
from charts import ResourceChartsFrame

from ui_widgets import (
    COLOR_ACCENT,
    COLOR_ACCENT_BUTTON,
    COLOR_ACCENT_BG,
    COLOR_ACCENT_HOVER,
    COLOR_BORDER,
    COLOR_BUTTON_TEXT,
    COLOR_DANGER,
    COLOR_DANGER_BUTTON,
    COLOR_DANGER_BG,
    COLOR_DANGER_HOVER,
    COLOR_SUCCESS,
    COLOR_SUCCESS_BG,
    COLOR_SURFACE,
    COLOR_SURFACE_ALT,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_SUBTLE,
    COLOR_WARNING,
    COLOR_WARNING_BG,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_CARD_TITLE,
    FONT_FAMILY,
    FONT_METRIC_VAL,
    FONT_MONO_SMALL,
    FONT_PAGE_SUB,
    FONT_PAGE_TITLE,
    FONT_SECTION_TITLE,
    FONT_SMALL,
    FONT_SMALL_BOLD,
    DataTable,
    MetricCard,
    StatusBanner,
)


def format_time_str(iso_or_ts):
    if not iso_or_ts:
        return "--"
    if isinstance(iso_or_ts, (int, float)):
        try:
            return datetime.fromtimestamp(iso_or_ts).strftime("%H:%M:%S %d/%m/%Y")
        except Exception:
            return str(iso_or_ts)
    try:
        dt = datetime.fromisoformat(str(iso_or_ts))
        return dt.strftime("%H:%M:%S %d/%m/%Y")
    except Exception:
        return str(iso_or_ts)


# ==============================================================================
# 1. TRANG TỔNG QUAN (OVERVIEW PAGE)
# ==============================================================================
class OverviewPage(ctk.CTkFrame):
    """Trang Tổng quan theo dõi sức khỏe và tài nguyên hệ thống theo thời gian thực."""

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app
        self._build_ui()

    def _build_ui(self):
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=4, pady=4)

        # 1. Thanh tóm tắt trạng thái máy tính (System Info Badge Bar)
        self.summary_bar = ctk.CTkFrame(
            self.scroll,
            fg_color=COLOR_SURFACE,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        self.summary_bar.pack(fill="x", pady=(0, 12))

        top_info = ctk.CTkFrame(self.summary_bar, fg_color="transparent")
        top_info.pack(fill="x", padx=16, pady=(10, 4))

        ctk.CTkLabel(top_info, text="Thiết bị:", font=FONT_BODY, text_color=COLOR_TEXT_MUTED).pack(side="left", padx=(0, 6))
        self.lbl_machine = ctk.CTkLabel(top_info, text="--", font=(FONT_FAMILY, 15, "bold"), text_color=COLOR_TEXT_MAIN)
        self.lbl_machine.pack(side="left")

        self.lbl_uptime = ctk.CTkLabel(
            top_info,
            text="Hoạt động: --",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_MUTED,
            fg_color=("#F1F1F3", "#202023"),
            corner_radius=8,
            padx=8,
            pady=2,
        )
        self.lbl_uptime.pack(side="right")

        self.lbl_process_count = ctk.CTkLabel(
            top_info,
            text="-- tiến trình",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_MUTED,
            fg_color=("#F1F1F3", "#202023"),
            corner_radius=8,
            padx=8,
            pady=2,
        )
        self.lbl_process_count.pack(side="right", padx=(0, 8))

        bot_info = ctk.CTkFrame(self.summary_bar, fg_color="transparent")
        bot_info.pack(fill="x", padx=16, pady=(0, 10))

        self.lbl_os = ctk.CTkLabel(bot_info, text="HĐH: --", font=FONT_SMALL, text_color=COLOR_TEXT_MUTED)
        self.lbl_os.pack(side="left")

        self.lbl_battery = ctk.CTkLabel(bot_info, text="Pin: --", font=FONT_SMALL, text_color=COLOR_TEXT_MUTED)
        self.lbl_battery.pack(side="right")

        # Dải thông báo lỗi / dữ liệu cũ
        self.banner = StatusBanner(self.scroll)

        # 2. Khối 3 thẻ chỉ số (CPU, RAM, Ổ đĩa hệ thống)
        self.cards_grid = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.cards_grid.pack(fill="x", pady=(0, 12))
        for col in range(3):
            self.cards_grid.columnconfigure(col, weight=1, uniform="overview_cards")

        self.card_cpu = MetricCard(self.cards_grid, "Bộ xử lý CPU")
        self.card_cpu.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self.card_ram = MetricCard(self.cards_grid, "Bộ nhớ RAM")
        self.card_ram.grid(row=0, column=1, sticky="nsew", padx=3)

        self.card_disk = MetricCard(self.cards_grid, "Ổ đĩa hệ thống")
        self.card_disk.grid(row=0, column=2, sticky="nsew", padx=(6, 0))

        # 3. Biểu đồ lịch sử tài nguyên CPU & RAM thật
        self.chart = ResourceChartsFrame(self.scroll, height=240)
        self.chart.pack(fill="both", expand=True, pady=(0, 12))

        # 4. Thông số kỹ thuật & phím tắt tiện ích
        bottom_box = ctk.CTkFrame(
            self.scroll,
            fg_color=COLOR_SURFACE,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        bottom_box.pack(fill="x", pady=(0, 10))

        sec_header = ctk.CTkFrame(bottom_box, fg_color="transparent")
        sec_header.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(
            sec_header,
            text="Thông số kỹ thuật & Tiện ích hệ thống",
            font=FONT_SECTION_TITLE,
            text_color=COLOR_TEXT_MAIN,
        ).pack(side="left")

        btn_box = ctk.CTkFrame(sec_header, fg_color="transparent")
        btn_box.pack(side="right")

        self.btn_task_mgr = ctk.CTkButton(
            btn_box,
            text="Mở Task Manager",
            command=lambda: self.app.open_tool("task_manager"),
            width=140,
            height=32,
            corner_radius=8,
            font=FONT_SMALL_BOLD,
            fg_color=("#E4E4E7", "#27272B"),
            hover_color=("#D4D4D8", "#36363B"),
            text_color=COLOR_TEXT_MAIN,
        )
        self.btn_task_mgr.pack(side="left", padx=(0, 8))

        self.btn_export = ctk.CTkButton(
            btn_box,
            text="Xuất báo cáo JSON...",
            command=self.app.export_report,
            width=150,
            height=32,
            corner_radius=8,
            font=FONT_SMALL_BOLD,
            fg_color=COLOR_ACCENT_BUTTON,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_BUTTON_TEXT,
        )
        self.btn_export.pack(side="left")

        # Lưới các mục thông số kỹ thuật chi tiết
        self.info_grid = ctk.CTkFrame(bottom_box, fg_color="transparent")
        self.info_grid.pack(fill="x", padx=16, pady=(0, 12))
        for c in range(2):
            self.info_grid.columnconfigure(c, weight=1, uniform="info_col")

        self.lbl_cpu_detail = ctk.CTkLabel(
            self.info_grid,
            text="CPU: Đang lấy thông tin…",
            font=FONT_BODY,
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
            justify="left",
        )
        self.lbl_cpu_detail.grid(row=0, column=0, sticky="w", pady=3)

        self.lbl_os_build = ctk.CTkLabel(
            self.info_grid,
            text="Bản dựng HĐH: --",
            font=FONT_BODY,
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
            justify="left",
        )
        self.lbl_os_build.grid(row=0, column=1, sticky="w", pady=3)

        self.lbl_arch = ctk.CTkLabel(
            self.info_grid,
            text="Kiến trúc: --",
            font=FONT_BODY,
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
            justify="left",
        )
        self.lbl_arch.grid(row=1, column=0, sticky="w", pady=3)

        self.lbl_boot_time = ctk.CTkLabel(
            self.info_grid,
            text="Thời điểm khởi động: --",
            font=FONT_BODY,
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
            justify="left",
        )
        self.lbl_boot_time.grid(row=1, column=1, sticky="w", pady=3)

    def apply_theme(self, theme):
        self.chart.set_theme(theme)

    def update_sample(self, data, is_stale=False):
        if not data:
            return

        # 1. Summary Bar
        self.lbl_machine.configure(text=data.get("machine_name") or "Máy tính của bạn")
        self.lbl_os.configure(text=f"HĐH: {data.get('os_name') or '--'}")

        uptime_s = data.get("uptime_seconds")
        if uptime_s is not None:
            self.lbl_uptime.configure(text=f"Hoạt động: {format_duration(uptime_s)}")
        else:
            self.lbl_uptime.configure(text="Hoạt động: --")

        pcount = data.get("process_count")
        if pcount is not None:
            self.lbl_process_count.configure(text=f"{pcount} tiến trình")
        else:
            self.lbl_process_count.configure(text="-- tiến trình")

        bat = data.get("battery")
        if bat and isinstance(bat, dict):
            pct = bat.get("percent", 0)
            plugged = bat.get("plugged", False)
            status_txt = "Đang cắm sạc" if plugged else "Dùng pin"
            sec = bat.get("seconds_left")
            extra = f" (Còn {format_duration(sec)})" if (not plugged and sec and sec > 0) else ""
            self.lbl_battery.configure(text=f"Pin: {pct}% - {status_txt}{extra}")
        else:
            self.lbl_battery.configure(text="Pin: Nguồn trực tiếp (Không dùng pin)")

        # 2. Thẻ CPU
        cpu_pct = data.get("cpu_percent")
        threads = data.get("cpu_threads", 1)
        cpu_name = data.get("cpu_name") or "Bộ xử lý"
        val_str = f"{cpu_pct:.1f}%" if cpu_pct is not None else "--%"
        self.card_cpu.update_data(
            "Bộ xử lý CPU",
            val_str,
            cpu_pct,
            f"{cpu_name}\n{threads} luồng logic",
        )

        # 3. Thẻ RAM
        mem = data.get("memory") or {}
        ram_pct = mem.get("percent")
        ram_val = f"{ram_pct:.1f}%" if ram_pct is not None else "--%"
        used_s = format_bytes(mem.get("used"))
        total_s = format_bytes(mem.get("total"))
        avail_s = format_bytes(mem.get("available"))
        self.card_ram.update_data(
            "Bộ nhớ RAM",
            ram_val,
            ram_pct,
            f"Đã dùng: {used_s} / {total_s}\nKhả dụng: {avail_s}",
        )

        # 4. Thẻ Ổ đĩa hệ thống
        disk = data.get("disk") or {}
        disk_path = disk.get("path") or "C:\\"
        disk_pct = disk.get("percent")
        if disk.get("error") or disk_pct is None:
            self.card_disk.update_data(
                f"Ổ đĩa hệ thống ({disk_path})",
                "--",
                None,
                disk.get("error") or "Không thể đọc dữ liệu ổ đĩa.",
                badge_text="Lỗi đọc",
                badge_kind="danger",
            )
        else:
            d_used = format_bytes(disk.get("used"))
            d_total = format_bytes(disk.get("total"))
            d_free = format_bytes(disk.get("free"))
            self.card_disk.update_data(
                f"Ổ đĩa hệ thống ({disk_path})",
                f"{disk_pct:.1f}%",
                disk_pct,
                f"Còn trống: {d_free}\nTổng dung lượng: {d_total}",
            )

        # 5. Cập nhật biểu đồ lịch sử
        if hasattr(self.app, "history"):
            self.chart.set_points(self.app.history.points)

        # 6. Dải thông báo
        if is_stale:
            self.banner.show("Đang hiển thị dữ liệu đã lưu gần nhất. Không kết nối được luồng đo mới.", kind="warning")
        else:
            self.banner.hide()

    def update_system_info(self, sinfo):
        if not sinfo:
            return
        cpu_str = f"CPU: {sinfo.get('cpu_name', '--')} ({sinfo.get('cpu_physical', '--')} nhân / {sinfo.get('cpu_threads', '--')} luồng)"
        self.lbl_cpu_detail.configure(text=cpu_str)
        self.lbl_os_build.configure(text=f"Bản dựng HĐH: {sinfo.get('os_build') or sinfo.get('os_name') or '--'}")
        self.lbl_arch.configure(text=f"Kiến trúc: {sinfo.get('architecture', '--')} | RAM tổng: {format_bytes(sinfo.get('memory_total'))}")
        boot_str = format_time_str(sinfo.get("boot_time"))
        self.lbl_boot_time.configure(text=f"Khởi động: {boot_str}")


# ==============================================================================
# 2. TRANG ĐANG CHẠY (PROCESSES PAGE)
# ==============================================================================
class ProcessesPage(ctk.CTkFrame):
    """Trang quản lý các tiến trình và ứng dụng đang chạy."""

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app
        self._selected_process = None
        self._build_ui()

    def _build_ui(self):
        # 1. Thanh điều khiển
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 10))

        self.search_entry = ctk.CTkEntry(
            top_bar,
            placeholder_text="Tìm kiếm tiến trình hoặc PID…",
            width=320,
            height=36,
            corner_radius=10,
            font=FONT_BODY,
        )
        self.search_entry.pack(side="left", padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", lambda _e: self.table.set_filter(self.search_entry.get()))

        self.lbl_count = ctk.CTkLabel(top_bar, text="Đang tải danh sách…", font=FONT_BODY, text_color=COLOR_TEXT_MUTED)
        self.lbl_count.pack(side="left")

        btn_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        btn_box.pack(side="right")

        self.btn_refresh = ctk.CTkButton(
            btn_box,
            text="Làm mới",
            command=self.app.refresh_processes,
            width=90,
            height=36,
            corner_radius=10,
            font=FONT_BODY_BOLD,
            fg_color=("#E4E4E7", "#27272B"),
            hover_color=("#D4D4D8", "#36363B"),
            text_color=COLOR_TEXT_MAIN,
        )
        self.btn_refresh.pack(side="left", padx=(0, 8))

        self.btn_stop = ctk.CTkButton(
            btn_box,
            text="Kết thúc tiến trình",
            command=self._on_stop_clicked,
            width=150,
            height=36,
            corner_radius=10,
            font=FONT_BODY_BOLD,
            fg_color=COLOR_DANGER_BUTTON,
            hover_color=COLOR_DANGER_HOVER,
            text_color="#FFFFFF",
            state="disabled",
        )
        self.btn_stop.pack(side="left")

        # 2. Bảng tiến trình
        cols = [
            ("pid", "PID", 80, "center", "int"),
            ("name", "Tên tiến trình", 240, "w", "str"),
            ("cpu_str", "CPU (%)", 100, "e", "float"),
            ("mem_str", "Bộ nhớ RAM", 120, "e", "bytes"),
            ("username", "Người dùng", 150, "w", "str"),
            ("stop_status", "Trạng thái", 170, "w", "str"),
        ]
        self.table = DataTable(self, columns=cols, id_column="_identity", on_select=self._on_row_select)
        self.table.pack(fill="both", expand=True, pady=(0, 10))
        self.table.set_empty_message("Đang tải danh sách tiến trình…")

        # 3. Khung chi tiết tiến trình được chọn
        self.detail_card = ctk.CTkFrame(
            self,
            fg_color=COLOR_SURFACE,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_BORDER,
            height=90,
        )
        self.detail_card.pack(fill="x")
        self.detail_card.pack_propagate(False)

        self.lbl_detail_title = ctk.CTkLabel(
            self.detail_card,
            text="Chọn một tiến trình trong danh sách để xem chi tiết hoặc kết thúc tác vụ.",
            font=FONT_BODY,
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
        )
        self.lbl_detail_title.pack(fill="x", padx=16, pady=(12, 4))

        self.lbl_detail_sub = ctk.CTkLabel(
            self.detail_card,
            text="",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
        )
        self.lbl_detail_sub.pack(fill="x", padx=16, pady=(0, 10))

    def apply_theme(self, theme):
        self.table.apply_theme(theme)

    def update_processes(self, proc_list):
        if proc_list is None:
            self.table.set_empty_message("Chưa tải được tiến trình. Bấm Làm mới để thử lại.")
            self.table.set_data([])
            self.lbl_count.configure(text="0 tiến trình")
            return

        formatted = []
        for p in proc_list:
            cpu_val = p.get("cpu_percent")
            cpu_str = f"{cpu_val:.1f}%" if cpu_val is not None else "--"
            mem_bytes = p.get("memory_bytes", 0)
            mem_str = format_bytes(mem_bytes)
            can_stop = p.get("can_stop", False)
            reason = p.get("protected_reason") or ""
            stop_str = "Có thể dừng" if can_stop else (reason or "Được bảo vệ")

            row = dict(p)
            row["_identity"] = f"{p['pid']}:{p['created']}"
            row["cpu_str"] = cpu_str
            row["mem_str"] = mem_str
            row["stop_status"] = stop_str
            formatted.append(row)

        self.table.set_empty_message("Không có tiến trình nào khớp với tìm kiếm.")
        self.table.set_data(formatted)
        self.lbl_count.configure(text=f"Tổng số: {len(proc_list)} tiến trình")

        sel = self.table.get_selected_item()
        self._on_row_select(sel)

    def _on_row_select(self, item):
        self._selected_process = item
        if not item:
            self.lbl_detail_title.configure(text="Chọn một tiến trình trong danh sách để xem chi tiết hoặc kết thúc tác vụ.")
            self.lbl_detail_sub.configure(text="")
            self.btn_stop.configure(state="disabled")
            return

        name = item.get("name", "--")
        pid = item.get("pid", "--")
        cpu = item.get("cpu_str", "--")
        ram = item.get("mem_str", "--")
        user = item.get("username", "--")
        can_stop = item.get("can_stop", False)
        reason = item.get("protected_reason") or ""
        created = format_time_str(item.get("created"))

        self.lbl_detail_title.configure(text=f"Tiến trình: {name} (PID: {pid}) • Người dùng: {user} • RAM: {ram} • CPU: {cpu}")

        if can_stop:
            self.lbl_detail_sub.configure(
                text=f"Khởi chạy: {created} • Ứng dụng người dùng hiện tại, có thể dừng khi cần.",
                text_color=COLOR_TEXT_MUTED,
            )
            self.btn_stop.configure(state="normal")
        else:
            self.lbl_detail_sub.configure(
                text=f"Khởi chạy: {created} • Không thể dừng: {reason or 'Tiến trình hệ thống hoặc được bảo vệ.'}",
                text_color=COLOR_DANGER,
            )
            self.btn_stop.configure(state="disabled")

    def _on_stop_clicked(self):
        if not self._selected_process:
            return
        p = self._selected_process
        if not p.get("can_stop"):
            messagebox.showwarning(
                "Không thể dừng",
                f"Tiến trình '{p.get('name')}' không thể kết thúc:\n{p.get('protected_reason') or 'Tiến trình hệ thống được bảo vệ.'}",
                parent=self,
            )
            return

        msg = (
            f"CẢNH BÁO MẤT DỮ LIỆU\n\n"
            f"Bạn có chắc chắn muốn kết thúc tiến trình:\n"
            f"• Tên: {p.get('name')}\n"
            f"• PID: {p.get('pid')}\n\n"
            f"Mọi dữ liệu chưa được lưu trong ứng dụng này có thể bị mất!"
        )
        if messagebox.askyesno("Xác nhận kết thúc tiến trình", msg, icon="warning", parent=self):
            self.app.stop_process(p.get("pid"), p.get("created"), p.get("name"))


# ==============================================================================
# 3. TRANG KHỞI ĐỘNG (STARTUP PAGE)
# ==============================================================================
class StartupPage(ctk.CTkFrame):
    """
    Trang quản lý các ứng dụng tự khởi động cùng Windows.
    Đúng phạm vi: Quản lý khóa Run của HKCU có bản lưu phục hồi.
    Các mục HKLM, thư mục Startup chỉ xem; Windows có thể còn quản lý riêng.
    Không hứa bao quát dịch vụ hoặc lịch tác vụ.
    """

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app
        self._selected_item = None
        self._build_ui()

    def _build_ui(self):
        # 1. Thanh điều khiển
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 10))

        self.search_entry = ctk.CTkEntry(
            top_bar,
            placeholder_text="Tìm kiếm ứng dụng khởi động…",
            width=300,
            height=36,
            corner_radius=10,
            font=FONT_BODY,
        )
        self.search_entry.pack(side="left", padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", lambda _e: self.table.set_filter(self.search_entry.get()))

        self.lbl_count = ctk.CTkLabel(top_bar, text="Đang tải…", font=FONT_BODY, text_color=COLOR_TEXT_MUTED)
        self.lbl_count.pack(side="left")

        btn_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        btn_box.pack(side="right")

        self.btn_sys_startup = ctk.CTkButton(
            btn_box,
            text="Mở Trình quản lý Windows",
            command=lambda: self.app.open_tool("startup"),
            width=180,
            height=36,
            corner_radius=10,
            font=FONT_BODY_BOLD,
            fg_color=("#E4E4E7", "#27272B"),
            hover_color=("#D4D4D8", "#36363B"),
            text_color=COLOR_TEXT_MAIN,
        )
        self.btn_sys_startup.pack(side="left", padx=(0, 8))

        self.btn_refresh = ctk.CTkButton(
            btn_box,
            text="Làm mới",
            command=self.app.refresh_startup,
            width=90,
            height=36,
            corner_radius=10,
            font=FONT_BODY_BOLD,
            fg_color=COLOR_ACCENT_BUTTON,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_BUTTON_TEXT,
        )
        self.btn_refresh.pack(side="left")

        # 2. Bảng ứng dụng khởi động
        cols = [
            ("name", "Tên chương trình", 220, "w", "str"),
            ("status_str", "Trạng thái", 110, "center", "str"),
            ("scope", "Phạm vi", 130, "w", "str"),
            ("can_toggle_str", "Quyền sửa", 120, "w", "str"),
            ("command", "Lệnh thực thi", 340, "w", "str"),
        ]
        self.table = DataTable(self, columns=cols, id_column="id", on_select=self._on_row_select)
        self.table.pack(fill="both", expand=True, pady=(0, 10))
        self.table.set_empty_message("Đang tải danh sách khởi động…")

        # 3. Khung chi tiết và nút Bật / Tắt khởi động
        self.detail_card = ctk.CTkFrame(
            self,
            fg_color=COLOR_SURFACE,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        self.detail_card.pack(fill="x")

        det_inner = ctk.CTkFrame(self.detail_card, fg_color="transparent")
        det_inner.pack(fill="x", padx=16, pady=12)

        info_box = ctk.CTkFrame(det_inner, fg_color="transparent")
        info_box.pack(side="left", fill="x", expand=True)

        self.lbl_det_title = ctk.CTkLabel(
            info_box,
            text="Chọn một mục trong bảng để quản lý quyền khởi động.",
            font=FONT_BODY_BOLD,
            text_color=COLOR_TEXT_MAIN,
            anchor="w",
        )
        self.lbl_det_title.pack(fill="x")

        self.lbl_det_sub = ctk.CTkLabel(
            info_box,
            text="Ứng dụng quản lý các mục Run của người dùng (HKCU) có bản sao lưu phục hồi. "
            "Windows có thể còn chặn riêng; dịch vụ và lịch tác vụ hệ thống cần mở công cụ Windows.",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
            wraplength=650,
            justify="left",
        )
        self.lbl_det_sub.pack(fill="x", pady=(2, 0))

        self.btn_toggle = ctk.CTkButton(
            det_inner,
            text="Tắt khởi động",
            command=self._on_toggle_clicked,
            width=140,
            height=36,
            corner_radius=10,
            font=FONT_BODY_BOLD,
            fg_color=COLOR_ACCENT_BUTTON,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_BUTTON_TEXT,
            state="disabled",
        )
        self.btn_toggle.pack(side="right", padx=(12, 0))

    def apply_theme(self, theme):
        self.table.apply_theme(theme)

    def update_startup_items(self, items):
        if items is None:
            self.table.set_empty_message("Chưa đọc được danh sách khởi động.")
            self.table.set_data([])
            self.lbl_count.configure(text="0 mục")
            return

        enabled_count = 0
        formatted = []
        for it in items:
            enabled = bool(it.get("enabled", False))
            if enabled:
                enabled_count += 1
            can_toggle = bool(it.get("can_toggle", False))

            row = dict(it)
            row["status_str"] = "Đang bật" if enabled else "Đã tắt"
            row["can_toggle_str"] = "Có thể bật/tắt" if can_toggle else "Chỉ xem"
            formatted.append(row)

        self.table.set_empty_message("Không có chương trình khởi động nào.")
        self.table.set_data(formatted)
        self.lbl_count.configure(text=f"Tổng số: {len(items)} mục ({enabled_count} đang bật)")

        sel = self.table.get_selected_item()
        self._on_row_select(sel)

    def _on_row_select(self, item):
        self._selected_item = item
        if not item:
            self.lbl_det_title.configure(text="Chọn một mục trong bảng để quản lý quyền khởi động.")
            self.lbl_det_sub.configure(
                text="Ứng dụng quản lý các mục Run của người dùng (HKCU) có bản sao lưu phục hồi. "
                "Windows có thể còn chặn riêng; dịch vụ và lịch tác vụ hệ thống cần mở công cụ Windows."
            )
            self.btn_toggle.configure(state="disabled", text="Tắt khởi động")
            return

        name = item.get("name") or "Không tên"
        enabled = bool(item.get("enabled", False))
        can_toggle = bool(item.get("can_toggle", False))
        scope = item.get("scope", "--")
        cmd = item.get("command", "--")
        note = item.get("note") or ""

        self.lbl_det_title.configure(text=f"{name} ({scope}) • Trạng thái: {'Đang bật' if enabled else 'Đã tắt'}")

        if can_toggle:
            btn_txt = "Tắt khởi động" if enabled else "Bật lại"
            btn_col = COLOR_DANGER if enabled else COLOR_ACCENT
            btn_hover = COLOR_DANGER_HOVER if enabled else COLOR_ACCENT_HOVER
            self.btn_toggle.configure(state="normal", text=btn_txt, fg_color=btn_col, hover_color=btn_hover)
            self.lbl_det_sub.configure(
                text=f"Lệnh: {cmd}\n"
                f"{note} (Thao tác có lưu sao lưu bền vững; Windows có thể còn quản lý trạng thái riêng của mục này).",
                text_color=COLOR_TEXT_MUTED,
            )
        else:
            self.btn_toggle.configure(state="disabled", text="Chỉ xem", fg_color=("#94A3B8", "#475569"))
            self.lbl_det_sub.configure(
                text=f"Lệnh: {cmd}\n"
                f"Chỉ xem: {note or 'Mục toàn máy hoặc thư mục hệ thống. Dịch vụ và tác vụ định kỳ cần mở Cài đặt Windows để quản lý.'}",
                text_color=COLOR_TEXT_MUTED,
            )

    def _on_toggle_clicked(self):
        if not self._selected_item:
            return
        it = self._selected_item
        if not it.get("can_toggle"):
            return

        name = it.get("name", "chương trình")
        current_enabled = bool(it.get("enabled", False))
        new_enabled = not current_enabled
        action_verb = "bật lại" if new_enabled else "tắt tự khởi động"

        msg = (
            f"XÁC NHẬN THAY ĐỔI KHỞI ĐỘNG\n\n"
            f"Bạn có chắc chắn muốn {action_verb} chương trình '{name}'?\n\n"
            f"• Phạm vi: Khóa Run người dùng (HKCU) - Có bản lưu dự phòng để khôi phục.\n"
            f"• Lưu ý: Windows hoặc phần mềm bảo mật có thể còn quản lý trạng thái riêng của mục này."
        )
        if messagebox.askyesno("Xác nhận", msg, parent=self):
            self.app.toggle_startup(it.get("id"), new_enabled, name)


# ==============================================================================
# 4. TRANG ỨNG DỤNG (APPS PAGE)
# ==============================================================================
class AppsPage(ctk.CTkFrame):
    """
    Trang xem danh sách phần mềm đã cài đặt trên máy tính.
    Đúng phạm vi: Ứng dụng desktop từ Registry; ứng dụng Store mở trong Cài đặt Windows;
    gỡ cài đặt qua nút mở Cài đặt Windows chính thức, không can thiệp lệnh registry trực tiếp.
    """

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app
        self._selected_app = None
        self._build_ui()

    def _build_ui(self):
        # 1. Thanh tìm kiếm và công cụ
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 10))

        self.search_entry = ctk.CTkEntry(
            top_bar,
            placeholder_text="Tìm kiếm ứng dụng desktop, nhà phát hành…",
            width=320,
            height=36,
            corner_radius=10,
            font=FONT_BODY,
        )
        self.search_entry.pack(side="left", padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", lambda _e: self.table.set_filter(self.search_entry.get()))

        self.lbl_count = ctk.CTkLabel(top_bar, text="Đang tải danh sách…", font=FONT_BODY, text_color=COLOR_TEXT_MUTED)
        self.lbl_count.pack(side="left")

        btn_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        btn_box.pack(side="right")

        self.btn_windows_apps = ctk.CTkButton(
            btn_box,
            text="Quản lý / gỡ bằng Windows",
            command=lambda: self.app.open_tool("apps"),
            width=230,
            height=36,
            corner_radius=10,
            font=FONT_BODY_BOLD,
            fg_color=("#E4E4E7", "#27272B"),
            hover_color=("#D4D4D8", "#36363B"),
            text_color=COLOR_TEXT_MAIN,
        )
        self.btn_windows_apps.pack(side="left", padx=(0, 8))

        self.btn_refresh = ctk.CTkButton(
            btn_box,
            text="Làm mới",
            command=self.app.refresh_apps,
            width=90,
            height=36,
            corner_radius=10,
            font=FONT_BODY_BOLD,
            fg_color=COLOR_ACCENT_BUTTON,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_BUTTON_TEXT,
        )
        self.btn_refresh.pack(side="left")

        # 2. Bảng ứng dụng
        cols = [
            ("name", "Tên phần mềm", 280, "w", "str"),
            ("version", "Phiên bản", 130, "w", "str"),
            ("publisher", "Nhà phát hành", 200, "w", "str"),
            ("size_str", "Dung lượng", 110, "e", "bytes"),
            ("install_location", "Vị trí cài đặt", 260, "w", "str"),
        ]
        self.table = DataTable(self, columns=cols, id_column="_identity", on_select=self._on_row_select)
        self.table.pack(fill="both", expand=True, pady=(0, 10))
        self.table.set_empty_message("Đang tải danh sách ứng dụng đã cài đặt…")

        # 3. Khung chi tiết ứng dụng
        self.detail_card = ctk.CTkFrame(
            self,
            fg_color=COLOR_SURFACE,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        self.detail_card.pack(fill="x")

        det_inner = ctk.CTkFrame(self.detail_card, fg_color="transparent")
        det_inner.pack(fill="x", padx=16, pady=12)

        info_box = ctk.CTkFrame(det_inner, fg_color="transparent")
        info_box.pack(side="left", fill="x", expand=True)

        self.lbl_det_title = ctk.CTkLabel(
            info_box,
            text="Chọn một ứng dụng để xem thông tin chi tiết.",
            font=FONT_BODY_BOLD,
            text_color=COLOR_TEXT_MAIN,
            anchor="w",
        )
        self.lbl_det_title.pack(fill="x")

        self.lbl_det_sub = ctk.CTkLabel(
            info_box,
            text="Danh sách desktop đọc từ Registry. Ứng dụng Store nằm trong Cài đặt Windows. Để gỡ bỏ ứng dụng sạch sẽ và an toàn, "
            "hãy nhấn 'Gỡ cài đặt trong Cài đặt Windows' để mở giao diện chính thức của hệ điều hành.",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
            wraplength=650,
            justify="left",
        )
        self.lbl_det_sub.pack(fill="x", pady=(2, 0))

        self.btn_uninstall = ctk.CTkButton(
            det_inner,
            text="Gỡ cài đặt qua Windows",
            command=lambda: self.app.open_tool("apps"),
            width=180,
            height=36,
            corner_radius=10,
            font=FONT_BODY_BOLD,
            fg_color=("#E4E4E7", "#27272B"),
            hover_color=("#D4D4D8", "#36363B"),
            text_color=COLOR_TEXT_MAIN,
        )
        self.btn_uninstall.pack(side="right", padx=(12, 0))

    def apply_theme(self, theme):
        self.table.apply_theme(theme)

    def update_apps(self, app_list):
        if app_list is None:
            self.table.set_empty_message("Chưa lấy được danh sách ứng dụng.")
            self.table.set_data([])
            self.lbl_count.configure(text="0 ứng dụng")
            return

        formatted = []
        for a in app_list:
            size_b = a.get("size_bytes")
            size_str = format_bytes(size_b) if size_b else "--"
            row = dict(a)
            row["_identity"] = repr((a.get("name"), a.get("version"), a.get("publisher")))
            row["size_str"] = size_str
            row["publisher"] = a.get("publisher") or "Không rõ"
            row["version"] = a.get("version") or "--"
            row["install_location"] = a.get("install_location") or "--"
            formatted.append(row)

        self.table.set_empty_message("Không tìm thấy ứng dụng nào khớp với từ khóa.")
        self.table.set_data(formatted)
        self.lbl_count.configure(text=f"Đã tìm thấy {len(app_list)} ứng dụng desktop")

        sel = self.table.get_selected_item()
        self._on_row_select(sel)

    def _on_row_select(self, item):
        self._selected_app = item
        if not item:
            self.lbl_det_title.configure(text="Chọn một ứng dụng để xem thông tin chi tiết.")
            self.lbl_det_sub.configure(
                text="Danh sách gồm ứng dụng desktop từ Registry. Để xem cả ứng dụng Store hoặc gỡ cài đặt, "
                "hãy nhấn 'Gỡ cài đặt trong Cài đặt Windows' để mở giao diện chính thức của hệ điều hành."
            )
            return

        name = item.get("name", "--")
        ver = item.get("version", "--")
        pub = item.get("publisher", "--")
        size = item.get("size_str", "--")
        loc = item.get("install_location", "--")

        self.lbl_det_title.configure(text=f"{name} (Phiên bản: {ver}) • Nhà phát hành: {pub}")
        self.lbl_det_sub.configure(
            text=f"Dung lượng ước tính: {size} • Thư mục: {loc}\n"
            f"Chọn ứng dụng cần gỡ trong cửa sổ Cài đặt Windows."
        )


# ==============================================================================
# 5. TRANG DUNG LƯỢNG (STORAGE PAGE)
# ==============================================================================
class StoragePage(ctk.CTkFrame):
    """Trang phân tích dung lượng ổ đĩa và thư mục trên máy tính."""

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app
        self._scan_result = None
        self._build_ui()

    def _build_ui(self):
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=4, pady=4)

        # 1. Khối danh sách các ổ đĩa trên máy
        drives_card = ctk.CTkFrame(
            self.scroll,
            fg_color=COLOR_SURFACE,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        drives_card.pack(fill="x", pady=(0, 14))

        d_header = ctk.CTkFrame(drives_card, fg_color="transparent")
        d_header.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(d_header, text="Danh sách Ổ đĩa", font=FONT_SECTION_TITLE, text_color=COLOR_TEXT_MAIN).pack(side="left")

        d_btn_box = ctk.CTkFrame(d_header, fg_color="transparent")
        d_btn_box.pack(side="right")

        self.btn_storage_settings = ctk.CTkButton(
            d_btn_box,
            text="Cài đặt Lưu trữ Windows",
            command=lambda: self.app.open_tool("storage"),
            width=170,
            height=32,
            corner_radius=8,
            font=FONT_SMALL_BOLD,
            fg_color=("#E4E4E7", "#27272B"),
            hover_color=("#D4D4D8", "#36363B"),
            text_color=COLOR_TEXT_MAIN,
        )
        self.btn_storage_settings.pack(side="left", padx=(0, 8))

        self.btn_refresh_drives = ctk.CTkButton(
            d_btn_box,
            text="Làm mới ổ đĩa",
            command=self.app.refresh_drives,
            width=120,
            height=32,
            corner_radius=8,
            font=FONT_SMALL_BOLD,
            fg_color=COLOR_ACCENT_BUTTON,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_BUTTON_TEXT,
        )
        self.btn_refresh_drives.pack(side="left")

        self.drives_container = ctk.CTkFrame(drives_card, fg_color="transparent")
        self.drives_container.pack(fill="x", padx=16, pady=(0, 12))

        # 2. Khối Quét phân tích thư mục (Interactive Folder Scanner - Heavy Scan Manual)
        scan_card = ctk.CTkFrame(
            self.scroll,
            fg_color=COLOR_SURFACE,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        scan_card.pack(fill="both", expand=True)

        s_header = ctk.CTkFrame(scan_card, fg_color="transparent")
        s_header.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(
            s_header,
            text="Phân tích chi tiết dung lượng thư mục",
            font=FONT_SECTION_TITLE,
            text_color=COLOR_TEXT_MAIN,
        ).pack(side="left")

        ctk.CTkLabel(
            scan_card,
            text="Chọn một thư mục bất kỳ để tìm ra các thư mục con và tệp lớn nhất đang chiếm dụng không gian.",
            font=FONT_BODY,
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 10))

        # Thanh chọn đường dẫn và nút Quét / Hủy quét
        path_box = ctk.CTkFrame(scan_card, fg_color="transparent")
        path_box.pack(fill="x", padx=16, pady=(0, 12))

        self.entry_scan_path = ctk.CTkEntry(
            path_box,
            placeholder_text="Nhập đường dẫn hoặc bấm nút Chọn thư mục…",
            height=36,
            corner_radius=10,
            font=FONT_BODY,
        )
        self.entry_scan_path.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry_scan_path.insert(0, str(Path.home()))

        self.btn_browse = ctk.CTkButton(
            path_box,
            text="Chọn thư mục…",
            command=self._on_browse_clicked,
            width=130,
            height=36,
            corner_radius=10,
            font=FONT_BODY_BOLD,
            fg_color=("#E4E4E7", "#27272B"),
            hover_color=("#D4D4D8", "#36363B"),
            text_color=COLOR_TEXT_MAIN,
        )
        self.btn_browse.pack(side="left", padx=(0, 8))

        self.btn_start_scan = ctk.CTkButton(
            path_box,
            text="Bắt đầu quét",
            command=self._on_start_scan_clicked,
            width=120,
            height=36,
            corner_radius=10,
            font=FONT_BODY_BOLD,
            fg_color=COLOR_ACCENT_BUTTON,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_BUTTON_TEXT,
        )
        self.btn_start_scan.pack(side="left", padx=(0, 8))

        self.btn_cancel_scan = ctk.CTkButton(
            path_box,
            text="Hủy quét",
            command=self.app.cancel_storage_scan,
            width=100,
            height=36,
            corner_radius=10,
            font=FONT_BODY_BOLD,
            fg_color=COLOR_DANGER_BUTTON,
            hover_color=COLOR_DANGER_HOVER,
            text_color="#FFFFFF",
            state="disabled",
        )
        self.btn_cancel_scan.pack(side="left")

        # Khung tóm tắt kết quả quét
        self.scan_summary = ctk.CTkFrame(
            scan_card,
            fg_color=COLOR_SURFACE_ALT,
            corner_radius=10,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        self.scan_summary.pack(fill="x", padx=16, pady=(0, 12))

        self.lbl_scan_status = ctk.CTkLabel(
            self.scan_summary,
            text="Chưa có lượt quét nào. Hãy chọn thư mục và nhấn 'Bắt đầu quét'.",
            font=FONT_BODY,
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
            wraplength=800,
            justify="left",
        )
        self.lbl_scan_status.pack(fill="x", padx=14, pady=10)

        # 2 Bảng kết quả: Top Thư mục con & Top Tệp lớn nhất
        res_grid = ctk.CTkFrame(scan_card, fg_color="transparent")
        res_grid.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        res_grid.columnconfigure(0, weight=1, uniform="res_col")
        res_grid.columnconfigure(1, weight=1, uniform="res_col")

        left_box = ctk.CTkFrame(res_grid, fg_color="transparent")
        left_box.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        ctk.CTkLabel(left_box, text="Top Thư mục con lớn nhất", font=FONT_BODY_BOLD, text_color=COLOR_TEXT_MAIN, anchor="w").pack(
            fill="x", pady=(0, 6)
        )

        cols_folder = [
            ("name", "Tên thư mục", 150, "w", "str"),
            ("size_str", "Dung lượng", 100, "e", "bytes"),
            ("path", "Đường dẫn", 220, "w", "str"),
        ]
        self.table_folders = DataTable(left_box, columns=cols_folder, id_column="path", on_select=self._on_folder_select)
        self.table_folders.pack(fill="both", expand=True, pady=(0, 6))
        self.table_folders.set_empty_message("Chưa có dữ liệu thư mục.")

        self.btn_open_folder = ctk.CTkButton(
            left_box,
            text="Mở thư mục được chọn trong Explorer",
            command=self._on_open_selected_folder,
            height=32,
            corner_radius=8,
            font=FONT_SMALL_BOLD,
            fg_color=("#E4E4E7", "#27272B"),
            hover_color=("#D4D4D8", "#36363B"),
            text_color=COLOR_TEXT_MAIN,
            state="disabled",
        )
        self.btn_open_folder.pack(fill="x")

        right_box = ctk.CTkFrame(res_grid, fg_color="transparent")
        right_box.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        ctk.CTkLabel(right_box, text="Top Tệp lớn nhất", font=FONT_BODY_BOLD, text_color=COLOR_TEXT_MAIN, anchor="w").pack(
            fill="x", pady=(0, 6)
        )

        cols_file = [
            ("name", "Tên tệp", 150, "w", "str"),
            ("size_str", "Dung lượng", 100, "e", "bytes"),
            ("path", "Đường dẫn", 220, "w", "str"),
        ]
        self.table_files = DataTable(right_box, columns=cols_file, id_column="path", on_select=self._on_file_select)
        self.table_files.pack(fill="both", expand=True, pady=(0, 6))
        self.table_files.set_empty_message("Chưa có dữ liệu tệp.")

        self.btn_open_file_loc = ctk.CTkButton(
            right_box,
            text="Mở vị trí tệp trong Explorer",
            command=self._on_open_selected_file_loc,
            height=32,
            corner_radius=8,
            font=FONT_SMALL_BOLD,
            fg_color=("#E4E4E7", "#27272B"),
            hover_color=("#D4D4D8", "#36363B"),
            text_color=COLOR_TEXT_MAIN,
            state="disabled",
        )
        self.btn_open_file_loc.pack(fill="x")

    def apply_theme(self, theme):
        self.table_folders.apply_theme(theme)
        self.table_files.apply_theme(theme)

    def update_drives(self, drives_list):
        for widget in self.drives_container.winfo_children():
            widget.destroy()

        if not drives_list:
            ctk.CTkLabel(self.drives_container, text="Không có thông tin ổ đĩa.", font=FONT_BODY, text_color=COLOR_TEXT_MUTED).pack(
                pady=10
            )
            return

        for d in drives_list:
            row = ctk.CTkFrame(self.drives_container, fg_color=COLOR_SURFACE_ALT, corner_radius=10)
            row.pack(fill="x", pady=4)

            top = ctk.CTkFrame(row, fg_color="transparent")
            top.pack(fill="x", padx=12, pady=(8, 2))

            dev = d.get("device") or d.get("path") or "Ổ đĩa"
            fstype = d.get("fstype") or ""
            fstype_tag = f"({fstype})" if fstype else ""
            ctk.CTkLabel(top, text=f"{dev} {fstype_tag}", font=FONT_BODY_BOLD, text_color=COLOR_TEXT_MAIN).pack(side="left")

            err = d.get("error")
            pct = d.get("percent")

            if err or pct is None:
                ctk.CTkLabel(top, text="Không thể đọc", font=FONT_SMALL_BOLD, text_color=COLOR_DANGER).pack(side="right")
                ctk.CTkLabel(
                    row,
                    text=err or "Lỗi đọc phân vùng.",
                    font=FONT_SMALL,
                    text_color=COLOR_DANGER,
                    anchor="w",
                ).pack(fill="x", padx=12, pady=(0, 8))
            else:
                pct_str = f"{pct:.1f}%"
                free_s = format_bytes(d.get("free"))
                total_s = format_bytes(d.get("total"))
                used_s = format_bytes(d.get("used"))

                ctk.CTkLabel(top, text=f"{pct_str} đã dùng", font=FONT_BODY_BOLD, text_color=COLOR_ACCENT).pack(side="right")

                prog = ctk.CTkProgressBar(row, height=6, corner_radius=3, fg_color=("#E4E4E7", "#27272B"), progress_color=COLOR_ACCENT)
                prog.set(max(0.0, min(1.0, pct / 100.0)))
                prog.pack(fill="x", padx=12, pady=(2, 6))

                bot = ctk.CTkFrame(row, fg_color="transparent")
                bot.pack(fill="x", padx=12, pady=(0, 8))
                ctk.CTkLabel(bot, text=f"Đã dùng: {used_s} / {total_s}", font=FONT_SMALL, text_color=COLOR_TEXT_MUTED).pack(
                    side="left"
                )
                ctk.CTkLabel(bot, text=f"Còn trống: {free_s}", font=FONT_SMALL, text_color=COLOR_SUCCESS).pack(side="right")

    def _on_browse_clicked(self):
        cur = self.entry_scan_path.get().strip() or str(Path.home())
        path = filedialog.askdirectory(initialdir=cur, title="Chọn thư mục cần phân tích dung lượng", parent=self)
        if path:
            self.entry_scan_path.delete(0, "end")
            self.entry_scan_path.insert(0, path)

    def _on_start_scan_clicked(self):
        path = self.entry_scan_path.get().strip()
        if not path:
            messagebox.showwarning("Chưa chọn đường dẫn", "Vui lòng chọn hoặc nhập đường dẫn thư mục cần quét.", parent=self)
            return

        p = Path(path)
        if not p.exists() or not p.is_dir():
            messagebox.showerror("Đường dẫn không hợp lệ", f"Thư mục không tồn tại:\n{path}", parent=self)
            return

        self.btn_start_scan.configure(state="disabled", text="Đang quét…")
        self.btn_cancel_scan.configure(state="normal")
        self.btn_browse.configure(state="disabled")
        self.lbl_scan_status.configure(
            text=f"Đang phân tích dung lượng thư mục: {path}\nQuá trình có thể mất từ vài giây đến một phút tùy dung lượng…",
            text_color=COLOR_ACCENT,
        )
        self.table_folders.set_data([])
        self.table_files.set_data([])

        self.app.start_storage_scan(path)

    def set_scan_busy(self, is_busy):
        if is_busy:
            self.btn_start_scan.configure(state="disabled", text="Đang quét…")
            self.btn_cancel_scan.configure(state="normal")
            self.btn_browse.configure(state="disabled")
        else:
            self.btn_start_scan.configure(state="normal", text="Bắt đầu quét")
            self.btn_cancel_scan.configure(state="disabled")
            self.btn_browse.configure(state="normal")

    def update_scan_result(self, res):
        self.set_scan_busy(False)
        if not res:
            self.lbl_scan_status.configure(text="Không có kết quả phân tích.", text_color=COLOR_TEXT_MUTED)
            return

        self._scan_result = res
        path = res.get("path", "--")
        tot_bytes = res.get("total_bytes", 0)
        tot_files = res.get("file_count", 0)
        skipped = res.get("skipped", 0)
        partial = res.get("partial", False)
        cancelled = res.get("cancelled", False)

        parts = [f"Thư mục: {path}", f"Tổng dung lượng: {format_bytes(tot_bytes)}", f"Số tệp quét được: {tot_files:,}"]
        notices = []
        if cancelled:
            notices.append("Quét đã bị dừng lại theo yêu cầu của bạn.")
        if partial:
            notices.append("Quét một phần (đạt giới hạn số tệp hoặc thời gian).")
        if skipped:
            notices.append(f"Đã bỏ qua {skipped} tệp/thư mục bị hạn chế hoặc là liên kết.")

        status_text = " • ".join(parts)
        if notices:
            status_text += "\n" + " • ".join(notices)

        self.lbl_scan_status.configure(text=status_text, text_color=COLOR_TEXT_MAIN)

        folders = res.get("folders") or []
        fmt_folders = []
        for f in folders:
            fmt_folders.append({
                "name": f.get("name") or "--",
                "size_str": format_bytes(f.get("bytes")),
                "path": f.get("path") or "",
                "bytes": f.get("bytes", 0),
            })
        self.table_folders.set_data(fmt_folders)

        files = res.get("largest_files") or []
        fmt_files = []
        for fl in files:
            fmt_files.append({
                "name": fl.get("name") or "--",
                "size_str": format_bytes(fl.get("bytes")),
                "path": fl.get("path") or "",
                "bytes": fl.get("bytes", 0),
            })
        self.table_files.set_data(fmt_files)

    def _on_folder_select(self, item):
        if item and item.get("path"):
            self.btn_open_folder.configure(state="normal")
        else:
            self.btn_open_folder.configure(state="disabled")

    def _on_open_selected_folder(self):
        sel = self.table_folders.get_selected_item()
        if sel and sel.get("path"):
            self.app.open_folder(sel.get("path"))

    def _on_file_select(self, item):
        if item and item.get("path"):
            self.btn_open_file_loc.configure(state="normal")
        else:
            self.btn_open_file_loc.configure(state="disabled")

    def _on_open_selected_file_loc(self):
        sel = self.table_files.get_selected_item()
        if sel and sel.get("path"):
            p = Path(sel.get("path"))
            parent_dir = str(p.parent if p.is_file() else p)
            self.app.open_folder(parent_dir)


# ==============================================================================
# 6. TRANG MẠNG (NETWORK PAGE)
# ==============================================================================
class NetworkPage(ctk.CTkFrame):
    """Trang theo dõi tốc độ truyền tải và trạng thái các cổng mạng."""

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app
        self._selected_adapter = None
        self._build_ui()

    def _build_ui(self):
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 10))

        title_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        title_box.pack(side="left")

        ctk.CTkLabel(title_box, text="Giám sát Kết nối & Lưu lượng Mạng", font=FONT_SECTION_TITLE, text_color=COLOR_TEXT_MAIN).pack(
            anchor="w"
        )
        ctk.CTkLabel(
            title_box,
            text="Theo dõi tốc độ tải xuống/tải lên trực tiếp và danh sách các bộ điều hợp mạng.",
            font=FONT_PAGE_SUB,
            text_color=COLOR_TEXT_MUTED,
        ).pack(anchor="w")

        btn_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        btn_box.pack(side="right")

        self.btn_sys_net = ctk.CTkButton(
            btn_box,
            text="Mở Cài đặt Mạng Windows",
            command=lambda: self.app.open_tool("network"),
            width=180,
            height=36,
            corner_radius=10,
            font=FONT_BODY_BOLD,
            fg_color=("#E4E4E7", "#27272B"),
            hover_color=("#D4D4D8", "#36363B"),
            text_color=COLOR_TEXT_MAIN,
        )
        self.btn_sys_net.pack(side="left", padx=(0, 8))

        self.btn_refresh = ctk.CTkButton(
            btn_box,
            text="Làm mới",
            command=self.app.refresh_network,
            width=90,
            height=36,
            corner_radius=10,
            font=FONT_BODY_BOLD,
            fg_color=COLOR_ACCENT_BUTTON,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_BUTTON_TEXT,
        )
        self.btn_refresh.pack(side="left")

        # Khối 4 thẻ tốc độ & lưu lượng mạng
        rates_frame = ctk.CTkFrame(self, fg_color="transparent")
        rates_frame.pack(fill="x", pady=(0, 12))
        for c in range(4):
            rates_frame.columnconfigure(c, weight=1, uniform="net_card")

        self.card_down = MetricCard(rates_frame, "Tốc độ tải xuống (Download)")
        self.card_down.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        self.card_up = MetricCard(rates_frame, "Tốc độ tải lên (Upload)")
        self.card_up.grid(row=0, column=1, sticky="nsew", padx=2)

        self.card_recv = MetricCard(rates_frame, "Tổng dữ liệu nhận")
        self.card_recv.grid(row=0, column=2, sticky="nsew", padx=2)

        self.card_sent = MetricCard(rates_frame, "Tổng dữ liệu gửi")
        self.card_sent.grid(row=0, column=3, sticky="nsew", padx=(4, 0))

        # Bảng danh sách các bộ điều hợp mạng
        cols = [
            ("name", "Bộ điều hợp", 200, "w", "str"),
            ("status_str", "Trạng thái", 110, "center", "str"),
            ("speed_str", "Tốc độ danh định", 120, "e", "int"),
            ("ipv4_str", "Địa chỉ IPv4", 150, "w", "str"),
            ("mac", "Địa chỉ MAC", 140, "center", "str"),
            ("recv_str", "Đã nhận", 110, "e", "bytes"),
            ("sent_str", "Đã gửi", 110, "e", "bytes"),
        ]
        self.table = DataTable(self, columns=cols, id_column="name", on_select=self._on_adapter_select)
        self.table.pack(fill="both", expand=True, pady=(0, 10))
        self.table.set_empty_message("Đang tải danh sách cổng mạng…")

        self.detail_card = ctk.CTkFrame(
            self,
            fg_color=COLOR_SURFACE,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        self.detail_card.pack(fill="x")

        self.lbl_det_title = ctk.CTkLabel(
            self.detail_card,
            text="Chọn một bộ điều hợp mạng để xem cấu hình chi tiết.",
            font=FONT_BODY_BOLD,
            text_color=COLOR_TEXT_MAIN,
            anchor="w",
        )
        self.lbl_det_title.pack(fill="x", padx=16, pady=(12, 4))

        self.lbl_det_sub = ctk.CTkLabel(
            self.detail_card,
            text="",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
            wraplength=800,
            justify="left",
        )
        self.lbl_det_sub.pack(fill="x", padx=16, pady=(0, 12))

    def apply_theme(self, theme):
        self.table.apply_theme(theme)

    def update_network_sample(self, net_dict):
        if not net_dict:
            return

        down_bps = net_dict.get("down_bps")
        up_bps = net_dict.get("up_bps")
        b_recv = net_dict.get("bytes_recv")
        b_sent = net_dict.get("bytes_sent")

        down_txt = f"{format_bytes(down_bps)}/s" if down_bps is not None else "Đang đo…"
        up_txt = f"{format_bytes(up_bps)}/s" if up_bps is not None else "Đang đo…"

        self.card_down.update_data("Tốc độ tải xuống (Download)", down_txt, None, "Đo đạc lưu lượng thực tế ~2s", badge_text="Live")
        self.card_up.update_data("Tốc độ tải lên (Upload)", up_txt, None, "Đo đạc lưu lượng thực tế ~2s", badge_text="Live")
        self.card_recv.update_data("Tổng dữ liệu nhận", format_bytes(b_recv), None, "Kể từ lúc bật máy")
        self.card_sent.update_data("Tổng dữ liệu gửi", format_bytes(b_sent), None, "Kể từ lúc bật máy")

    def update_adapters(self, adapters_list):
        if adapters_list is None:
            self.table.set_empty_message("Chưa tải được danh sách mạng.")
            self.table.set_data([])
            return

        formatted = []
        for ad in adapters_list:
            is_up = bool(ad.get("is_up", False))
            status_str = "Đang kết nối" if is_up else "Đã ngắt"
            speed = ad.get("speed_mbps")
            speed_str = f"{speed} Mbps" if speed and speed > 0 else "--"

            ipv4_list = ad.get("ipv4") or []
            ipv4_str = ", ".join(ipv4_list) if ipv4_list else "--"

            row = dict(ad)
            row["status_str"] = status_str
            row["speed_str"] = speed_str
            row["ipv4_str"] = ipv4_str
            row["mac"] = ad.get("mac") or "--"
            row["recv_str"] = format_bytes(ad.get("bytes_recv"))
            row["sent_str"] = format_bytes(ad.get("bytes_sent"))
            formatted.append(row)

        self.table.set_empty_message("Không có bộ điều hợp mạng nào.")
        self.table.set_data(formatted)

        sel = self.table.get_selected_item()
        self._on_adapter_select(sel)

    def _on_adapter_select(self, item):
        self._selected_adapter = item
        if not item:
            self.lbl_det_title.configure(text="Chọn một bộ điều hợp mạng để xem cấu hình chi tiết.")
            self.lbl_det_sub.configure(text="")
            return

        name = item.get("name", "--")
        status = item.get("status_str", "--")
        mac = item.get("mac", "--")
        speed = item.get("speed_str", "--")
        ipv4 = item.get("ipv4_str", "--")
        recv = item.get("recv_str", "--")
        sent = item.get("sent_str", "--")

        self.lbl_det_title.configure(text=f"Bộ điều hợp: {name} • Trạng thái: {status} • Tốc độ: {speed}")
        self.lbl_det_sub.configure(
            text=f"Địa chỉ MAC: {mac} • Địa chỉ IPv4: {ipv4}\n"
            f"Lưu lượng tích lũy: Nhận {recv} | Gửi {sent}"
        )


# ==============================================================================
# 7. TRANG TỐI ƯU (OPTIMIZE PAGE)
# ==============================================================================
class OptimizePage(ctk.CTkFrame):
    """
    Trang Tối ưu và Bảo dưỡng hệ thống an toàn, minh bạch.
    Quy tắc brief:
    1. Dọn dẹp tệp tạm thời người dùng (Temp Cleanup) là nhiệm vụ chính có preview rõ ràng.
    2. Phím tắt quản lý khởi động.
    3. Bộ chọn kế hoạch nguồn điện (Power Plans) + Khôi phục chế độ trước.
    4. Làm mới bộ nhớ đệm DNS (Flush DNS).
    Tuyệt đối không có RAM boost giả hay chỉnh sửa registry tùy tiện.
    """

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app
        self._temp_token = None
        self._temp_preview = None
        self._power_plans_data = None
        self._build_ui()

    def _build_ui(self):
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=4, pady=4)

        # ----------------------------------------------------------------------
        # MỤC 1 (CHÍNH): DỌN DẸP TỆP TẠM THỜI NGƯỜI DÙNG (USER TEMP CLEANUP)
        # ----------------------------------------------------------------------
        temp_card = ctk.CTkFrame(
            self.scroll,
            fg_color=COLOR_SURFACE,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        temp_card.pack(fill="x", pady=(0, 14))

        t_header = ctk.CTkFrame(temp_card, fg_color="transparent")
        t_header.pack(fill="x", padx=16, pady=(12, 4))

        ctk.CTkLabel(t_header, text="Dọn tệp tạm", font=FONT_SECTION_TITLE, text_color=COLOR_TEXT_MAIN).pack(
            side="left"
        )

        ctk.CTkLabel(
            t_header,
            text="An toàn • Xem trước • Cũ hơn 24 giờ",
            font=FONT_SMALL_BOLD,
            text_color=COLOR_SUCCESS,
            fg_color=COLOR_SUCCESS_BG,
            corner_radius=8,
            padx=8,
            pady=2,
        ).pack(side="right")

        ctk.CTkLabel(
            temp_card,
            text="Hệ thống chỉ quét và đề xuất xóa các tệp tạm thời của người dùng cũ hơn 24 giờ. "
            "Tuyệt đối không can thiệp tệp đang sử dụng, tệp hệ thống Windows hoặc các liên kết junction.",
            font=FONT_BODY,
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
            wraplength=800,
            justify="left",
        ).pack(fill="x", padx=16, pady=(0, 10))

        # Nút hành động quét và dọn dẹp
        t_actions = ctk.CTkFrame(temp_card, fg_color="transparent")
        t_actions.pack(fill="x", padx=16, pady=(0, 10))

        self.btn_scan_temp = ctk.CTkButton(
            t_actions,
            text="Quét tệp tạm",
            command=self._on_scan_temp_clicked,
            width=130,
            height=36,
            corner_radius=10,
            font=FONT_BODY_BOLD,
            fg_color=COLOR_ACCENT_BUTTON,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_BUTTON_TEXT,
        )
        self.btn_scan_temp.pack(side="left", padx=(0, 8))

        self.btn_cancel_temp = ctk.CTkButton(
            t_actions,
            text="Hủy quét",
            command=self.app.cancel_temp_scan,
            width=100,
            height=36,
            corner_radius=10,
            font=FONT_BODY_BOLD,
            fg_color=COLOR_DANGER_BUTTON,
            hover_color=COLOR_DANGER_HOVER,
            text_color="#FFFFFF",
            state="disabled",
        )
        self.btn_cancel_temp.pack(side="left", padx=(0, 12))

        self.btn_clean_temp = ctk.CTkButton(
            t_actions,
            text="Dọn dẹp tệp tạm",
            command=self._on_clean_temp_clicked,
            width=170,
            height=36,
            corner_radius=10,
            font=FONT_BODY_BOLD,
            fg_color=COLOR_DANGER_BUTTON,
            hover_color=COLOR_DANGER_HOVER,
            text_color="#FFFFFF",
            state="disabled",
        )
        self.btn_clean_temp.pack(side="left")

        # Khung tóm tắt và xem trước danh sách tệp
        self.temp_summary_box = ctk.CTkFrame(
            temp_card,
            fg_color=COLOR_SURFACE_ALT,
            corner_radius=10,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        self.temp_summary_box.pack(fill="x", padx=16, pady=(0, 10))

        self.lbl_temp_status = ctk.CTkLabel(
            self.temp_summary_box,
            text="Bấm 'Quét tệp tạm' để xem trước các tệp có thể xóa an toàn.",
            font=FONT_BODY,
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
            wraplength=800,
            justify="left",
        )
        self.lbl_temp_status.pack(fill="x", padx=14, pady=10)

        # Bảng xem trước danh sách tệp tạm
        cols_temp = [
            ("path", "Đường dẫn tệp tạm", 550, "w", "str"),
            ("size_str", "Dung lượng", 110, "e", "bytes"),
        ]
        self.table_temp = DataTable(temp_card, columns=cols_temp, id_column="path", height=180)
        self.table_temp.tree.configure(height=5)
        self.table_temp.pack(fill="x", padx=16, pady=(0, 14))
        self.table_temp.set_empty_message("Chưa có danh sách xem trước.")

        # ----------------------------------------------------------------------
        # MỤC 2: QUẢN LÝ ỨNG DỤNG KHỞI ĐỘNG (STARTUP SHORTCUT)
        # ----------------------------------------------------------------------
        startup_card = ctk.CTkFrame(
            self.scroll,
            fg_color=COLOR_SURFACE,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        startup_card.pack(fill="x", pady=(0, 14))

        s_inner = ctk.CTkFrame(startup_card, fg_color="transparent")
        s_inner.pack(fill="x", padx=16, pady=12)

        s_text = ctk.CTkFrame(s_inner, fg_color="transparent")
        s_text.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(s_text, text="Khởi động cùng Windows", font=FONT_SECTION_TITLE, text_color=COLOR_TEXT_MAIN, anchor="w").pack(
            fill="x"
        )
        ctk.CTkLabel(
            s_text,
            text="Quản lý mục khởi động người dùng: Bật/tắt các mục trong khóa Run HKCU có bản lưu phục hồi. "
            "Không can thiệp dịch vụ hoặc tác vụ hệ thống.",
            font=FONT_BODY,
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
            wraplength=600,
            justify="left",
        ).pack(fill="x", pady=(2, 0))

        s_btns = ctk.CTkFrame(s_inner, fg_color="transparent")
        s_btns.pack(side="right")

        ctk.CTkButton(
            s_btns,
            text="Mở trang Khởi động",
            command=lambda: self.app.switch_page("startup"),
            width=150,
            height=36,
            corner_radius=10,
            font=FONT_BODY_BOLD,
            fg_color=COLOR_ACCENT_BUTTON,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_BUTTON_TEXT,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            s_btns,
            text="Cài đặt Windows",
            command=lambda: self.app.open_tool("startup"),
            width=130,
            height=36,
            corner_radius=10,
            font=FONT_BODY_BOLD,
            fg_color=("#E4E4E7", "#27272B"),
            hover_color=("#D4D4D8", "#36363B"),
            text_color=COLOR_TEXT_MAIN,
        ).pack(side="left")

        # ----------------------------------------------------------------------
        # MỤC 3: CHẾ ĐỘ NGUỒN ĐIỆN & HIỆU NĂNG (POWER PLANS)
        # ----------------------------------------------------------------------
        power_card = ctk.CTkFrame(
            self.scroll,
            fg_color=COLOR_SURFACE,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        power_card.pack(fill="x", pady=(0, 14))

        p_inner = ctk.CTkFrame(power_card, fg_color="transparent")
        p_inner.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(p_inner, text="Chế độ nguồn và hiệu năng", font=FONT_SECTION_TITLE, text_color=COLOR_TEXT_MAIN, anchor="w").pack(
            fill="x"
        )
        ctk.CTkLabel(
            p_inner,
            text="Lựa chọn kế hoạch sử dụng năng lượng có sẵn trên máy để cân bằng giữa tốc độ xử lý và mức tiết kiệm pin. "
            "Thay đổi có thể hoàn tác trong ứng dụng.",
            font=FONT_BODY,
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
            wraplength=800,
            justify="left",
        ).pack(fill="x", pady=(2, 10))

        p_controls = ctk.CTkFrame(p_inner, fg_color="transparent")
        p_controls.pack(fill="x")

        self.power_menu = ctk.CTkOptionMenu(
            p_controls,
            values=["Đang tải danh sách chế độ…"],
            width=260,
            height=36,
            corner_radius=10,
            font=FONT_BODY,
            fg_color=COLOR_SURFACE_ALT,
            button_color=COLOR_ACCENT_BG,
            button_hover_color=("#D4D4D8", "#36363B"),
            text_color=COLOR_TEXT_MAIN,
            dropdown_fg_color=COLOR_SURFACE,
            dropdown_hover_color=COLOR_ACCENT_BG,
            dropdown_text_color=COLOR_TEXT_MAIN,
        )
        self.power_menu.pack(side="left", padx=(0, 10))

        self.btn_apply_power = ctk.CTkButton(
            p_controls,
            text="Áp dụng chế độ",
            command=self._on_apply_power_clicked,
            width=140,
            height=36,
            corner_radius=10,
            font=FONT_BODY_BOLD,
            fg_color=COLOR_ACCENT_BUTTON,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_BUTTON_TEXT,
        )
        self.btn_apply_power.pack(side="left", padx=(0, 8))

        self.btn_restore_power = ctk.CTkButton(
            p_controls,
            text="Khôi phục chế độ trước",
            command=self._on_restore_power_clicked,
            width=170,
            height=36,
            corner_radius=10,
            font=FONT_BODY_BOLD,
            fg_color=("#E4E4E7", "#27272B"),
            hover_color=("#D4D4D8", "#36363B"),
            text_color=COLOR_TEXT_MAIN,
            state="disabled",
        )
        self.btn_restore_power.pack(side="left", padx=(0, 8))

        self.btn_power_tool = ctk.CTkButton(
            p_controls,
            text="Cài đặt Nguồn Windows",
            command=lambda: self.app.open_tool("power"),
            width=170,
            height=36,
            corner_radius=10,
            font=FONT_BODY_BOLD,
            fg_color=("#E4E4E7", "#27272B"),
            hover_color=("#D4D4D8", "#36363B"),
            text_color=COLOR_TEXT_MAIN,
        )
        self.btn_power_tool.pack(side="left")

        # ----------------------------------------------------------------------
        # MỤC 4: LÀM MỚI BỘ NHỚ ĐỆM DNS (FLUSH DNS)
        # ----------------------------------------------------------------------
        dns_card = ctk.CTkFrame(
            self.scroll,
            fg_color=COLOR_SURFACE,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        dns_card.pack(fill="x", pady=(0, 10))

        dns_inner = ctk.CTkFrame(dns_card, fg_color="transparent")
        dns_inner.pack(fill="x", padx=16, pady=12)

        dns_text = ctk.CTkFrame(dns_inner, fg_color="transparent")
        dns_text.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(dns_text, text="Làm mới bộ nhớ đệm DNS (Flush DNS)", font=FONT_SECTION_TITLE, text_color=COLOR_TEXT_MAIN, anchor="w").pack(
            fill="x"
        )
        ctk.CTkLabel(
            dns_text,
            text="Xóa sạch dữ liệu phân giải tên miền đã lưu trên máy. Giúp khắc phục sự cố không truy cập được website "
            "khi máy chủ vừa đổi địa chỉ IP. (Thao tác an toàn, không làm tăng tốc độ internet tổng thể).",
            font=FONT_BODY,
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
            wraplength=600,
            justify="left",
        ).pack(fill="x", pady=(2, 0))

        self.btn_flush_dns = ctk.CTkButton(
            dns_inner,
            text="Làm mới DNS",
            command=self._on_flush_dns_clicked,
            width=150,
            height=36,
            corner_radius=10,
            font=FONT_BODY_BOLD,
            fg_color=COLOR_ACCENT_BUTTON,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_BUTTON_TEXT,
        )
        self.btn_flush_dns.pack(side="right", padx=(12, 0))

    def apply_theme(self, theme):
        self.table_temp.apply_theme(theme)

    # --- TEMP CLEANUP CALLBACKS ---
    def _on_scan_temp_clicked(self):
        self.btn_scan_temp.configure(state="disabled", text="Đang quét…")
        self.btn_cancel_temp.configure(state="normal")
        self.btn_clean_temp.configure(state="disabled")
        self.lbl_temp_status.configure(
            text="Đang quét các tệp tạm thời cũ hơn 24 giờ trong thư mục Temp người dùng…",
            text_color=COLOR_ACCENT,
        )
        self.table_temp.set_data([])
        self.app.start_temp_scan()

    def set_temp_scan_busy(self, is_busy):
        if is_busy:
            self.btn_scan_temp.configure(state="disabled", text="Đang quét…")
            self.btn_cancel_temp.configure(state="normal")
        else:
            self.btn_scan_temp.configure(state="normal", text="Quét tệp tạm")
            self.btn_cancel_temp.configure(state="disabled")

    def update_temp_scan_result(self, res):
        self.set_temp_scan_busy(False)
        if not res:
            self.lbl_temp_status.configure(text="Không có kết quả quét tệp tạm.", text_color=COLOR_TEXT_MUTED)
            self.btn_clean_temp.configure(state="disabled")
            return

        self._temp_preview = res
        self._temp_token = res.get("token")

        count = res.get("count", 0)
        b_val = res.get("bytes", 0)
        skipped = res.get("skipped", 0)
        partial = res.get("partial", False)
        cancelled = res.get("cancelled", False)
        roots = res.get("roots") or []
        roots_str = ", ".join(roots) if roots else "User Temp"

        parts = [f"Tìm thấy: {count:,} tệp ({format_bytes(b_val)})", f"Phạm vi: {roots_str}"]
        if skipped:
            parts.append(f"Bỏ qua: {skipped} tệp/mục chưa đủ điều kiện")
        if partial:
            parts.append("Quét một phần")
        if cancelled:
            parts.append("Đã dừng quét")

        self.lbl_temp_status.configure(text=" • ".join(parts), text_color=COLOR_TEXT_MAIN)

        files = res.get("files") or []
        fmt_files = []
        for f in files:
            fmt_files.append({
                "path": f.get("path") or "",
                "size_str": format_bytes(f.get("bytes")),
                "bytes": f.get("bytes", 0),
            })
        self.table_temp.set_data(fmt_files)

        if count > 0 and self._temp_token:
            self.btn_clean_temp.configure(
                state="normal",
                text=f"Dọn dẹp tệp tạm ({count:,} tệp - {format_bytes(b_val)})",
            )
        else:
            self.btn_clean_temp.configure(state="disabled", text="Không có tệp tạm để dọn")

    def _on_clean_temp_clicked(self):
        if not self._temp_token or not self._temp_preview:
            messagebox.showwarning(
                "Chưa có bản xem trước",
                "Vui lòng quét lại danh sách tệp tạm trước khi thực hiện dọn dẹp.",
                parent=self,
            )
            return

        count = self._temp_preview.get("count", 0)
        b_val = self._temp_preview.get("bytes", 0)

        msg = (
            f"XÁC NHẬN XÓA VĨNH VIỄN TỆP TẠM\n\n"
            f"Hệ thống sẽ XÓA VĨNH VIỄN {count:,} tệp tạm thời ({format_bytes(b_val)}) "
            f"cũ hơn 24 giờ trong thư mục Temp người dùng.\n\n"
            f"Thao tác này KHÔNG THỂ KHÔI PHỤC lại. Bạn có chắc chắn muốn tiếp tục?"
        )
        if messagebox.askyesno("Xác nhận dọn dẹp tệp tạm", msg, icon="warning", parent=self):
            token = self._temp_token
            self._temp_token = None
            self.btn_clean_temp.configure(state="disabled", text="Đang dọn dẹp…")
            self.app.clean_temp(token)

    def on_clean_temp_finished(self, res):
        self._temp_token = None
        self._temp_preview = None
        self.btn_clean_temp.configure(state="disabled", text="Dọn dẹp tệp tạm")
        self.table_temp.set_data([])

        if not res or not res.get("ok"):
            err_msg = res.get("message") if res else "Lỗi không xác định."
            self.lbl_temp_status.configure(
                text=f"Dọn dẹp không thành công: {err_msg}. Vui lòng quét lại.",
                text_color=COLOR_DANGER,
            )
            messagebox.showerror("Lỗi dọn dẹp", f"Không thể hoàn thành dọn dẹp:\n{err_msg}\nHãy bấm 'Quét tệp tạm' để thử lại.", parent=self)
            return

        del_cnt = res.get("deleted_count", 0)
        del_bytes = res.get("deleted_bytes", 0)
        skipped = res.get("skipped", 0)

        report = f"Đã xóa thành công: {del_cnt:,} tệp ({format_bytes(del_bytes)})."
        if skipped:
            report += f" Bỏ qua {skipped} tệp do đang được ứng dụng khác mở."

        self.lbl_temp_status.configure(text=report, text_color=COLOR_SUCCESS)
        messagebox.showinfo("Dọn dẹp hoàn tất", report, parent=self)

    # --- POWER PLANS CALLBACKS ---
    def update_power_plans(self, p_data):
        self._power_plans_data = p_data or {}
        plans = self._power_plans_data.get("plans") or []
        prev = self._power_plans_data.get("previous")

        if not plans:
            self.power_menu.configure(values=["Không lấy được chế độ nguồn"])
            self.btn_apply_power.configure(state="disabled")
            self.btn_restore_power.configure(state="disabled")
            return

        names = []
        self._power_choices = {}
        active_name = None
        for p in plans:
            name = p.get("name") or p.get("guid")
            if p.get("active"):
                name_display = f"{name} (Đang dùng)"
                active_name = name_display
            else:
                name_display = name
            if name_display in self._power_choices:
                name_display += f" [{p.get('guid', '')[:8]}]"
            self._power_choices[name_display] = p
            names.append(name_display)

        self.power_menu.configure(values=names)
        if active_name:
            self.power_menu.set(active_name)
        elif names:
            self.power_menu.set(names[0])

        self.btn_apply_power.configure(state="normal")
        if prev:
            self.btn_restore_power.configure(state="normal")
        else:
            self.btn_restore_power.configure(state="disabled")

    def _on_apply_power_clicked(self):
        if not self._power_plans_data:
            return
        selected_display = self.power_menu.get()
        plans = self._power_plans_data.get("plans") or []

        target_plan = self._power_choices.get(selected_display)

        if not target_plan:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn một chế độ nguồn điện.", parent=self)
            return

        if target_plan.get("active"):
            messagebox.showinfo("Thông báo", f"Chế độ '{target_plan.get('name')}' đang được sử dụng.", parent=self)
            return

        p_name = target_plan.get("name")
        guid = target_plan.get("guid")
        msg = (
            f"XÁC NHẬN ĐỔI CHẾ ĐỘ NGUỒN ĐIỆN\n\n"
            f"Bạn có muốn chuyển sang chế độ: '{p_name}'?\n\n"
            f"Thao tác này có thể ảnh hưởng đến tốc độ xử lý phần cứng và thời lượng dùng pin của máy."
        )
        if messagebox.askyesno("Xác nhận đổi chế độ", msg, parent=self):
            self.app.set_power_plan(guid, p_name)

    def _on_restore_power_clicked(self):
        msg = "Bạn có chắc chắn muốn khôi phục lại chế độ nguồn điện đã lưu trước đó không?"
        if messagebox.askyesno("Khôi phục chế độ nguồn", msg, parent=self):
            self.app.restore_power_plan()

    # --- FLUSH DNS CALLBACK ---
    def _on_flush_dns_clicked(self):
        msg = (
            f"XÁC NHẬN LÀM MỚI BỘ NHỚ ĐỆM DNS\n\n"
            f"Bạn có muốn xóa sạch bộ nhớ đệm phân giải tên miền (DNS Cache) của Windows không?\n\n"
            f"(Thao tác này an toàn và giúp khắc phục sự cố không vào được website khi vừa đổi mạng)."
        )
        if messagebox.askyesno("Làm mới DNS", msg, parent=self):
            self.app.flush_dns()


# ==============================================================================
# 8. TRANG LỊCH SỬ (HISTORY PAGE)
# ==============================================================================
class HistoryPage(ctk.CTkFrame):
    """Trang nhật ký các thao tác tối ưu và bảo dưỡng máy tính."""

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app
        self._selected_item = None
        self._build_ui()

    def _build_ui(self):
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 10))

        title_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        title_box.pack(side="left")

        ctk.CTkLabel(title_box, text="Nhật ký Hoạt động Hệ thống", font=FONT_SECTION_TITLE, text_color=COLOR_TEXT_MAIN).pack(
            anchor="w"
        )
        self.lbl_count = ctk.CTkLabel(
            title_box,
            text="Ghi nhận các thao tác dọn dẹp, thay đổi chế độ pin, và bật/tắt khởi động.",
            font=FONT_PAGE_SUB,
            text_color=COLOR_TEXT_MUTED,
        )
        self.lbl_count.pack(anchor="w")

        btn_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        btn_box.pack(side="right")

        self.btn_export = ctk.CTkButton(
            btn_box,
            text="Xuất báo cáo JSON...",
            command=self.app.export_report,
            width=160,
            height=36,
            corner_radius=10,
            font=FONT_BODY_BOLD,
            fg_color=("#E4E4E7", "#27272B"),
            hover_color=("#D4D4D8", "#36363B"),
            text_color=COLOR_TEXT_MAIN,
        )
        self.btn_export.pack(side="left", padx=(0, 8))

        self.btn_refresh = ctk.CTkButton(
            btn_box,
            text="Làm mới",
            command=self.app.refresh_history,
            width=90,
            height=36,
            corner_radius=10,
            font=FONT_BODY_BOLD,
            fg_color=COLOR_ACCENT_BUTTON,
            hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_BUTTON_TEXT,
        )
        self.btn_refresh.pack(side="left")

        # Bảng lịch sử
        cols = [
            ("at_str", "Thời gian", 160, "center", "str"),
            ("action", "Hành động thực hiện", 220, "w", "str"),
            ("status_str", "Kết quả", 110, "center", "str"),
            ("message", "Chi tiết thông báo", 420, "w", "str"),
        ]
        self.table = DataTable(self, columns=cols, id_column="id", on_select=self._on_row_select)
        self.table.pack(fill="both", expand=True, pady=(0, 10))
        self.table.set_empty_message("Chưa có hoạt động nào được ghi nhận.")

        self.detail_card = ctk.CTkFrame(
            self,
            fg_color=COLOR_SURFACE,
            corner_radius=14,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        self.detail_card.pack(fill="x")

        self.lbl_det_title = ctk.CTkLabel(
            self.detail_card,
            text="Chọn một sự kiện trong bảng để xem toàn bộ nội dung phản hồi.",
            font=FONT_BODY_BOLD,
            text_color=COLOR_TEXT_MAIN,
            anchor="w",
        )
        self.lbl_det_title.pack(fill="x", padx=16, pady=(12, 4))

        self.lbl_det_sub = ctk.CTkLabel(
            self.detail_card,
            text="",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
            wraplength=800,
            justify="left",
        )
        self.lbl_det_sub.pack(fill="x", padx=16, pady=(0, 12))

    def apply_theme(self, theme):
        self.table.apply_theme(theme)

    def update_history(self, history_list):
        if not history_list:
            self.table.set_empty_message("Chưa có hoạt động nào được ghi nhận.")
            self.table.set_data([])
            self.lbl_count.configure(text="0 hoạt động được ghi nhận.")
            return

        formatted = []
        for i, item in enumerate(history_list):
            at_raw = item.get("at")
            at_str = format_time_str(at_raw)
            ok = bool(item.get("ok", True))
            status_str = "Thành công" if ok else "Thất bại"

            row = dict(item)
            row["id"] = f"{at_raw}_{i}"
            row["at_str"] = at_str
            row["status_str"] = status_str
            formatted.append(row)

        self.table.set_data(formatted)
        self.lbl_count.configure(text=f"Ghi nhận {len(history_list)} hoạt động tối ưu và thay đổi hệ thống.")

        sel = self.table.get_selected_item()
        self._on_row_select(sel)

    def _on_row_select(self, item):
        self._selected_item = item
        if not item:
            self.lbl_det_title.configure(text="Chọn một sự kiện trong bảng để xem toàn bộ nội dung phản hồi.")
            self.lbl_det_sub.configure(text="")
            return

        action = item.get("action", "--")
        at = item.get("at_str", "--")
        status = item.get("status_str", "--")
        msg = item.get("message", "--")

        self.lbl_det_title.configure(text=f"[{status}] {action} • Thời điểm: {at}")
        self.lbl_det_sub.configure(text=f"Chi tiết kết quả:\n{msg}")
