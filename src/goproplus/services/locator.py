"""Resolve GoPro credentials from the environment (extensible later)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Credentials:
    auth_token: str
    user_id: str


class MissingCredentials(RuntimeError):
    pass


def resolve_credentials(settings) -> Credentials:
    token = settings.auth_token
    user_id = settings.user_id
    if not token or not user_id:
        raise MissingCredentials(
            "AUTH_TOKEN and USER_ID must be set (env or .env). "
            "See README 'Environment Variables' for how to obtain them."
        )
    return Credentials(auth_token=token, user_id=user_id)
