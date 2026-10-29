"""
app.py - Điểm khởi chạy và Lớp ứng dụng chính cho PC Monitor 2.0.
Triển khai giao diện hiện đại kiểu Windows 11, hỗ trợ 8 màn hình hoàn chỉnh,
hàng đợi đa luồng không giật lag (Worker Queue), chuyển đổi Sáng / Tối,
và kết nối trực tiếp với backend SystemService.
"""

from datetime import datetime
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk

from system_service import SystemService, format_bytes, format_duration
from monitor import VERSION, MetricHistory, load_theme, save_theme
from ui_widgets import (
    COLOR_ACCENT,
    COLOR_ACCENT_BUTTON,
    COLOR_ACCENT_BG,
    COLOR_ACCENT_HOVER,
    COLOR_BG,
    COLOR_BORDER,
    COLOR_DANGER,
    COLOR_DANGER_BG,
    COLOR_SURFACE,
    COLOR_SURFACE_ALT,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_MUTED,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_CARD_TITLE,
    FONT_FAMILY,
    FONT_PAGE_SUB,
    FONT_PAGE_TITLE,
    FONT_SMALL,
    FONT_SMALL_BOLD,
    NavIconCanvas,
)
from ui_pages import (
    AppsPage,
    HistoryPage,
    NetworkPage,
    OptimizePage,
    OverviewPage,
    ProcessesPage,
    StartupPage,
    StoragePage,
)

AUTO_SAMPLE_MS = 2000
PROCESS_POLL_MS = 2500


