"""Explicit Windows maintenance; no background mutations or arbitrary commands."""

import ctypes
from ctypes import wintypes
import hashlib
import heapq
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import tempfile
import time

from state_store import StateStore

try:
    import winreg
except ImportError:
    winreg = None

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
REPARSE = 0x400
DAY = 86400
GUID = re.compile(r"\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b")
BLOCKED_EXTENSIONS = {".exe", ".dll", ".sys", ".lnk", ".reg", ".ps1", ".bat", ".cmd", ".msi"}


def _system_directory():
    if os.name != "nt":
        raise ValueError("Công cụ này chỉ hỗ trợ Windows.")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetSystemDirectoryW.argtypes = [wintypes.LPWSTR, wintypes.UINT]
    kernel.GetSystemDirectoryW.restype = wintypes.UINT
    buffer = ctypes.create_unicode_buffer(32768)
    size = kernel.GetSystemDirectoryW(buffer, len(buffer))
    if not size or size >= len(buffer):
        raise OSError("Chưa xác định được thư mục công cụ của Windows.")
    return Path(buffer.value)


def _plain(path, directory=False):
    info = Path(path).lstat()
    if getattr(info, "st_file_attributes", 0) & REPARSE or stat.S_ISLNK(info.st_mode):
        return None
    valid = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    return info if valid else None


def _contained(path, root):
    try:
        Path(path).relative_to(root)
        return Path(path) != Path(root)
    except ValueError:
        return False


