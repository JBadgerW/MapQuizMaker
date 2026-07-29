from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from map_quiz_maker.export.naming import sanitize_filename
from map_quiz_maker.export.typst_build import build_quiz
from map_quiz_maker.gui.answer_list_panel import AnswerListPanel
from map_quiz_maker.gui.build_options_panel import BuildOptionsPanel
from map_quiz_maker.gui.details_form_panel import DetailsFormPanel
from map_quiz_maker.gui.image_canvas_panel import ImageCanvasPanel
from map_quiz_maker.models import QuizState


class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Map Quiz Maker")
        self.quiz_state = QuizState()
        self.quiz_state.add_listener(self._on_quiz_state_changed)

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.main_frame = ttk.Frame(root)
        self.main_frame.grid(row=0, column=0, sticky='nsew')
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=0)
        self.main_frame.rowconfigure(0, weight=1)

        self.image_panel = ImageCanvasPanel(
            self.main_frame,
            root,
            on_click_add=self._on_marker_add,
            on_click_delete=self._on_marker_delete,
            on_image_loaded=self._on_image_loaded,
        )
        self.image_panel.frame.grid(row=0, column=0, sticky='nsew')

        self.right_frame = ttk.Frame(self.main_frame, width=380)
        self.right_frame.grid(row=0, column=1, sticky='ns')
        self.right_frame.grid_propagate(False)
        self.right_frame.columnconfigure(0, weight=1)
        self.right_frame.rowconfigure(2, weight=1)

        self.details_panel = DetailsFormPanel(
            self.right_frame, on_save=self._on_save, on_save_as=self._on_save_as
        )
        self.details_panel.frame.grid(row=0, column=0, sticky='new')

        self.build_options_panel = BuildOptionsPanel(self.right_frame)
        self.build_options_panel.frame.grid(row=1, column=0, sticky='new', pady=(8, 0))

        self.answer_list_panel = AnswerListPanel(self.right_frame, on_answer_changed=self._on_answer_changed)
        self.answer_list_panel.frame.grid(row=2, column=0, sticky='nsew')

    def _on_quiz_state_changed(self) -> None:
        markers = self.quiz_state.markers
        self.answer_list_panel.refresh(markers)
        self.image_panel.update_marker_numbers(markers)

    def _on_marker_add(self, x_cm, y_cm):
        marker = self.quiz_state.add_marker(x_cm, y_cm)
        return marker.id, marker.display_number

    def _on_marker_delete(self, marker_id, displayed_number):
        self.quiz_state.delete_marker(marker_id)

    def _on_answer_changed(self, marker_id, new_answer):
        self.quiz_state.update_answer(marker_id, new_answer)

    def _on_image_loaded(self) -> None:
        self.quiz_state.reset()

    def _on_save(self) -> None:
        self._build(output_dir=None, filename_stem=None)

    def _on_save_as(self) -> None:
        if not self.image_panel.image_file_path:
            messagebox.showerror("Map Quiz Maker", "Load an image before saving a quiz.")
            return

        suggested_name = sanitize_filename(
            f"{self.details_panel.get_class()}_{self.details_panel.get_title()}"
        ).strip("_") or "quiz"

        chosen_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=suggested_name,
        )
        if not chosen_path:
            return

        path = Path(chosen_path)
        self._build(output_dir=path.parent, filename_stem=path.stem)

    def _build(self, output_dir, filename_stem) -> None:
        if not self.image_panel.image_file_path:
            messagebox.showerror("Map Quiz Maker", "Load an image before saving a quiz.")
            return

        try:
            build_quiz(
                quiz_state=self.quiz_state,
                image_file_path=self.image_panel.image_file_path,
                image_width_cm=self.image_panel.img_width_cm,
                image_height_cm=self.image_panel.img_height_cm,
                class_name=self.details_panel.get_class(),
                title=self.details_panel.get_title(),
                instructions=self.details_panel.get_instructions(),
                num_versions=self.build_options_panel.get_num_versions(),
                separate_files=self.build_options_panel.get_separate_files(),
                include_word_bank=self.build_options_panel.get_include_word_bank(),
                output_dir=output_dir,
                filename_stem=filename_stem,
            )
        except Exception as exc:
            messagebox.showerror("Map Quiz Maker", f"Failed to save quiz:\n{exc}")
