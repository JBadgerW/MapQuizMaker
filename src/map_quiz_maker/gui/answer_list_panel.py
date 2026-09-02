"""The answer list: one row per marker, linked to the map.

`refresh` reconciles the existing rows against the document rather than
destroying and rebuilding them. Rebuilding was what lost typed answers, and
it also threw away focus, selection and scroll position on every change --
which, with thirty markers, is most of the work of using the app.
"""

import tkinter as tk
from tkinter import ttk

import ttkbootstrap as ttkb

ROW_SELECTED_STYLE = "info.TLabel"
ROW_NORMAL_STYLE = "TLabel"
MISSING_ANSWER_STYLE = "danger.TLabel"


class _AnswerRow:
    """One marker's row: its number, its answer entry, and a delete button."""

    def __init__(self, parent, marker, callbacks):
        self.marker_id = marker.id
        self._callbacks = callbacks

        self.frame = ttk.Frame(parent)
        self.frame.columnconfigure(1, weight=1)

        self.label = ttk.Label(self.frame, width=4, anchor="e")
        self.label.grid(row=0, column=0, sticky="w", padx=(0, 4))

        self.var = tk.StringVar(value=marker.answer)
        # Write through on every keystroke. A focus-out commit loses the text
        # whenever the row is replaced before focus moves, which is what
        # clicking the map to add the next marker does.
        self.var.trace_add("write", self._on_typed)

        self.entry = ttk.Entry(self.frame, textvariable=self.var)
        self.entry.grid(row=0, column=1, sticky="ew")
        self.entry.bind("<FocusIn>", self._on_focus)
        self.entry.bind("<Return>", self._on_return)
        self.entry.bind("<Down>", self._on_return)
        self.entry.bind("<Up>", self._on_up)

        self.delete_button = ttkb.Button(
            self.frame, text="×", width=2, bootstyle="secondary-link",
            command=self._on_delete,
        )
        self.delete_button.grid(row=0, column=2, padx=(2, 0))

    def _on_typed(self, *_):
        self._callbacks["changed"](self.marker_id, self.var.get())

    def _on_focus(self, _event):
        self._callbacks["select"](self.marker_id)

    def _on_return(self, _event):
        self._callbacks["next"](self.marker_id)
        return "break"

    def _on_up(self, _event):
        self._callbacks["previous"](self.marker_id)
        return "break"

    def _on_delete(self):
        self._callbacks["delete"](self.marker_id)

    def update(self, marker, selected: bool) -> None:
        self.label.config(text=f"{marker.display_number}:")
        # Only touch the entry when it actually differs, so a renumber never
        # disturbs the cursor of the row being typed into.
        if self.var.get() != marker.answer:
            self.var.set(marker.answer)

        if selected:
            style = ROW_SELECTED_STYLE
        elif not marker.answer.strip():
            style = MISSING_ANSWER_STYLE
        else:
            style = ROW_NORMAL_STYLE
        self.label.configure(style=style)

    def destroy(self) -> None:
        self.frame.destroy()


