"""Mapper tests against realistic GoPro API payload shapes."""

from datetime import datetime, timezone

from goproplus.infra.gopro.mappers import payload_to_media_item, payloads_to_media_items


def test_maps_core_fields():
    payload = {
        "id": "abc123",
        "filename": "GX010042.MP4",
        "captured_at": "2023-02-25T00:25:58Z",
        "created_at": "2023-02-26T08:00:00Z",
        "content_title": "Skiing 2023",
        "file_extension": "MP4",
        "file_size": 123456,
    }
    item = payload_to_media_item(payload)
    assert item.id == "abc123"
    assert item.filename == "GX010042.MP4"
    assert item.captured_at == datetime(2023, 2, 25, 0, 25, 58, tzinfo=timezone.utc)
    assert item.uploaded_at == datetime(2023, 2, 26, 8, 0, 0, tzinfo=timezone.utc)
    assert item.size_bytes == 123456
    assert item.media_type.value == "video"
    assert item.raw_json == payload


def test_falls_back_to_created_at_without_captured_at():
    item = payload_to_media_item({"id": "x", "filename": "G001.JPG", "created_at": "2023-02-25T00:25:58Z"})
    assert item.captured_at == datetime(2023, 2, 25, 0, 25, 58, tzinfo=timezone.utc)


def test_handles_missing_dates():
    item = payload_to_media_item({"id": "x", "filename": "G001.JPG"})
    assert item.captured_at is None
    assert item.uploaded_at is None
    assert item.media_type.value == "photo"


def test_batch_mapping():
    items = payloads_to_media_items([{"id": "1", "filename": "a.MP4"}, {"id": "2", "filename": "b.JPG"}])
    assert [i.media_type.value for i in items] == ["video", "photo"]
