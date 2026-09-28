"""Filesystem adapter: destination layout and archive extraction."""

from __future__ import annotations

import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path

from goproplus.domain.media import MediaItem, media_type_from_filename


def layout_path(dest_dir: Path, filename: str, captured_at: "datetime | None", media_type: "MediaType | None" = None) -> Path:
    """Canonical destination: <dest_dir>/<YYYY>/<MM>/<DD>/<type>/<filename>.

    The content type is derived from the filename when not provided; items
    without a capture date land under "unknown-date".
    """
    if captured_at is not None:
        folder = f"{captured_at.year:04d}/{captured_at.month:02d}/{captured_at.day:02d}"
    else:
        folder = "unknown-date"
    if media_type is None:
        media_type = media_type_from_filename(filename)
    return dest_dir / folder / media_type.value / filename


def destination_path(item: MediaItem, dest_dir: Path) -> Path:
    """Per-item destination derived from the capture date and content type."""
    return layout_path(dest_dir, item.filename, item.captured_at, item.media_type)


def extract_archive(
    archive_bytes: bytes, items: list[MediaItem], dest_dir: Path
) -> dict[str, Path]:
    """Extract archive members that match the expected items.

    Returns a map of media id -> extracted path. Members whose name does not
    match a requested item are ignored.
    """
    by_filename = {item.filename: item for item in items if item.filename}
    extracted: dict[str, Path] = {}
    with zipfile.ZipFile(BytesIO(archive_bytes)) as archive:
        for info in archive.infolist():
            member_name = Path(info.filename).name  # discard zip folder structure
            item = by_filename.get(member_name)
            if item is None:
                continue
            target = destination_path(item, dest_dir)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(info))
            extracted[item.id] = target
    return extracted
