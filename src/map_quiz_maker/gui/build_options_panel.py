"""Number-of-versions / separate-files / word-bank options."""

import tkinter as tk
from tkinter import ttk

MAX_VERSIONS = 50


class BuildOptionsPanel:
    """Build options, written straight to the document as they change."""

    def __init__(self, parent, on_changed):
        self.on_changed = on_changed
        self._loading = False

        self.frame = ttk.LabelFrame(parent, text="Build Options")
        self.frame.columnconfigure(1, weight=1)

        ttk.Label(self.frame, text="Number of versions:", width=20, anchor="e").grid(
            row=0, column=0, sticky="e", padx=5, pady=4
        )
        self.num_versions_var = tk.IntVar(value=1)
        self.num_versions_var.trace_add("write", lambda *_: self._changed())
        ttk.Spinbox(
            self.frame, from_=1, to=MAX_VERSIONS,
            textvariable=self.num_versions_var, width=5,
        ).grid(row=0, column=1, sticky="w", padx=5, pady=4)

        self.separate_files_var = tk.BooleanVar(value=False)
        self.separate_files_var.trace_add("write", lambda *_: self._changed())
        ttk.Checkbutton(
            self.frame, text="Save each version as its own file",
            variable=self.separate_files_var,
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=5, pady=4)

        self.word_bank_var = tk.BooleanVar(value=False)
        self.word_bank_var.trace_add("write", lambda *_: self._changed())
        ttk.Checkbutton(
            self.frame, text="Include word bank", variable=self.word_bank_var,
        ).grid(row=2, column=0, columnspan=2, sticky="w", padx=5, pady=4)

        # Off by default: the answer key used to be bound into the worksheet
        # PDF with no way to separate it, so printing thirty copies handed
        # out the answers on page two.
        self.combine_key_var = tk.BooleanVar(value=False)
        self.combine_key_var.trace_add("write", lambda *_: self._changed())
        ttk.Checkbutton(
            self.frame,
            text="Put the answer key in the same PDF",
            variable=self.combine_key_var,
        ).grid(row=3, column=0, columnspan=2, sticky="w", padx=5, pady=4)

    def _num_versions(self) -> int:
        """A spinbox can hold text mid-edit, so an unreadable value means 1."""
        try:
            return max(1, min(MAX_VERSIONS, int(self.num_versions_var.get())))
        except (tk.TclError, ValueError):
            return 1

    def _changed(self) -> None:
        if self._loading:
            return
        self.on_changed(
            num_versions=self._num_versions(),
            separate_files=bool(self.separate_files_var.get()),
            include_word_bank=bool(self.word_bank_var.get()),
            combine_key=bool(self.combine_key_var.get()),
        )

    def load(self, meta) -> None:
        self._loading = True
        try:
            self.num_versions_var.set(meta.num_versions)
            self.separate_files_var.set(meta.separate_files)
            self.word_bank_var.set(meta.include_word_bank)
            self.combine_key_var.set(meta.combine_key)
        finally:
            self._loading = False
