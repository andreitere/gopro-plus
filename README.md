# gopro-plus

A GoPro Plus media library toolkit: **sync** your cloud library into a local
catalog, **download** only what you don't already have, filtered by **date
range** and **content type** (video/photo), and inspect the catalog from the
command line.

> Inspired by the original [gopro-plus](https://github.com/itsankoff/gopro-plus)
> by [Ivaylo Tsankov](https://github.com/itsankoff) — this is a modernized
> rewrite (uv, typed modules, database-backed sync). Full credit to the
> original project for the GoPro API reverse engineering.

## How it works

```text
gpp sync        → fetches your entire cloud library index (paginated)
                  and upserts it into data/goproplus.db
gpp download    → downloads only items with status "known" (not yet on disk),
                  unpacks into data/downloads/<YYYY>/<MM>/ and marks them
gpp list/stats  → query the local catalog, no network involved
```

Every downloaded item's state lives in the database, so re-runs are
incremental and idempotent — nothing is downloaded twice.

## Requirements

* Python 3.12+
* [uv](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
* A GoPro Plus account

## Installation

```bash
git clone <your-fork-url> && cd gopro-plus
uv sync
```

## Authentication

`AUTH_TOKEN` and `USER_ID` come from the cookies of the
[GoPro media library](https://plus.gopro.com/media-library/) web app:

1. Sign in to the media library and open DevTools → Network tab
2. Filter requests by `user` and open any request's **Cookies** section
3. Copy `gp_access_token` → `AUTH_TOKEN`, `gp_user_id` → `USER_ID`

Then either export them in your shell or put them in `.envrc`/`.env`.

## Commands

### `gpp sync`

Indexes your entire cloud library into the local database. Run this first,
and re-run it to pick up new cloud items.

| Option | Default | Description |
|---|---|---|
| `--per-page` | `30` | items per index page |
| `--data-dir` | `./data` | where the database and downloads live |

### `gpp download`

Downloads missing items matching the filter. Safe to re-run anytime.

| Option | Default | Description |
|---|---|---|
| `--since` | – | only items on/after this date: `YYYY-MM-DD`, or `today`, `yesterday`, `last-week`, `last-month`, `last-year` |
| `--until` | – | only items on/before this date (`YYYY-MM-DD`, inclusive) |
| `--type` | – | filter by content type: `video` or `photo` |
| `--batch-size` | `100` | media ids per zip request (API limit is 100) |
| `--retry-failed` | off | reset previously failed items so they are retried |
| `--data-dir` | `./data` | data directory |

Date and type filters combine freely:

```bash
gpp download                                # everything not yet on disk
gpp download --type video                   # all videos
gpp download --since last-month             # last 30 days
gpp download --since 2024-01-01 --until 2024-12-31 --type photo
```

Files land in `data/downloads/<year>/<month>/<day>/<video|photo>/<filename>`,
keeping the original GoPro filenames. If the layout ever changes, `gpp
organize` re-files your existing downloads (dry-run available).

### `gpp list`

Browse the local catalog (newest first). Never touches the network.

| Option | Default | Description |
|---|---|---|
| `--since` / `--until` | – | same date filters as `download` |
| `--type` | – | `video` or `photo` |
| `--limit` | `50` | max rows to show |
| `--data-dir` | `./data` | data directory |

### `gpp organize`

| Option | Default | Description |
|---|---|---|
| `--dry-run` | off | only show what would move |
| `--data-dir` | `./data` | data directory |

### `gpp reconcile`

Re-links files already in the download tree to catalog rows (by filename),
re-files them into the canonical layout, and marks them downloaded — for
recovering after a database reset without re-downloading.

| Option | Default | Description |
|---|---|---|
| `--dry-run` | off | only show what would be linked |
| `--data-dir` | `./data` | data directory |

### `gpp stats`

Counts by media type and by download status (`known` / `downloaded` /
`failed`), optionally filtered by date. Useful to answer "what's still
missing?" before a download run.

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `AUTH_TOKEN` | yes | GoPro `gp_access_token` cookie |
| `USER_ID` | yes | GoPro `gp_user_id` cookie |
| `GOPROPLUS_DATA_DIR` | no | overrides the data directory (default `./data`) |

Or put them in a `.env` file in the project root (real environment
variables always win over `.env` values):

```dotenv
AUTH_TOKEN=eyJhbGciOi...
USER_ID=12345
```

## Docker

```bash
docker build -t goproplus .
docker run --rm \
  -e AUTH_TOKEN='<token>' -e USER_ID='<id>' \
  -v /path/to/data:/data \
  goproplus sync            # or: download, list, stats
```

## Development

```bash
uv sync          # set up the venv
uv run pytest    # run tests
```

The codebase is layered so it stays easy to extend — the CLI is a thin shell
over services, which orchestrate a pure domain layer and I/O adapters:

```text
src/goproplus/
├── domain/      pure models: MediaItem, MediaFilter, events
├── infra/       adapters: gopro/ (API client+mappers), database/ (sqlite), storage, settings
├── services/    use-cases: sync, download, catalog — shared by CLI and future web UI
└── cli/         typer commands over the services
```

Planned next: a small web UI (`goproplus.web`) served over the same catalog —
the database schema and download layout already anticipate it.

## License

MIT — see [LICENSE](LICENSE).
