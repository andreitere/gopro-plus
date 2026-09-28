"""Catalog use-cases: list/count stats purely from the DB. No network."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from goproplus.domain.media import MediaFilter
from goproplus.infra.database.repository import MediaRepository
from goproplus.infra.database.schema import ItemStatus


@dataclass(slots=True)
class CatalogStats:
    total: int
    by_type: dict[str, int]
    by_status: dict[str, int]


def list_items(repository: MediaRepository, media_filter: Optional[MediaFilter], *, limit: int | None = None):
    return repository.find(media_filter, limit=limit)


def stats(repository: MediaRepository, media_filter: MediaFilter | None = None) -> CatalogStats:
    media_filter = media_filter or MediaFilter()
    by_type: dict[str, int] = {}
    for item in repository.find(media_filter):
        by_type[item.media_type.value] = by_type.get(item.media_type.value, 0) + 1
    by_status = {
        ItemStatus.KNOWN.value: repository.count_by_status(media_filter, status=ItemStatus.KNOWN),
        ItemStatus.DOWNLOADED.value: repository.count_by_status(media_filter, status=ItemStatus.DOWNLOADED),
        ItemStatus.FAILED.value: repository.count_by_status(media_filter, status=ItemStatus.FAILED),
    }
    return CatalogStats(total=sum(by_type.values()), by_type=by_type, by_status=by_status)
