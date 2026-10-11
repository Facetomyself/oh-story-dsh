"""Shared URL helpers."""

from __future__ import annotations

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def normalize_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        query = {
            key: value
            for key, value in parse_qs(parsed.query).items()
            if not key.lower().startswith("utm_")
        }
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path.rstrip("/"),
            parsed.params,
            urlencode(query, doseq=True) if query else "",
            "",
        ))
    except Exception:
        return url.rstrip("/")


def resolve_search_url(base_url: str | None, default: str) -> str:
    parsed = urlparse((base_url or default).rstrip("/"))
    path = parsed.path.rstrip("/")
    if not path.endswith("/search"):
        path = f"{path}/search" if path else "/search"
    return urlunparse(parsed._replace(path=path))
