import tkinter as tk
from tkinter import ttk

import ttkbootstrap as ttkb


class AnswerListPanel:
    """Scrollable list of marker-number -> answer entry rows."""

    def __init__(self, parent, on_answer_changed):
        self.on_answer_changed = on_answer_changed

        self.frame = ttk.Frame(parent)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        answer_label = ttk.Label(self.frame, text="Answers", font=("Arial", 12))
        answer_label.grid(row=0, column=0, pady=10)

        self.answer_frame = ttk.Frame(self.frame)
        self.answer_frame.grid(row=1, column=0, sticky='nsew')
        self.answer_frame.columnconfigure(0, weight=1)
        self.answer_frame.rowconfigure(0, weight=1)

        # tk.Canvas isn't a themable ttk widget, so its background is set
        # explicitly to match the current ttkbootstrap theme's surface color.
        self.answer_canvas = tk.Canvas(self.answer_frame, background=ttkb.Style().colors.bg, highlightthickness=0)
        self.answer_canvas.grid(row=0, column=0, sticky='nsew')

        self.answer_scrollbar = ttk.Scrollbar(self.answer_frame, orient=tk.VERTICAL, command=self.answer_canvas.yview)
        self.answer_scrollbar.grid(row=0, column=1, sticky='ns')

        self.answer_canvas.configure(yscrollcommand=self.answer_scrollbar.set)
        self.answer_canvas.bind('<Configure>', self._on_answer_canvas_configure)

        self.answer_list_frame = ttk.Frame(self.answer_canvas)
        self.answer_list_window = self.answer_canvas.create_window((0, 0), window=self.answer_list_frame, anchor=tk.NW)

        self.answer_list_frame.bind('<Configure>', self._on_answer_frame_configure)

    def _on_answer_canvas_configure(self, event):
        self.answer_canvas.itemconfig(self.answer_list_window, width=event.width)

    def _on_answer_frame_configure(self, event):
        self.answer_canvas.configure(scrollregion=self.answer_canvas.bbox("all"))

    def refresh(self, markers):
        for widget in self.answer_list_frame.winfo_children():
            widget.destroy()

        self.answer_list_frame.columnconfigure(0, weight=1)

        for idx, marker in enumerate(markers):
            frame = ttk.Frame(self.answer_list_frame)
            frame.grid(row=idx, column=0, sticky='ew', padx=5, pady=2)
            frame.columnconfigure(0, weight=0)
            frame.columnconfigure(1, weight=1)

            label = ttk.Label(frame, text=f"{marker.display_number}:", width=5)
            label.grid(row=0, column=0, sticky="w")

            entry = ttk.Entry(frame)
            entry.grid(row=0, column=1, sticky="ew")
            entry.insert(0, marker.answer)
            entry.bind('<FocusOut>', lambda e, mid=marker.id: self.on_answer_changed(mid, e.widget.get()))

        self.answer_list_frame.update_idletasks()
        self.answer_canvas.configure(scrollregion=self.answer_canvas.bbox("all"))
