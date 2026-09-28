"""`gpp download` — fetch missing items matching the filter."""

from __future__ import annotations

import typer

from goproplus.cli.context import AppContext
from goproplus.cli.output import RichDownloadProgress, console
from goproplus.domain.media import MediaFilter, MediaType
from goproplus.infra.settings import parse_date
from goproplus.services.download_service import run_download


def _media_type(value: str | None) -> MediaType | None:
    if value is None:
        return None
    try:
        return MediaType(value.lower())
    except ValueError as exc:
        raise typer.BadParameter(f"unknown media type: {value} (use video|photo)") from exc


def download(
    since: str | None = typer.Option(
        None, "--since", help="only items on/after this date (YYYY-MM-DD, or today/yesterday/last-week/last-month/last-year)"
    ),
    until: str | None = typer.Option(None, "--until", help="only items on/before this date (YYYY-MM-DD)"),
    media_type: str | None = typer.Option(None, "--type", help="filter by content type: video|photo"),
    batch_size: int = typer.Option(100, help="media ids per zip request (API limit is 100)"),
    retry_failed: bool = typer.Option(False, help="reset previously failed items so they are retried"),
    data_dir: str | None = typer.Option(None, help="data directory (db + downloads)"),
) -> None:
    """Download missing items matching the filter. Re-runs skip what's already on disk."""
    media_filter = MediaFilter(
        since=parse_date(since),
        until=parse_date(until),
        media_type=_media_type(media_type),
    )
    context = AppContext.build(data_dir)
    if retry_failed:
        reset_count = context.repository.reset_failed()
        console.print(f"reset {reset_count} failed item(s) for retry.")
    with RichDownloadProgress() as progress:
        result = run_download(
            context.client,
            context.repository,
            media_filter,
            auth_token=context.settings.auth_token,
            dest_dir=context.settings.download_dir,
            batch_size=batch_size,
            log=lambda message: console.print(message),
            progress=progress,
        )
    console.print(
        f"[green]download finished[/green]: {len(result.succeeded)} succeeded, "
        f"{len(result.failed)} failed (of {result.planned} planned)."
    )
