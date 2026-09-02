"""The dialog shown after a successful build.

"Save Quiz" used to give no feedback at all -- the button was pressed,
nothing visibly changed, and the PDF landed in a folder the user could not
name. This dialog answers both halves of "did it work, and where is it?"
and offers to open the result rather than making the user go looking.
"""

import tkinter as tk
from tkinter import messagebox, ttk

import ttkbootstrap as ttkb

from map_quiz_maker.config import APP_NAME
from map_quiz_maker.desktop import open_file, show_in_folder

# Enough to confirm what was written without turning the dialog into a list.
MAX_LISTED_FILES = 6


KEY_SUFFIX = "_KEY"


def _describe(pdf_paths) -> str:
    if len(pdf_paths) == 1:
        return f"Saved {pdf_paths[0].name}"
    worksheets = [p for p in pdf_paths if not p.stem.endswith(KEY_SUFFIX)]
    if len(worksheets) < len(pdf_paths):
        sheets = "worksheet" if len(worksheets) == 1 else "worksheets"
        return f"Saved {len(worksheets)} {sheets} and an answer key"
    return f"Saved {len(pdf_paths)} files"


def show_build_result(parent, pdf_paths) -> None:
    """Reports a finished build and offers to open it.

    `pdf_paths` is the non-empty list returned by `build_quiz`; the first
    entry is what the "Open PDF" button opens.
    """
    if not pdf_paths:
        return

    folder = pdf_paths[0].parent

    dialog = ttkb.Toplevel(parent)
    dialog.title(APP_NAME)
    dialog.transient(parent)
    dialog.resizable(False, False)

    body = ttk.Frame(dialog, padding=20)
    body.grid(row=0, column=0, sticky="nsew")
    body.columnconfigure(0, weight=1)

    ttk.Label(body, text=_describe(pdf_paths), font=("Arial", 13, "bold")).grid(
        row=0, column=0, sticky="w"
    )

    ttk.Label(body, text=f"in {folder}", wraplength=420, foreground="grey").grid(
        row=1, column=0, sticky="w", pady=(4, 0)
    )

    if len(pdf_paths) > 1:
        listed = [p.name for p in pdf_paths[:MAX_LISTED_FILES]]
        remaining = len(pdf_paths) - len(listed)
        if remaining:
            listed.append(f"and {remaining} more")
        ttk.Label(body, text="\n".join(listed), justify="left", wraplength=420).grid(
            row=2, column=0, sticky="w", pady=(10, 0)
        )

    buttons = ttk.Frame(body)
    buttons.grid(row=3, column=0, sticky="e", pady=(20, 0))

    def _open_pdf():
        if not open_file(pdf_paths[0]):
            messagebox.showerror(
                APP_NAME,
                "That PDF couldn't be opened automatically.\n\n"
                f"You can find it at:\n{pdf_paths[0]}",
                parent=dialog,
            )

    def _show_folder():
        if not show_in_folder(pdf_paths[0]):
            messagebox.showerror(
                APP_NAME,
                f"That folder couldn't be opened automatically.\n\n{folder}",
                parent=dialog,
            )

    ttkb.Button(buttons, text="Open PDF", command=_open_pdf, bootstyle="success").grid(
        row=0, column=0, padx=(0, 6)
    )
    ttkb.Button(
        buttons, text="Show in Folder", command=_show_folder, bootstyle="secondary"
    ).grid(row=0, column=1, padx=(0, 6))

    close_button = ttkb.Button(
        buttons, text="Close", command=dialog.destroy, bootstyle="secondary-outline"
    )
    close_button.grid(row=0, column=2)

    dialog.bind("<Escape>", lambda _event: dialog.destroy())
    dialog.bind("<Return>", lambda _event: _open_pdf())

    _centre_on_parent(dialog, parent)
    close_button.focus_set()
    dialog.grab_set()
    dialog.wait_window()


def _centre_on_parent(dialog: tk.Toplevel, parent) -> None:
    dialog.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() - dialog.winfo_width()) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - dialog.winfo_height()) // 3
    dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
