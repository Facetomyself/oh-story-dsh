"""JSON POST for the search providers. Tests pass an in-memory transport."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class HttpResult:
    status: int
    headers: dict[str, str]
    body: bytes

    def json(self) -> Any:
        if not self.body:
            return {}
        return json.loads(self.body.decode("utf-8"))

    def header(self, name: str) -> str:
        target = name.lower()
        for key, value in self.headers.items():
            if key.lower() == target:
                return value
        return ""


Transport = Callable[[str, dict[str, str], dict[str, Any], float], HttpResult]


def post_json(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: float,
    transport: Transport | None = None,
) -> HttpResult:
    if transport is not None:
        return transport(url, headers, payload, timeout)
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw_headers = {key: value for key, value in response.headers.items()}
            return HttpResult(int(response.status), raw_headers, response.read())
    except urllib.error.HTTPError as exc:
        raw_headers = {key: value for key, value in exc.headers.items()} if exc.headers else {}
        return HttpResult(int(exc.code), raw_headers, exc.read() or b"")
