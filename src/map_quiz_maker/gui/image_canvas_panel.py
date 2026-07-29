import tkinter as tk
from tkinter import filedialog, ttk

import ttkbootstrap as ttkb
from PIL import Image, ImageTk

from map_quiz_maker.config import IMG_WIDTH_CM


class ImageCanvasPanel:
    """Owns the image canvas, scrollbars, and click hit-testing.

    Marker add/delete decisions are delegated to callbacks so this panel
    stays free of quiz-state bookkeeping.
    """

    def __init__(self, parent, root, on_click_add, on_click_delete, on_image_loaded):
        self.root = root
        self.on_click_add = on_click_add
        self.on_click_delete = on_click_delete
        self.on_image_loaded = on_image_loaded

        self.img_width = 0
        self.img_height = 0
        self.img_width_cm = IMG_WIDTH_CM
        self.img_height_cm = 0
        self.scale_factor = 1
        self.image_file_path = None

        # marker id <-> canvas text item id, so a click can be resolved back
        # to a stable marker id instead of matching on displayed text.
        self._item_to_marker_id: dict[int, int] = {}
        self._marker_canvas_items: dict[int, int] = {}

        self.frame = ttk.Frame(parent)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        load_button = ttkb.Button(self.frame, text="Load Image", command=self.load_image, bootstyle="primary")
        load_button.grid(row=0, column=0, pady=10)

        self.canvas_frame = ttk.Frame(self.frame)
        self.canvas_frame.grid(row=1, column=0, sticky='nsew')
        self.canvas_frame.columnconfigure(0, weight=1)
        self.canvas_frame.rowconfigure(0, weight=1)

        # tk.Canvas isn't a themable ttk widget, so its background is set
        # explicitly to match the current ttkbootstrap theme's surface color.
        self.canvas = tk.Canvas(self.canvas_frame, background=ttkb.Style().colors.bg, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky='nsew')

        self.v_scrollbar = ttk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.v_scrollbar.grid(row=0, column=1, sticky='ns')

        self.h_scrollbar = ttk.Scrollbar(self.frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.h_scrollbar.grid(row=2, column=0, sticky='ew')

        self.canvas.configure(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)
        self.canvas.bind('<Configure>', self._on_canvas_configure)

        self.result_label = ttk.Label(self.frame, text="Load an image to begin", padding=(0, 10))
        self.result_label.grid(row=3, column=0)

        self.canvas.bind("<Button-1>", self._on_canvas_click)

    def _on_canvas_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._update_scrollbar_visibility()

    def _update_scrollbar_visibility(self):
        bbox = self.canvas.bbox("all")
        if bbox is None:
            self.v_scrollbar.grid_remove()
            self.h_scrollbar.grid_remove()
            return

        content_width = bbox[2] - bbox[0]
        content_height = bbox[3] - bbox[1]

        if content_height > self.canvas.winfo_height():
            self.v_scrollbar.grid()
        else:
            self.v_scrollbar.grid_remove()

        if content_width > self.canvas.winfo_width():
            self.h_scrollbar.grid()
        else:
            self.h_scrollbar.grid_remove()

    def _on_canvas_click(self, event):
        if self.img_width == 0 or self.img_height == 0:
            return  # No image loaded

        x_scroll = self.canvas.canvasx(event.x)
        y_scroll = self.canvas.canvasy(event.y)

        x_percentage = x_scroll / (self.img_width * self.scale_factor)
        y_percentage = 1 - (y_scroll / (self.img_height * self.scale_factor))  # Invert y-axis

        x_location = round(x_percentage * self.img_width_cm, 1)
        y_location = round(y_percentage * self.img_height_cm, 1)

        self.result_label.config(text=f"Clicked at: ({x_location:.1f} cm, {y_location:.1f} cm)")

        clicked_items = self.canvas.find_overlapping(x_scroll - 5, y_scroll - 5, x_scroll + 5, y_scroll + 5)
        for item in clicked_items:
            marker_id = self._item_to_marker_id.get(item)
            if marker_id is not None:
                displayed_number = self.canvas.itemcget(item, 'text')
                self.canvas.delete(item)
                del self._item_to_marker_id[item]
                del self._marker_canvas_items[marker_id]
                self.on_click_delete(marker_id, displayed_number)
                return

        self._add_marker_at(x_scroll, y_scroll, x_location, y_location)

    def _add_marker_at(self, x_scroll, y_scroll, x_location, y_location):
        marker_id, display_number = self.on_click_add(x_location, y_location)
        item_id = self.canvas.create_text(
            x_scroll, y_scroll,
            text=str(display_number),
            fill="red",
            font=("Arial", 12, "bold"),
        )
        self._item_to_marker_id[item_id] = marker_id
        self._marker_canvas_items[marker_id] = item_id

    def update_marker_numbers(self, markers) -> None:
        """Re-syncs displayed canvas numbers after a renumber (e.g. a delete)."""
        for marker in markers:
            item_id = self._marker_canvas_items.get(marker.id)
            if item_id is not None:
                self.canvas.itemconfigure(item_id, text=str(marker.display_number))

    def load_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.gif")])
        if not file_path:
            return

        image = Image.open(file_path)
        self.img_width, self.img_height = image.size
        self.img_height_cm = self.img_width_cm * self.img_height / self.img_width

        screen_width = self.root.winfo_screenwidth() - 380  # Subtract answer list width
        screen_height = self.root.winfo_screenheight() * 0.8  # Use 80% of screen height

        width_ratio = screen_width / self.img_width
        height_ratio = screen_height / self.img_height
        self.scale_factor = min(width_ratio, height_ratio, 1)  # Don't scale up, only down

        new_width = int(self.img_width * self.scale_factor)
        new_height = int(self.img_height * self.scale_factor)
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        photo = ImageTk.PhotoImage(image)
        self.canvas.delete("all")
        self._item_to_marker_id.clear()
        self._marker_canvas_items.clear()
        self.canvas.create_image(0, 0, anchor=tk.NW, image=photo)
        self.canvas.image = photo  # Keep a reference

        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._update_scrollbar_visibility()

        self.result_label.config(text="Click on the image to add or remove quiz locations")
        self.image_file_path = file_path
        self.on_image_loaded()