class AnswerListPanel:
    def __init__(self, parent, on_answer_changed, on_delete, on_select):
        self._callbacks = {
            "changed": on_answer_changed,
            "delete": on_delete,
            "select": on_select,
            "next": self._focus_next,
            "previous": self._focus_previous,
        }
        self._rows: dict[int, _AnswerRow] = {}
        self._order: list[int] = []

        self.frame = ttk.Frame(parent)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        self.heading = ttk.Label(self.frame, text="Answers", font=("Arial", 12))
        self.heading.grid(row=0, column=0, pady=10)

        self.answer_frame = ttk.Frame(self.frame)
        self.answer_frame.grid(row=1, column=0, sticky="nsew")
        self.answer_frame.columnconfigure(0, weight=1)
        self.answer_frame.rowconfigure(0, weight=1)

        # tk.Canvas isn't a themable ttk widget, so its background is set
        # explicitly to match the current ttkbootstrap theme's surface color.
        self.answer_canvas = tk.Canvas(
            self.answer_frame, background=ttkb.Style().colors.bg, highlightthickness=0
        )
        self.answer_canvas.grid(row=0, column=0, sticky="nsew")

        self.answer_scrollbar = ttk.Scrollbar(
            self.answer_frame, orient=tk.VERTICAL, command=self.answer_canvas.yview
        )
        self.answer_scrollbar.grid(row=0, column=1, sticky="ns")

        self.answer_canvas.configure(yscrollcommand=self.answer_scrollbar.set)
        self.answer_canvas.bind("<Configure>", self._on_canvas_configure)

        self.list_frame = ttk.Frame(self.answer_canvas)
        self.list_window = self.answer_canvas.create_window(
            (0, 0), window=self.list_frame, anchor=tk.NW
        )
        self.list_frame.columnconfigure(0, weight=1)
        self.list_frame.bind("<Configure>", self._on_frame_configure)

        for widget in (self.answer_canvas, self.list_frame):
            widget.bind("<MouseWheel>", self._on_wheel)
            widget.bind("<Button-4>", self._on_wheel)
            widget.bind("<Button-5>", self._on_wheel)

        self.empty_label = ttk.Label(
            self.list_frame,
            text="Click the map to add a location.",
            foreground="grey",
            wraplength=280,
            justify="left",
        )

    # -- scrolling ----------------------------------------------------------

    def _on_canvas_configure(self, event):
        self.answer_canvas.itemconfig(self.list_window, width=event.width)

    def _on_frame_configure(self, _event):
        self.answer_canvas.configure(scrollregion=self.answer_canvas.bbox("all"))

    def _on_wheel(self, event):
        if event.num == 4:
            steps = 1
        elif event.num == 5:
            steps = -1
        else:
            steps = 1 if event.delta > 0 else -1
        self.answer_canvas.yview_scroll(-steps, "units")
        return "break"

    # -- keyboard navigation ------------------------------------------------

    def _neighbour(self, marker_id, offset):
        if marker_id not in self._order:
            return None
        index = self._order.index(marker_id) + offset
        if 0 <= index < len(self._order):
            return self._order[index]
        return None

    def _focus_next(self, marker_id):
        self.focus_marker(self._neighbour(marker_id, 1))

    def _focus_previous(self, marker_id):
        self.focus_marker(self._neighbour(marker_id, -1))

    def focus_marker(self, marker_id) -> None:
        row = self._rows.get(marker_id)
        if row is not None:
            row.entry.focus_set()
            row.entry.icursor(tk.END)
            self.scroll_to(marker_id)

    def scroll_to(self, marker_id) -> None:
        """Brings a row into view without disturbing focus."""
        row = self._rows.get(marker_id)
        if row is None:
            return
        self.list_frame.update_idletasks()
        total = max(1, self.list_frame.winfo_height())
        top = row.frame.winfo_y() / total
        bottom = (row.frame.winfo_y() + row.frame.winfo_height()) / total
        view_top, view_bottom = self.answer_canvas.yview()
        if top < view_top:
            self.answer_canvas.yview_moveto(top)
        elif bottom > view_bottom:
            self.answer_canvas.yview_moveto(
                max(0.0, bottom - (view_bottom - view_top))
            )

    # -- reconciliation -----------------------------------------------------

    def refresh(self, markers, selected_id=None) -> None:
        markers = list(markers)
        self._order = [m.id for m in markers]
        wanted = set(self._order)

        for marker_id in list(self._rows):
            if marker_id not in wanted:
                self._rows.pop(marker_id).destroy()

        for position, marker in enumerate(markers):
            row = self._rows.get(marker.id)
            if row is None:
                row = _AnswerRow(self.list_frame, marker, self._callbacks)
                self._rows[marker.id] = row
            row.frame.grid(row=position, column=0, sticky="ew", padx=5, pady=2)
            row.update(marker, selected=marker.id == selected_id)

        if markers:
            self.empty_label.grid_forget()
        else:
            self.empty_label.grid(row=0, column=0, sticky="w", padx=8, pady=8)

        missing = sum(1 for m in markers if not m.answer.strip())
        if not markers:
            self.heading.config(text="Answers")
        elif missing:
            self.heading.config(text=f"Answers  ({missing} still blank)")
        else:
            self.heading.config(text=f"Answers  ({len(markers)})")

        self.list_frame.update_idletasks()
        self.answer_canvas.configure(scrollregion=self.answer_canvas.bbox("all"))
