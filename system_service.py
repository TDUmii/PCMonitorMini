"""Real resource collectors and bounded per-user actions for PC Monitor 2.0."""

from datetime import datetime
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import threading
import time

import psutil

from maintenance import MaintenanceService, _system_directory
from monitor import VERSION, get_os_name, read_metrics

PROTECTED_NAMES = {"system", "registry", "idle", "system idle process", "smss.exe", "csrss.exe", "wininit.exe",
                   "winlogon.exe", "services.exe", "lsass.exe", "svchost.exe", "fontdrvhost.exe", "dwm.exe",
                   "sihost.exe", "explorer.exe", "taskhostw.exe", "securityhealthservice.exe", "msmpeng.exe",
                   "audiodg.exe", "memory compression", "secure system", "conhost.exe"}
TOOLS = {"apps": "ms-settings:appsfeatures", "startup": "ms-settings:startupapps",
         "storage": "ms-settings:storagesense", "network": "ms-settings:network-status",
         "update": "ms-settings:windowsupdate", "power": "ms-settings:powersleep", "display": "ms-settings:display"}


def format_bytes(value):
    if value is None:
        return "--"
    value = max(0, float(value))
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024


def format_duration(seconds):
    if seconds is None or seconds < 0:
        return "--"
    days, remainder = divmod(int(seconds), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes = remainder // 60
    return (f"{days} ngày " if days else "") + (f"{hours} giờ " if hours or days else "") + f"{minutes} phút"


class SystemService(MaintenanceService):
    def __init__(self, state_dir=None, temp_roots=None, registry=None):
        super().__init__(state_dir, temp_roots, registry)
        self._sample_lock = threading.Lock()
        self._process_lock = threading.Lock()
        self._last_network = None
        self._process_baselines = {}
        try:
            self._username = psutil.Process().username().casefold()
            self._protected_pids = {os.getpid(), *(p.pid for p in psutil.Process().parents())}
        except psutil.Error:
            self._username = ""
            self._protected_pids = {os.getpid()}

    def sample(self):
        with self._sample_lock:
            snapshot = read_metrics()
            now = time.monotonic()
            counters = psutil.net_io_counters()
            network = {"down_bps": None, "up_bps": None, "bytes_recv": None, "bytes_sent": None}
            if counters:
                network.update(bytes_recv=counters.bytes_recv, bytes_sent=counters.bytes_sent)
                if self._last_network and now > self._last_network[0]:
                    elapsed = now - self._last_network[0]
                    received, sent = counters.bytes_recv - self._last_network[1], counters.bytes_sent - self._last_network[2]
                    if received >= 0 and sent >= 0:
                        network.update(down_bps=received / elapsed, up_bps=sent / elapsed)
                self._last_network = (now, counters.bytes_recv, counters.bytes_sent)
            battery = psutil.sensors_battery()
            snapshot.update(network=network, uptime_seconds=max(0, time.time() - psutil.boot_time()),
                            process_count=len(psutil.pids()), battery=None if battery is None else
                            {"percent": battery.percent, "plugged": battery.power_plugged,
                             "seconds_left": battery.secsleft if battery.secsleft >= 0 else None})
            return snapshot

    def _stop_reason(self, pid, name, username, exe=None):
        if pid <= 4 or pid in self._protected_pids or name.casefold() in PROTECTED_NAMES:
            return "Tiến trình hệ thống hoặc ứng dụng đang quản lý máy được bảo vệ."
        if not self._username or not username or username.casefold() != self._username:
            return "Chỉ cho phép dừng ứng dụng thuộc tài khoản hiện tại."
        if exe:
            system = Path(os.environ.get("SystemRoot", r"C:\Windows")).absolute()
            try:
                Path(exe).absolute().relative_to(system)
                return "Ứng dụng trong thư mục Windows được bảo vệ."
            except ValueError:
                pass
        return ""

    def processes(self):
        with self._process_lock:
            now = time.monotonic()
            baselines, rows = {}, []
            cores = psutil.cpu_count() or 1
            for process in psutil.process_iter(attrs=["pid", "name", "username", "create_time", "memory_info", "cpu_times", "exe"], ad_value=None):
                try:
                    info = process.info
                    created = info["create_time"]
                    if created is None:
                        continue
                    identity = (process.pid, created)
                    cpu = None
                    times = info["cpu_times"]
                    if times:
                        used = times.user + times.system
                        previous = self._process_baselines.get(identity)
                        if previous and now > previous[0]:
                            cpu = max(0, min(100, 100 * (used - previous[1]) / (now - previous[0]) / cores))
                        baselines[identity] = (now, used)
                    name, username = info["name"] or f"PID {process.pid}", info["username"] or ""
                    reason = self._stop_reason(process.pid, name, username, info["exe"])
                    rows.append({"pid": process.pid, "name": name, "username": username, "created": created,
                                 "cpu_percent": cpu, "memory_bytes": info["memory_info"].rss if info["memory_info"] else 0,
                                 "can_stop": not reason and bool(info["exe"]), "protected_reason": reason or ("Không đọc được vị trí ứng dụng." if not info["exe"] else "")})
                except (OSError, psutil.Error):
                    continue
            self._process_baselines = baselines
            return sorted(rows, key=lambda item: item["memory_bytes"], reverse=True)

    def stop_process(self, pid, created, confirmed=False):
        self._confirmed(confirmed)
        if not isinstance(pid, int) or isinstance(pid, bool) or not isinstance(created, (int, float)):
            raise ValueError("Tiến trình không hợp lệ. Hãy chọn lại trong danh sách.")
        try:
            process = psutil.Process(pid)
            if abs(process.create_time() - created) > 0.001:
                raise ValueError("Ứng dụng đã thay đổi. Hãy làm mới để tránh dừng nhầm tiến trình.")
            name, username, exe = process.name(), process.username(), process.exe()
            reason = self._stop_reason(pid, name, username, exe)
            if reason or not exe:
                raise ValueError(reason or "Không xác định được ứng dụng để dừng.")
            process.terminate()
            try:
                process.wait(timeout=3)
            except psutil.TimeoutExpired:
                return self.store.result("Dừng ứng dụng", False, "Đã gửi yêu cầu nhưng tiến trình vẫn đang chạy. Hãy kiểm tra lại danh sách.")
            return self.store.result("Dừng ứng dụng", True, f"Đã dừng {name} (PID {pid}).")
        except psutil.NoSuchProcess:
            return self.store.result("Dừng ứng dụng", False, "Tiến trình đã kết thúc. Hãy làm mới danh sách.")
        except psutil.AccessDenied as exc:
            raise ValueError("Windows không cho phép dừng tiến trình này. Ứng dụng không tự nâng quyền.") from exc

    def drives(self):
        rows = []
        for partition in psutil.disk_partitions(all=False):
            if os.name == "nt" and ("cdrom" in partition.opts or not partition.fstype):
                continue
            row = {"device": partition.device, "path": partition.mountpoint, "fstype": partition.fstype,
                   "total": None, "used": None, "free": None, "percent": None, "error": None}
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                row.update(total=usage.total, used=usage.used, free=usage.free, percent=usage.percent)
            except (OSError, psutil.Error):
                row["error"] = "Chưa đọc được ổ đĩa."
            rows.append(row)
        return rows

    def network_adapters(self):
        counters, stats = psutil.net_io_counters(pernic=True), psutil.net_if_stats()
        rows = []
        for name, addresses in psutil.net_if_addrs().items():
            status, counter = stats.get(name), counters.get(name)
            rows.append({"name": name, "is_up": bool(status and status.isup),
                         "speed_mbps": status.speed if status else 0,
                         "ipv4": [address.address for address in addresses if address.family == socket.AF_INET],
                         "mac": next((address.address for address in addresses if address.family == psutil.AF_LINK), ""),
                         "bytes_recv": counter.bytes_recv if counter else None,
                         "bytes_sent": counter.bytes_sent if counter else None})
        return sorted(rows, key=lambda item: (not item["is_up"], item["name"].casefold()))

    def installed_apps(self):
        registry = self.registry
        if registry is None:
            raise ValueError("Danh sách ứng dụng hiện hỗ trợ Windows.")
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
        rows, seen = [], set()
        for hive in (registry.HKEY_CURRENT_USER, registry.HKEY_LOCAL_MACHINE):
            for view in {getattr(registry, "KEY_WOW64_64KEY", 0), getattr(registry, "KEY_WOW64_32KEY", 0)}:
                try:
                    with registry.OpenKey(hive, key_path, 0, registry.KEY_READ | view) as root:
                        for index in range(registry.QueryInfoKey(root)[0]):
                            try:
                                child = registry.EnumKey(root, index)
                                with registry.OpenKey(root, child) as key:
                                    def value(name, default=""):
                                        try:
                                            return registry.QueryValueEx(key, name)[0]
                                        except OSError:
                                            return default
                                    name = value("DisplayName")
                                    if not isinstance(name, str) or not name.strip() or value("SystemComponent", 0) == 1 or value("ParentKeyName"):
                                        continue
                                    version, publisher = str(value("DisplayVersion")), str(value("Publisher"))
                                    identity = (name.casefold(), version, publisher)
                                    if identity in seen:
                                        continue
                                    seen.add(identity)
                                    size = value("EstimatedSize", None)
                                    rows.append({"name": name.strip(), "version": version, "publisher": publisher,
                                                 "size_bytes": size * 1024 if isinstance(size, int) and size >= 0 else None,
                                                 "install_location": str(value("InstallLocation"))})
                            except OSError:
                                continue
                except OSError:
                    continue
        return sorted(rows, key=lambda item: item["name"].casefold())

    def system_info(self):
        metrics = read_metrics()
        return {"os_name": get_os_name(), "os_build": platform.version(), "machine_name": metrics["machine_name"],
                "cpu_name": metrics["cpu_name"], "cpu_physical": psutil.cpu_count(logical=False),
                "cpu_threads": metrics["cpu_threads"], "architecture": platform.machine(),
                "memory_total": metrics["memory"]["total"], "boot_time": datetime.fromtimestamp(psutil.boot_time()).astimezone().isoformat(timespec="seconds"),
                "python_version": platform.python_version(), "app_version": VERSION}

    def export_report(self, path):
        destination = Path(path).absolute()
        if destination.suffix.casefold() != ".json":
            raise ValueError("Hãy lưu báo cáo với phần mở rộng .json.")
        if destination.exists():
            raise ValueError("Tệp đã tồn tại. Hãy chọn tên mới để giữ nguyên báo cáo cũ.")
        report = {"generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                  "system": self.system_info(), "snapshot": self.sample(), "drives": self.drives()}
        with destination.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
        return self.store.result("Xuất báo cáo", True, "Đã lưu báo cáo JSON trên máy. Báo cáo không được tải lên mạng.")

    def open_tool(self, name):
        if os.name != "nt":
            raise ValueError("Công cụ này chỉ hỗ trợ Windows.")
        if name in TOOLS:
            os.startfile(TOOLS[name])
        elif name == "task_manager":
            executable = _system_directory() / "Taskmgr.exe"
            subprocess.Popen([str(executable)], creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            raise ValueError("Công cụ không nằm trong danh sách được hỗ trợ.")
        return {"ok": True, "message": "Đã gửi yêu cầu mở công cụ Windows."}

    def open_folder(self, path):
        folder = Path(path).absolute()
        if os.name != "nt" or str(folder).startswith("\\\\") or not folder.is_dir():
            raise ValueError("Thư mục cục bộ không tồn tại hoặc không đọc được.")
        os.startfile(str(folder))
        return {"ok": True, "message": "Đã mở thư mục trong File Explorer."}
