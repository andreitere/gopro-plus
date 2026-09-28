"""Download use-case: plan a batch of missing items, fetch, verify, mark."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, Protocol

from goproplus.domain.events import ItemDownloaded, ItemFailed
from goproplus.domain.media import MediaFilter, MediaItem
from goproplus.infra.database.repository import MediaRepository
from goproplus.infra.gopro.client import MAX_ZIP_BATCH_SIZE, GoProClient
from goproplus.infra.storage import extract_archive


class DownloadProgress(Protocol):
    """Interface the service calls into; the CLI provides a rich renderer."""

    def start_batch(self, index: int, total_batches: int, items: int) -> None: ...
    def update(self, done_bytes: int, total_bytes: int | None) -> None: ...
    def finish_batch(self) -> None: ...


class NullDownloadProgress:
    """No-op default: used when no UI is attached."""

    def start_batch(self, index: int, total_batches: int, items: int) -> None:
        pass

    def update(self, done_bytes: int, total_bytes: int | None) -> None:
        pass

    def finish_batch(self) -> None:
        pass


@dataclass(slots=True)
class DownloadResult:
    planned: int = 0
    succeeded: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


def run_download(
    client: GoProClient,
    repository: MediaRepository,
    media_filter: MediaFilter,
    *,
    auth_token: str,
    dest_dir: Path,
    batch_size: int = MAX_ZIP_BATCH_SIZE,
    on_event: Optional[Callable[[object], None]] = None,
    log: Optional[Callable[[str], None]] = None,
    progress: Optional[DownloadProgress] = None,
) -> DownloadResult:
    """Download missing items matching the filter, then organize on disk.

    Only items with status KNOWN (i.e. not already downloaded) are planned,
    so re-running skips everything already present.
    """
    log = log or (lambda message: None)
    on_event = on_event or (lambda event: None)
    progress = progress or NullDownloadProgress()
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    pending = repository.missing(media_filter)
    result = DownloadResult(planned=len(pending))
    if not pending:
        log("nothing to download")
        return result

    effective_batch_size = min(batch_size, MAX_ZIP_BATCH_SIZE)
    batch_count = (len(pending) + effective_batch_size - 1) // effective_batch_size
    for batch_index, batch_start in enumerate(range(0, len(pending), effective_batch_size), start=1):
        batch = pending[batch_start : batch_start + effective_batch_size]
        _download_batch(
            client,
            repository,
            batch,
            auth_token=auth_token,
            dest_dir=dest_dir,
            result=result,
            on_event=on_event,
            log=log,
            progress=progress,
            batch_index=batch_index,
            batch_count=batch_count,
        )
    return result


def _download_batch(
    client: GoProClient,
    repository: MediaRepository,
    batch: list[MediaItem],
    *,
    auth_token: str,
    dest_dir: Path,
    result: DownloadResult,
    on_event: Callable[[object], None],
    log: Callable[[str], None],
    progress: DownloadProgress,
    batch_index: int,
    batch_count: int,
) -> None:
    ids = [item.id for item in batch]
    progress.start_batch(batch_index, batch_count, len(ids))
    log(f"fetching zip for {len(ids)} items ...")

    # The zip endpoint streams without Content-Length; fall back to the
    # summed catalog sizes as an expected total for the progress bar.
    expected_total = sum(item.size_bytes or 0 for item in batch)

    try:
        stream, total_size = client.download_zip_stream(ids, auth_token)
    except Exception as exc:  # noqa: BLE001 - request-level failure: items stay KNOWN for retry
        log(f"zip request failed: {exc}")
        log("batch not attempted; items remain in the queue for the next run.")
        result.failed.extend(item.id for item in batch)
        return

    bar_total = total_size if total_size is not None else (expected_total or None)
    buffer = bytearray()
    for chunk in stream:
        buffer += chunk
        progress.update(len(buffer), bar_total)

    progress.finish_batch()
    extracted = extract_archive(bytes(buffer), batch, dest_dir)
    for item in batch:
        local_path = extracted.get(item.id)
        if local_path is None:
            # archive was fetched fine but this item never showed up: a real per-item failure
            repository.mark_failed(item.id)
            result.failed.append(item.id)
            on_event(
                ItemFailed(
                    media_id=item.id,
                    filename=item.filename,
                    reason=f"missing from archive (expected {item.filename}; archive had {len(extracted)} of {len(batch)} files)",
                )
            )
        else:
            repository.mark_downloaded(item.id, str(local_path))
            result.succeeded.append(item.id)
            on_event(ItemDownloaded(media_id=item.id, filename=item.filename, local_path=str(local_path)))
