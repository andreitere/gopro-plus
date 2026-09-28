"""Engine creation helpers and session factory."""

from __future__ import annotations

from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from goproplus.infra.database import schema  # noqa: F401  (registers table models)


def create_db_engine(db_path: Path, *, echo: bool = False):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}", echo=echo)
    SQLModel.metadata.create_all(engine)
    _migrate(engine)
    return engine


def _migrate(engine) -> None:
    """Lightweight in-code migrations (alpha phase; alembic if this grows)."""
    with engine.connect() as connection:
        columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(media)")}
        if "captured_at" not in columns:
            connection.exec_driver_sql("ALTER TABLE media ADD COLUMN captured_at DATETIME")
            # interim backfill: until the next sync brings real capture dates,
            # keep items where they are by treating upload date as capture date
            connection.exec_driver_sql("UPDATE media SET captured_at = created_at WHERE captured_at IS NULL")
            connection.commit()


def open_session(engine) -> Session:
    return Session(engine)
