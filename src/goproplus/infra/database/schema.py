"""SQLModel tables for the media catalog and sync history."""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ItemStatus(str, enum.Enum):
    KNOWN = "known"              # seen in the cloud index, not downloaded yet
    DOWNLOADED = "downloaded"    # fetched and verified on disk
    FAILED = "failed"            # last attempt failed (retryable)


class MediaRecord(SQLModel, table=True):
    """One row per GoPro cloud asset; the sync key is the GoPro media id."""

    __tablename__ = "media"

    id: str = Field(primary_key=True)
    filename: str = ""
    file_extension: str | None = None
    content_title: str | None = None
    media_type: str = "other"           # MediaType value
    created_at: datetime | None = None  # when the cloud item was created (upload time)
    captured_at: datetime | None = None  # when the media was captured (primary date)
    size_bytes: int | None = None

    # sync bookkeeping
    status: ItemStatus = Field(default=ItemStatus.KNOWN)
    local_path: str | None = None
    downloaded_at: datetime | None = None
    first_seen_at: datetime = Field(default_factory=utcnow)
    last_seen_at: datetime | None = None
    raw_json: str | None = None        # full API payload, for the web app later


class SyncRun(SQLModel, table=True):
    """Audit log of sync runs."""

    __tablename__ = "sync_runs"

    id: int | None = Field(default=None, primary_key=True)
    started_at: datetime = Field(default_factory=utcnow)
    finished_at: datetime | None = None
    indexed: int = 0
    new_items: int = 0
    missing: int = 0
    ok: bool = True