def _fingerprint(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def _validate_candidate(path, root, expected):
    if not _contained(path, root):
        return False
    cursor = Path(path).parent
    while True:
        if not _plain(cursor, directory=True):
            return False
        if cursor == root:
            break
        cursor = cursor.parent
    info = _plain(path)
    return bool(info and info.st_nlink == 1 and _fingerprint(info) == expected)


def _delete_candidate(path, root, expected):
    """Delete the previewed file by handle on Windows, never follow a reparse point."""
    if not _validate_candidate(path, root, expected):
        return False
    if os.name != "nt":
        os.unlink(path)
        return True

    class FileInfo(ctypes.Structure):
        _fields_ = [("attributes", wintypes.DWORD), ("created", wintypes.FILETIME),
                    ("accessed", wintypes.FILETIME), ("modified", wintypes.FILETIME),
                    ("volume", wintypes.DWORD), ("size_high", wintypes.DWORD),
                    ("size_low", wintypes.DWORD), ("links", wintypes.DWORD),
                    ("index_high", wintypes.DWORD), ("index_low", wintypes.DWORD)]

    class Disposition(ctypes.Structure):
        _fields_ = [("delete", ctypes.c_ubyte)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                  wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.GetFileInformationByHandle.argtypes = [wintypes.HANDLE, ctypes.POINTER(FileInfo)]
    kernel.GetFileInformationByHandle.restype = wintypes.BOOL
    kernel.GetFinalPathNameByHandleW.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
    kernel.GetFinalPathNameByHandleW.restype = wintypes.DWORD
    kernel.SetFileInformationByHandle.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
    kernel.SetFileInformationByHandle.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateFileW(str(path), 0x10000 | 0x80, 0, None, 3, 0x00200000, None)
    if handle == wintypes.HANDLE(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        info = FileInfo()
        if not kernel.GetFileInformationByHandle(handle, ctypes.byref(info)):
            raise ctypes.WinError(ctypes.get_last_error())
        identifier = (info.index_high << 32) | info.index_low
        size = (info.size_high << 32) | info.size_low
        if info.attributes & (REPARSE | 0x10) or info.links != 1 or identifier != expected[1] or size != expected[2]:
            return False
        # Last-write time is rechecked after acquiring an exclusive file handle.
        modified = (((info.modified.dwHighDateTime << 32) | info.modified.dwLowDateTime) - 116444736000000000) * 100
        if abs(modified - expected[3]) > 100:
            return False
        buffer = ctypes.create_unicode_buffer(32768)
        length = kernel.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0)
        if not length or length >= len(buffer):
            return False
        final = buffer.value
        if final.startswith("\\\\?\\"):
            final = final[4:]
        if os.path.normcase(final) != os.path.normcase(str(path)) or not _contained(Path(final), root):
            return False
        disposition = Disposition(1)
        if not kernel.SetFileInformationByHandle(handle, 4, ctypes.byref(disposition), ctypes.sizeof(disposition)):
            raise ctypes.WinError(ctypes.get_last_error())
        return True
    finally:
        kernel.CloseHandle(handle)


class MaintenanceService:
    def __init__(self, state_dir=None, temp_roots=None, registry=None):
        self.store = StateStore(state_dir)
        self.registry = registry if registry is not None else winreg
        user_temp = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "Temp"
        self._temp_roots = [Path(p).absolute() for p in temp_roots] if temp_roots is not None else [user_temp.absolute()]
        self._preview = None

    @staticmethod
    def _confirmed(confirmed):
        if confirmed is not True:
            raise ValueError("Hãy xác nhận thao tác trong ứng dụng trước khi thực hiện.")

    def history(self):
        return self.store.history()

    def scan_temp(self, cancel_event=None):
        with self.store.lock:
            self._preview = None
        deadline, cutoff = time.monotonic() + 10, time.time() - DAY
        roots, candidates = [], []
        skipped = visited = 0
        partial = cancelled = False
        for root in self._temp_roots:
            # A changed TEMP variable must never turn a home or drive root into a cleanup target.
            if root.name.casefold() not in {"temp", "tmp"} or root == root.parent or not _plain(root, True):
                continue
            if any(getattr(p.lstat(), "st_file_attributes", 0) & REPARSE or p.is_symlink() for p in root.parents):
                continue
            roots.append(str(root))
            pending = [root]
            while pending:
                if (cancel_event and cancel_event.is_set()) or time.monotonic() >= deadline or visited >= 20000 or len(candidates) >= 5000:
                    cancelled = bool(cancel_event and cancel_event.is_set())
                    partial = True
                    break
                directory = pending.pop()
                try:
                    if not _plain(directory, True):
                        skipped += 1
                        continue
                    with os.scandir(directory) as entries:
                        for entry in entries:
                            visited += 1
                            if visited >= 20000 or len(candidates) >= 5000 or time.monotonic() >= deadline or (cancel_event and cancel_event.is_set()):
                                partial = True
                                cancelled = bool(cancel_event and cancel_event.is_set())
                                break
                            path = Path(entry.path)
                            try:
                                info = entry.stat(follow_symlinks=False)
                                if getattr(info, "st_file_attributes", 0) & REPARSE or stat.S_ISLNK(info.st_mode):
                                    skipped += 1
                                elif stat.S_ISDIR(info.st_mode):
                                    if entry.name.startswith(("_MEI", ".")) or entry.name in {"node_modules", "__pycache__", "venv"}:
                                        skipped += 1
                                    else:
                                        pending.append(path)
                                elif stat.S_ISREG(info.st_mode):
                                    # Windows DirEntry.stat omits file identity/link count; lstat fetches those.
                                    info = path.lstat()
                                    if info.st_mtime < cutoff and info.st_nlink == 1 and path.suffix.casefold() not in BLOCKED_EXTENSIONS:
                                        candidates.append({"path": str(path), "bytes": info.st_size, "root": str(root), "identity": _fingerprint(info)})
                                    else:
                                        skipped += 1
                                else:
                                    skipped += 1
                            except OSError:
                                skipped += 1
                except OSError:
                    skipped += 1
            if partial:
                break
        if not roots:
            raise ValueError("Không tìm thấy thư mục Temp hợp lệ của người dùng. Hãy mở Dung lượng trong Cài đặt Windows.")
        token = secrets.token_urlsafe(24)
        with self.store.lock:
            self._preview = None if cancelled else {"token": token, "at": time.monotonic(), "files": candidates}
        return {"token": None if cancelled else token, "count": len(candidates),
                "bytes": sum(f["bytes"] for f in candidates), "roots": roots,
                "files": [{"path": f["path"], "bytes": f["bytes"]} for f in candidates],
                "skipped": skipped, "partial": partial, "cancelled": cancelled}

    def clean_temp(self, token, confirmed=False):
        self._confirmed(confirmed)
        with self.store.lock:
            preview = self._preview
            if not preview or not isinstance(token, str) or not secrets.compare_digest(token, preview["token"]) or time.monotonic() - preview["at"] > 300:
                raise ValueError("Lần xem trước đã hết hạn hoặc không hợp lệ. Hãy quét lại trước khi dọn.")
            self._preview = None  # A preview is single-use, including partial failures.
            deleted = size = skipped = errors = 0
            for item in preview["files"]:
                try:
                    if _delete_candidate(Path(item["path"]), Path(item["root"]), item["identity"]):
                        deleted += 1
                        size += item["bytes"]
                    else:
                        skipped += 1
                except OSError:
                    errors += 1  # Locked or changed files are left untouched.
            return self.store.result("Dọn tệp tạm", errors == 0,
                                     f"Đã xóa {deleted} tệp tạm. Bỏ qua {skipped + errors} tệp đã đổi hoặc đang bận.",
                                     deleted_count=deleted, deleted_bytes=size, skipped=skipped, errors=errors)

    def scan_storage(self, path, cancel_event=None):
        root = Path(path).absolute()
        if str(root).startswith("\\\\") or not _plain(root, True):
            raise ValueError("Hãy chọn một thư mục cục bộ, không phải liên kết hoặc ổ mạng.")
        deadline = time.monotonic() + 30
        pending, folders, largest = [(root, None)], {}, []
        count = total = skipped = visited = 0
        partial = cancelled = False
        while pending:
            if visited >= 100000 or time.monotonic() >= deadline or (cancel_event and cancel_event.is_set()):
                partial = True
                cancelled = bool(cancel_event and cancel_event.is_set())
                break
            directory, group = pending.pop()
            try:
                if not _plain(directory, True):
                    skipped += 1
                    continue
                with os.scandir(directory) as entries:
                    for entry in entries:
                        visited += 1
                        if visited >= 100000 or time.monotonic() >= deadline or (cancel_event and cancel_event.is_set()):
                            partial = True
                            cancelled = bool(cancel_event and cancel_event.is_set())
                            break
                        try:
                            info = entry.stat(follow_symlinks=False)
                            if getattr(info, "st_file_attributes", 0) & REPARSE or stat.S_ISLNK(info.st_mode):
                                skipped += 1
                            elif stat.S_ISDIR(info.st_mode):
                                top = group or entry.path
                                folders.setdefault(top, 0)
                                pending.append((Path(entry.path), top))
                            elif stat.S_ISREG(info.st_mode):
                                total += info.st_size
                                count += 1
                                top = group or str(root)
                                folders[top] = folders.get(top, 0) + info.st_size
                                heapq.heappush(largest, (info.st_size, entry.path))
                                if len(largest) > 30:
                                    heapq.heappop(largest)
                        except OSError:
                            skipped += 1
            except OSError:
                skipped += 1
        return {"path": str(root), "total_bytes": total, "file_count": count,
                "folders": [{"name": Path(p).name if p != str(root) else "Tệp ở thư mục gốc", "path": p, "bytes": size}
                            for p, size in sorted(folders.items(), key=lambda item: item[1], reverse=True)[:30]],
                "largest_files": [{"name": Path(p).name, "path": p, "bytes": size} for size, p in sorted(largest, reverse=True)],
                "skipped": skipped, "partial": partial, "cancelled": cancelled}

    def _run(self, tool, arguments):
        if tool not in {"powercfg.exe", "ipconfig.exe"} or os.name != "nt":
            raise ValueError("Công cụ này chỉ hỗ trợ Windows.")
        executable = _system_directory() / tool
        completed = subprocess.run([str(executable), *arguments], capture_output=True, timeout=20,
                                   creationflags=subprocess.CREATE_NO_WINDOW, text=True, errors="replace")
        if completed.returncode:
            raise OSError("Windows chưa thực hiện được yêu cầu. Hãy kiểm tra quyền tài khoản hoặc mở công cụ Windows tương ứng.")
        return completed.stdout

    def power_plans(self):
        output = self._run("powercfg.exe", ["/LIST"])
        active_output = self._run("powercfg.exe", ["/GETACTIVESCHEME"])
        active = GUID.search(active_output)
        plans = []
        for line in output.splitlines():
            match = GUID.search(line)
            if match:
                label = line[match.end():].strip().strip("*").strip()
                plans.append({"guid": match.group().lower(), "name": label.strip("() ") or "Chế độ nguồn Windows",
                              "active": bool(active and active.group().lower() == match.group().lower())})
        if not plans or not active:
            raise ValueError("Chưa đọc được chế độ nguồn. Hãy mở Cài đặt nguồn của Windows.")
        backup = self.store.read("power.json", {})
        if not isinstance(backup, dict) or (backup.get("previous") is not None and
                                           (not isinstance(backup["previous"], str) or not GUID.fullmatch(backup["previous"]))):
            raise ValueError("Bản lưu chế độ nguồn không hợp lệ. Dữ liệu được giữ nguyên để kiểm tra.")
        return {"plans": plans, "previous": backup.get("previous")}

    def set_power_plan(self, guid, confirmed=False):
        self._confirmed(confirmed)
        with self.store.lock:
            listing = self.power_plans()
            if not isinstance(guid, str) or not GUID.fullmatch(guid) or guid.lower() not in {p["guid"] for p in listing["plans"]}:
                raise ValueError("Chế độ nguồn không còn tồn tại. Hãy làm mới danh sách.")
            current = next(p["guid"] for p in listing["plans"] if p["active"])
            if current == guid.lower():
                return {"ok": True, "message": "Máy đang dùng chế độ nguồn này."}
            self.store.write("power.json", {"previous": current, "selected": guid.lower()})
            self._run("powercfg.exe", ["/SETACTIVE", guid.lower()])
            actual = self.power_plans()
            success = any(p["guid"] == guid.lower() and p["active"] for p in actual["plans"])
            return self.store.result("Đổi chế độ nguồn", success, "Đã đổi chế độ nguồn. Có thể hoàn tác trong ứng dụng." if success else "Windows chưa xác nhận chế độ nguồn mới. Hãy làm mới.")

    def restore_power_plan(self, confirmed=False):
        self._confirmed(confirmed)
        with self.store.lock:
            listing = self.power_plans()
            previous = listing.get("previous")
            if previous not in {p["guid"] for p in listing["plans"]}:
                raise ValueError("Không có chế độ nguồn trước đó để hoàn tác.")
            self._run("powercfg.exe", ["/SETACTIVE", previous])
            success = any(p["guid"] == previous and p["active"] for p in self.power_plans()["plans"])
            if success:
                self.store.write("power.json", {})
            return self.store.result("Hoàn tác nguồn", success, "Đã khôi phục chế độ nguồn trước đó." if success else "Chưa xác nhận được hoàn tác. Hãy làm mới.")

    def flush_dns(self, confirmed=False):
        self._confirmed(confirmed)
        self._run("ipconfig.exe", ["/flushdns"])
        return self.store.result("Làm mới DNS", True, "Windows đã làm mới bộ nhớ DNS. Lần truy cập tiếp theo sẽ tra cứu lại địa chỉ.")

    def _startup_backup(self):
        backup = self.store.read("startup.json", {})
        if not isinstance(backup, dict) or any(not isinstance(v, dict) or not isinstance(v.get("command"), str)
                                              or v.get("type") not in {1, 2} for v in backup.values()):
            raise ValueError("Bản lưu khởi động không hợp lệ. Ứng dụng giữ nguyên dữ liệu để bạn kiểm tra.")
        return backup

    @staticmethod
    def _startup_id(source, name):
        return hashlib.sha256(f"{source}\0{name}".encode("utf-8")).hexdigest()

    def startup_items(self):
        registry = self.registry
        if registry is None:
            raise ValueError("Quản lý khởi động hiện hỗ trợ Windows.")
        with self.store.lock:
            backup = self._startup_backup()
            items = []
            views = [getattr(registry, "KEY_WOW64_64KEY", 0), getattr(registry, "KEY_WOW64_32KEY", 0)]
            sources = [(registry.HKEY_CURRENT_USER, "HKCU", views[0]),
                       (registry.HKEY_LOCAL_MACHINE, "HKLM64", views[0]),
                       (registry.HKEY_LOCAL_MACHINE, "HKLM32", views[1])]
            live_user = set()
            for hive, source, view in sources:
                try:
                    with registry.OpenKey(hive, RUN_KEY, 0, registry.KEY_READ | view) as key:
                        index = 0
                        while True:
                            try:
                                name, command, kind = registry.EnumValue(key, index)
                            except OSError:
                                break
                            index += 1
                            if not isinstance(command, str) or kind not in {registry.REG_SZ, registry.REG_EXPAND_SZ}:
                                continue
                            identifier = self._startup_id(source, name)
                            if source == "HKCU":
                                live_user.add(name)
                            collision = source == "HKCU" and name in backup and (
                                command != backup[name]["command"] or kind != backup[name]["type"])
                            items.append({"id": identifier, "name": name, "command": command,
                                          "scope": "Người dùng" if source == "HKCU" else "Toàn máy",
                                          "enabled": True, "can_toggle": source == "HKCU" and not collision,
                                          "note": "Có bản lưu cũ trùng tên; không ghi đè." if collision else
                                          "Khóa Run; trạng thái bật/tắt bổ sung do Windows quản lý." if source == "HKCU" else "Chỉ xem; mở Cài đặt Windows để quản lý.",
                                          "_source": source, "_type": kind})
                except OSError:
                    continue
            for name, saved in backup.items():
                if name not in live_user:
                    items.append({"id": self._startup_id("HKCU", name), "name": name, "command": saved["command"],
                                  "scope": "Người dùng", "enabled": False, "can_toggle": True,
                                  "note": "Đã tắt bằng ứng dụng; có thể khôi phục.", "_source": "HKCU", "_type": saved["type"]})
            for variable, relative in [("APPDATA", r"Microsoft\Windows\Start Menu\Programs\Startup"),
                                       ("PROGRAMDATA", r"Microsoft\Windows\Start Menu\Programs\Startup")]:
                base = os.environ.get(variable)
                if not base:
                    continue
                folder = Path(base) / relative
                try:
                    for path in folder.iterdir():
                        if path.name.casefold() != "desktop.ini" and path.is_file():
                            items.append({"id": self._startup_id(variable, str(path)), "name": path.stem,
                                          "command": str(path), "scope": "Thư mục Startup", "enabled": True,
                                          "can_toggle": False, "note": "Chỉ xem; mở Cài đặt Windows để quản lý.", "_source": variable})
                except OSError:
                    continue
            return sorted(items, key=lambda item: (not item["can_toggle"], item["name"].casefold()))

    def toggle_startup(self, identifier, enabled, confirmed=False):
        self._confirmed(confirmed)
        if not isinstance(enabled, bool):
            raise ValueError("Trạng thái khởi động phải là bật hoặc tắt.")
        with self.store.lock:
            item = next((item for item in self.startup_items() if item["id"] == identifier), None)
            if not item or not item["can_toggle"] or item["_source"] != "HKCU":
                raise ValueError("Mục này chỉ xem hoặc đã thay đổi. Hãy làm mới; có thể quản lý các mục khác trong Windows.")
            if enabled == item["enabled"]:
                return {"ok": True, "message": "Mục khởi động đã ở trạng thái này."}
            registry = self.registry
            backup = self._startup_backup()
            access = registry.KEY_QUERY_VALUE | registry.KEY_SET_VALUE | getattr(registry, "KEY_WOW64_64KEY", 0)
            if enabled:
                with registry.CreateKeyEx(registry.HKEY_CURRENT_USER, RUN_KEY, 0, access) as key:
                    try:
                        registry.QueryValueEx(key, item["name"])
                    except FileNotFoundError:
                        pass
                    else:
                        raise ValueError("Đã có mục cùng tên. Ứng dụng không ghi đè; hãy làm mới danh sách.")
                    saved = backup[item["name"]]
                    registry.SetValueEx(key, item["name"], 0, saved["type"], saved["command"])
                    actual, kind = registry.QueryValueEx(key, item["name"])
                    if actual != saved["command"] or kind != saved["type"]:
                        raise OSError("Windows chưa xác nhận dữ liệu khởi động vừa khôi phục.")
                del backup[item["name"]]
                self.store.write("startup.json", backup)
                message = f"Đã khôi phục mục khởi động {item['name']}. Windows có thể còn quản lý trạng thái riêng của mục này."
            else:
                with registry.OpenKey(registry.HKEY_CURRENT_USER, RUN_KEY, 0, access) as key:
                    actual, kind = registry.QueryValueEx(key, item["name"])
                    if actual != item["command"] or kind != item["_type"]:
                        raise ValueError("Mục khởi động vừa thay đổi. Hãy làm mới rồi thử lại.")
                    backup[item["name"]] = {"command": actual, "type": kind}
                    self.store.write("startup.json", backup)  # Durable backup precedes every deletion.
                    registry.DeleteValue(key, item["name"])
                message = f"Đã tắt mục khởi động {item['name']}. Có thể bật lại trong ứng dụng."
            return self.store.result("Khởi động Windows", True, message)
