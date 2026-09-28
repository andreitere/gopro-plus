"""Tests for the filesystem layout and the organize use-case."""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

from goproplus.domain.media import MediaItem, MediaType
from goproplus.infra.database.repository import MediaRepository
from goproplus.infra.storage import destination_path, layout_path
from goproplus.services.organize_service import run_organize


def test_layout_includes_day_and_type():
    created = datetime(2024, 3, 5, 12, 0, tzinfo=timezone.utc)
    path = layout_path(Path("data/downloads"), "GX010042.MP4", created, MediaType.VIDEO)
    assert path == Path("data/downloads/2024/03/05/video/GX010042.MP4")


def test_layout_unknown_date():
    path = layout_path(Path("dest"), "x.MP4", None, MediaType.VIDEO)
    assert path == Path("dest/unknown-date/video/x.MP4")


def test_layout_infers_type_when_missing():
    path = layout_path(Path("dest"), "G001.JPG", None)
    assert path == Path("dest/unknown-date/photo/G001.JPG")


def test_destination_path_delegates():
    item = MediaItem(id="i", filename="a.MP4", captured_at=datetime(2025, 1, 2, tzinfo=timezone.utc), media_type=MediaType.VIDEO)
    assert destination_path(item, Path("d")) == Path("d/2025/01/02/video/a.MP4")


@pytest.fixture()
def repository(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    from goproplus.infra.database import schema  # noqa: F401

    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield MediaRepository(session)


def test_organize_moves_files_and_updates_db(repository, tmp_path):
    dest_dir = tmp_path / "downloads"
    old_path = dest_dir / "2024" / "03" / "GX010042.MP4"
    old_path.parent.mkdir(parents=True)
    old_path.write_bytes(b"data")

    captured = datetime(2024, 3, 5, tzinfo=timezone.utc)
    repository.upsert_media([MediaItem(id="i", filename="GX010042.MP4", captured_at=captured, media_type=MediaType.VIDEO)])
    repository.mark_downloaded("i", str(old_path))

    result = run_organize(repository, dest_dir)
    assert len(result.moved) == 1
    expected = dest_dir / "2024" / "03" / "05" / "video" / "GX010042.MP4"
    assert expected.exists()
    assert not old_path.exists()
    assert repository.find_downloaded()[0].local_path == str(expected)


def test_organize_dry_run_moves_nothing(repository, tmp_path):
    dest_dir = tmp_path / "downloads"
    old_path = dest_dir / "2024" / "03" / "a.MP4"
    old_path.parent.mkdir(parents=True)
    old_path.write_bytes(b"data")

    captured = datetime(2024, 3, 5, tzinfo=timezone.utc)
    repository.upsert_media([MediaItem(id="i", filename="a.MP4", captured_at=captured, media_type=MediaType.VIDEO)])
    repository.mark_downloaded("i", str(old_path))

    result = run_organize(repository, dest_dir, apply=False)
    assert len(result.moved) == 1
    assert old_path.exists()
    assert not (dest_dir / "2024" / "03" / "05" / "video").exists()
