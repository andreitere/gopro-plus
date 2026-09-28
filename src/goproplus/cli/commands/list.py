"""`gpp list` — show what the local catalog knows about your library."""

from __future__ import annotations

import typer
from rich.table import Table

from goproplus.cli.context import AppContext
from goproplus.cli.output import console
from goproplus.domain.media import MediaFilter, MediaType
from goproplus.infra.settings import parse_date


def _media_type(value: str | None) -> MediaType | None:
    if value is None:
        return None
    try:
        return MediaType(value.lower())
    except ValueError as exc:
        raise typer.BadParameter(f"unknown media type: {value} (use video|photo)") from exc


def list_cmd(
    since: str | None = typer.Option(None, "--since", help="only items on/after this date"),
    until: str | None = typer.Option(None, "--until", help="only items on/before this date"),
    media_type: str | None = typer.Option(None, "--type", help="video|photo"),
    limit: int = typer.Option(50, help="max rows to show"),
    data_dir: str | None = typer.Option(None, help="data directory"),
) -> None:
    """List catalog items (newest first). No network access."""
    media_filter = MediaFilter(since=parse_date(since), until=parse_date(until), media_type=_media_type(media_type))
    context = AppContext.build(data_dir)
    items = context.repository.find(media_filter, limit=limit)
    table = Table(title="catalog items")
    table.add_column("id")
    table.add_column("filename")
    table.add_column("type")
    table.add_column("captured_at")
    for item in items:
        table.add_row(item.id, item.filename, item.media_type.value, str(item.captured_at or "?"))
    console.print(table)
    console.print(f"showing {len(items)} items (limit {limit}).")
