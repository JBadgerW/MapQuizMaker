"""The document: the single authoritative state object for one quiz.

Marker positions are stored as fractions of the image (0..1, x left-to-right
and y TOP-DOWN, matching both the canvas and Typst). They used to be stored
in centimetres derived from a fixed print width, with a bottom-left origin
inherited from the old TikZ output that every renderer then had to flip back
-- an inversion that had already caused one bug. Fractions make a saved
document survive a change of print size, and let the same numbers drive the
on-screen canvas, the printed worksheet, and the burnt-in export image.

Views observe this object and reconcile against it; they never hold marker
state of their own.
"""

from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

# How many snapshots back a user can undo. Documents are small (a few dozen
# markers), so whole-state snapshots cost less than a command hierarchy and
# cannot drift out of sync with the state they describe.
UNDO_DEPTH = 100


@dataclass
class Marker:
    """One numbered location on the map.

    `id` is stable and never reused, so a view can key its widgets by it.
    `display_number` is recomputed on every change so the numbers the user
    sees stay contiguous 1..N regardless of deletions.
    """

    id: int
    x: float  # 0..1 across the image, left to right
    y: float  # 0..1 down the image, top to bottom
    answer: str = ""
    display_number: int = 0


@dataclass
class QuizMeta:
    """Everything about the quiz that isn't a marker."""

    class_name: str = ""
    author: str = ""
    title: str = ""
    instructions: str = ""
    num_versions: int = 1
    separate_files: bool = False
    include_word_bank: bool = False


@dataclass
class _Snapshot:
    """An undoable point in the document's history."""

    markers: list[Marker]
    meta: QuizMeta
    image_path: Path | None
    next_id: int


class QuizDocument:
    """One quiz: its image, its markers, its metadata, and its history.

    Mutating methods notify listeners once, after the change is complete, and
    mark the document dirty. Every mutation that a user would think of as one
    action pushes a single undo entry.
    """

    def __init__(self):
        self._markers: dict[int, Marker] = {}
        self._next_id = 1
        self._meta = QuizMeta()
        self._image_path: Path | None = None

        self._listeners: list[Callable[[], None]] = []
        self._undo: list[_Snapshot] = []
        self._redo: list[_Snapshot] = []
        self._dirty = False

        # Identity assigned on first save; see map_quiz_maker.etqw.
        self.etqw_id: str | None = None
        self.etqw_source_id: str | None = None
        self.created_at: str | None = None
        self.file_path: Path | None = None

        # Set by the loader to a TemporaryDirectory holding the map image
        # extracted from a bundle; held so it outlives the load and is
        # cleaned up when the document is dropped.
        self._media_tmp = None

    # -- observation --------------------------------------------------------

    def add_listener(self, listener: Callable[[], None]) -> None:
        self._listeners.append(listener)

    def _notify(self) -> None:
        for listener in self._listeners:
            listener()

    # -- read-only views ----------------------------------------------------

    @property
    def markers(self) -> list[Marker]:
        return sorted(self._markers.values(), key=lambda m: m.id)

    @property
    def meta(self) -> QuizMeta:
        return self._meta

    @property
    def image_path(self) -> Path | None:
        return self._image_path

    @property
    def dirty(self) -> bool:
        return self._dirty

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def get_marker(self, marker_id: int) -> Marker | None:
        return self._markers.get(marker_id)

    def answers(self) -> list[str]:
        """Answers in display order, blanks dropped."""
        return [m.answer.strip() for m in self.markers if m.answer.strip()]

    def markers_missing_answers(self) -> list[Marker]:
        return [m for m in self.markers if not m.answer.strip()]

    # -- history ------------------------------------------------------------

    def _snapshot(self) -> _Snapshot:
        return _Snapshot(
            markers=[replace(m) for m in self.markers],
            meta=replace(self._meta),
            image_path=self._image_path,
            next_id=self._next_id,
        )

    def _restore(self, snapshot: _Snapshot) -> None:
        self._markers = {m.id: replace(m) for m in snapshot.markers}
        self._meta = replace(snapshot.meta)
        self._image_path = snapshot.image_path
        self._next_id = snapshot.next_id
        self._renumber()

    def _checkpoint(self) -> None:
        """Records the current state as an undo point and drops the redo tail.

        Called before a mutation, so undo restores what was there before it.
        """
        self._undo.append(self._snapshot())
        del self._undo[:-UNDO_DEPTH]
        self._redo.clear()

    def undo(self) -> None:
        if not self._undo:
            return
        self._redo.append(self._snapshot())
        self._restore(self._undo.pop())
        self._dirty = True
        self._notify()

    def redo(self) -> None:
        if not self._redo:
            return
        self._undo.append(self._snapshot())
        self._restore(self._redo.pop())
        self._dirty = True
        self._notify()

    # -- mutation -----------------------------------------------------------

    def add_marker(self, x: float, y: float) -> Marker:
        self._checkpoint()
        marker = Marker(id=self._next_id, x=x, y=y)
        self._markers[marker.id] = marker
        self._next_id += 1
        self._changed()
        return marker

    def delete_marker(self, marker_id: int) -> None:
        if marker_id not in self._markers:
            return
        self._checkpoint()
        del self._markers[marker_id]
        self._changed()

    def move_marker(self, marker_id: int, x: float, y: float) -> None:
        """Repositions a marker, keeping its number and answer."""
        marker = self._markers.get(marker_id)
        if marker is None or (marker.x, marker.y) == (x, y):
            return
        self._checkpoint()
        marker.x, marker.y = x, y
        self._changed()

    def update_answer(self, marker_id: int, answer: str) -> None:
        """Sets a marker's answer.

        Deliberately does NOT notify: this is called on every keystroke, and
        a notification would rebuild the very row being typed into. It does
        not checkpoint either -- undoing a quiz one character at a time is
        not what a user means by undo.
        """
        marker = self._markers.get(marker_id)
        if marker is not None and marker.answer != answer:
            marker.answer = answer
            self._dirty = True

    def update_meta(self, **fields) -> None:
        """Replaces named QuizMeta fields. Unknown names raise."""
        updated = replace(self._meta, **fields)
        if updated == self._meta:
            return
        self._meta = updated
        self._dirty = True

    def set_image(self, path, *, keep_markers: bool = False) -> None:
        """Points the document at a map image.

        Replacing the image normally clears the markers, since their
        positions describe the old picture. `keep_markers` is for loading a
        saved document, where the markers belong to the image being set.
        """
        self._checkpoint()
        self._image_path = Path(path) if path is not None else None
        if not keep_markers:
            self._markers.clear()
            self._next_id = 1
        self._changed()

    # -- persistence bookkeeping -------------------------------------------

    def mark_clean(self, file_path=None) -> None:
        """Called after a successful save or load."""
        if file_path is not None:
            self.file_path = Path(file_path)
        self._dirty = False

    def load_markers(self, markers, next_id: int | None = None) -> None:
        """Replaces the marker set wholesale, without an undo checkpoint."""
        self._markers = {m.id: m for m in markers}
        self._next_id = next_id if next_id is not None else self._highest_id() + 1
        self._renumber()

    def _highest_id(self) -> int:
        return max(self._markers, default=0)

    # -- internals ----------------------------------------------------------

    def _changed(self) -> None:
        self._renumber()
        self._dirty = True
        self._notify()

    def _renumber(self) -> None:
        for n, marker in enumerate(self.markers, start=1):
            marker.display_number = n
