"""`gpp reconcile` — link files already on disk to catalog rows."""

from __future__ import annotations

import typer

from goproplus.cli.context import AppContext
from goproplus.cli.output import console
from goproplus.services.reconcile_service import run_reconcile


def reconcile(
    dry_run: bool = typer.Option(False, "--dry-run", help="only show what would be linked"),
    data_dir: str | None = typer.Option(None, help="data directory"),
) -> None:
    """Match files already in the download tree to catalog items (no re-download)."""
    context = AppContext.build(data_dir)
    if dry_run:
        console.print("[dim]dry run — no files will be moved[/dim]")
        result = run_reconcile(
            context.repository,
            context.settings.download_dir,
            apply=False,
        )
        console.print(
            f"{result.matched} file(s) would be linked and marked downloaded "
            f"({result.moved} would move to their canonical path); "
            f"{len(result.unmatched_files)} file(s) on disk have no catalog match."
        )
        return
    result = run_reconcile(
        context.repository,
        context.settings.download_dir,
        log=lambda message: console.print(message),
    )
    console.print(
        f"[green]reconciled[/green] {result.matched} items with existing files "
        f"({result.moved} re-filed); {len(result.unmatched_files)} file(s) on disk have no catalog match."
    )
