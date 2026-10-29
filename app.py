"""
PC Monitor Mini - Giao diện Desktop Giám sát Hệ thống Hiện đại kiểu Windows 11.
Phiên bản 1.1.0 hỗ trợ Biểu đồ Lịch sử CPU/RAM và Chế độ Sáng / Tối (Light / Dark).
"""

from pathlib import Path
import queue
import threading
from datetime import datetime
import tkinter as tk
import customtkinter as ctk

from monitor import VERSION, format_gib, read_metrics, MetricHistory, load_theme, save_theme
from charts import ResourceChartsFrame

# Hằng số tự động làm mới định kỳ (mili-giây)
AUTO_REFRESH_MS = 2000

# --- PHẦN 1: BẢNG MÀU SẮC, PHÔNG CHỮ & TIỆN ÍCH DỮ LIỆU ---
COLOR_BG = ("#F4F6FA", "#0B1220")
COLOR_CARD = ("#FFFFFF", "#131F32")
COLOR_BORDER = ("#E8ECF2", "#26344C")
COLOR_TEXT_MAIN = ("#182133", "#E8EEFB")
COLOR_TEXT_MUTED = ("#556278", "#A5B4CC")
COLOR_ACCENT = ("#2563EB", "#3B82F6")
COLOR_ACCENT_HOVER = ("#1D4ED8", "#2563EB")
COLOR_DANGER = ("#B91C1C", "#F87171")
COLOR_DANGER_BG = ("#FEF2F2", "#3B181E")

FONT_MAIN = "Segoe UI"
FONT_TITLE = (FONT_MAIN, 20, "bold")
FONT_SUB = (FONT_MAIN, 12)
FONT_CARD_TITLE = (FONT_MAIN, 13, "bold")
FONT_METRIC = (FONT_MAIN, 30, "bold")
FONT_STATUS = (FONT_MAIN, 11, "bold")
FONT_BODY = (FONT_MAIN, 12)
FONT_BOLD = (FONT_MAIN, 12, "bold")


def get_status_info(percent):
    """Xác định trạng thái chữ, màu chữ tuple, màu nền pill tuple và màu thanh tiến trình tuple."""
    if percent is None:
        return "Không có dữ liệu", ("#556278", "#A5B4CC"), ("#F1F5F9", "#1A273D"), ("#CBD5E1", "#334155")
    if percent < 60:
        return "Đang dùng ít", ("#1D4ED8", "#60A5FA"), ("#EFF6FF", "#172A46"), ("#2563EB", "#3B82F6")
    if percent < 85:
        return "Trung bình", ("#B45309", "#FBBF24"), ("#FFFBEB", "#382811"), ("#F59E0B", "#F59E0B")
    return "Đang dùng nhiều", ("#B91C1C", "#F87171"), ("#FEF2F2", "#3B181E"), ("#EF4444", "#EF4444")


def truncate_text(text, max_len=30):
    """Rút gọn chuỗi dài để không làm vỡ hoặc tràn giao diện cửa sổ."""
    val = str(text) if text is not None else "--"
    return val if len(val) <= max_len else val[: max_len - 3] + "..."


def format_time(iso_str):
    """Chuyển chuỗi ISO timestamp sang định dạng giờ:phút:giây."""
    if not iso_str:
        return "--:--:--"
    try:
        return datetime.fromisoformat(iso_str).strftime("%H:%M:%S")
    except (TypeError, ValueError):
        return iso_str


