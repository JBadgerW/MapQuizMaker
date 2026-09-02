"""The map canvas: the image, the markers drawn on it, and pointer handling.

The panel holds no marker state of its own. `render_markers` reconciles the
canvas against the document's list -- creating, moving, restyling and
deleting individual items -- rather than clearing and redrawing, so a marker
being dragged keeps its identity and the canvas never flickers.

Pointer model:
  click empty space   add a marker there
  click a marker      select it (and begin a drag)
  drag a marker       reposition it; committed on release
  right-click         delete the marker under the pointer
  wheel               scroll; ctrl+wheel zooms, shift+wheel scrolls sideways
"""

import tkinter as tk
from tkinter import filedialog, ttk

import ttkbootstrap as ttkb
from PIL import Image, ImageTk

MIN_ZOOM = 0.05
MAX_ZOOM = 8.0
ZOOM_STEP = 1.25

# Drawn at a fixed pixel size rather than scaled with the image, so a marker
# stays readable and clickable at every zoom level.
MARKER_RADIUS = 11
MARKER_FILL = "#ffffff"
MARKER_EDGE = "#c0392b"
MARKER_EDGE_SELECTED = "#1b6c75"
MARKER_TEXT = "#c0392b"
MARKER_TEXT_SELECTED = "#1b6c75"

# How far the pointer must travel before a click becomes a drag. Without it,
# the hand-tremor of an ordinary click would nudge markers off their feature.
DRAG_THRESHOLD_PX = 3


