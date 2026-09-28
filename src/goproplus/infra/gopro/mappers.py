"""Map GoPro API JSON payloads into domain MediaItems."""

from __future__ import annotations

from datetime import datetime, timezone

from goproplus.domain.media import MediaItem, media_type_from_filename


def parse_created_at(value: object) -> datetime | None:
    """Parse GoPro's created_at strings like '2023-02-25T00:25:58Z'."""
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def payload_to_media_item(payload: dict) -> MediaItem:
    filename = payload.get("filename") or ""
    return MediaItem(
        id=str(payload.get("id", "")),
        filename=filename,
        captured_at=parse_created_at(payload.get("captured_at"))
        or parse_created_at(payload.get("created_at")),
        uploaded_at=parse_created_at(payload.get("created_at")),
        media_type=media_type_from_filename(filename),
        file_extension=payload.get("file_extension"),
        content_title=payload.get("content_title"),
        size_bytes=payload.get("file_size") or payload.get("filesize"),
        raw_json=payload,
    )


def payloads_to_media_items(payloads: list[dict]) -> list[MediaItem]:
    return [payload_to_media_item(p) for p in payloads]
