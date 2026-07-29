from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

import ttkbootstrap as ttkb


class DetailsFormPanel:
    """Class/Title/Instructions fields plus Save Quiz / Save As buttons."""

    def __init__(self, parent, on_save, on_save_as):
        self.frame = ttk.LabelFrame(parent, text="Quiz Details")
        self.frame.columnconfigure(1, weight=1)

        self.class_entry = self._add_entry_row(0, "Class:")
        self.title_entry = self._add_entry_row(1, "Title:")

        instructions_label = ttk.Label(self.frame, text="Instructions:", width=12, anchor="e")
        instructions_label.grid(row=2, column=0, sticky="ne", padx=5, pady=4)

        self.instructions_text = ScrolledText(self.frame, height=5, width=1, wrap="word")
        self.instructions_text.grid(row=2, column=1, sticky="nsew", padx=5, pady=4)

        button_frame = ttk.Frame(self.frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)

        save_button = ttkb.Button(button_frame, text="Save Quiz", command=on_save, bootstyle="success")
        save_button.grid(row=0, column=0, padx=(0, 6))

        save_as_button = ttkb.Button(button_frame, text="Save As...", command=on_save_as, bootstyle="secondary")
        save_as_button.grid(row=0, column=1)

    def _add_entry_row(self, row, label_text):
        label = ttk.Label(self.frame, text=label_text, width=12, anchor="e")
        label.grid(row=row, column=0, sticky="e", padx=5, pady=4)
        entry = ttk.Entry(self.frame)
        entry.grid(row=row, column=1, sticky="ew", padx=5, pady=4)
        return entry

    def get_class(self) -> str:
        return self.class_entry.get()

    def get_title(self) -> str:
        return self.title_entry.get()

    def get_instructions(self) -> str:
        return self.instructions_text.get("1.0", "end-1c")
