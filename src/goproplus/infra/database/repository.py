"""All persistence logic lives here. Services never write SQL directly."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import Iterable

from sqlmodel import Session, func, select

from goproplus.domain.media import MediaFilter, MediaItem, MediaType
from goproplus.infra.database.schema import ItemStatus, MediaRecord, SyncRun, utcnow

UTC = timezone.utc


def _exclusive_upper(day: date) -> datetime:
    """`until` is inclusive; convert the day into an exclusive upper bound."""
    return datetime.combine(day, datetime.min.time(), tzinfo=UTC) + timedelta(days=1)


def _dumps(raw: dict | None) -> str | None:
    if raw is None:
        return None
    return json.dumps(raw, default=str)


def _record_to_item(record: MediaRecord) -> MediaItem:
    return MediaItem(
        id=record.id,
        filename=record.filename,
        captured_at=record.captured_at,
        uploaded_at=record.created_at,
        media_type=MediaType(record.media_type),
        file_extension=record.file_extension,
        content_title=record.content_title,
        size_bytes=record.size_bytes,
        raw_json=None,
    )


class MediaRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # -- upserting ----------------------------------------------------------

    def upsert_media(self, items: Iterable[MediaItem]) -> tuple[int, int]:
        """Upsert a batch of items.

        Returns (total_seen, new_items) where new_items counts rows that
        were not present before this call.
        """
        total = 0
        new = 0
        now = utcnow()
        for item in items:
            total += 1
            record = self._session.get(MediaRecord, item.id)
            if record is None:
                new += 1
                record = MediaRecord(
                    id=item.id,
                    filename=item.filename,
                    file_extension=item.file_extension,
                    content_title=item.content_title,
                    media_type=item.media_type.value,
                    created_at=item.uploaded_at,
                    captured_at=item.captured_at,
                    size_bytes=item.size_bytes,
                    first_seen_at=now,
                    last_seen_at=now,
                    raw_json=_dumps(item.raw_json),
                )
                self._session.add(record)
            else:
                record.filename = item.filename or record.filename
                record.file_extension = item.file_extension or record.file_extension
                record.content_title = item.content_title or record.content_title
                record.media_type = item.media_type.value
                record.created_at = item.uploaded_at or record.created_at
                record.captured_at = item.captured_at or record.captured_at
                record.size_bytes = item.size_bytes or record.size_bytes
                record.last_seen_at = now
                record.raw_json = _dumps(item.raw_json) or record.raw_json
        self._session.commit()
        return total, new

    # -- querying -----------------------------------------------------------

    @staticmethod
    def _apply_filter(statement, media_filter: MediaFilter | None):
        if media_filter is None:
            return statement
        if media_filter.media_type is not None:
            statement = statement.where(MediaRecord.media_type == media_filter.media_type.value)
        if media_filter.since is not None:
            statement = statement.where(
                MediaRecord.captured_at >= datetime.combine(media_filter.since, datetime.min.time(), tzinfo=UTC)
            )
        if media_filter.until is not None:
            statement = statement.where(
                MediaRecord.captured_at < _exclusive_upper(media_filter.until)
            )
        return statement

    def find(
        self,
        media_filter: MediaFilter | None = None,
        *,
        status: ItemStatus | None = None,
        limit: int | None = None,
    ) -> list[MediaItem]:
        statement = select(MediaRecord)
        statement = self._apply_filter(statement, media_filter)
        if status is not None:
            statement = statement.where(MediaRecord.status == status)
        statement = statement.order_by(MediaRecord.captured_at.desc().nulls_last())
        if limit is not None:
            statement = statement.limit(limit)
        rows = self._session.exec(statement).all()
        return [_record_to_item(r) for r in rows]

    def missing(self, media_filter: MediaFilter | None = None) -> list[MediaItem]:
        """Items that are known but not yet downloaded (i.e. need fetching)."""
        return self.find(media_filter, status=ItemStatus.KNOWN)

    def count(self, media_filter: MediaFilter | None = None) -> int:
        statement = select(func.count()).select_from(MediaRecord)
        statement = self._apply_filter(statement, media_filter)
        return int(self._session.exec(statement).one())

    def count_by_status(self, media_filter: MediaFilter | None = None, *, status: ItemStatus) -> int:
        statement = select(func.count()).select_from(MediaRecord)
        statement = self._apply_filter(statement, media_filter)
        statement = statement.where(MediaRecord.status == status)
        return int(self._session.exec(statement).one())

    def find_downloaded(self, media_filter: MediaFilter | None = None) -> list[MediaRecord]:
        """Full records (including local_path) of downloaded items."""
        statement = select(MediaRecord).where(MediaRecord.status == ItemStatus.DOWNLOADED)
        statement = self._apply_filter(statement, media_filter)
        statement = statement.order_by(MediaRecord.captured_at.desc().nulls_last())
        return list(self._session.exec(statement).all())

    def update_local_path(self, media_id: str, local_path: str) -> None:
        record = self._session.get(MediaRecord, media_id)
        if record is None:
            return
        record.local_path = local_path
        self._session.commit()

    # -- state transitions --------------------------------------------------

    def mark_downloaded(self, media_id: str, local_path: str) -> None:
        record = self._session.get(MediaRecord, media_id)
        if record is None:
            return
        record.status = ItemStatus.DOWNLOADED
        record.local_path = local_path
        record.downloaded_at = utcnow()
        self._session.commit()

    def mark_failed(self, media_id: str) -> None:
        record = self._session.get(MediaRecord, media_id)
        if record is None:
            return
        record.status = ItemStatus.FAILED
        self._session.commit()

    def reset_failed(self) -> int:
        """Back to KNOWN so a following download retries them."""
        statement = select(MediaRecord).where(MediaRecord.status == ItemStatus.FAILED)
        rows = self._session.exec(statement).all()
        for r in rows:
            r.status = ItemStatus.KNOWN
        self._session.commit()
        return len(rows)

    # -- sync runs ----------------------------------------------------------

    def start_sync_run(self) -> SyncRun:
        run = SyncRun()
        self._session.add(run)
        self._session.commit()
        return run

    def finish_sync_run(self, run: SyncRun, *, indexed: int, new_items: int, missing: int, ok: bool = True) -> None:
        run.indexed = indexed
        run.new_items = new_items
        run.missing = missing
        run.ok = ok
        run.finished_at = utcnow()
        self._session.add(run)
        self._session.commit()
