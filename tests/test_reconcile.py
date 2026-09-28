"""Tests for the reconcile use-case (linking on-disk files to catalog rows)."""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

from goproplus.domain.media import MediaItem, MediaType
from goproplus.infra.database.repository import MediaRepository
from goproplus.services.reconcile_service import run_reconcile


@pytest.fixture()
def repository(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    from goproplus.infra.database import schema  # noqa: F401

    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield MediaRepository(session)


def test_reconcile_matches_and_refiles(repository, tmp_path):
    dest_dir = tmp_path / "downloads"
    stray = dest_dir / "some-old-layout" / "GX010042.MP4"
    stray.parent.mkdir(parents=True)
    stray.write_bytes(b"data")

    captured = datetime(2024, 3, 5, tzinfo=timezone.utc)
    repository.upsert_media(
        [MediaItem(id="i", filename="GX010042.MP4", captured_at=captured, media_type=MediaType.VIDEO)]
    )

    result = run_reconcile(repository, dest_dir)
    assert result.matched == 1
    canonical = dest_dir / "2024" / "03" / "05" / "video" / "GX010042.MP4"
    assert canonical.exists()
    assert not stray.exists()
    assert repository.find_downloaded()[0].local_path == str(canonical)


def test_reconcile_dry_run_touches_nothing(repository, tmp_path):
    dest_dir = tmp_path / "downloads"
    stray = dest_dir / "GX010042.MP4"
    stray.parent.mkdir(parents=True)
    stray.write_bytes(b"data")

    repository.upsert_media(
        [MediaItem(id="i", filename="GX010042.MP4", captured_at=None, media_type=MediaType.VIDEO)]
    )

    result = run_reconcile(repository, dest_dir, apply=False)
    assert result.matched == 1
    assert stray.exists()
    assert repository.find()[0].filename == "GX010042.MP4"


def test_reconcile_ignores_already_downloaded(repository, tmp_path):
    dest_dir = tmp_path / "downloads"
    stray = dest_dir / "a.MP4"
    stray.parent.mkdir(parents=True)
    stray.write_bytes(b"data")

    repository.upsert_media(
        [MediaItem(id="i", filename="a.MP4", captured_at=None, media_type=MediaType.VIDEO)]
    )
    repository.mark_downloaded("i", "somewhere-else/a.MP4")

    result = run_reconcile(repository, dest_dir)
    assert result.matched == 0
    assert stray.exists()
