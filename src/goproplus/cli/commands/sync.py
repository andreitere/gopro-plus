"""`gpp sync` — index the cloud library into the local database."""

from __future__ import annotations

import typer

from goproplus.cli.context import AppContext
from goproplus.cli.output import console
from goproplus.services.sync_service import run_sync


def sync(
    per_page: int = typer.Option(30, help="items per index page"),
    data_dir: str | None = typer.Option(None, help="data directory (db + downloads)"),
) -> None:
    """Index your entire GoPro cloud library into the local database."""
    context = AppContext.build(data_dir)
    with console.status("syncing cloud index ..."):
        result = run_sync(context.client, context.repository, per_page=per_page)
    console.print(
        f"[green]sync complete[/green]: {result.indexed} items indexed "
        f"({result.new_items} new) across {result.pages} pages; "
        f"{result.missing} still missing locally."
    )
