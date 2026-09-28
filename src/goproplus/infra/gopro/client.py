"""HTTP client for the GoPro Plus media library API.

All GoPro-specific transport details (auth cookies, headers, endpoints,
pagination shape) live here and nowhere else.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

BASE_HOST = "https://api.gopro.com"

# The GoPro zip endpoint rejects requests with more than 100 media ids (HTTP 422).
MAX_ZIP_BATCH_SIZE = 100

DEFAULT_MEDIA_FIELDS = "id,filename,created_at,captured_at,content_title,file_extension,file_size"
LEGACY_MEDIA_FIELDS = "id,created_at,content_title,filename,file_extension"

DEFAULT_HEADERS = {
    "Accept": "application/vnd.gopro.jk.media+json; version=2.0.0",
    "Accept-Language": "en-US,en;q=0.9",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
}


class GoProApiError(RuntimeError):
    """Raised when the API answers with a non-200 or malformed payload."""


@dataclass(slots=True)
class MediaPage:
    items: list[dict]
    page: int
    total_pages: int


class GoProClient:
    """Thin httpx wrapper. Returns raw payloads; mapping is mappers.py's job."""

    def __init__(
        self,
        auth_token: str,
        user_id: str,
        *,
        base_host: str = BASE_HOST,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._fields = DEFAULT_MEDIA_FIELDS
        self._client = client or httpx.Client(
            base_url=base_host,
            timeout=timeout,
            headers=DEFAULT_HEADERS,
            cookies={"gp_access_token": auth_token, "gp_user_id": user_id},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "GoProClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # -- endpoints ----------------------------------------------------------

    def validate(self) -> bool:
        response = self._client.get("/media/user")
        return response.status_code == 200

    def fetch_media_page(
        self,
        page: int = 1,
        per_page: int = 30,
    ) -> MediaPage:
        params = {"per_page": per_page, "page": page, "fields": self._fields}
        response = self._client.get("/media/search", params=params)
        if response.status_code != 200 and self._fields == DEFAULT_MEDIA_FIELDS:
            # older API builds reject the filesize field: fall back for the
            # rest of this session and retry this page once
            self._fields = LEGACY_MEDIA_FIELDS
            return self.fetch_media_page(page=page, per_page=per_page)
        if response.status_code != 200:
            raise GoProApiError(
                f"failed to fetch media page {page}: status {response.status_code}: "
                f"{_safe_text(response)}"
            )
        content = response.json()
        try:
            items = content["_embedded"]["media"]
            total_pages = int(content["_pages"]["total_pages"])
        except (KeyError, TypeError, ValueError) as exc:
            raise GoProApiError(f"unexpected media search payload: {exc}") from exc
        return MediaPage(items=items, page=page, total_pages=total_pages)

    def iter_media(self, per_page: int = 30, start_page: int = 1):
        """Iterate over all media pages lazily (page payloads, dicts)."""
        page = start_page
        total_pages = None
        while True:
            media_page = self.fetch_media_page(page=page, per_page=per_page)
            if total_pages is None:
                total_pages = media_page.total_pages
            yield media_page
            if page >= total_pages:
                break
            page += 1

    def download_zip_stream(self, ids: list[str], token: str, *, chunk_size: int = 8192):
        """Stream a zip of the given media ids.

        Returns (chunk_iterator, total_size) where total_size comes from
        the Content-Length header when the server provides one, else None.
        """
        response = self._client.get(
            "/media/x/zip/source",
            params={"ids": ",".join(ids), "access_token": token},
        )
        if response.status_code != 200:
            raise GoProApiError(
                f"zip download failed: status {response.status_code}: {_safe_text(response)}"
            )
        content_length = response.headers.get("content-length")
        total_size = int(content_length) if content_length and content_length.isdigit() else None
        return response.iter_bytes(chunk_size), total_size


def _safe_text(response: httpx.Response) -> str:
    try:
        return response.text[:500]
    except Exception:
        return "<unreadable body>"
