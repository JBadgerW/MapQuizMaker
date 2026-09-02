"""Running a build without freezing the window.

`build_quiz` invokes Typst once per output file, each of which re-reads and
re-embeds the map. On the UI thread that stops the window repainting, and the
OS greys it out as "not responding" -- at which point the reasonable thing
for a user to do is click Build again.

So the build runs on a worker thread and the Tk main loop polls a queue with
`after()`. Tk is not thread-safe: the worker only ever puts messages on the
queue, and every widget call happens back on the main thread.
"""

import queue
import threading
import tkinter as tk
from tkinter import ttk

import ttkbootstrap as ttkb

from map_quiz_maker.config import APP_NAME

POLL_INTERVAL_MS = 40

_PROGRESS = "progress"
_DONE = "done"
_FAILED = "failed"
_CANCELLED = "cancelled"


class BuildProgressDialog:
    """A modal progress window that owns one background build.

    `run` blocks until the build finishes, fails or is cancelled, and returns
    the list of PDF paths, or None if it did not complete.
    """

    def __init__(self, parent, build_callable):
        self.parent = parent
        self.build_callable = build_callable

        self._queue: queue.Queue = queue.Queue()
        self._cancel = threading.Event()
        self._result = None
        self._error = None

        self.dialog = ttkb.Toplevel(parent)
        self.dialog.title(APP_NAME)
        self.dialog.transient(parent)
        self.dialog.resizable(False, False)
        # The window manager's close button means the same as Cancel.
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)

        body = ttk.Frame(self.dialog, padding=20)
        body.grid(row=0, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)

        self.label = ttk.Label(body, text="Starting...", width=44, anchor="w")
        self.label.grid(row=0, column=0, sticky="w")

        self.bar = ttk.Progressbar(body, mode="determinate", length=340, maximum=1)
        self.bar.grid(row=1, column=0, sticky="ew", pady=(12, 0))

        self.cancel_button = ttkb.Button(
            body, text="Cancel", command=self.cancel, bootstyle="secondary"
        )
        self.cancel_button.grid(row=2, column=0, sticky="e", pady=(16, 0))

        self.dialog.bind("<Escape>", lambda _event: self.cancel())

    # -- worker side (no widget calls below this line) ----------------------

    def _report(self, done, total, label) -> None:
        self._queue.put((_PROGRESS, (done, total, label)))

    def _should_cancel(self) -> bool:
        return self._cancel.is_set()

    def _work(self) -> None:
        from map_quiz_maker.export.typst_build import BuildCancelled

        try:
            paths = self.build_callable(self._report, self._should_cancel)
        except BuildCancelled:
            self._queue.put((_CANCELLED, None))
        except Exception as exc:  # noqa: BLE001
            # A build runs PIL, Typst and the filesystem. Whatever comes back
            # has to reach the user as a dialog, not a traceback on a terminal
            # they cannot see, so nothing may escape this thread.
            self._queue.put((_FAILED, exc))
        else:
            self._queue.put((_DONE, paths))

    # -- main thread --------------------------------------------------------

    def cancel(self) -> None:
        """Asks the build to stop at the next version boundary.

        A Typst compile in flight cannot be interrupted, so the button
        reports that it has been heard rather than pretending to be instant.
        """
        self._cancel.set()
        self.cancel_button.configure(state="disabled")
        self.label.config(text="Finishing the current file, then stopping...")

    def _poll(self) -> None:
        try:
            while True:
                kind, payload = self._queue.get_nowait()
                if kind == _PROGRESS:
                    done, total, label = payload
                    self.bar.configure(maximum=max(1, total), value=done)
                    if not self._cancel.is_set():
                        self.label.config(text=label)
                elif kind == _DONE:
                    self._result = payload
                    self._finish()
                    return
                elif kind == _FAILED:
                    self._error = payload
                    self._finish()
                    return
                else:  # cancelled
                    self._finish()
                    return
        except queue.Empty:
            pass
        self.dialog.after(POLL_INTERVAL_MS, self._poll)

    def _finish(self) -> None:
        self.dialog.grab_release()
        self.dialog.destroy()

    def run(self):
        """Runs the build, returning its paths, or None if it did not finish.

        Re-raises whatever the build raised, so the caller can turn it into a
        message worth reading.
        """
        _centre_on_parent(self.dialog, self.parent)
        self.dialog.grab_set()

        worker = threading.Thread(target=self._work, daemon=True)
        worker.start()

        self.dialog.after(POLL_INTERVAL_MS, self._poll)
        self.parent.wait_window(self.dialog)

        if self._error is not None:
            raise self._error
        return self._result


def _centre_on_parent(dialog: tk.Toplevel, parent) -> None:
    dialog.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() - dialog.winfo_width()) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - dialog.winfo_height()) // 3
    dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
