"""Small atomic local store. Application state is never kept in the source repo."""

import copy
import json
import os
import tempfile
import threading
from datetime import datetime
from pathlib import Path


class StateStore:
    def __init__(self, directory=None):
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".local" / "share")
        self.directory = Path(directory) if directory is not None else base / "PCMonitorMini" / "v2"
        self.lock = threading.RLock()

    def read(self, name, default):
        with self.lock:
            try:
                return json.loads((self.directory / name).read_text(encoding="utf-8"))
            except FileNotFoundError:
                return copy.deepcopy(default)
            except (ValueError, UnicodeError) as exc:
                raise ValueError("Bản lưu cục bộ không đọc được. Dữ liệu được giữ nguyên; hãy kiểm tra thư mục AppData của ứng dụng.") from exc

    def write(self, name, data):
        with self.lock:
            self.directory.mkdir(parents=True, exist_ok=True)
            descriptor, temporary = tempfile.mkstemp(prefix=".save-", dir=self.directory)
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                    json.dump(data, stream, ensure_ascii=False, indent=2)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, self.directory / name)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)

    def history(self):
        entries = self.read("history.json", [])
        if not isinstance(entries, list):
            raise ValueError("Lịch sử cục bộ bị sai định dạng; ứng dụng không ghi đè dữ liệu đó.")
        return list(reversed(entries[-100:]))

    def result(self, action, ok, message, **extra):
        result = {"ok": bool(ok), "message": message, **extra}
        entry = {"at": datetime.now().astimezone().isoformat(timespec="seconds"),
                 "action": action, "ok": bool(ok), "message": message}
        try:
            with self.lock:
                entries = list(reversed(self.history()))
                self.write("history.json", (entries + [entry])[-100:])
        except (OSError, ValueError):
            result["message"] += " Chưa ghi được lịch sử cục bộ."
        return result
