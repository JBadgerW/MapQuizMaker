"""The application window: owns the document and keeps the views in step.

The document is the single source of truth. Panels report user intent through
callbacks and are re-rendered from the document afterwards; no panel holds
marker state of its own, which is what makes selection, undo and the
map<->list link possible without any of them drifting apart.
"""

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from map_quiz_maker import settings
from map_quiz_maker.config import APP_NAME
from map_quiz_maker.etqw import FILE_SUFFIX, EtqwError, load_document, save_document
from map_quiz_maker.export.naming import sanitize_filename
from map_quiz_maker.export.typst_build import build_quiz
from map_quiz_maker.gui.answer_list_panel import AnswerListPanel
from map_quiz_maker.gui.build_options_panel import BuildOptionsPanel
from map_quiz_maker.gui.build_result_dialog import show_build_result
from map_quiz_maker.gui.details_form_panel import DetailsFormPanel
from map_quiz_maker.gui.image_canvas_panel import ImageCanvasPanel
from map_quiz_maker.models import QuizDocument

QUIZ_FILETYPES = [("Map quiz", f"*{FILE_SUFFIX}"), ("All files", "*.*")]
DEFAULT_GEOMETRY = "1280x820"
MIN_SIZE = (960, 640)


class MainWindow:
    def __init__(self, root):
        self.root = root
        self.doc = QuizDocument()
        self.selected_id = None

        root.title(APP_NAME)
        root.geometry(DEFAULT_GEOMETRY)
        root.minsize(*MIN_SIZE)
        root.protocol("WM_DELETE_WINDOW", self.quit)

        self._build_layout()
        self._build_menu()
        self._bind_shortcuts()

        self.doc.add_listener(self._sync_views)
        self._new_document(prompt=False)

    # -- construction -------------------------------------------------------

    def _build_layout(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.main_frame = ttk.Frame(self.root)
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(0, weight=1)

        self.image_panel = ImageCanvasPanel(
            self.main_frame, self.root,
            on_add=self._add_marker,
            on_delete=self._delete_marker,
            on_move=self._move_marker,
            on_select=self._select_marker,
        )
        self.image_panel.frame.grid(row=0, column=0, sticky="nsew")
        self.image_panel.load_button.configure(command=self.open_image)

        self.right_frame = ttk.Frame(self.main_frame, width=380, padding=(8, 10, 8, 8))
        self.right_frame.grid(row=0, column=1, sticky="ns")
        self.right_frame.grid_propagate(False)
        self.right_frame.columnconfigure(0, weight=1)
        self.right_frame.rowconfigure(2, weight=1)

        self.details_panel = DetailsFormPanel(self.right_frame, on_changed=self._meta_changed)
        self.details_panel.frame.grid(row=0, column=0, sticky="new")

        self.build_options_panel = BuildOptionsPanel(
            self.right_frame, on_changed=self._meta_changed
        )
        self.build_options_panel.frame.grid(row=1, column=0, sticky="new", pady=(8, 0))

        self.answer_list_panel = AnswerListPanel(
            self.right_frame,
            on_answer_changed=self._answer_changed,
            on_delete=self._delete_marker,
            on_select=self._select_marker,
        )
        self.answer_list_panel.frame.grid(row=2, column=0, sticky="nsew")

    def _build_menu(self):
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New Quiz", accelerator="Ctrl+N", command=self.new_quiz)
        file_menu.add_command(label="Open...", accelerator="Ctrl+O", command=self.open_quiz)
        self.recent_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Open Recent", menu=self.recent_menu)
        file_menu.add_separator()
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.save_quiz)
        file_menu.add_command(
            label="Save As...", accelerator="Ctrl+Shift+S", command=self.save_quiz_as
        )
        file_menu.add_separator()
        file_menu.add_command(label="Load Map Image...", command=self.open_image)
        file_menu.add_separator()
        file_menu.add_command(label="Build Quiz PDF", accelerator="Ctrl+B", command=self.build)
        file_menu.add_command(label="Build Quiz PDF As...", command=self.build_as)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", accelerator="Ctrl+Q", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Undo", accelerator="Ctrl+Z", command=self.undo)
        edit_menu.add_command(label="Redo", accelerator="Ctrl+Y", command=self.redo)
        edit_menu.add_separator()
        edit_menu.add_command(
            label="Delete Selected Location", accelerator="Del",
            command=self._delete_selected,
        )
        menubar.add_cascade(label="Edit", menu=edit_menu)
        self.edit_menu = edit_menu

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="How to Make a Quiz", command=self.show_help)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)
        self._refresh_recent_menu()

    def _bind_shortcuts(self):
        bindings = {
            "<Control-n>": self.new_quiz,
            "<Control-o>": self.open_quiz,
            "<Control-s>": self.save_quiz,
            "<Control-S>": self.save_quiz_as,
            "<Control-b>": self.build,
            "<Control-q>": self.quit,
            "<Control-z>": self.undo,
            "<Control-y>": self.redo,
        }
        for sequence, command in bindings.items():
            self.root.bind_all(sequence, lambda _e, c=command: (c(), "break")[1])
        self.root.bind_all("<Delete>", self._on_delete_key)

    # -- document lifecycle -------------------------------------------------

    def _new_document(self, prompt=True, doc=None) -> bool:
        if prompt and not self._confirm_discard():
            return False
        self.doc = doc if doc is not None else QuizDocument()
        self.doc.add_listener(self._sync_views)
        self.selected_id = None

        if self.doc.image_path is not None:
            self.image_panel.show_image(self.doc.image_path)
        else:
            self.image_panel.clear_image()

        self.details_panel.load(self.doc.meta)
        self.build_options_panel.load(self.doc.meta)
        self._sync_views()
        return True

    def _confirm_discard(self) -> bool:
        """Asks about unsaved work. True means it's fine to proceed."""
        if not self.doc.dirty:
            return True
        name = self.doc.file_path.name if self.doc.file_path else "this quiz"
        answer = messagebox.askyesnocancel(
            APP_NAME,
            f"Save changes to {name} before closing it?",
            parent=self.root,
        )
        if answer is None:
            return False
        if answer:
            return self.save_quiz()
        return True

    def new_quiz(self) -> None:
        self._new_document(prompt=True)

    def open_quiz(self) -> None:
        if not self._confirm_discard():
            return
        chosen = filedialog.askopenfilename(
            filetypes=QUIZ_FILETYPES, initialdir=str(settings.get_output_dir())
        )
        if chosen:
            self._open_path(Path(chosen))

    def _open_path(self, path: Path) -> None:
        try:
            doc = load_document(path)
        except EtqwError as exc:
            messagebox.showerror(APP_NAME, str(exc), parent=self.root)
            settings.forget_recent_file(path)
            self._refresh_recent_menu()
            return
        except OSError as exc:
            messagebox.showerror(
                APP_NAME, f"That file couldn't be opened:\n{exc}", parent=self.root
            )
            return

        self._new_document(prompt=False, doc=doc)
        settings.remember_recent_file(path)
        self._refresh_recent_menu()

    def save_quiz(self) -> bool:
        if self.doc.file_path is None:
            return self.save_quiz_as()
        return self._save_to(self.doc.file_path)

    def save_quiz_as(self) -> bool:
        if self.doc.image_path is None:
            messagebox.showerror(
                APP_NAME, "Load a map image before saving this quiz.", parent=self.root
            )
            return False
        suggested = sanitize_filename(f"{self.doc.meta.class_name}_{self.doc.meta.title}")
        chosen = filedialog.asksaveasfilename(
            defaultextension=FILE_SUFFIX,
            filetypes=QUIZ_FILETYPES,
            initialfile=suggested,
            initialdir=str(settings.get_output_dir()),
        )
        if not chosen:
            return False
        return self._save_to(Path(chosen))

    def _save_to(self, path: Path) -> bool:
        try:
            save_document(self.doc, path)
        except (EtqwError, OSError) as exc:
            messagebox.showerror(
                APP_NAME, f"This quiz couldn't be saved:\n{exc}", parent=self.root
            )
            return False
        settings.remember_recent_file(path)
        self._refresh_recent_menu()
        self._sync_views()
        return True

    def quit(self) -> None:
        if self._confirm_discard():
            self.root.destroy()

    # -- recent files -------------------------------------------------------

    def _refresh_recent_menu(self) -> None:
        self.recent_menu.delete(0, "end")
        recent = settings.get_recent_files()
        if not recent:
            self.recent_menu.add_command(label="(nothing yet)", state="disabled")
            return
        for path in recent:
            self.recent_menu.add_command(
                label=path.name, command=lambda p=path: self._open_recent(p)
            )

    def _open_recent(self, path: Path) -> None:
        if self._confirm_discard():
            self._open_path(path)

    # -- image --------------------------------------------------------------

    def open_image(self) -> None:
        chosen = self.image_panel.choose_image()
        if not chosen:
            return
        if self.doc.markers and not messagebox.askokcancel(
            APP_NAME,
            "Loading a different map removes the locations you've already "
            "marked, because their positions describe the old map.\n\n"
            "Continue?",
            parent=self.root,
        ):
            return
        try:
            self.image_panel.show_image(chosen)
        except (OSError, ValueError) as exc:
            messagebox.showerror(
                APP_NAME,
                "That image couldn't be opened. Try saving it as a PNG or "
                f"JPEG first.\n\n{exc}",
                parent=self.root,
            )
            return
        self.doc.set_image(chosen)

    # -- marker intent ------------------------------------------------------

    def _add_marker(self, x, y) -> None:
        marker = self.doc.add_marker(x, y)
        self.selected_id = marker.id
        self._sync_views()
        self.answer_list_panel.focus_marker(marker.id)

    def _delete_marker(self, marker_id) -> None:
        if self.selected_id == marker_id:
            self.selected_id = None
        self.doc.delete_marker(marker_id)

    def _delete_selected(self) -> None:
        if self.selected_id is not None:
            self._delete_marker(self.selected_id)

    def _on_delete_key(self, event):
        # Delete inside a text field means "delete a character".
        if isinstance(getattr(event, "widget", None), (ttk.Entry,)):
            return None
        self._delete_selected()
        return "break"

    def _move_marker(self, marker_id, x, y) -> None:
        self.doc.move_marker(marker_id, x, y)

    def _select_marker(self, marker_id) -> None:
        if self.selected_id == marker_id:
            return
        self.selected_id = marker_id
        self._sync_views()
        self.answer_list_panel.scroll_to(marker_id)

    def _answer_changed(self, marker_id, answer) -> None:
        self.doc.update_answer(marker_id, answer)
        # update_answer deliberately doesn't notify -- that would rebuild the
        # row being typed into -- so refresh only the parts that can change.
        self._refresh_title()
        self.answer_list_panel.refresh(self.doc.markers, self.selected_id)

    def _meta_changed(self, **fields) -> None:
        self.doc.update_meta(**fields)
        self._refresh_title()

    def undo(self) -> None:
        self.doc.undo()

    def redo(self) -> None:
        self.doc.redo()

    # -- view sync ----------------------------------------------------------

    def _sync_views(self) -> None:
        markers = self.doc.markers
        if self.selected_id is not None and self.doc.get_marker(self.selected_id) is None:
            self.selected_id = None

        self.image_panel.render_markers(markers, self.selected_id)
        self.answer_list_panel.refresh(markers, self.selected_id)
        self.details_panel.load(self.doc.meta)
        self.build_options_panel.load(self.doc.meta)
        self._refresh_title()
        self._refresh_status()
        self._refresh_edit_menu()

    def _refresh_title(self) -> None:
        name = self.doc.file_path.stem if self.doc.file_path else "Untitled"
        marker = "*" if self.doc.dirty else ""
        self.root.title(f"{marker}{name} — {APP_NAME}")

    def _refresh_status(self) -> None:
        if self.doc.image_path is None:
            self.image_panel.set_status("Load an image to begin")
            return
        count = len(self.doc.markers)
        if count == 0:
            self.image_panel.set_status("Click the map to add a location")
            return
        missing = len(self.doc.markers_missing_answers())
        parts = [f"{count} location{'s' if count != 1 else ''}"]
        parts.append(f"{missing} still need answers" if missing else "all answered")
        self.image_panel.set_status(" · ".join(parts))

    def _refresh_edit_menu(self) -> None:
        self.edit_menu.entryconfig(
            0, state="normal" if self.doc.can_undo else "disabled"
        )
        self.edit_menu.entryconfig(
            1, state="normal" if self.doc.can_redo else "disabled"
        )

    # -- building -----------------------------------------------------------

    def build(self) -> None:
        self._build(output_dir=None, filename_stem=None)

    def build_as(self) -> None:
        if not self._ready_to_build():
            return
        suggested = sanitize_filename(f"{self.doc.meta.class_name}_{self.doc.meta.title}")
        chosen = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=suggested,
            initialdir=str(settings.get_output_dir()),
        )
        if not chosen:
            return
        path = Path(chosen)
        self._build(output_dir=path.parent, filename_stem=path.stem)

    def _ready_to_build(self) -> bool:
        if self.doc.image_path is None:
            messagebox.showerror(
                APP_NAME, "Load a map image before building a quiz.", parent=self.root
            )
            return False
        if not self.doc.markers:
            messagebox.showerror(
                APP_NAME,
                "This quiz has no locations yet. Click the map to add some.",
                parent=self.root,
            )
            return False
        missing = self.doc.markers_missing_answers()
        if missing:
            numbers = ", ".join(str(m.display_number) for m in missing[:10])
            if len(missing) > 10:
                numbers += ", ..."
            return messagebox.askokcancel(
                APP_NAME,
                f"{len(missing)} location(s) have no answer yet: {numbers}.\n\n"
                "They'll print as blank lines in the answer key. Build anyway?",
                parent=self.root,
            )
        return True

    def _build(self, output_dir, filename_stem) -> None:
        if not self._ready_to_build():
            return
        try:
            pdf_paths = build_quiz(
                self.doc, output_dir=output_dir, filename_stem=filename_stem
            )
        except Exception as exc:  # noqa: BLE001 - see below
            # Deliberately broad: a build runs PIL, Typst and the filesystem,
            # and the teacher needs a dialog rather than a traceback in a
            # terminal they cannot see. Narrowing this would let some new
            # failure mode kill the window silently.
            messagebox.showerror(
                APP_NAME, f"This quiz couldn't be built:\n{exc}", parent=self.root
            )
            return

        settings.set_output_dir(pdf_paths[0].parent)
        show_build_result(self.root, pdf_paths)

    # -- help ---------------------------------------------------------------

    def show_help(self) -> None:
        messagebox.showinfo(
            APP_NAME,
            "1. Load a map image.\n"
            "2. Click the map to mark a location, then type its answer.\n"
            "3. Drag a marker to move it. Right-click it, or use the × in the\n"
            "    answer list, to remove it.\n"
            "4. Fill in Class, Title and Instructions.\n"
            "5. Build Quiz PDF makes as many shuffled versions as you ask for.\n\n"
            "Save keeps your work as an .etqw file, which you can reopen here "
            "or import into your test generator.",
            parent=self.root,
        )
