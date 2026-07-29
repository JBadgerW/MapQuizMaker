from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class Marker:
    id: int
    x_cm: float
    y_cm: float
    answer: str = ""
    display_number: int = 0


class QuizState:
    """Marker bookkeeping, decoupled from tkinter.

    Marker ``id`` is stable and never reused, even after deletion.
    ``display_number`` is recomputed after every add/delete so the numbers
    shown to the user stay contiguous (1..N) regardless of deletions.
    """

    def __init__(self):
        self._markers: dict[int, Marker] = {}
        self._next_id = 1
        self._listeners: list[Callable[[], None]] = []

    def add_listener(self, listener: Callable[[], None]) -> None:
        self._listeners.append(listener)

    def add_marker(self, x_cm: float, y_cm: float) -> Marker:
        marker = Marker(id=self._next_id, x_cm=x_cm, y_cm=y_cm)
        self._markers[marker.id] = marker
        self._next_id += 1
        self._renumber()
        self._notify()
        return marker

    def delete_marker(self, marker_id: int) -> None:
        self._markers.pop(marker_id, None)
        self._renumber()
        self._notify()

    def update_answer(self, marker_id: int, answer: str) -> None:
        marker = self._markers.get(marker_id)
        if marker is not None:
            marker.answer = answer

    def get_marker(self, marker_id: int) -> Optional[Marker]:
        return self._markers.get(marker_id)

    def reset(self) -> None:
        self._markers = {}
        self._next_id = 1
        self._notify()

    @property
    def markers(self) -> list[Marker]:
        return sorted(self._markers.values(), key=lambda m: m.id)

    def _renumber(self) -> None:
        for n, marker in enumerate(self.markers, start=1):
            marker.display_number = n

    def _notify(self) -> None:
        for listener in self._listeners:
            listener()
