"""CLI for Exa, Tavily, and grounded Grok search."""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

from searchmin.exa import search_exa
from searchmin.grok import config_from_keys, search_grok
from searchmin.http import HttpResult
from searchmin.keys import get_keys
from searchmin.orchestrate import dedup, execute_search, render_markdown
from searchmin.tavily import search_tavily
from searchmin.urls import normalize_url


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Exa + Tavily + grounded Grok search")
    parser.add_argument("--query", default=None)
    parser.add_argument("--mode", choices=["fast", "deep", "answer"], default="deep")
    parser.add_argument("--num", type=int, default=5)
    parser.add_argument("--freshness", choices=["pd", "pw", "pm", "py"], default=None)
    parser.add_argument("--intent", default=None)
    parser.add_argument("--source", default=None, help="Comma list: exa,tavily,grok")
    parser.add_argument("--out", default=None)
    parser.add_argument("--self-test", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.self_test:
        return run_self_test()
    if not args.query:
        print('{"status":"failed","error":"missing_query"}', file=sys.stderr)
        return 2
    sources = None
    if args.source:
        sources = {item.strip() for item in args.source.split(",") if item.strip()}
    report = execute_search(
        args.query,
        args.mode,
        get_keys(),
        max(1, min(args.num, 10)),
        freshness=args.freshness,
        sources=sources,
        intent=args.intent,
    )
    text = render_markdown(report)
    sys.stdout.write(text)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    return 0 if report["ok"] else 2


def run_self_test() -> int:
    checks: list[str] = []

    def check(ok: bool, name: str) -> None:
        if not ok:
            raise SystemExit(f"searchmin self-test failed: {name}")
        checks.append(name)

    check(normalize_url("https://ex.com/a/?utm_source=x&b=1") == "https://ex.com/a?b=1", "normalize")
    merged = dedup([
        {"url": "https://ex.com/a/", "title": "", "snippet": "", "source": "exa"},
        {"url": "https://ex.com/a", "title": "标题", "snippet": "摘要", "source": "tavily"},
    ])
    check(len(merged) == 1 and merged[0]["source"] == "exa, tavily" and merged[0]["title"] == "标题", "dedup")

    captured: list[dict[str, Any]] = []

    def transport(url: str, headers: dict[str, str], payload: dict[str, Any], timeout: float) -> HttpResult:
        captured.append({"url": url, "headers": dict(headers), "payload": payload, "timeout": timeout})
        if "exa" in url:
            return HttpResult(200, {"content-type": "application/json"}, json.dumps({
                "resolvedSearchType": payload.get("type"),
                "results": [
                    {"url": "https://shared.example/a/", "title": "共有", "highlights": ["高亮甲"]},
                    {"title": "无链接"},
                    {"url": "https://exa.example/only", "title": "仅 Exa", "text": "正文"},
                ],
            }).encode())
        if "tavily" in url:
            return HttpResult(200, {"content-type": "application/json"}, json.dumps({
                "answer": "回答甲" if payload.get("include_answer") else None,
                "results": [
                    {"url": "https://shared.example/a", "title": "共有", "content": "Tavily 摘要"},
                    {"url": "https://tavily.example/only", "title": "仅 Tavily", "content": "内容"},
                ],
            }).encode())
        if url.endswith("/models"):
            return HttpResult(500, {}, b"{}")
        model = payload.get("model")
        if model == "grok-fallback":
            body = _grok_body("https://fallback.example/a", "备用", "see [x](https://evil.example/made-up)")
        elif model == "grok-retry":
            posts = [item for item in captured if item["payload"].get("model") == "grok-retry"]
            if len(posts) == 1:
                return HttpResult(429, {}, b"{}")
            body = _grok_body("https://retry.example/a", "重试", "正文")
        elif model == "grok-sse":
            sse = (
                'data: {"type":"response.completed","response":'
                + json.dumps(_grok_payload("https://sse.example/a", "流式", "see [x](https://evil.example/made-up)"))
                + "}\n\n"
            )
            return HttpResult(200, {"content-type": "text/event-stream"}, sse.encode())
        elif model == "grok-empty":
            body = json.dumps({"output": [{"type": "message", "content": [
                {"type": "output_text", "text": "see [x](https://evil.example/made-up)"}
            ]}]}).encode()
        else:
            body = _grok_body("https://grok.example/a", "Grok", "see [x](https://evil.example/made-up)")
        return HttpResult(200, {"content-type": "application/json"}, body)

    exa = search_exa("题材", "exa-key", 5, exa_type="fast", freshness="pw", transport=transport)
    check(exa["status"] == "ok" and [item["url"] for item in exa["results"]] == [
        "https://shared.example/a/", "https://exa.example/only"
    ], "exa urls")
    check(exa["results"][0]["snippet"] == "高亮甲", "exa highlight")
    check(captured[-1]["payload"]["contents"]["highlights"]["maxCharacters"] == 1200, "exa highlights cap")
    check("startPublishedDate" in captured[-1]["payload"] and captured[-1]["url"].endswith("/search"), "exa freshness")

    tav = search_tavily("题材", "tav-key", 5, include_answer=True, freshness="pw", transport=transport)
    check(tav["status"] == "ok" and tav["answer"] == "回答甲" and tav["results"][0]["source"] == "tavily", "tavily answer")
    check(captured[-1]["payload"]["days"] == 7 and captured[-1]["payload"]["include_answer"] is True, "tavily days")

    keys = {"exa": "exa-key", "tavily": "tav-key", "grok_key": "grok-key", "grok_url": "https://api.x.ai/v1"}
    fast = execute_search("题材", "fast", keys, transport=transport)
    check(fast["ok"] and {item["source"] for item in fast["attempts"]} == {"exa"}, "fast only exa")
    deep = execute_search("题材", "deep", keys, transport=transport)
    urls = {normalize_url(item["url"]) for item in deep["results"]}
    check(deep["ok"] and urls == {
        "https://shared.example/a",
        "https://exa.example/only",
        "https://tavily.example/only",
        "https://grok.example/a",
    }, "deep urls")
    shared = next(item for item in deep["results"] if "shared.example" in item["url"])
    check("exa" in shared["source"] and "tavily" in shared["source"], "deep dedup")
    check(all(not url.endswith("/models") for url in _urls(captured)), "no model discovery")
    grok_call = next(item for item in captured if item["url"].endswith("/responses") and item["payload"]["model"] == "grok-4.5")
    check(grok_call["payload"]["tools"] == [{"type": "web_search"}], "grok web_search")
    check(grok_call["headers"]["Authorization"] == "Bearer grok-key", "grok bearer")
    check("https://evil.example/made-up" not in urls, "drop model-written url")

    partial = execute_search("题材", "deep", {"exa": "exa-key", "grok_key": "grok-key", "grok_url": "https://api.x.ai/v1"}, transport=transport)
    check(partial["ok"] and any(item["source"] == "tavily" and item["status"] == "skipped" for item in partial["attempts"]), "skip missing tavily")

    answer = execute_search("题材", "answer", keys, freshness="pw", transport=transport)
    check(answer["ok"] and answer["answer"] == "回答甲", "answer mode")
    check(all(item["source"] == "tavily" for item in answer["attempts"]), "answer only tavily")

    empty = search_grok("题材", {"grok_key": "grok-key", "grok_url": "https://api.x.ai/v1", "grok_search_model": "grok-empty"}, transport=transport)
    check(empty["status"] == "ok" and empty["results"] == [], "ungrounded markdown url")

    blocked = search_grok("题材", {"grok_key": "grok-key", "grok_url": "https://api.x.ai/v1", "grok_transport": "chat"}, transport=transport)
    chat_calls = [item for item in captured if "chat" in item["url"]]
    check(blocked["status"] == "disabled" and chat_calls == [], "block chat urls")

    before = len(captured)
    retried = search_grok("题材", {"grok_key": "grok-key", "grok_url": "https://api.x.ai/v1", "grok_search_model": "grok-retry"}, transport=transport)
    retry_posts = [item for item in captured[before:] if item["payload"].get("model") == "grok-retry"]
    check(retried["status"] == "ok" and retried["results"][0]["url"] == "https://retry.example/a" and len(retry_posts) == 2, "retry 429")

    fallback = search_grok("题材", {
        "grok_key": "grok-key",
        "grok_url": "https://api.x.ai/v1",
        "grok_search_model": "grok-empty",
        "grok_fallback_search_models": ["grok-fallback"],
    }, transport=transport)
    check(fallback["results"][0]["url"] == "https://fallback.example/a", "fallback model")

    sse = search_grok("题材", {"grok_key": "grok-key", "grok_url": "https://api.x.ai/v1", "grok_search_model": "grok-sse"}, transport=transport)
    check(sse["results"][0]["url"] == "https://sse.example/a" and sse["results"][0]["meta"]["providerGrounded"] is True, "sse citation")

    check(config_from_keys({"grok_key": "grok-key"}).api_url == "https://api.x.ai/v1", "default grok url")

    secret = "unit-test-secret-key"
    stderr = io.StringIO()
    names = [
        "SEARCH_LAYER_CREDENTIALS", "EXA_API_KEY", "EXA_API_URL", "EXA_API_BASE",
        "TAVILY_API_KEY", "TAVILY_API_URL", "TAVILY_API_BASE",
        "GROK_API_KEY", "GROK_API_URL", "GROK_SEARCH_MODEL", "GROK_TRANSPORT",
    ]
    saved = {name: os.environ.get(name) for name in names}
    try:
        for name in names:
            os.environ.pop(name, None)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "search.json"
            path.write_text(json.dumps({
                "exa": {"apiKey": "file-exa"},
                "grok": {"apiKey": secret, "apiUrl": "https://api.x.ai/v1"},
            }), encoding="utf-8")
            os.environ["SEARCH_LAYER_CREDENTIALS"] = str(path)
            os.environ["EXA_API_KEY"] = "env-exa"
            loaded = get_keys()
            check(loaded.get("exa") == "env-exa" and loaded.get("grok_key") == secret, "env overrides file")

            def leaky(url: str, headers: dict[str, str], payload: dict[str, Any], timeout: float) -> HttpResult:
                echoed = headers.get("x-api-key") or payload.get("api_key") or headers.get("Authorization") or ""
                return HttpResult(401, {}, json.dumps({"error": {"message": echoed}}).encode())

            with redirect_stderr(stderr):
                failed = execute_search("题材", "fast", loaded, transport=leaky)
            text = stderr.getvalue()
            check(failed["ok"] is False, "http failure")
            check(secret not in text and "env-exa" not in text and "file-exa" not in text and "Bearer" not in text, "stderr hides keys")
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    none = execute_search("题材", "deep", {}, transport=transport)
    check(none["ok"] is False and {item["status"] for item in none["attempts"]} == {"skipped"}, "no keys")
    rendered = render_markdown(deep)
    check("https://grok.example/a" in rendered and "grok-key" not in rendered, "markdown")

    print(f"searchmin self-test ok ({len(checks)})")
    return 0


def _grok_payload(url: str, title: str, text: str) -> dict[str, Any]:
    return {"output": [{"type": "message", "content": [{
        "type": "output_text",
        "text": text,
        "annotations": [{"type": "url_citation", "url": url, "title": title}],
    }]}]}


def _grok_body(url: str, title: str, text: str) -> bytes:
    return json.dumps(_grok_payload(url, title, text)).encode()


def _urls(captured: list[dict[str, Any]]) -> list[str]:
    return [str(item["url"]) for item in captured]


if __name__ == "__main__":
    raise SystemExit(main())
