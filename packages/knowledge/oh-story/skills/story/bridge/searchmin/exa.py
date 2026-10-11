"""Exa search."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from searchmin.http import Transport, post_json
from searchmin.urls import resolve_search_url


def exa_type_for_query(mode: str, intent: str | None) -> str:
    if intent == "resource":
        return "instant"
    if intent in {"status", "news"}:
        return "fast"
    if intent == "exploratory":
        return "deep" if mode == "deep" else "auto"
    return "auto"


def exa_start_published_date(freshness: str | None) -> str | None:
    if not freshness:
        return None
    days = {"pd": 1, "pw": 7, "pm": 30, "py": 365}.get(freshness)
    if not days:
        return None
    moment = datetime.now(timezone.utc) - timedelta(days=days)
    return moment.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _coerce_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                parts.append(item.strip())
            elif isinstance(item, dict):
                text = str(item.get("text", "")).strip()
                if text:
                    parts.append(text)
        return " … ".join(parts)
    if isinstance(value, dict):
        return str(value.get("text", "")).strip()
    return ""


def extract_exa_snippet(result: dict[str, Any]) -> str:
    for key in ("highlights", "text", "summary", "snippet"):
        text = _coerce_text(result.get(key))
        if text:
            return text
    return ""


def search_exa(
    query: str,
    key: str,
    num: int = 5,
    *,
    exa_type: str = "auto",
    freshness: str | None = None,
    base_url: str | None = None,
    transport: Transport | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "query": query,
        "numResults": num,
        "type": exa_type,
        "contents": {"highlights": {"maxCharacters": 1200}},
    }
    start = exa_start_published_date(freshness)
    if start:
        payload["startPublishedDate"] = start
    url = resolve_search_url(base_url, "https://api.exa.ai")
    try:
        response = post_json(
            url,
            {"x-api-key": key, "Content-Type": "application/json"},
            payload,
            20,
            transport,
        )
        if response.status >= 400:
            print(
                '{"provider":"exa","status":"failed","http_status":%d}' % response.status,
                file=sys.stderr,
            )
            return {"results": [], "status": "failed"}
        data = response.json()
    except Exception as exc:
        print('{"provider":"exa","status":"failed","error":"%s"}' % type(exc).__name__, file=sys.stderr)
        return {"results": [], "status": "failed"}
    if not isinstance(data, dict):
        return {"results": [], "status": "failed"}
    resolved = data.get("resolvedSearchType", exa_type)
    results = []
    for item in data.get("results") or []:
        if not isinstance(item, dict):
            continue
        item_url = item.get("url")
        if not item_url:
            continue
        results.append({
            "title": item.get("title", ""),
            "url": item_url,
            "snippet": extract_exa_snippet(item),
            "published_date": item.get("publishedDate", ""),
            "source": "exa",
            "meta": {"exaType": resolved},
        })
    return {"results": results, "status": "ok"}
