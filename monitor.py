"""Doc thong so may. File nay duoc giao vien chuan bi san cho buoi hoc UI."""

import os
import platform
import sys
import json
import math
from collections import deque
from datetime import datetime
from pathlib import Path

import psutil

VERSION = "1.1.0"
GIB = 1024**3


class MetricHistory:
    """Last 60 valid measured samples, with real timestamps. No seeded data."""

    def __init__(self):
        self._points = deque(maxlen=60)

    def add(self, snapshot):
        try:
            timestamp = datetime.fromisoformat(snapshot["captured_at"]).timestamp()
            cpu = float(snapshot["cpu_percent"])
            ram = float(snapshot["memory"]["percent"])
        except (KeyError, TypeError, ValueError, OverflowError, OSError):
            return False
        if not all(math.isfinite(v) for v in (timestamp, cpu, ram)):
            return False
        if not (0 <= cpu <= 100 and 0 <= ram <= 100):
            return False
        if self._points and timestamp <= self._points[-1]["timestamp"]:
            return False
        self._points.append({"timestamp": timestamp, "cpu_percent": cpu, "memory_percent": ram})
        return True

    @property
    def points(self):
        return [point.copy() for point in self._points]


def _settings_path():
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".local" / "share")
    return Path(base) / "PCMonitorMini" / "settings.json"


def load_theme():
    try:
        data = json.loads(_settings_path().read_text(encoding="utf-8"))
        theme = data.get("theme") if isinstance(data, dict) else None
        return theme if theme in ("Light", "Dark") else "Light"
    except (OSError, ValueError):
        return "Light"


def save_theme(theme):
    if theme not in ("Light", "Dark"):
        raise ValueError("Theme must be Light or Dark")
    try:
        path = _settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"theme": theme}), encoding="utf-8")
        return True
    except OSError:
        return False


def get_os_name():
    """Python 3.11 can report Windows 11's NT version as Windows 10."""
    release = platform.release()
    if os.name == "nt":
        version = sys.getwindowsversion()
        if version.major == 10 and version.build >= 22000 and version.product_type == 1:
            release = "11"
    return f"{platform.system()} {release}"


def read_metrics():
    """Return one real snapshot. Call in a worker: CPU sampling takes 0.2s.

    Values are bytes and percentages (0..100). A failed disk read leaves
    CPU/RAM usable; the UI must show disk.error instead of a fabricated zero.
    """
    cpu_percent = psutil.cpu_percent(interval=0.2)
    memory = psutil.virtual_memory()
    cpu_name = platform.processor() or "Bộ xử lý"
    if os.name == "nt":
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
                cpu_name = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip() or cpu_name
        except OSError:
            pass  # A restricted registry still leaves platform.processor() usable.
    disk_path = os.environ.get("SystemDrive", "C:") + "\\" if os.name == "nt" else "/"
    disk = {"path": disk_path, "error": None}
    try:
        usage = psutil.disk_usage(disk_path)
        disk.update(
            total=usage.total,
            used=usage.used,
            free=usage.free,
            percent=usage.percent,
        )
    except (OSError, psutil.Error):
        disk.update(
            total=None,
            used=None,
            free=None,
            percent=None,
            error="Chưa đọc được ổ đĩa. Hãy thử làm mới.",
        )

    return {
        "machine_name": platform.node() or "Máy tính của bạn",
        "os_name": get_os_name(),
        "cpu_name": cpu_name,
        "cpu_threads": psutil.cpu_count(logical=True) or 1,
        "cpu_percent": cpu_percent,
        "memory": {
            "total": memory.total,
            "used": memory.total - memory.available,
            "available": memory.available,
            "percent": memory.percent,
        },
        "disk": disk,
        "captured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }


def format_gib(value):
    """Binary capacity, labelled GiB so units match the calculation."""
    return f"{value / GIB:.1f} GiB" if value is not None else "--"


if __name__ == "__main__":
    import json

    print(json.dumps(read_metrics(), ensure_ascii=False, indent=2))