class MonitorApp(ctk.CTk):
    """Cửa sổ chính của PC Monitor 2.0 quản lý thanh điều hướng và luồng dữ liệu."""

    PAGES_INFO = [
        ("overview", "Tổng quan", "Theo dõi hiệu năng và sức khỏe tổng thể hệ thống"),
        ("processes", "Đang chạy", "Quản lý các tiến trình và ứng dụng đang hoạt động"),
        ("startup", "Khởi động", "Quản lý mục tự chạy của tài khoản, có bản sao để khôi phục"),
        ("apps", "Ứng dụng", "Ứng dụng desktop; mở Windows để quản lý thêm ứng dụng Store"),
        ("storage", "Dung lượng", "Phân tích dung lượng các ổ đĩa và thư mục"),
        ("network", "Mạng", "Thông tin kết nối mạng và lưu lượng truyền tải"),
        ("optimize", "Tối ưu", "Dọn dẹp và tinh chỉnh hệ thống an toàn, minh bạch"),
        ("history", "Lịch sử", "Nhật ký các thao tác tối ưu và thay đổi hệ thống"),
    ]

    def __init__(self):
        super().__init__()
        self.title("PC Monitor 2.0")
        self.geometry("1200x800")
        self.minsize(1020, 700)

        # 1. Nạp và áp dụng chủ đề Sáng / Tối
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

        # 2. Khởi tạo Backend Service trực tiếp (không tạo stub/fallback giả)
        self.service = SystemService()

        # 3. Quản lý trạng thái và hàng đợi đa luồng
        self.history = MetricHistory()
        self._queue = queue.Queue()
        self._busy_jobs = set()
        self._is_closing = False
        self._last_metrics = None
        self._page_errors = {}

        # Sự kiện hủy quét cho các tác vụ nặng
        self._storage_scan_cancel = threading.Event()
        self._temp_scan_cancel = threading.Event()

        # Quản lý Timer
        self._poll_id = None
        self._sample_loop_id = None
        self._process_loop_id = None
        self._startup_id = None

        self.current_page_key = "overview"
        self.pages = {}
        self.nav_buttons = {}

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Dựng bố cục tổng thể
        self._build_layout()
        for page in self.pages.values():
            page.apply_theme(self.theme)
        self._install_keyboard_access()
        self._style_theme_segment()

        # Phím tắt chuyển giao diện Ctrl+T
        self.bind("<Control-t>", lambda _e: self.toggle_theme())
        self.bind("<Control-T>", lambda _e: self.toggle_theme())

        # Bắt đầu vòng lặp xử lý hàng đợi
        self._poll_queue()

        # Kích hoạt lấy mẫu nền định kỳ
        self._startup_id = self.after(100, self._start_background_loops)

    # ==========================================================================
    # BỐ CỤC TỔNG THỂ (MAIN LAYOUT)
    # ==========================================================================
    def _build_layout(self):
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True)

        self._build_sidebar()
        self._build_content_area()

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self.main_container,
            width=230,
            fg_color=COLOR_SURFACE,
            corner_radius=0,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Header Sidebar
        app_brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        app_brand.pack(fill="x", padx=16, pady=(18, 16))

        logo_badge = ctk.CTkFrame(app_brand, width=38, height=38, corner_radius=10, fg_color=COLOR_ACCENT)
        logo_badge.pack(side="left", padx=(0, 10))
        logo_badge.pack_propagate(False)

        ctk.CTkLabel(logo_badge, text="PC", font=(FONT_FAMILY, 13, "bold"), text_color="#FFFFFF").pack(expand=True)

        brand_text = ctk.CTkFrame(app_brand, fg_color="transparent")
        brand_text.pack(side="left")
        ctk.CTkLabel(brand_text, text="PC Monitor", font=(FONT_FAMILY, 15, "bold"), text_color=COLOR_TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(brand_text, text=f"Phiên bản {VERSION}", font=FONT_SMALL, text_color=COLOR_TEXT_MUTED).pack(anchor="w")

        # Đường kẻ phân cách
        sep = ctk.CTkFrame(self.sidebar, height=1, fg_color=COLOR_BORDER)
        sep.pack(fill="x", padx=16, pady=(0, 12))

        # Danh sách 8 nút điều hướng (Dùng Canvas vẽ icon vector, KHÔNG DÙNG EMOJI)
        self.nav_container = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.nav_container.pack(fill="both", expand=True, padx=10)

        for key, title, _ in self.PAGES_INFO:
            self._create_nav_item(key, title)

        # Chân Sidebar: Nút đổi giao diện Sáng / Tối và chú thích Ctrl+T
        sidebar_footer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        sidebar_footer.pack(fill="x", padx=12, pady=16)

        self.theme_segment = ctk.CTkSegmentedButton(
            sidebar_footer,
            values=["Sáng", "Tối"],
            command=self._on_theme_segmented,
            height=34,
            corner_radius=8,
            font=FONT_SMALL_BOLD,
            fg_color=("#E2E8F0", "#1E2B40"),
            selected_color=COLOR_ACCENT_BUTTON,
            selected_hover_color=COLOR_ACCENT_HOVER,
            unselected_color=("#E2E8F0", "#1E2B40"),
            unselected_hover_color=("#CBD5E1", "#2D3F5C"),
            text_color=COLOR_TEXT_MAIN,
        )
        self.theme_segment.set("Sáng" if self.theme == "Light" else "Tối")
        self.theme_segment.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(
            sidebar_footer,
            text="Phím tắt: Ctrl + T",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_MUTED,
        ).pack()

    def _create_nav_item(self, key, title):
        btn_frame = ctk.CTkFrame(
            self.nav_container,
            height=42,
            corner_radius=10,
            fg_color="transparent",
            cursor="hand2",
        )
        btn_frame.pack(fill="x", pady=2)
        btn_frame.pack_propagate(False)

        icon = NavIconCanvas(btn_frame, icon_name=key, size=20, bg=self._apply_appearance_mode(COLOR_SURFACE))
        icon.pack(side="left", padx=(12, 10))

        label = ctk.CTkLabel(
            btn_frame,
            text=title,
            font=FONT_BODY_BOLD,
            text_color=COLOR_TEXT_MAIN,
            anchor="w",
        )
        label.pack(side="left", fill="both", expand=True)

        for widget in (btn_frame, icon, label):
            widget.bind("<Button-1>", lambda _e, k=key: self.switch_page(k))
            widget.bind("<Enter>", lambda _e, k=key: self._on_nav_enter(k))
            widget.bind("<Leave>", lambda _e, k=key: self._on_nav_leave(k))

        self.nav_buttons[key] = {
            "frame": btn_frame,
            "icon": icon,
            "label": label,
        }

    def _build_content_area(self):
        self.content_area = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.content_area.pack(side="left", fill="both", expand=True, padx=20, pady=16)

        # 1. Header trang
        self.header = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.header.pack(fill="x", pady=(0, 12))

        title_box = ctk.CTkFrame(self.header, fg_color="transparent")
        title_box.pack(side="left", anchor="w", fill="x", expand=True, padx=(0, 12))

        self.lbl_page_title = ctk.CTkLabel(
            title_box,
            text="Tổng quan",
            font=FONT_PAGE_TITLE,
            text_color=COLOR_TEXT_MAIN,
            anchor="w",
        )
        self.lbl_page_title.pack(anchor="w")

        self.lbl_page_sub = ctk.CTkLabel(
            title_box,
            text="Theo dõi hiệu năng và sức khỏe tổng thể hệ thống",
            font=FONT_PAGE_SUB,
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
            wraplength=500,
        )
        self.lbl_page_sub.pack(anchor="w", fill="x")

        header_actions = ctk.CTkFrame(self.header, fg_color="transparent")
        header_actions.pack(side="right", anchor="ne", before=title_box)

        self.btn_context_refresh = ctk.CTkButton(
            header_actions,
            text="Làm mới trang",
            command=self._on_contextual_refresh,
            width=120,
            height=36,
            corner_radius=10,
            font=FONT_BODY_BOLD,
            fg_color=COLOR_ACCENT_BUTTON,
            hover_color=COLOR_ACCENT_HOVER,
            text_color="#FFFFFF",
        )
        self.btn_context_refresh.pack(side="left")

        self.lbl_page_error = ctk.CTkLabel(self.content_area, text="", text_color=COLOR_DANGER,
                                          fg_color=COLOR_DANGER_BG, font=FONT_BODY, anchor="w",
                                          justify="left", corner_radius=8, wraplength=720)
        self.lbl_page_error.bind("<Configure>", lambda event: self.lbl_page_error.configure(
            wraplength=max(180, int(event.width / self.lbl_page_error._get_widget_scaling()) - 20)))

        # 2. Khung chứa 8 trang
        self.page_container = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.page_container.pack(fill="both", expand=True)

        self.pages["overview"] = OverviewPage(self.page_container, app=self)
        self.pages["processes"] = ProcessesPage(self.page_container, app=self)
        self.pages["startup"] = StartupPage(self.page_container, app=self)
        self.pages["apps"] = AppsPage(self.page_container, app=self)
        self.pages["storage"] = StoragePage(self.page_container, app=self)
        self.pages["network"] = NetworkPage(self.page_container, app=self)
        self.pages["optimize"] = OptimizePage(self.page_container, app=self)
        self.pages["history"] = HistoryPage(self.page_container, app=self)

        # 3. Footer
        self.footer = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.footer.pack(fill="x", pady=(8, 0))

        self.lbl_global_status = ctk.CTkLabel(
            self.footer,
            text="Khởi động ứng dụng…",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_MUTED,
        )
        self.lbl_global_status.pack(side="left")

        self.lbl_last_updated = ctk.CTkLabel(
            self.footer,
            text="Cập nhật: Chưa có dữ liệu",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_MUTED,
        )
        self.lbl_last_updated.pack(side="right")

        self.switch_page("overview")

    # ==========================================================================
    # ĐIỀU HƯỚNG & CHUYỂN TRANG (NAVIGATION)
    # ==========================================================================
    def switch_page(self, page_key):
        if page_key not in self.pages:
            return

        self.current_page_key = page_key

        for k, page in self.pages.items():
            if k == page_key:
                page.pack(fill="both", expand=True)
            else:
                page.pack_forget()

        for k, title, sub in self.PAGES_INFO:
            if k == page_key:
                self.lbl_page_title.configure(text=title)
                self.lbl_page_sub.configure(text=sub)
                break

        self._update_sidebar_styles()
        self._render_page_error()
        self._on_page_activated(page_key)

    def _render_page_error(self):
        message = " | ".join(message for job, message in self._page_errors.items()
                              if self._job_page(job) == self.current_page_key)
        if message:
            self.lbl_page_error.configure(text=f"{message}  Thử lại thao tác hoặc bấm Làm mới trang.")
            self.lbl_page_error.pack(fill="x", pady=(0, 8), before=self.page_container)
        else:
            self.lbl_page_error.pack_forget()

    @staticmethod
    def _job_page(job_key):
        if job_key.startswith("stop_proc_"):
            return "processes"
        if job_key.startswith("toggle_startup_"):
            return "startup"
        return {"sample": "overview", "system_info": "overview", "processes": "processes",
                "startup_items": "startup", "installed_apps": "apps", "apps": "apps",
                "drives": "storage", "scan_storage": "storage", "network_adapters": "network",
                "scan_temp": "optimize", "clean_temp": "optimize", "power_plans": "optimize",
                "set_power_plan": "optimize", "restore_power_plan": "optimize", "flush_dns": "optimize",
                "history": "history"}.get(job_key)

    def _install_keyboard_access(self):
        def wrap(event, label):
            width = max(120, int(label.winfo_width() / label._get_widget_scaling()) - 8)
            if label.cget("wraplength") != width:
                label.configure(wraplength=width)
        def walk(parent):
            for widget in parent.winfo_children():
                if isinstance(widget, ctk.CTkButton):
                    canvas = widget._canvas
                    canvas.configure(takefocus=1)
                    canvas.bind("<Return>", lambda event, button=widget: button.invoke())
                    canvas.bind("<space>", lambda event, button=widget: button.invoke())
                    border = widget.cget("border_width")
                    canvas.bind("<FocusIn>", lambda event, button=widget: button.configure(border_width=2, border_color=COLOR_ACCENT))
                    canvas.bind("<FocusOut>", lambda event, button=widget, width=border: button.configure(border_width=width))
                elif isinstance(widget, ctk.CTkLabel) and widget.cget("wraplength"):
                    try:
                        fills_width = widget.pack_info().get("fill") in {"x", "both"}
                    except tk.TclError:
                        fills_width = False
                    if fills_width:
                        widget.bind("<Configure>", lambda event, label=widget: wrap(event, label))
                walk(widget)
        walk(self)
        for index, (key, controls) in enumerate(self.nav_buttons.items(), 1):
            canvas = controls["frame"]._canvas
            canvas.configure(takefocus=1)
            for sequence in ("<Return>", "<space>"):
                canvas.bind(sequence, lambda event, page=key: self.switch_page(page))
            canvas.bind("<FocusIn>", lambda event, frame=controls["frame"]: frame.configure(border_width=2, border_color=COLOR_ACCENT))
            canvas.bind("<FocusOut>", lambda event, frame=controls["frame"]: frame.configure(border_width=0))
            self.bind(f"<Alt-Key-{index}>", lambda event, page=key: self.switch_page(page))

    def _style_theme_segment(self):
        selected = "Sáng" if self.theme == "Light" else "Tối"
        for value, button in self.theme_segment._buttons_dict.items():
            button.configure(text_color="#FFFFFF" if value == selected else COLOR_TEXT_MAIN)

    def _update_sidebar_styles(self):
        is_dark = self.theme == "Dark"
        surf_bg = self._apply_appearance_mode(COLOR_SURFACE)
        active_bg = self._apply_appearance_mode(COLOR_ACCENT_BG)
        active_fg = self._apply_appearance_mode(COLOR_ACCENT)
        normal_fg = self._apply_appearance_mode(COLOR_TEXT_MAIN)
        icon_normal = self._apply_appearance_mode(COLOR_TEXT_MUTED)

        for k, btn_dict in self.nav_buttons.items():
            f = btn_dict["frame"]
            ic = btn_dict["icon"]
            lbl = btn_dict["label"]

            if k == self.current_page_key:
                f.configure(fg_color=active_bg)
                lbl.configure(text_color=active_fg)
                ic.update_style(color=active_fg, bg_color=active_bg)
            else:
                f.configure(fg_color="transparent")
                lbl.configure(text_color=normal_fg)
                ic.update_style(color=icon_normal, bg_color=surf_bg)

    def _on_nav_enter(self, key):
        if key == self.current_page_key:
            return
        is_dark = self.theme == "Dark"
        hover_bg = self._apply_appearance_mode(COLOR_SURFACE_ALT)
        btn = self.nav_buttons.get(key)
        if btn:
            btn["frame"].configure(fg_color=hover_bg)
            btn["icon"].update_style(btn["icon"].color, bg_color=hover_bg)

    def _on_nav_leave(self, key):
        if key == self.current_page_key:
            return
        is_dark = self.theme == "Dark"
        normal_bg = self._apply_appearance_mode(COLOR_SURFACE)
        btn = self.nav_buttons.get(key)
        if btn:
            btn["frame"].configure(fg_color="transparent")
            btn["icon"].update_style(btn["icon"].color, bg_color=normal_bg)

    def _on_page_activated(self, page_key):
        if page_key == "overview":
            self.refresh_sample()
            self._load_system_info()
        elif page_key == "processes":
            self.refresh_processes()
        elif page_key == "startup":
            self.refresh_startup()
        elif page_key == "apps":
            self.refresh_apps()
        elif page_key == "storage":
            self.refresh_drives()
        elif page_key == "network":
            self.refresh_network()
        elif page_key == "optimize":
            self.refresh_power_plans()
        elif page_key == "history":
            self.refresh_history()

    def _on_contextual_refresh(self):
        self._on_page_activated(self.current_page_key)

    # ==========================================================================
    # QUẢN LÝ CHỦ ĐỀ SÁNG / TỐI (THEME SWITCHING)
    # ==========================================================================
    def toggle_theme(self):
        new_theme = "Dark" if self.theme == "Light" else "Light"
        self.set_theme(new_theme)

    def _on_theme_segmented(self, val):
        t = "Light" if val == "Sáng" else "Dark"
        self.set_theme(t)

    def set_theme(self, mode):
        self.theme = "Dark" if str(mode).lower() in ("dark", "tối") else "Light"
        ctk.set_appearance_mode(self.theme)
        saved = save_theme(self.theme)

        if hasattr(self, "theme_segment") and self.theme_segment:
            self.theme_segment.set("Sáng" if self.theme == "Light" else "Tối")

        for page in self.pages.values():
            if hasattr(page, "apply_theme"):
                page.apply_theme(self.theme)

        self._update_sidebar_styles()
        self._style_theme_segment()
        if not saved:
            self.lbl_global_status.configure(text="Đã đổi giao diện; chưa lưu được lựa chọn. Hãy kiểm tra quyền ghi AppData.", text_color=COLOR_DANGER)

    # ==========================================================================
    # HÀNG ĐỢI ĐA LUỒNG & ASYNC WORKER (WORKER QUEUE ARCHITECTURE)
    # ==========================================================================
    def _run_async(self, job_key, worker_func, on_success, on_error=None):
        """Khởi chạy tác vụ luồng nền với nguyên tắc Single-flight per job_key."""
        if self._is_closing:
            return
        if job_key in self._busy_jobs:
            return

        self._busy_jobs.add(job_key)
        self._update_busy_controls()

        def runner():
            try:
                res = worker_func()
                self._queue.put((job_key, "SUCCESS", res, on_success, on_error))
            except Exception as exc:
                self._queue.put((job_key, "ERROR", exc, on_success, on_error))

        threading.Thread(target=runner, daemon=True).start()

    def _update_busy_controls(self):
        loading = any(self._job_page(job) == self.current_page_key for job in self._busy_jobs)
        self.btn_context_refresh.configure(state="disabled" if loading else "normal",
                                           text="Đang xử lý..." if loading else "Làm mới trang")
        if "optimize" in self.pages:
            page = self.pages["optimize"]
            cleaning = "clean_temp" in self._busy_jobs
            scanning = "scan_temp" in self._busy_jobs
            page.btn_scan_temp.configure(state="disabled" if cleaning or scanning else "normal")
            if cleaning:
                page.btn_clean_temp.configure(state="disabled")

    def _poll_queue(self):
        """Hút kết quả từ luồng nền trên luồng chính Tkinter."""
        self._poll_id = None
        if self._is_closing:
            return

        try:
            while True:
                job_key, status, payload, on_success, on_error = self._queue.get_nowait()
                self._busy_jobs.discard(job_key)
                page_key = self._job_page(job_key)
                if page_key:
                    if status == "ERROR":
                        self._page_errors[job_key] = str(payload)
                    elif isinstance(payload, dict) and payload.get("ok") is False:
                        self._page_errors[job_key] = payload.get("message", "Thao tác chưa hoàn tất.")
                    else:
                        self._page_errors.pop(job_key, None)
                    self._render_page_error()

                if status == "SUCCESS":
                    if on_success:
                        on_success(payload)
                else:
                    err_msg = str(payload)
                    if on_error:
                        on_error(err_msg)
                    else:
                        self._handle_default_error(job_key, err_msg)
                self._update_busy_controls()
        except queue.Empty:
            pass
        except tk.TclError:
            return

        if not self._is_closing:
            self._poll_id = self.after(40, self._poll_queue)

    def _handle_default_error(self, job_key, err_msg):
        self.lbl_global_status.configure(
            text=f"Lỗi thao tác [{job_key}]: {err_msg}",
            text_color=COLOR_DANGER,
        )

    # ==========================================================================
    # CÁC TÁC VỤ DỮ LIỆU & GỌI BACKEND SERVICE (SERVICE CALLS)
    # ==========================================================================
    def _start_background_loops(self):
        """Khởi động lấy mẫu định kỳ 2s và đọc tiến trình khi trang mở."""
        self._startup_id = None
        if self._is_closing:
            return
        self.refresh_sample()
        self._load_system_info()
        self._schedule_sample_loop()
        self._schedule_process_loop()

    def _schedule_sample_loop(self):
        if self._is_closing:
            return

        def task():
            self.refresh_sample()
            if not self._is_closing:
                self._sample_loop_id = self.after(AUTO_SAMPLE_MS, task)

        self._sample_loop_id = self.after(AUTO_SAMPLE_MS, task)

    def _schedule_process_loop(self):
        if self._is_closing:
            return

        def task():
            if self.current_page_key == "processes" and not self._is_closing:
                self.refresh_processes()
            if not self._is_closing:
                self._process_loop_id = self.after(PROCESS_POLL_MS, task)

        self._process_loop_id = self.after(PROCESS_POLL_MS, task)

    def refresh_sample(self):
        def worker():
            return self.service.sample()

        def on_success(data):
            self._last_metrics = data
            self.history.add(data)

            if "overview" in self.pages:
                self.pages["overview"].update_sample(data, is_stale=False)

            if "network" in self.pages and data.get("network"):
                self.pages["network"].update_network_sample(data["network"])

            cap_at = data.get("captured_at")
            if cap_at:
                try:
                    t_str = datetime.fromisoformat(cap_at).strftime("%H:%M:%S")
                except Exception:
                    t_str = str(cap_at)
                self.lbl_last_updated.configure(text=f"Cập nhật: {t_str}")
            self.lbl_global_status.configure(text="Đang theo dõi thời gian thực", text_color=COLOR_TEXT_MUTED)

        def on_error(err):
            if self._last_metrics and "overview" in self.pages:
                self.pages["overview"].update_sample(self._last_metrics, is_stale=True)
            self.lbl_global_status.configure(text=f"Lỗi lấy mẫu: {err}", text_color=COLOR_DANGER)

        self._run_async("sample", worker, on_success, on_error)

    def _load_system_info(self):
        def worker():
            return self.service.system_info()

        def on_success(sinfo):
            if "overview" in self.pages:
                self.pages["overview"].update_system_info(sinfo)

        self._run_async("system_info", worker, on_success)

    def refresh_processes(self):
        def worker():
            return self.service.processes()

        def on_success(procs):
            if "processes" in self.pages:
                self.pages["processes"].update_processes(procs)

        def on_error(err):
            self.lbl_global_status.configure(text=f"Lỗi đọc tiến trình: {err}", text_color=COLOR_DANGER)

        self._run_async("processes", worker, on_success, on_error)

    def stop_process(self, pid, created, name):
        def worker():
            return self.service.stop_process(pid, created, confirmed=True)

        def on_success(res):
            if res and res.get("ok"):
                self.lbl_global_status.configure(text=f"Đã dừng tiến trình {name} (PID: {pid})", text_color=COLOR_ACCENT)
                messagebox.showinfo("Thành công", f"Đã kết thúc tiến trình:\n• Tên: {name}\n• PID: {pid}", parent=self)
                self.refresh_processes()
                self.refresh_history()
            else:
                msg = res.get("message") if res else "Không xác định"
                messagebox.showerror("Không thể dừng tiến trình", f"Lỗi: {msg}", parent=self)

        def on_error(err):
            messagebox.showerror("Lỗi hệ thống", f"Không thể dừng tiến trình:\n{err}", parent=self)

        self._run_async(f"stop_proc_{pid}", worker, on_success, on_error)

    def refresh_startup(self):
        def worker():
            return self.service.startup_items()

        def on_success(items):
            if "startup" in self.pages:
                self.pages["startup"].update_startup_items(items)

        def on_error(err):
            self.lbl_global_status.configure(text=f"Lỗi đọc khởi động: {err}", text_color=COLOR_DANGER)

        self._run_async("startup_items", worker, on_success, on_error)

    def toggle_startup(self, item_id, enabled, name):
        def worker():
            return self.service.toggle_startup(item_id, enabled=enabled, confirmed=True)

        def on_success(res):
            if res and res.get("ok"):
                action_str = "bật lại" if enabled else "tắt khởi động"
                messagebox.showinfo("Thành công", f"Đã {action_str} thành công cho '{name}'.", parent=self)
                self.refresh_startup()
                self.refresh_history()
            else:
                msg = res.get("message") if res else "Không thể thay đổi"
                messagebox.showerror("Lỗi thay đổi", msg, parent=self)

        def on_error(err):
            messagebox.showerror("Lỗi hệ thống", f"Không thể thay đổi mục khởi động:\n{err}", parent=self)

        self._run_async(f"toggle_startup_{item_id}", worker, on_success, on_error)

    def refresh_apps(self):
        def worker():
            return self.service.installed_apps()

        def on_success(apps):
            if "apps" in self.pages:
                self.pages["apps"].update_apps(apps)

        def on_error(err):
            self.lbl_global_status.configure(text=f"Lỗi đọc ứng dụng: {err}", text_color=COLOR_DANGER)

        self._run_async("installed_apps", worker, on_success, on_error)

    def refresh_drives(self):
        def worker():
            return self.service.drives()

        def on_success(drives):
            if "storage" in self.pages:
                self.pages["storage"].update_drives(drives)

        def on_error(err):
            self.lbl_global_status.configure(text=f"Lỗi đọc ổ đĩa: {err}", text_color=COLOR_DANGER)

        self._run_async("drives", worker, on_success, on_error)

    def start_storage_scan(self, path):
        self._storage_scan_cancel.clear()

        def worker():
            return self.service.scan_storage(path, cancel_event=self._storage_scan_cancel)

        def on_success(res):
            if "storage" in self.pages:
                self.pages["storage"].update_scan_result(res)

        def on_error(err):
            if "storage" in self.pages:
                self.pages["storage"].set_scan_busy(False)
            messagebox.showerror("Lỗi phân tích dung lượng", f"Quá trình quét thất bại:\n{err}", parent=self)

        self._run_async("scan_storage", worker, on_success, on_error)

    def cancel_storage_scan(self):
        self._storage_scan_cancel.set()
        self.lbl_global_status.configure(text="Đang yêu cầu dừng quét dung lượng…", text_color=COLOR_TEXT_MUTED)

    def open_folder(self, path):
        def worker():
            return self.service.open_folder(path)

        def on_success(res):
            if res and not res.get("ok"):
                messagebox.showerror("Không thể mở", res.get("message") or "Thư mục không tồn tại.", parent=self)

        def on_error(err):
            messagebox.showerror("Lỗi", str(err), parent=self)

        self._run_async(f"open_folder_{path}", worker, on_success, on_error)

    def refresh_network(self):
        def worker():
            return self.service.network_adapters()

        def on_success(adapters):
            if "network" in self.pages:
                self.pages["network"].update_adapters(adapters)

        def on_error(err):
            self.lbl_global_status.configure(text=f"Lỗi đọc cổng mạng: {err}", text_color=COLOR_DANGER)

        self._run_async("network_adapters", worker, on_success, on_error)

    def start_temp_scan(self):
        self._temp_scan_cancel.clear()

        def worker():
            return self.service.scan_temp(cancel_event=self._temp_scan_cancel)

        def on_success(res):
            if "optimize" in self.pages:
                self.pages["optimize"].update_temp_scan_result(res)

        def on_error(err):
            if "optimize" in self.pages:
                self.pages["optimize"].set_temp_scan_busy(False)
            messagebox.showerror("Lỗi quét tệp tạm", f"Quá trình quét gặp sự cố:\n{err}", parent=self)

        self._run_async("scan_temp", worker, on_success, on_error)

    def cancel_temp_scan(self):
        self._temp_scan_cancel.set()
        self.lbl_global_status.configure(text="Đang yêu cầu dừng quét tệp tạm…", text_color=COLOR_TEXT_MUTED)

    def clean_temp(self, token):
        def worker():
            return self.service.clean_temp(token, confirmed=True)

        def on_success(res):
            if "optimize" in self.pages:
                self.pages["optimize"].on_clean_temp_finished(res)
            self.refresh_history()

        def on_error(err):
            if "optimize" in self.pages:
                self.pages["optimize"].on_clean_temp_finished({"ok": False, "message": str(err)})

        self._run_async("clean_temp", worker, on_success, on_error)

    def refresh_power_plans(self):
        def worker():
            return self.service.power_plans()

        def on_success(p_data):
            if "optimize" in self.pages:
                self.pages["optimize"].update_power_plans(p_data)

        def on_error(err):
            self.lbl_global_status.configure(text=f"Lỗi đọc chế độ nguồn: {err}", text_color=COLOR_DANGER)

        self._run_async("power_plans", worker, on_success, on_error)

    def set_power_plan(self, guid, plan_name):
        def worker():
            return self.service.set_power_plan(guid, confirmed=True)

        def on_success(res):
            if res and res.get("ok"):
                messagebox.showinfo("Thành công", f"Đã áp dụng chế độ nguồn điện: '{plan_name}'.", parent=self)
                self.refresh_power_plans()
                self.refresh_history()
            else:
                msg = res.get("message") if res else "Không thể áp dụng"
                messagebox.showerror("Lỗi", msg, parent=self)

        def on_error(err):
            messagebox.showerror("Lỗi hệ thống", f"Không thể đổi chế độ nguồn:\n{err}", parent=self)

        self._run_async("set_power_plan", worker, on_success, on_error)

    def restore_power_plan(self):
        def worker():
            return self.service.restore_power_plan(confirmed=True)

        def on_success(res):
            if res and res.get("ok"):
                messagebox.showinfo("Thành công", "Đã khôi phục lại chế độ nguồn điện trước đó.", parent=self)
                self.refresh_power_plans()
                self.refresh_history()
            else:
                msg = res.get("message") if res else "Không thể khôi phục"
                messagebox.showerror("Lỗi", msg, parent=self)

        def on_error(err):
            messagebox.showerror("Lỗi", str(err), parent=self)

        self._run_async("restore_power_plan", worker, on_success, on_error)

    def flush_dns(self):
        def worker():
            return self.service.flush_dns(confirmed=True)

        def on_success(res):
            if res and res.get("ok"):
                msg = res.get("message") or "Đã làm mới bộ nhớ đệm DNS thành công."
                messagebox.showinfo("Làm mới DNS thành công", msg, parent=self)
                self.refresh_history()
            else:
                msg = res.get("message") if res else "Lệnh không thành công."
                messagebox.showerror("Lỗi làm mới DNS", msg, parent=self)

        def on_error(err):
            messagebox.showerror("Lỗi hệ thống", f"Không thể làm mới DNS:\n{err}", parent=self)

        self._run_async("flush_dns", worker, on_success, on_error)

    def refresh_history(self):
        def worker():
            return self.service.history()

        def on_success(hist_list):
            if "history" in self.pages:
                self.pages["history"].update_history(hist_list)

        def on_error(err):
            self.lbl_global_status.configure(text=f"Lỗi đọc lịch sử: {err}", text_color=COLOR_DANGER)

        self._run_async("history", worker, on_success, on_error)

    def export_report(self):
        suggested_name = f"PCMonitor_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path = filedialog.asksaveasfilename(
            initialfile=suggested_name,
            defaultextension=".json",
            filetypes=[("Tệp JSON (*.json)", "*.json"), ("Tất cả các tệp (*.*)", "*.*")],
            title="Chọn vị trí lưu báo cáo hệ thống",
            parent=self,
        )
        if not path:
            return

        def worker():
            return self.service.export_report(path)

        def on_success(res):
            if res and res.get("ok"):
                messagebox.showinfo("Xuất báo cáo thành công", f"Báo cáo hệ thống đã được lưu an toàn tại:\n{path}", parent=self)
                self.refresh_history()
            else:
                msg = res.get("message") if res else "Không thể lưu tệp"
                messagebox.showerror("Lỗi xuất báo cáo", msg, parent=self)

        def on_error(err):
            messagebox.showerror("Lỗi hệ thống", f"Không thể xuất báo cáo:\n{err}", parent=self)

        self._run_async("export_report", worker, on_success, on_error)

    def open_tool(self, tool_name):
        """Mở tiện ích Windows nằm trong allowlist an toàn."""
        def worker():
            return self.service.open_tool(tool_name)

        def on_success(res):
            if res and not res.get("ok"):
                messagebox.showwarning("Không thể mở công cụ", res.get("message") or "Thao tác không hoàn thành.", parent=self)

        def on_error(err):
            messagebox.showerror("Lỗi mở công cụ", str(err), parent=self)

        self._run_async(f"open_tool_{tool_name}", worker, on_success, on_error)

    # ==========================================================================
    # ĐÓNG ỨNG DỤNG AN TOÀN (CLEAN SHUTDOWN)
    # ==========================================================================
    def _on_close(self):
        changing = any(job in {"clean_temp", "set_power_plan", "restore_power_plan", "flush_dns"}
                       or job.startswith(("stop_proc_", "toggle_startup_")) for job in self._busy_jobs)
        if changing:
            messagebox.showinfo("Đang hoàn tất thao tác", "Hãy chờ thao tác đang chạy hoàn tất rồi đóng ứng dụng.", parent=self)
            return
        self._is_closing = True

        self._storage_scan_cancel.set()
        self._temp_scan_cancel.set()

        for tid in (self._poll_id, self._sample_loop_id, self._process_loop_id, self._startup_id):
            if tid is not None:
                try:
                    self.after_cancel(tid)
                except Exception:
                    pass

        self.destroy()


if __name__ == "__main__":
    app = MonitorApp()
    app.mainloop()
