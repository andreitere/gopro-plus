"""`gpp organize` — re-file downloaded items to match the current layout."""

from __future__ import annotations

import typer

from goproplus.cli.context import AppContext
from goproplus.cli.output import console
from goproplus.services.organize_service import run_organize


def organize(
    dry_run: bool = typer.Option(False, "--dry-run", help="only show what would move"),
    data_dir: str | None = typer.Option(None, help="data directory"),
) -> None:
    """Re-organize downloaded files into <YYYY>/<MM>/<DD>/ and fix the catalog."""
    context = AppContext.build(data_dir)
    if dry_run:
        console.print("[dim]dry run — no files will be moved[/dim]")
        result = run_organize(
            context.repository,
            context.settings.download_dir,
            apply=not dry_run,
            log=lambda message: console.print(message),
        )
        for source, target in result.moved[:20]:
            console.print(f"would move: {source} → {target}")
        if len(result.moved) > 20:
            console.print(f"... and {len(result.moved) - 20} more")
        console.print(
            f"{result.checked} downloaded items: {len(result.moved)} would move, "
            f"{result.unchanged} already in place, {result.missing_on_disk} missing on disk, "
            f"{result.collisions} skipped (target exists)."
        )
        return
    run_organize(
        context.repository,
        context.settings.download_dir,
        log=lambda message: console.print(message),
    )
