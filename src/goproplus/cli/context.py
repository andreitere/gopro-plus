"""Shared CLI wiring: build services wired to real infra. No logic here."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlmodel import Session

from goproplus.infra.database.engine import create_db_engine
from goproplus.infra.database.repository import MediaRepository
from goproplus.infra.gopro.client import GoProClient
from goproplus.infra.settings import Settings
from goproplus.services.locator import resolve_credentials


@dataclass(slots=True)
class AppContext:
    settings: Settings
    client: GoProClient
    repository: MediaRepository
    session: Session

    @classmethod
    def build(cls, data_dir: str | Path | None) -> "AppContext":
        settings = Settings.from_env(data_dir=data_dir)
        credentials = resolve_credentials(settings)
        engine = create_db_engine(settings.db_path)
        session = Session(engine)
        client = GoProClient(credentials.auth_token, credentials.user_id)
        return cls(settings=settings, client=client, repository=MediaRepository(session), session=session)
