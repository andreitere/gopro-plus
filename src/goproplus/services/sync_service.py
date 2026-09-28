"""Sync use-case: index cloud media into the DB and compute what is missing."""

from __future__ import annotations

from dataclasses import dataclass

from goproplus.infra.database.repository import MediaRepository
from goproplus.infra.gopro.client import GoProClient
from goproplus.infra.gopro.mappers import payloads_to_media_items


@dataclass(slots=True)
class SyncResult:
    indexed: int
    new_items: int
    missing: int
    pages: int


def run_sync(client: GoProClient, repository: MediaRepository, *, per_page: int = 30) -> SyncResult:
    """Fetch every cloud index page, upsert into DB, report the missing set.

    Re-running is cheap and idempotent: only new cloud items change rows.
    """
    run = repository.start_sync_run()
    indexed = 0
    new_items = 0
    pages = 0

    for media_page in client.iter_media(per_page=per_page):
        items = payloads_to_media_items(media_page.items)
        pages += 1
        _, page_new = repository.upsert_media(items)
        indexed += len(items)
        new_items += page_new

    missing = len(repository.missing())
    repository.finish_sync_run(run, indexed=indexed, new_items=new_items, missing=missing, ok=True)
    return SyncResult(indexed=indexed, new_items=new_items, missing=missing, pages=pages)