# --- PHẦN 2: LỚP ỨNG DỤNG GIAO DIỆN CHÍNH (MAIN APPLICATION) ---
class MonitorApp(ctk.CTk):
    """Cửa sổ chính giám sát hiệu năng với phong cách bo góc hiện đại và biểu đồ."""

    AUTO_REFRESH_MS = AUTO_REFRESH_MS

    def __init__(self):
        super().__init__()
        self.title("PC Monitor Mini")
        self.geometry("1000x740")
        self.minsize(860, 700)

        # 1. Tải và thiết lập chế độ Sáng / Tối trước khi dựng UI
        self.theme = load_theme()
        ctk.set_appearance_mode(self.theme)
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=COLOR_BG)

        # Biểu tượng ứng dụng nếu có
        ico_path = Path(__file__).parent / "assets" / "app.ico"
        if ico_path.exists():
            try:
                self.iconbitmap(str(ico_path))
            except Exception:
                pass

        # 2. Khởi tạo cấu trúc dữ liệu và hàng đợi đa luồng
        self.history = MetricHistory()
        self._queue = queue.Queue()
        self._reading, self._is_closing = False, False
        self._last_metrics = None
        self._poll_id = None
        self._startup_id = None
        self._auto_id = None

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_ui()

        # Phím tắt chuyển đổi chế độ giao diện
        self.bind("<Control-t>", lambda _e: self.set_theme("Dark" if self.theme == "Light" else "Light"))
        self.bind("<Control-T>", lambda _e: self.set_theme("Dark" if self.theme == "Light" else "Light"))

        # Tự động đọc dữ liệu mẫu đầu tiên sau khi khởi động
        self._startup_id = self.after(100, self.refresh)

    # --- PHẦN 3: XÂY DỰNG CÁC KHỐI GIAO DIỆN (UI COMPONENTS) ---
    def _build_ui(self):
        """Khởi tạo toàn bộ bố cục: Header, Panel tóm tắt máy, 3 Thẻ số liệu, Biểu đồ và Footer."""
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=24, pady=16)

        # 1. Header: Biểu tượng PC, Tiêu đề, Segmented Button Sáng/Tối và Nút Làm mới
        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))

        header_left = ctk.CTkFrame(header, fg_color="transparent")
        header_left.pack(side="left", anchor="w")

        pc_mark = ctk.CTkFrame(header_left, width=38, height=38, corner_radius=10, fg_color="#2563EB")
        pc_mark.pack(side="left", padx=(0, 10))
        pc_mark.pack_propagate(False)
        ctk.CTkLabel(pc_mark, text="PC", font=(FONT_MAIN, 13, "bold"), text_color="#FFFFFF").pack(expand=True)

        title_box = ctk.CTkFrame(header_left, fg_color="transparent")
        title_box.pack(side="left")
        ctk.CTkLabel(title_box, text="PC Monitor Mini", font=FONT_TITLE, text_color=COLOR_TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(title_box, text="Bảng theo dõi hiệu năng hệ thống", font=FONT_SUB, text_color=COLOR_TEXT_MUTED).pack(anchor="w")

        controls_box = ctk.CTkFrame(header, fg_color="transparent")
        controls_box.pack(side="right", anchor="e")

        self.theme_control = ctk.CTkSegmentedButton(
            controls_box,
            values=["Sáng", "Tối"],
            command=self._on_theme_select,
            width=130,
            height=36,
            corner_radius=10,
            font=FONT_BOLD,
            fg_color=("#E7EDF5", "#1A2A44"),
            selected_color="#2563EB",
            selected_hover_color="#1D4ED8",
            unselected_color=("#E7EDF5", "#1A2A44"),
            unselected_hover_color=("#D7E2F2", "#263B5B"),
            text_color=COLOR_TEXT_MAIN,
        )
        self.theme_control.set("Sáng" if self.theme == "Light" else "Tối")
        self._style_theme_control()
        self.theme_control.pack(side="left", padx=(0, 10))
        self._bind_segmented_keys(self.theme_control)

        self.btn_refresh = ctk.CTkButton(
            controls_box,
            text="Làm mới",
            command=self.refresh,
            width=100,
            height=36,
            corner_radius=10,
            font=FONT_BOLD,
            fg_color="#2563EB",
            hover_color=COLOR_ACCENT_HOVER,
        )
        self.btn_refresh.pack(side="left")
        self.btn_refresh.bind("<Return>", lambda _e: self.refresh())
        self.btn_refresh.bind("<space>", lambda _e: self.refresh())
        self._focus_buttons = [*self.theme_control._buttons_dict.values(), self.btn_refresh]
        self.bind("<Tab>", lambda _e: self._focus_next(1))
        self.bind("<Shift-Tab>", lambda _e: self._focus_next(-1))
        for button in self._focus_buttons:
            button.bind("<FocusIn>", lambda _e, b=button: b.configure(border_width=2, border_color=("#172554", "#93C5FD")))
            button.bind("<FocusOut>", lambda _e, b=button: b.configure(border_width=0))

        # 2. Panel tóm tắt thông tin máy tính
        summary_panel = ctk.CTkFrame(container, fg_color=COLOR_CARD, corner_radius=16, border_width=1, border_color=COLOR_BORDER)
        summary_panel.pack(fill="x", pady=(0, 10))

        row_top = ctk.CTkFrame(summary_panel, fg_color="transparent")
        row_top.pack(fill="x", padx=16, pady=(10, 2))

        ctk.CTkLabel(row_top, text="Thiết bị:", font=FONT_BODY, text_color=COLOR_TEXT_MUTED).pack(side="left", padx=(0, 6))
        self.lbl_machine = ctk.CTkLabel(row_top, text="--", font=(FONT_MAIN, 15, "bold"), text_color=COLOR_TEXT_MAIN)
        self.lbl_machine.pack(side="left")

        self.lbl_os = ctk.CTkLabel(row_top, text="--", font=FONT_BODY, text_color=COLOR_TEXT_MUTED, fg_color=("#F1F5F9", "#1A273D"), corner_radius=8, padx=8, pady=2)
        self.lbl_os.pack(side="right")
        self.lbl_cpu_threads = ctk.CTkLabel(row_top, text="--", font=FONT_BODY, text_color=COLOR_TEXT_MUTED, fg_color=("#F1F5F9", "#1A273D"), corner_radius=8, padx=8, pady=2)
        self.lbl_cpu_threads.pack(side="right", padx=(0, 8))

        row_bot = ctk.CTkFrame(summary_panel, fg_color="transparent")
        row_bot.pack(fill="x", padx=16, pady=(0, 10))
        ctk.CTkLabel(row_bot, text="Bộ xử lý:", font=FONT_BODY, text_color=COLOR_TEXT_MUTED).pack(side="left", padx=(0, 6))
        self.lbl_cpu_model = ctk.CTkLabel(row_bot, text="--", font=FONT_BODY, text_color=COLOR_TEXT_MAIN, anchor="w", justify="left")
        self.lbl_cpu_model.pack(side="left", fill="x")

        # Băng thông báo lỗi trong cửa sổ (ẩn mặc định)
        self.lbl_error = ctk.CTkLabel(
            container,
            text="",
            font=FONT_BODY,
            text_color=COLOR_DANGER,
            fg_color=COLOR_DANGER_BG,
            corner_radius=10,
            height=32,
            anchor="w",
            padx=14,
            justify="left",
            wraplength=720,
        )
        container.bind("<Configure>", lambda e: self.lbl_error.configure(wraplength=max(200, e.width - 60)))

        # 3. Khối 3 thẻ số liệu gọn gàng (CPU, RAM, Ổ đĩa hệ thống)
        self.cards_frame = ctk.CTkFrame(container, fg_color="transparent")
        self.cards_frame.pack(fill="x", pady=(0, 10))
        for col in range(3):
            self.cards_frame.columnconfigure(col, weight=1, uniform="metric_card")
        self.cards_frame.rowconfigure(0, weight=1)

        c_cpu, _, self.lbl_cpu_percent, self.prog_cpu, self.lbl_cpu_status, self.lbl_cpu_detail = self._create_card(
            self.cards_frame, "Bộ xử lý CPU"
        )
        c_cpu.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        c_ram, _, self.lbl_ram_percent, self.prog_ram, self.lbl_ram_status, self.lbl_ram_detail = self._create_card(
            self.cards_frame, "Bộ nhớ RAM"
        )
        c_ram.grid(row=0, column=1, sticky="nsew", padx=3)

        c_disk, self.lbl_disk_title, self.lbl_disk_percent, self.prog_disk, self.lbl_disk_status, self.lbl_disk_detail = self._create_card(
            self.cards_frame, "Ổ đĩa hệ thống"
        )
        c_disk.grid(row=0, column=2, sticky="nsew", padx=(6, 0))

        # 4. Khối biểu đồ lịch sử tài nguyên (CPU & RAM)
        self.chart = ResourceChartsFrame(container)
        self.chart.pack(fill="both", expand=True, pady=(0, 10))
        self.chart.set_theme(self.theme)

        # 5. Thanh chân trang (Footer)
        footer = ctk.CTkFrame(container, fg_color="transparent")
        footer.pack(fill="x")
        self.lbl_status = ctk.CTkLabel(footer, text="Khởi động ứng dụng...", font=(FONT_MAIN, 12), text_color=COLOR_TEXT_MUTED)
        self.lbl_status.pack(side="left")

        self.lbl_updated = ctk.CTkLabel(footer, text="Cập nhật: Chưa có dữ liệu", font=(FONT_MAIN, 12), text_color=COLOR_TEXT_MUTED)
        self.lbl_updated.pack(side="right")

    def _bind_segmented_keys(self, widget):
        """Hỗ trợ phím mũi tên và Space/Enter cho segmented control."""
        for value, btn in widget._buttons_dict.items():
            mode = "Light" if value == "Sáng" else "Dark"
            btn.bind("<space>", lambda _e, m=mode: self.set_theme(m))
            btn.bind("<Return>", lambda _e, m=mode: self.set_theme(m))
            btn.bind("<Left>", lambda _e: self.set_theme("Light"))
            btn.bind("<Right>", lambda _e: self.set_theme("Dark"))

    def _focus_next(self, direction):
        focus = self.focus_get()
        current = next((i for i, btn in enumerate(self._focus_buttons) if focus in (btn._text_label, btn._canvas)), -1)
        self._focus_buttons[(current + direction) % len(self._focus_buttons)].focus_set()
        return "break"

    def _create_card(self, parent, default_title):
        """Khởi tạo một thẻ số liệu gọn gàng với bo góc và thanh tiến trình bo tròn."""
        card = ctk.CTkFrame(parent, fg_color=COLOR_CARD, corner_radius=16, border_width=1, border_color=COLOR_BORDER)

        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=16, pady=(10, 4))

        lbl_title = ctk.CTkLabel(top_row, text=default_title, font=FONT_CARD_TITLE, text_color=COLOR_TEXT_MAIN, anchor="w")
        lbl_title.pack(side="left")

        lbl_status = ctk.CTkLabel(
            top_row,
            text="--",
            font=FONT_STATUS,
            text_color=("#1D4ED8", "#60A5FA"),
            fg_color=("#EFF6FF", "#172A46"),
            corner_radius=10,
            padx=8,
            pady=2,
        )
        lbl_status.pack(side="right")

        mid_row = ctk.CTkFrame(card, fg_color="transparent")
        mid_row.pack(fill="x", padx=16, pady=(0, 4))

        lbl_percent = ctk.CTkLabel(mid_row, text="--%", font=FONT_METRIC, text_color=COLOR_TEXT_MAIN, anchor="w")
        lbl_percent.pack(side="left")

        prog = ctk.CTkProgressBar(card, height=8, corner_radius=4, fg_color=("#E2E8F0", "#1E2B40"), progress_color=COLOR_ACCENT)
        prog.set(0.0)
        prog.pack(fill="x", padx=16, pady=(0, 6))

        lbl_detail = ctk.CTkLabel(
            card,
            text="--",
            font=FONT_BODY,
            text_color=COLOR_TEXT_MUTED,
            justify="left",
            anchor="w",
            wraplength=220,
        )
        lbl_detail.pack(fill="x", padx=16, pady=(0, 10))

        return card, lbl_title, lbl_percent, prog, lbl_status, lbl_detail

    # --- PHẦN 4: ĐIỀU KHIỂN CHẾ ĐỘ SÁNG / TỐI (THEME SWITCHING) ---
    def _on_theme_select(self, value):
        theme = "Light" if value == "Sáng" else "Dark"
        self.set_theme(theme)

    def _style_theme_control(self):
        selected = "Sáng" if self.theme == "Light" else "Tối"
        for value, button in self.theme_control._buttons_dict.items():
            button.configure(text_color="#FFFFFF" if value == selected else COLOR_TEXT_MAIN)

    def set_theme(self, mode):
        """Chuyển đổi giao diện Sáng / Tối, lưu cấu hình và vẽ lại biểu đồ."""
        if str(mode).lower() in ("dark", "tối"):
            theme = "Dark"
        else:
            theme = "Light"
        self.theme = theme
        saved = save_theme(theme)
        ctk.set_appearance_mode(theme)
        if hasattr(self, "theme_control") and self.theme_control is not None:
            self.theme_control.set("Sáng" if theme == "Light" else "Tối")
            self._style_theme_control()
        if hasattr(self, "chart") and self.chart is not None:
            self.chart.set_theme(theme)
        if not saved:
            self.lbl_status.configure(text="Đã đổi giao diện, chưa lưu được lựa chọn", text_color=COLOR_DANGER)

    # --- PHẦN 5: ĐA LUỒNG & TIẾN TRÌNH LÀM MỚI (DAEMON WORKER & QUEUE) ---
    def refresh(self):
        """Kích hoạt đọc dữ liệu trên luồng nền (Single-flight, không chồng lặp)."""
        if self._reading or self._is_closing:
            return
        if self._startup_id is not None:
            try:
                self.after_cancel(self._startup_id)
            except Exception:
                pass
            self._startup_id = None
        if self._auto_id is not None:
            try:
                self.after_cancel(self._auto_id)
            except Exception:
                pass
            self._auto_id = None

        self._reading = True
        self.btn_refresh.configure(state="disabled", text="Đang đọc…")
        self.lbl_status.configure(text="Đang đọc thông số hệ thống...", text_color=COLOR_ACCENT)

        def worker():
            try:
                self._queue.put(("SUCCESS", read_metrics()))
            except Exception as exc:
                self._queue.put(("ERROR", str(exc)))

        threading.Thread(target=worker, daemon=True).start()
        self._poll_id = self.after(50, self._check_queue)

    def _check_queue(self):
        """Định kỳ kiểm tra kết quả từ luồng nền trên luồng chính Tkinter."""
        self._poll_id = None
        if self._is_closing:
            return
        try:
            if not self.winfo_exists():
                return
            status, payload = self._queue.get_nowait()
        except tk.TclError:
            return
        except queue.Empty:
            if self._reading and not self._is_closing:
                self._poll_id = self.after(50, self._check_queue)
            return

        self._reading = False
        self.btn_refresh.configure(state="normal", text="Làm mới")

        if status == "SUCCESS":
            self._last_metrics = payload
            self.history.add(payload)
            self._update_ui(payload, is_stale=False)
            if hasattr(self, "chart") and self.chart is not None:
                self.chart.set_points(self.history.points)
            self.lbl_error.pack_forget()
            self.lbl_status.configure(text="Đang theo dõi • ~2 giây/mẫu", text_color=COLOR_TEXT_MUTED)
        else:
            is_stale = self._last_metrics is not None
            if is_stale:
                self._update_ui(self._last_metrics, is_stale=True)
            msg = f"Chưa đọc được dữ liệu: {truncate_text(payload, 80)}. Hãy bấm Làm mới để thử lại."
            if is_stale:
                msg += " Đang hiển thị số liệu cũ."
            self.lbl_error.configure(text=msg)
            self.lbl_error.pack(fill="x", pady=(0, 10), before=self.cards_frame)
            self.lbl_status.configure(text="Lỗi cập nhật số liệu", text_color=COLOR_DANGER)

        # Lên lịch tự động lấy mẫu định kỳ nếu cửa sổ chưa đóng
        if not self._is_closing:
            delay = getattr(self, "AUTO_REFRESH_MS", AUTO_REFRESH_MS)
            self._auto_id = self.after(delay, self.refresh)

    # --- PHẦN 6: CẬP NHẬT DỮ LIỆU LÊN GIAO DIỆN (UPDATE UI) ---
    def _update_ui(self, data, is_stale=False):
        """Hiển thị số liệu thật từ backend lên các widget tương ứng."""
        # 1. Thông tin phần cứng máy tính
        self.lbl_machine.configure(text=truncate_text(data.get("machine_name"), 24))
        self.lbl_os.configure(text=truncate_text(data.get("os_name"), 24))
        self.lbl_cpu_threads.configure(text=f"{data.get('cpu_threads', 1)} luồng")
        self.lbl_cpu_model.configure(text=truncate_text(data.get("cpu_name"), 65))

        # 2. Thẻ CPU
        cpu_pct, threads = data.get("cpu_percent", 0.0), data.get("cpu_threads", 1)
        c_text, c_tcol, c_pbg, c_prog = get_status_info(cpu_pct)
        self.lbl_cpu_percent.configure(text=f"{cpu_pct:.1f}%")
        self.prog_cpu.set(max(0.0, min(1.0, cpu_pct / 100.0)))
        self.prog_cpu.configure(progress_color=c_prog)
        self.lbl_cpu_status.configure(text=c_text, text_color=c_tcol, fg_color=c_pbg)
        self.lbl_cpu_detail.configure(text=f"Máy có {threads} luồng logic\nLấy mẫu CPU trong 0,2 giây")

        # 3. Thẻ RAM
        mem = data.get("memory", {})
        ram_pct = mem.get("percent", 0.0)
        r_text, r_tcol, r_pbg, r_prog = get_status_info(ram_pct)
        self.lbl_ram_percent.configure(text=f"{ram_pct:.1f}%")
        self.prog_ram.set(max(0.0, min(1.0, ram_pct / 100.0)))
        self.prog_ram.configure(progress_color=r_prog)
        self.lbl_ram_status.configure(text=r_text, text_color=r_tcol, fg_color=r_pbg)
        self.lbl_ram_detail.configure(
            text=f"Đã dùng: {format_gib(mem.get('used'))} / {format_gib(mem.get('total'))}\nKhả dụng: {format_gib(mem.get('available'))}"
        )

        # 4. Thẻ Ổ đĩa hệ thống
        disk = data.get("disk", {})
        disk_path = disk.get("path") or "Hệ thống"
        self.lbl_disk_title.configure(text=f"Ổ đĩa hệ thống ({disk_path})")

        if disk.get("error") or disk.get("percent") is None:
            self.lbl_disk_percent.configure(text="--")
            self.prog_disk.set(0.0)
            self.prog_disk.configure(progress_color=("#CBD5E1", "#334155"))
            self.lbl_disk_status.configure(text="Không khả dụng", text_color=COLOR_DANGER, fg_color=COLOR_DANGER_BG)
            self.lbl_disk_detail.configure(text=disk.get("error") or "Không đọc được dữ liệu ổ đĩa.")
        else:
            disk_pct = disk["percent"]
            d_text, d_tcol, d_pbg, d_prog = get_status_info(disk_pct)
            self.lbl_disk_percent.configure(text=f"{disk_pct:.1f}%")
            self.prog_disk.set(max(0.0, min(1.0, disk_pct / 100.0)))
            self.prog_disk.configure(progress_color=d_prog)
            self.lbl_disk_status.configure(text=d_text, text_color=d_tcol, fg_color=d_pbg)
            self.lbl_disk_detail.configure(
                text=f"Còn trống: {format_gib(disk.get('free'))}\nTổng dung lượng: {format_gib(disk.get('total'))}"
            )

        # 5. Cập nhật thời điểm
        stale_tag = " (Dữ liệu cũ)" if is_stale else ""
        self.lbl_updated.configure(text=f"Cập nhật: {format_time(data.get('captured_at'))}{stale_tag}")

    def _on_close(self):
        """Đóng cửa sổ an toàn, hủy toàn bộ các timer đang chờ."""
        self._is_closing = True
        for timer in (self._startup_id, self._poll_id, self._auto_id):
            if timer is not None:
                try:
                    self.after_cancel(timer)
                except Exception:
                    pass
        self.destroy()


# --- PHẦN 7: ĐIỂM KHỞI CHẠY CHƯƠNG TRÌNH (__MAIN__) ---
if __name__ == "__main__":
    app = MonitorApp()
    app.mainloop()
