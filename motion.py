"""Interruptible Tk animations; no worker threads, timers stop when idle."""

import ctypes
import os
import time
import tkinter as tk


def system_motion_enabled():
    if os.name == "nt":
        enabled = ctypes.c_int(1)
        if ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(enabled), 0):
            return bool(enabled.value)
    return True


def blend(start, end, progress):
    progress = max(0.0, min(1.0, float(progress)))
    a = tuple(int(start[index:index + 2], 16) for index in (1, 3, 5))
    b = tuple(int(end[index:index + 2], 16) for index in (1, 3, 5))
    return "#" + "".join(f"{round(x + (y - x) * progress):02x}" for x, y in zip(a, b))


class Animator:
    def __init__(self, owner, enabled=True):
        self.owner, self.enabled = owner, bool(enabled)
        self._jobs = {}
        owner.bind("<Destroy>", self._destroy, add="+")

    def _destroy(self, event):
        if event.widget is self.owner or event.widget is getattr(self.owner, "_canvas", None):
            self.cancel_all()

    @property
    def active_count(self):
        return len(self._jobs)

    def animate(self, key, update, duration=0.28, complete=None):
        self.cancel(key)
        if not self.enabled or duration <= 0:
            update(1.0)
            if complete:
                complete()
            return
        job = {"after": None, "update": update, "complete": complete}
        self._jobs[key] = job
        start = time.monotonic()

        def tick():
            if self._jobs.get(key) is not job:
                return
            job["after"] = None
            try:
                if not self.owner.winfo_exists():
                    self.cancel(key)
                    return
                elapsed = min(1.0, max(0.0, (time.monotonic() - start) / duration))
                update(1.0 - (1.0 - elapsed) ** 3)
                if self._jobs.get(key) is not job:
                    return
                if elapsed >= 1:
                    self._jobs.pop(key, None)
                    if complete:
                        complete()
                else:
                    job["after"] = self.owner.after(16, tick)
            except tk.TclError:
                self.cancel(key)
            except Exception:
                self.cancel(key)
                raise

        tick()

    def cancel(self, key):
        job = self._jobs.pop(key, None)
        if job and job["after"] is not None:
            try:
                self.owner.after_cancel(job["after"])
            except tk.TclError:
                pass

    def cancel_all(self):
        for key in tuple(self._jobs):
            self.cancel(key)

    def set_enabled(self, enabled):
        jobs = list(self._jobs.values())
        self.cancel_all()
        self.enabled = bool(enabled)
        for job in jobs:
            try:
                job["update"](1.0)
                if job["complete"]:
                    job["complete"]()
            except tk.TclError:
                pass
