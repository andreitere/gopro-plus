"""`gpp stats` — summarize the catalog by type and download status."""

from __future__ import annotations

import typer

from goproplus.cli.context import AppContext
from goproplus.cli.output import console
from goproplus.domain.media import MediaFilter
from goproplus.infra.database.schema import ItemStatus
from goproplus.infra.settings import parse_date
from goproplus.services.catalog_service import stats as compute_stats


def stats_cmd(
    since: str | None = typer.Option(None, "--since", help="only items on/after this date"),
    until: str | None = typer.Option(None, "--until", help="only items on/before this date"),
    data_dir: str | None = typer.Option(None, help="data directory"),
) -> None:
    """Counts by media type and by download status."""
    media_filter = MediaFilter(since=parse_date(since), until=parse_date(until), media_type=None)
    context = AppContext.build(data_dir)
    result = compute_stats(context.repository, media_filter)
    console.print(f"total items: {result.total}")
    console.print(f"by type: {result.by_type}")
    console.print(f"by status: {result.by_status}")
