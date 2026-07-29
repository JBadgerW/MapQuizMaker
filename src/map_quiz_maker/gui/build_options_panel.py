import tkinter as tk
from tkinter import ttk


class BuildOptionsPanel:
    """Number-of-versions / separate-files / word-bank build options."""

    def __init__(self, parent):
        self.frame = ttk.LabelFrame(parent, text="Build Options")
        self.frame.columnconfigure(1, weight=1)

        ttk.Label(self.frame, text="Number of versions:", width=20, anchor="e").grid(
            row=0, column=0, sticky="e", padx=5, pady=4
        )
        self.num_versions_var = tk.IntVar(value=1)
        self.num_versions_spinbox = ttk.Spinbox(
            self.frame, from_=1, to=50, textvariable=self.num_versions_var, width=5
        )
        self.num_versions_spinbox.grid(row=0, column=1, sticky="w", padx=5, pady=4)

        self.separate_files_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self.frame, text="Save each version as its own file", variable=self.separate_files_var
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=5, pady=4)

        self.word_bank_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self.frame, text="Include word bank", variable=self.word_bank_var
        ).grid(row=2, column=0, columnspan=2, sticky="w", padx=5, pady=4)

    def get_num_versions(self) -> int:
        try:
            return max(1, int(self.num_versions_var.get()))
        except (tk.TclError, ValueError):
            return 1

    def get_separate_files(self) -> bool:
        return bool(self.separate_files_var.get())

    def get_include_word_bank(self) -> bool:
        return bool(self.word_bank_var.get())
