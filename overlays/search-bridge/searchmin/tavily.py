"""Tavily search."""

from __future__ import annotations

import sys
from typing import Any

from searchmin.http import Transport, post_json
from searchmin.urls import resolve_search_url


def search_tavily(
    query: str,
    key: str,
    num: int = 5,
    *,
    include_answer: bool = False,
    freshness: str | None = None,
    base_url: str | None = None,
    transport: Transport | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "api_key": key,
        "query": query,
        "max_results": num,
        "include_answer": include_answer,
    }
    days = {"pd": 1, "pw": 7, "pm": 30, "py": 365}.get(freshness or "")
    if days:
        payload["days"] = days
    url = resolve_search_url(base_url, "https://api.tavily.com")
    try:
        response = post_json(
            url,
            {"Content-Type": "application/json"},
            payload,
            20,
            transport,
        )
        if response.status >= 400:
            print(
                '{"provider":"tavily","status":"failed","http_status":%d}' % response.status,
                file=sys.stderr,
            )
            return {"results": [], "answer": None, "status": "failed"}
        data = response.json()
    except Exception as exc:
        print('{"provider":"tavily","status":"failed","error":"%s"}' % type(exc).__name__, file=sys.stderr)
        return {"results": [], "answer": None, "status": "failed"}
    if not isinstance(data, dict):
        return {"results": [], "answer": None, "status": "failed"}
    results = []
    for item in data.get("results") or []:
        if not isinstance(item, dict) or not item.get("url"):
            continue
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url"),
            "snippet": item.get("content", ""),
            "published_date": item.get("published_date", ""),
            "source": "tavily",
        })
    return {"results": results, "answer": data.get("answer"), "status": "ok"}