class ImageCanvasPanel:
    def __init__(self, parent, root, on_add, on_delete, on_move, on_select):
        self.root = root
        self.on_add = on_add
        self.on_delete = on_delete
        self.on_move = on_move
        self.on_select = on_select

        self.img_width = 0
        self.img_height = 0
        self.scale_factor = 1.0

        self._original_image = None
        self._image_canvas_item = None
        self._markers = []
        self._selected_id = None

        # marker id <-> canvas item ids, so a click resolves back to a stable
        # marker id instead of matching on displayed text.
        self._item_to_marker_id: dict[int, int] = {}
        self._marker_items: dict[int, tuple[int, int]] = {}  # id -> (circle, text)

        self._drag_marker_id = None
        self._drag_origin = None
        self._dragging = False
        self._fitted_once = False

        self.frame = ttk.Frame(parent)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        self._build_toolbar()
        self._build_canvas()

        self.status_label = ttk.Label(
            self.frame, text="Load an image to begin", padding=(0, 10)
        )
        self.status_label.grid(row=3, column=0)

    # -- construction -------------------------------------------------------

    def _build_toolbar(self):
        self.toolbar = ttk.Frame(self.frame)
        self.toolbar.grid(row=0, column=0, pady=10)

        self.load_button = ttkb.Button(
            self.toolbar, text="Load Image", command=self.choose_image, bootstyle="primary"
        )
        self.load_button.grid(row=0, column=0, padx=(0, 10))

        ttkb.Button(
            self.toolbar, text="Fit", command=self.fit_to_canvas, bootstyle="secondary"
        ).grid(row=0, column=1, padx=2)

        ttkb.Button(
            self.toolbar, text="-", command=self._zoom_out, bootstyle="secondary", width=3
        ).grid(row=0, column=2, padx=2)

        self.zoom_label = ttk.Label(self.toolbar, text="100%", width=5, anchor="center")
        self.zoom_label.grid(row=0, column=3, padx=2)

        ttkb.Button(
            self.toolbar, text="+", command=self._zoom_in, bootstyle="secondary", width=3
        ).grid(row=0, column=4, padx=2)

    def _build_canvas(self):
        self.canvas_frame = ttk.Frame(self.frame)
        self.canvas_frame.grid(row=1, column=0, sticky="nsew")
        self.canvas_frame.columnconfigure(0, weight=1)
        self.canvas_frame.rowconfigure(0, weight=1)

        # tk.Canvas isn't a themable ttk widget, so its background is set
        # explicitly to match the current ttkbootstrap theme's surface color.
        self.canvas = tk.Canvas(
            self.canvas_frame, background=ttkb.Style().colors.bg, highlightthickness=0
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.v_scrollbar = ttk.Scrollbar(
            self.canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview
        )
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")

        self.h_scrollbar = ttk.Scrollbar(
            self.frame, orient=tk.HORIZONTAL, command=self.canvas.xview
        )
        self.h_scrollbar.grid(row=2, column=0, sticky="ew")

        self.canvas.configure(
            yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set
        )

        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<Button-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Button-3>", self._on_right_click)

        # Wheel bindings differ by platform: X11 delivers buttons 4/5, while
        # Windows and macOS send <MouseWheel> with a delta.
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Button-4>", self._on_wheel)
        self.canvas.bind("<Button-5>", self._on_wheel)

    # -- coordinate conversion ---------------------------------------------

    def _to_fraction(self, canvas_x, canvas_y):
        """Canvas pixels -> (x, y) as fractions of the image, clamped to it."""
        width = self.img_width * self.scale_factor
        height = self.img_height * self.scale_factor
        if width <= 0 or height <= 0:
            return None
        return (
            min(1.0, max(0.0, canvas_x / width)),
            min(1.0, max(0.0, canvas_y / height)),
        )

    def _to_canvas(self, marker):
        return (
            marker.x * self.img_width * self.scale_factor,
            marker.y * self.img_height * self.scale_factor,
        )

    def _marker_at(self, canvas_x, canvas_y):
        """The topmost marker under a point, or None."""
        hits = self.canvas.find_overlapping(
            canvas_x - 2, canvas_y - 2, canvas_x + 2, canvas_y + 2
        )
        for item in reversed(hits):  # topmost first
            marker_id = self._item_to_marker_id.get(item)
            if marker_id is not None:
                return marker_id
        return None

    # -- pointer handling ---------------------------------------------------

    def _event_point(self, event):
        return self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

    def _on_press(self, event):
        if not self._has_image():
            return
        x, y = self._event_point(event)

        marker_id = self._marker_at(x, y)
        if marker_id is not None:
            self._drag_marker_id = marker_id
            self._drag_origin = (x, y)
            self._dragging = False
            self.on_select(marker_id)
            return

        position = self._to_fraction(x, y)
        if position is not None:
            self.on_add(*position)

    def _on_drag(self, event):
        if self._drag_marker_id is None:
            return
        x, y = self._event_point(event)

        if not self._dragging:
            origin_x, origin_y = self._drag_origin
            if max(abs(x - origin_x), abs(y - origin_y)) < DRAG_THRESHOLD_PX:
                return
            self._dragging = True

        position = self._to_fraction(x, y)
        if position is None:
            return
        # Move the item live for feedback; the document is told on release so
        # one drag becomes one undo step rather than dozens.
        items = self._marker_items.get(self._drag_marker_id)
        if items:
            self._place_items(items, *self._fraction_to_canvas(*position))

    def _on_release(self, event):
        if self._drag_marker_id is None:
            return
        marker_id, dragged = self._drag_marker_id, self._dragging
        self._drag_marker_id = None
        self._dragging = False

        if not dragged:
            return
        position = self._to_fraction(*self._event_point(event))
        if position is not None:
            self.on_move(marker_id, *position)

    def _on_right_click(self, event):
        if not self._has_image():
            return
        marker_id = self._marker_at(*self._event_point(event))
        if marker_id is not None:
            self.on_delete(marker_id)

    def _on_wheel(self, event):
        # Normalize: X11 sends Button-4/5, everything else a signed delta.
        if event.num == 4:
            steps = 1
        elif event.num == 5:
            steps = -1
        else:
            steps = 1 if event.delta > 0 else -1

        if event.state & 0x0004:  # ctrl
            self._zoom_about(event, ZOOM_STEP if steps > 0 else 1 / ZOOM_STEP)
        elif event.state & 0x0001:  # shift
            self.canvas.xview_scroll(-steps, "units")
        else:
            self.canvas.yview_scroll(-steps, "units")
        return "break"

    # -- marker rendering ---------------------------------------------------

    def _fraction_to_canvas(self, x, y):
        return x * self.img_width * self.scale_factor, y * self.img_height * self.scale_factor

    def _place_items(self, items, x, y):
        circle, text = items
        self.canvas.coords(
            circle, x - MARKER_RADIUS, y - MARKER_RADIUS, x + MARKER_RADIUS, y + MARKER_RADIUS
        )
        self.canvas.coords(text, x, y)

    def _create_marker_items(self, marker):
        x, y = self._to_canvas(marker)
        circle = self.canvas.create_oval(
            x - MARKER_RADIUS, y - MARKER_RADIUS, x + MARKER_RADIUS, y + MARKER_RADIUS,
            fill=MARKER_FILL, outline=MARKER_EDGE, width=2,
        )
        text = self.canvas.create_text(
            x, y, text=str(marker.display_number), fill=MARKER_TEXT,
            font=("Arial", 10, "bold"),
        )
        for item in (circle, text):
            self._item_to_marker_id[item] = marker.id
        self._marker_items[marker.id] = (circle, text)
        return circle, text

    def render_markers(self, markers, selected_id=None) -> None:
        """Reconciles the canvas against `markers`.

        Only what actually differs is touched, so dragging, typing and
        selection never cause a full redraw.
        """
        self._markers = list(markers)
        self._selected_id = selected_id
        wanted = {m.id for m in self._markers}

        for marker_id in list(self._marker_items):
            if marker_id not in wanted:
                circle, text = self._marker_items.pop(marker_id)
                for item in (circle, text):
                    self.canvas.delete(item)
                    self._item_to_marker_id.pop(item, None)

        for marker in self._markers:
            items = self._marker_items.get(marker.id)
            if items is None:
                items = self._create_marker_items(marker)
            circle, text = items

            self._place_items(items, *self._to_canvas(marker))
            if self.canvas.itemcget(text, "text") != str(marker.display_number):
                self.canvas.itemconfigure(text, text=str(marker.display_number))

            chosen = marker.id == selected_id
            self.canvas.itemconfigure(
                circle,
                outline=MARKER_EDGE_SELECTED if chosen else MARKER_EDGE,
                width=3 if chosen else 2,
            )
            self.canvas.itemconfigure(
                text, fill=MARKER_TEXT_SELECTED if chosen else MARKER_TEXT
            )

        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._update_scrollbar_visibility()

    # -- image and zoom -----------------------------------------------------

    def _has_image(self) -> bool:
        return self.img_width > 0 and self.img_height > 0

    def _on_canvas_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._update_scrollbar_visibility()
        # The first fit has to wait for a real canvas size; before the widget
        # is mapped winfo_width() reports 1, which would clamp to MIN_ZOOM.
        if self._has_image() and not self._fitted_once and event.width > 1:
            self._fitted_once = True
            self.fit_to_canvas()

    def _update_scrollbar_visibility(self):
        bbox = self.canvas.bbox("all")
        if bbox is None:
            self.v_scrollbar.grid_remove()
            self.h_scrollbar.grid_remove()
            return

        if bbox[3] - bbox[1] > self.canvas.winfo_height():
            self.v_scrollbar.grid()
        else:
            self.v_scrollbar.grid_remove()

        if bbox[2] - bbox[0] > self.canvas.winfo_width():
            self.h_scrollbar.grid()
        else:
            self.h_scrollbar.grid_remove()

    def _render_at_current_scale(self) -> None:
        new_width = max(1, round(self.img_width * self.scale_factor))
        new_height = max(1, round(self.img_height * self.scale_factor))
        resized = self._original_image.resize(
            (new_width, new_height), Image.Resampling.LANCZOS
        )
        photo = ImageTk.PhotoImage(resized)

        if self._image_canvas_item is None:
            self._image_canvas_item = self.canvas.create_image(
                0, 0, anchor=tk.NW, image=photo
            )
            self.canvas.tag_lower(self._image_canvas_item)
        else:
            self.canvas.itemconfigure(self._image_canvas_item, image=photo)
        self.canvas.image = photo  # keep a reference

        self.zoom_label.config(text=f"{round(self.scale_factor * 100)}%")
        self.render_markers(self._markers, self._selected_id)

    def _set_zoom(self, new_scale_factor) -> None:
        if not self._has_image():
            return
        self.scale_factor = max(MIN_ZOOM, min(MAX_ZOOM, new_scale_factor))
        self._render_at_current_scale()

    def _zoom_about(self, event, factor) -> None:
        """Zooms while keeping the point under the pointer where it is."""
        if not self._has_image():
            return
        before = self._to_fraction(*self._event_point(event))
        self._set_zoom(self.scale_factor * factor)
        if before is None:
            return
        x, y = self._fraction_to_canvas(*before)
        bbox = self.canvas.bbox("all")
        if not bbox or bbox[2] - bbox[0] <= 0 or bbox[3] - bbox[1] <= 0:
            return
        self.canvas.xview_moveto((x - event.x) / (bbox[2] - bbox[0]))
        self.canvas.yview_moveto((y - event.y) / (bbox[3] - bbox[1]))

    def _zoom_in(self) -> None:
        self._set_zoom(self.scale_factor * ZOOM_STEP)

    def _zoom_out(self) -> None:
        self._set_zoom(self.scale_factor / ZOOM_STEP)

    def fit_to_canvas(self) -> None:
        if not self._has_image():
            return
        self.root.update_idletasks()
        canvas_width = self.canvas.winfo_width() or 1
        canvas_height = self.canvas.winfo_height() or 1
        self._set_zoom(
            min(canvas_width / self.img_width, canvas_height / self.img_height)
        )

    # -- loading ------------------------------------------------------------

    def choose_image(self):
        """Asks for an image file. Returns the chosen path, or None."""
        return filedialog.askopenfilename(
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.gif *.tif *.tiff *.webp"),
                ("All files", "*.*"),
            ]
        ) or None

    def show_image(self, path) -> None:
        """Displays `path`, discarding whatever was drawn before."""
        image = Image.open(path)
        image.load()  # surface a truncated or corrupt file here, not later
        self._original_image = image
        self.img_width, self.img_height = image.size

        self.canvas.delete("all")
        self._item_to_marker_id.clear()
        self._marker_items.clear()
        self._markers = []
        self._image_canvas_item = None
        self._fitted_once = False

        self.fit_to_canvas()
        if self.canvas.winfo_width() > 1:
            self._fitted_once = True

    def clear_image(self) -> None:
        self.canvas.delete("all")
        self._item_to_marker_id.clear()
        self._marker_items.clear()
        self._markers = []
        self._original_image = None
        self._image_canvas_item = None
        self.img_width = self.img_height = 0
        self._fitted_once = False

    def set_status(self, text: str) -> None:
        self.status_label.config(text=text)
