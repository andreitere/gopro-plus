"""Settings: env parsing and filesystem paths. Resolved once, passed down."""

from __future__ import annotations

import datetime as dt
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_DATA_DIR = Path("data")

DEFAULT_ENV_FILE = Path(".env")

# Friendly aliases for --since/--until, mapped to "days back from today".
_DATE_ALIASES: dict[str, int] = {
    "today": 0,
    "yesterday": 1,
    "last-week": 7,
    "last-month": 30,
    "last-year": 365,
}

_UTC = dt.timezone.utc


def parse_date(value: str | None) -> date | None:
    """Parse --since/--until values.

    Accepts ISO dates (2024-03-01) and the aliases in _DATE_ALIASES.
    """
    if value is None or value.strip() == "":
        return None
    normalized = value.strip().lower()
    if normalized in _DATE_ALIASES:
        return date.today() - dt.timedelta(days=_DATE_ALIASES[normalized])
    return date.fromisoformat(normalized)


@dataclass(slots=True)
class Settings:
    """Runtime configuration resolved from environment (or .env later)."""

    auth_token: str
    user_id: str
    data_dir: Path

    @property
    def db_path(self) -> Path:
        return self.data_dir / "goproplus.db"

    @property
    def download_dir(self) -> Path:
        return self.data_dir / "downloads"

    @classmethod
    def from_env(cls, *, data_dir: str | os.PathLike | None = None) -> "Settings":
        """Resolve settings from env vars, filling from .env when present.

        Real environment variables always win over .env values.
        """
        load_dotenv(dotenv_path=DEFAULT_ENV_FILE, override=False)
        resolved = Path(data_dir) if data_dir else Path(os.environ.get("GOPROPLUS_DATA_DIR", DEFAULT_DATA_DIR))
        return cls(
            auth_token=os.environ.get("AUTH_TOKEN", ""),
            user_id=os.environ.get("USER_ID", ""),
            data_dir=resolved,
        )
