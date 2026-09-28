"""Domain value objects and models.

This module is deliberately free of I/O concerns (http, sql, filesystem).
All downstream services work against these types so that a new backend
(GoPro API today, SD-card importer or a NAS crawler tomorrow) can plug
in without touching business logic.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import date, datetime


class MediaType(str, enum.Enum):
    """Kind of content, derived from the file extension."""

    VIDEO = "video"
    PHOTO = "photo"
    OTHER = "other"


VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".hevc", ".webm", ".360", ".gpr"}
PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".tif", ".tiff", ".raw", ".lrg"}


def media_type_from_filename(filename: str) -> MediaType:
    """Infer the media type from a filename's extension."""
    suffix = ""
    if "." in filename:
        suffix = "." + filename.rsplit(".", 1)[1].lower()
    if suffix in VIDEO_EXTENSIONS:
        return MediaType.VIDEO
    if suffix in PHOTO_EXTENSIONS:
        return MediaType.PHOTO
    return MediaType.OTHER


@dataclass(slots=True)
class MediaItem:
    """Universal unit of cloud media. Every backend maps into this object."""

    id: str
    filename: str
    captured_at: datetime | None = None   # when the media was captured (primary date)
    uploaded_at: datetime | None = None   # when the cloud item was created (upload)
    media_type: MediaType = MediaType.OTHER
    file_extension: str | None = None
    content_title: str | None = None
    size_bytes: int | None = None
    raw_json: dict | None = field(default=None, repr=False, compare=False)


@dataclass(slots=True)
class MediaFilter:
    """Shared filter used by sync, download, list and stats.

    Constructed by the CLI, consumed unchanged by services and repositories
    so filter semantics never drift between commands.
    """

    since: date | None = None
    until: date | None = None
    media_type: MediaType | None = None

    def matches(self, item: MediaItem) -> bool:
        """Pure predicate over a MediaItem (in-memory use, e.g. tests)."""
        if self.media_type is not None and item.media_type != self.media_type:
            return False
        if item.captured_at is not None:
            day = item.captured_at.date()
            if self.since is not None and day < self.since:
                return False
            if self.until is not None and day > self.until:
                return False
        return True

    def is_empty(self) -> bool:
        return self.since is None and self.until is None and self.media_type is None
