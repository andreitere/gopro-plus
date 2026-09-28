"""Typer app entrypoint. Subcommands registered here; no logic in this file."""

from __future__ import annotations

import typer

from goproplus.cli.commands import download, list, stats, sync
from goproplus.cli.commands import organize, reconcile
from goproplus.version import __version__

app = typer.Typer(help="GoPro Plus media library toolkit.", no_args_is_help=True)
app.command()(sync.sync)
app.command()(download.download)
app.command(name="list")(list.list_cmd)
app.command(name="stats")(stats.stats_cmd)
app.command()(organize.organize)
app.command()(reconcile.reconcile)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"gpp {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(None, "--version", "-V", callback=_version_callback, is_eager=True),
) -> None:
    """GoPro Plus media library toolkit."""


def run() -> None:
    app()


if __name__ == "__main__":
    run()
