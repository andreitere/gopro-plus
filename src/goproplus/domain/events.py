"""Domain event types.

Services may emit these so that future layers (web app, uploaders,
notifiers) can subscribe without coupling to the CLI or the GoPro API.
Currently they are plain dataclasses; wiring/dispatch comes later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True, frozen=True, kw_only=True)
class DomainEvent:
    """Base event: timestamp of emission."""

    occurred_at: datetime = field(default_factory=_utcnow)


@dataclass(slots=True, frozen=True, kw_only=True)
class SyncCompleted(DomainEvent):
    indexed: int
    new_items: int
    missing: int


@dataclass(slots=True, frozen=True, kw_only=True)
class ItemDownloaded(DomainEvent):
    media_id: str
    filename: str
    local_path: str


@dataclass(slots=True, frozen=True, kw_only=True)
class ItemFailed(DomainEvent):
    media_id: str
    filename: str
    reason: str
