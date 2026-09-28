"""Rich-based output helpers (progress bars, tables). No business logic."""

from __future__ import annotations

import time

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    ProgressColumn,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.text import Text

console = Console()


def log(message: str) -> None:
    console.print(message)


class AverageSpeedColumn(ProgressColumn):
    """Speed measured as total bytes / time since the first byte arrived.

    Rich's TransferSpeedColumn shows the last refresh's instantaneous rate,
    which is misleading when a server generates the archive slowly and then
    flushes it in a fast burst.
    """

    def render(self, task: "Progress") -> Text:  # noqa: ARG002 - signature fixed by rich
        speed = task.fields.get("avg_speed")
        if not speed:
            return Text("—", style="progress.speed")
        return Text(f"{speed / (1024 * 1024):.1f} MB/s", style="progress.speed")


PROGRESS_COLUMNS = [
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    TextColumn("[progress.description]{task.fields[done_bytes]}"),
    AverageSpeedColumn(),
    TimeElapsedColumn(),
]


class RichDownloadProgress:
    """Rich rendering of the DownloadProgress protocol (one bar per batch)."""

    def __init__(self) -> None:
        self._progress = Progress(*PROGRESS_COLUMNS, console=console)
        self._task_id: int | None = None
        self._description = ""
        self._first_byte_at: float | None = None
        self._done_bytes = 0

    def __enter__(self) -> "RichDownloadProgress":
        self._progress.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._progress.stop()

    def start_batch(self, index: int, total_batches: int, items: int) -> None:
        self._description = f"batch {index}/{total_batches} ({items} items)"
        self._first_byte_at = None
        self._task_id = self._progress.add_task(
            f"{self._description} — waiting for server", total=None, done_bytes=""
        )

    def update(self, done_bytes: int, total_bytes: int | None) -> None:
        if self._task_id is None:
            return
        self._done_bytes = done_bytes
        fields: dict = {"done_bytes": f"{done_bytes / (1024 * 1024):.1f} MB"}
        if self._first_byte_at is None and done_bytes > 0:
            self._first_byte_at = time.monotonic()
            self._progress.update(self._task_id, description=f"{self._description} — downloading")
        if self._first_byte_at is not None:
            elapsed = time.monotonic() - self._first_byte_at
            if elapsed > 0:
                fields["avg_speed"] = done_bytes / elapsed
        self._progress.update(self._task_id, completed=done_bytes, total=total_bytes, **fields)

    def finish_batch(self) -> None:
        if self._task_id is None:
            return
        self._progress.update(
            self._task_id,
            description=f"{self._description} — done ({self._done_bytes / (1024 * 1024):.1f} MB)",
            refresh=True,
        )
        self._task_id = None
