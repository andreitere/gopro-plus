"""Tests for settings/env resolution."""

from pathlib import Path

from goproplus.infra.settings import Settings, parse_date


def test_parse_date_iso():
    assert parse_date("2024-03-01") is not None
    assert parse_date("") is None
    assert parse_date(None) is None


def test_parse_date_aliases():
    from datetime import date, timedelta

    assert parse_date("today") == date.today()
    assert parse_date("yesterday") == date.today() - timedelta(days=1)
    assert parse_date("last-week") == date.today() - timedelta(days=7)


def test_env_file_is_loaded(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("AUTH_TOKEN=from-file\nUSER_ID=file-user\n")

    # use the tmp .env by chdir'ing there
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AUTH_TOKEN", raising=False)
    monkeypatch.delenv("USER_ID", raising=False)

    settings = Settings.from_env(data_dir=tmp_path)
    assert settings.auth_token == "from-file"
    assert settings.user_id == "file-user"


def test_real_env_wins_over_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("AUTH_TOKEN=from-file\nUSER_ID=file-user\n")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AUTH_TOKEN", "from-shell")

    settings = Settings.from_env(data_dir=tmp_path)
    assert settings.auth_token == "from-shell"
    assert settings.user_id == "file-user"
