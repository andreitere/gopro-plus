"""Repository tests using an in-memory sqlite database."""

from datetime import date, datetime, timezone

import pytest
from sqlmodel import Session, SQLModel, create_engine

from goproplus.domain.media import MediaFilter, MediaItem, MediaType
from goproplus.infra.database.repository import MediaRepository


@pytest.fixture()
def repository():
    engine = create_engine("sqlite://")
    from goproplus.infra.database import schema  # noqa: F401

    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield MediaRepository(session)


def _item(i: str, captured: datetime | None, media_type: MediaType = MediaType.VIDEO) -> MediaItem:
    return MediaItem(id=i, filename=f"{i}.MP4", captured_at=captured, media_type=media_type)


def test_upsert_counts_new_once(repository):
    items = [_item("a", datetime(2024, 5, 1, tzinfo=timezone.utc)), _item("b", None)]
    total, new = repository.upsert_media(items)
    assert (total, new) == (2, 2)
    total, new = repository.upsert_media(items)
    assert (total, new) == (2, 0)
    assert repository.count() == 2


def test_upsert_updates_captured_at(repository):
    repository.upsert_media([_item("a", None)])
    assert repository.find()[0].captured_at is None
    repository.upsert_media([_item("a", datetime(2024, 5, 1, tzinfo=timezone.utc))])
    assert repository.find()[0].captured_at == datetime(2024, 5, 1, tzinfo=timezone.utc)


def test_missing_and_mark_downloaded(repository):
    repository.upsert_media([_item("a", datetime(2024, 5, 1, tzinfo=timezone.utc))])
    assert len(repository.missing()) == 1
    repository.mark_downloaded("a", "data/downloads/2024/05/a.MP4")
    assert repository.missing() == []
    assert repository.count_by_status(status=_status_downloaded()) == 1


def test_filtering_by_type_and_date(repository):
    repository.upsert_media(
        [
            _item("v", datetime(2024, 5, 1, tzinfo=timezone.utc), MediaType.VIDEO),
            _item("p", datetime(2024, 6, 1, tzinfo=timezone.utc), MediaType.PHOTO),
            _item("old", datetime(2020, 1, 1, tzinfo=timezone.utc), MediaType.VIDEO),
        ]
    )
    f = MediaFilter(since=date(2024, 1, 1), until=date(2024, 12, 31), media_type=MediaType.VIDEO)
    ids = [i.id for i in repository.find(f)]
    assert ids == ["v"]


def _status_downloaded():
    from goproplus.infra.database.schema import ItemStatus

    return ItemStatus.DOWNLOADED
