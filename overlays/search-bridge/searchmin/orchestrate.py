"""Run Exa, Tavily, and grounded Grok, then deduplicate URLs."""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from searchmin.exa import exa_type_for_query, search_exa
from searchmin.grok import search_grok
from searchmin.http import Transport
from searchmin.tavily import search_tavily
from searchmin.urls import normalize_url


def dedup(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    ordered: list[dict[str, Any]] = []
    for item in results:
        key = normalize_url(str(item.get("url") or ""))
        if not key:
            continue
        current = seen.get(key)
        if current is None:
            seen[key] = item
            ordered.append(item)
            continue
        source = str(current.get("source") or "")
        extra = str(item.get("source") or "")
        if extra and extra not in source.split(", "):
            current["source"] = f"{source}, {extra}" if source else extra
        if not current.get("snippet") and item.get("snippet"):
            current["snippet"] = item["snippet"]
        if not current.get("title") and item.get("title"):
            current["title"] = item["title"]
    return ordered


def _want(sources: set[str] | None, name: str) -> bool:
    return sources is None or name in sources


def execute_search(
    query: str,
    mode: str,
    keys: dict[str, Any],
    num: int = 5,
    *,
    freshness: str | None = None,
    sources: set[str] | None = None,
    intent: str | None = None,
    transport: Transport | None = None,
) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    answer = None

    def note(source: str, status: str, count: int = 0) -> None:
        attempts.append({"source": source, "status": status, "count": count})
        if status == "skipped":
            print(
                '{"provider":"%s","status":"skipped","error":"missing_key"}' % source,
                file=sys.stderr,
            )

    jobs: dict[str, Any] = {}
    if mode == "fast":
        if _want(sources, "exa"):
            if keys.get("exa"):
                jobs["exa"] = lambda: search_exa(
                    query,
                    keys["exa"],
                    num,
                    exa_type=exa_type_for_query(mode, intent),
                    freshness=freshness,
                    base_url=keys.get("exa_url"),
                    transport=transport,
                )
            else:
                note("exa", "skipped")
    elif mode == "answer":
        if _want(sources, "tavily"):
            if keys.get("tavily"):
                jobs["tavily"] = lambda: search_tavily(
                    query,
                    keys["tavily"],
                    num,
                    include_answer=True,
                    freshness=freshness,
                    base_url=keys.get("tavily_url"),
                    transport=transport,
                )
            else:
                note("tavily", "skipped")
    else:
        if _want(sources, "exa"):
            if keys.get("exa"):
                jobs["exa"] = lambda: search_exa(
                    query,
                    keys["exa"],
                    num,
                    exa_type=exa_type_for_query(mode, intent),
                    freshness=freshness,
                    base_url=keys.get("exa_url"),
                    transport=transport,
                )
            else:
                note("exa", "skipped")
        if _want(sources, "tavily"):
            if keys.get("tavily"):
                jobs["tavily"] = lambda: search_tavily(
                    query,
                    keys["tavily"],
                    num,
                    include_answer=False,
                    freshness=freshness,
                    base_url=keys.get("tavily_url"),
                    transport=transport,
                )
            else:
                note("tavily", "skipped")
        if _want(sources, "grok"):
            if keys.get("grok_key"):
                jobs["grok"] = lambda: search_grok(query, keys, num, freshness, transport)
            else:
                note("grok", "skipped")

    if len(jobs) == 1:
        name, job = next(iter(jobs.items()))
        _collect(name, job(), results, attempts, answer_box := {})
        answer = answer_box.get("answer")
    elif jobs:
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(job): name for name, job in jobs.items()}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    payload = future.result()
                except Exception as exc:
                    print(
                        '{"provider":"%s","status":"failed","error":"%s"}' % (name, type(exc).__name__),
                        file=sys.stderr,
                    )
                    attempts.append({"source": name, "status": "failed", "count": 0})
                    continue
                box: dict[str, Any] = {}
                _collect(name, payload, results, attempts, box)
                if box.get("answer"):
                    answer = box["answer"]
    ok = any(item["status"] == "ok" for item in attempts)
    return {
        "ok": ok,
        "query": query,
        "mode": mode,
        "results": dedup(results),
        "answer": answer,
        "attempts": attempts,
    }


def _collect(
    name: str,
    payload: dict[str, Any],
    results: list[dict[str, Any]],
    attempts: list[dict[str, Any]],
    answer_box: dict[str, Any],
) -> None:
    rows = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        rows = []
    status = str(payload.get("status") or "failed")
    attempts.append({"source": name, "status": status, "count": len(rows)})
    results.extend(item for item in rows if isinstance(item, dict))
    if payload.get("answer"):
        answer_box["answer"] = payload.get("answer")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# 搜索",
        "",
        f"- 查询：{report.get('query') or ''}",
        f"- 模式：{report.get('mode') or ''}",
    ]
    ran = [item["source"] for item in report.get("attempts") or [] if item["status"] != "skipped"]
    skipped = [item["source"] for item in report.get("attempts") or [] if item["status"] == "skipped"]
    failed = [item["source"] for item in report.get("attempts") or [] if item["status"] == "failed"]
    lines.append(f"- 已查询：{'、'.join(ran) if ran else '无'}")
    lines.append(f"- 跳过：{'、'.join(skipped) if skipped else '无'}")
    lines.append(f"- 失败：{'、'.join(failed) if failed else '无'}")
    answer = report.get("answer")
    if isinstance(answer, str) and answer.strip():
        lines.extend(["", "## 回答", "", answer.strip()])
    lines.extend(["", "## 结果", ""])
    rows = report.get("results") or []
    if not rows:
        lines.append("没有带来源链接的结果。")
    for index, item in enumerate(rows, start=1):
        title = str(item.get("title") or item.get("url") or "未命名")
        snippet = str(item.get("snippet") or "").replace("\n", " ").strip()
        if len(snippet) > 600:
            snippet = snippet[:600] + "…"
        lines.append(f"{index}. **{title}**")
        lines.append(f"   - 来源：{item.get('source') or ''}")
        lines.append(f"   - URL：{item.get('url') or ''}")
        published = item.get("published_date") or ""
        if published:
            lines.append(f"   - 日期：{published}")
        if snippet:
            lines.append(f"   - 摘要：{snippet}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
