"""Domain layer unit tests: pure, fast, no I/O."""

from datetime import date, datetime, timezone

from goproplus.domain.media import MediaFilter, MediaItem, MediaType, media_type_from_filename


def _item(captured: datetime, filename: str = "GX010001.MP4") -> MediaItem:
    return MediaItem(
        id="x",
        filename=filename,
        captured_at=captured,
        media_type=media_type_from_filename(filename),
    )


def test_media_type_from_filename():
    assert media_type_from_filename("GX010042.MP4") is MediaType.VIDEO
    assert media_type_from_filename("GX010042.mov") is MediaType.VIDEO
    assert media_type_from_filename("G0041710.JPG") is MediaType.PHOTO
    assert media_type_from_filename("hero.heic") is MediaType.PHOTO
    assert media_type_from_filename("weird.xyz") is MediaType.OTHER
    assert media_type_from_filename("noext") is MediaType.OTHER


def test_filter_matches_date_range():
    media_filter = MediaFilter(since=date(2024, 1, 1), until=date(2024, 12, 31))
    assert media_filter.matches(_item(datetime(2024, 6, 1, 10, 0, tzinfo=timezone.utc)))
    assert not media_filter.matches(_item(datetime(2023, 6, 1, 10, 0, tzinfo=timezone.utc)))
    assert not media_filter.matches(_item(datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)))


def test_filter_matches_video_only():
    media_filter = MediaFilter(media_type=MediaType.VIDEO)
    assert media_filter.matches(_item(datetime(2024, 6, 1, tzinfo=timezone.utc), "a.MP4"))
    assert not media_filter.matches(_item(datetime(2024, 6, 1, tzinfo=timezone.utc), "b.JPG"))
