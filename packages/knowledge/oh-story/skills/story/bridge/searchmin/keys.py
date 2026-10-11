"""Load Exa, Tavily, and Grok settings. Never print the values."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _find_credentials() -> str | None:
    home = Path.home()
    candidates = [
        os.environ.get("SEARCH_LAYER_CREDENTIALS", ""),
        str(home / ".dsh" / "search.json"),
        str(home / ".codex" / "credentials" / "search.json"),
        str(home / ".claude" / "credentials" / "search.json"),
    ]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    return None


def _assign_provider(keys: dict[str, Any], name: str, value: Any) -> None:
    if isinstance(value, dict):
        if token := value.get("apiKey"):
            keys[name] = token
        if url := (value.get("apiUrl") or value.get("baseUrl") or value.get("apiBase")):
            keys[f"{name}_url"] = url
    elif isinstance(value, str) and value:
        keys[name] = value


def get_keys() -> dict[str, Any]:
    keys: dict[str, Any] = {}
    cred_path = _find_credentials()
    if cred_path:
        try:
            with open(cred_path, encoding="utf-8") as handle:
                cred = json.load(handle)
        except (OSError, json.JSONDecodeError):
            cred = None
        if isinstance(cred, dict):
            _assign_provider(keys, "exa", cred.get("exa"))
            _assign_provider(keys, "tavily", cred.get("tavily"))
            if url := (cred.get("exaApiUrl") or cred.get("exaApiBase") or cred.get("exaBaseUrl")):
                keys["exa_url"] = url
            if url := (cred.get("tavilyApiUrl") or cred.get("tavilyApiBase") or cred.get("tavilyBaseUrl")):
                keys["tavily_url"] = url
            grok = cred.get("grok")
            if isinstance(grok, dict):
                keys["grok_url"] = grok.get("apiUrl", "")
                keys["grok_key"] = grok.get("apiKey", "")
                legacy_model = grok.get("model", "grok-4.5")
                keys["grok_model"] = legacy_model
                keys["grok_transport"] = grok.get("transport", "responses")
                keys["grok_search_model"] = grok.get("searchModel", "grok-4.5")
                keys["grok_chat_model"] = grok.get("chatModel", legacy_model)
                keys["grok_fallback_search_models"] = grok.get("fallbackSearchModels", [])
                keys["grok_reasoning_effort"] = grok.get("reasoningEffort", "low")
                keys["grok_reasoning_format"] = grok.get("reasoningFormat", "nested")
                keys["grok_web_search"] = grok.get("webSearch", True)
                keys["grok_x_search"] = grok.get("xSearch", False)
                keys["grok_stream"] = grok.get("stream", False)
                keys["grok_structured_output"] = grok.get("structuredOutput", False)
                keys["grok_timeout_seconds"] = grok.get("timeoutSeconds", 60)
                keys["grok_fallback_policy"] = grok.get("fallbackPolicy", "empty")

    if value := os.environ.get("EXA_API_KEY"):
        keys["exa"] = value
    if value := (os.environ.get("EXA_API_BASE") or os.environ.get("EXA_API_URL")):
        keys["exa_url"] = value
    if value := os.environ.get("TAVILY_API_KEY"):
        keys["tavily"] = value
    if value := (os.environ.get("TAVILY_API_BASE") or os.environ.get("TAVILY_API_URL")):
        keys["tavily_url"] = value
    if value := os.environ.get("GROK_API_KEY"):
        keys["grok_key"] = value
    if value := os.environ.get("GROK_API_URL"):
        keys["grok_url"] = value
    if value := os.environ.get("GROK_MODEL"):
        keys["grok_model"] = value
        keys["grok_chat_model"] = value
    if value := os.environ.get("GROK_TRANSPORT"):
        keys["grok_transport"] = value
    if value := os.environ.get("GROK_SEARCH_MODEL"):
        keys["grok_search_model"] = value
    if value := os.environ.get("GROK_CHAT_MODEL"):
        keys["grok_chat_model"] = value
    if value := os.environ.get("GROK_FALLBACK_SEARCH_MODELS"):
        keys["grok_fallback_search_models"] = value
    if value := os.environ.get("GROK_REASONING_EFFORT"):
        keys["grok_reasoning_effort"] = value
    if value := os.environ.get("GROK_REASONING_FORMAT"):
        keys["grok_reasoning_format"] = value
    if value := os.environ.get("GROK_WEB_SEARCH"):
        keys["grok_web_search"] = value
    if value := os.environ.get("GROK_X_SEARCH"):
        keys["grok_x_search"] = value
    if value := os.environ.get("GROK_STREAM"):
        keys["grok_stream"] = value
    if value := os.environ.get("GROK_STRUCTURED_OUTPUT"):
        keys["grok_structured_output"] = value
    if value := os.environ.get("GROK_TIMEOUT_SECONDS"):
        keys["grok_timeout_seconds"] = value
    if value := os.environ.get("GROK_FALLBACK_POLICY"):
        keys["grok_fallback_policy"] = value
    return keys
