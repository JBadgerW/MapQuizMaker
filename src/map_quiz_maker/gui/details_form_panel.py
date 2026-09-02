"""Class / Author / Title / Instructions, written straight to the document."""

from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

FIELDS = [
    ("class_name", "Class:"),
    ("author", "Author:"),
    ("title", "Title:"),
]


class DetailsFormPanel:
    """Quiz metadata. Every field writes through on edit, so the document is
    always current and no 'flush before build' step is needed.

    Author and Class become the etqw manifest's `author` and `course`.
    """

    def __init__(self, parent, on_changed):
        self.on_changed = on_changed
        self._loading = False

        self.frame = ttk.LabelFrame(parent, text="Quiz Details")
        self.frame.columnconfigure(1, weight=1)

        self.entries = {}
        for row, (field, label_text) in enumerate(FIELDS):
            ttk.Label(self.frame, text=label_text, width=12, anchor="e").grid(
                row=row, column=0, sticky="e", padx=5, pady=4
            )
            entry = ttk.Entry(self.frame)
            entry.grid(row=row, column=1, sticky="ew", padx=5, pady=4)
            entry.bind("<KeyRelease>", lambda _e, f=field: self._changed(f))
            self.entries[field] = entry

        instructions_row = len(FIELDS)
        ttk.Label(self.frame, text="Instructions:", width=12, anchor="e").grid(
            row=instructions_row, column=0, sticky="ne", padx=5, pady=4
        )
        self.instructions_text = ScrolledText(self.frame, height=4, width=1, wrap="word")
        self.instructions_text.grid(
            row=instructions_row, column=1, sticky="nsew", padx=5, pady=4
        )
        self.instructions_text.bind("<KeyRelease>", lambda _e: self._changed("instructions"))

    def _changed(self, field: str) -> None:
        if self._loading:
            return
        self.on_changed(**{field: self._read(field)})

    def _read(self, field: str) -> str:
        if field == "instructions":
            return self.instructions_text.get("1.0", "end-1c")
        return self.entries[field].get()

    def load(self, meta) -> None:
        """Replaces the visible values from `meta` without echoing back."""
        self._loading = True
        try:
            for field, _ in FIELDS:
                entry = self.entries[field]
                value = getattr(meta, field)
                if entry.get() != value:
                    entry.delete(0, "end")
                    entry.insert(0, value)
            if self.instructions_text.get("1.0", "end-1c") != meta.instructions:
                self.instructions_text.delete("1.0", "end")
                self.instructions_text.insert("1.0", meta.instructions)
        finally:
            self._loading = False
