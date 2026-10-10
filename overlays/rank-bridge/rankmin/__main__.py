from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from .ciweimao import (
    DEFAULT_CATEGORIES as CIWEIMAO_DEFAULTS,
    normalize_ciweimao,
    parse_ciweimao_rank,
    resolve_ciweimao_category,
)
from .ciweimao import ciweimao_source
from .contracts import RankFetchError
from .fanqie import (
    DEFAULT_CATEGORIES as FANQIE_DEFAULTS,
    fetch_fanqie_rank,
    normalize_fanqie,
    parse_fanqie_initial_state,
    polluted_fields,
    resolve_fanqie_category,
)
from .markdown_out import render_markdown, write_snapshot
from .qidian import (
    DEFAULT_CATEGORIES as QIDIAN_DEFAULTS,
    fetch_qidian_mobile,
    normalize_qidian_mobile,
    parse_qidian_mobile_rank_ssr,
    qidian_source,
    resolve_qidian_category,
)
from .textutil import today_cst

_DAY = re.compile(r"^\d{8}$")
_QIDIAN_FIXTURE = """
<script id="vite-plugin-ssr_pageContext" type="application/json">
{"pageContext":{"pageProps":{"pageData":{"records":[
  {"bid":"1001","bName":"测试书甲","bAuth":"作者甲","desc":"简介甲","cnt":"12万","cat":"玄幻","subCat":"东方玄幻","state":"连载","rankCnt":"100万月票","rankNum":1},
  {"bid":"1002","bName":"测试书乙","bAuth":"作者乙","desc":"简介乙","cnt":"3万","cat":"都市","state":"连载","rankCnt":"","rankNum":2}
]}}}}
</script>
"""
_FANQIE_FIXTURE = """
<script>window.__INITIAL_STATE__={"rank":{"rankTypeText":"阅读榜","book_list":[
  {"bookId":"9001","bookName":"番茄书","author":"作者丙","abstract":"简介丙","read_count":"1.2万","wordNumber":"30万","category":"西方奇幻","creationStatus":"1"}
]}};</script>
"""
_FANQIE_POLLUTED = """
<script>window.__INITIAL_STATE__={"rank":{"book_list":[
  {"bookId":"9002","bookName":"乱码\\ue000书","author":"作者","abstract":"简介"}
]}};</script>
"""


def _split(raw: str, defaults: tuple[str, ...]) -> list[str]:
    if raw.strip() in {"", "default"}:
        return list(defaults)
    return [part.strip() for part in raw.split(",") if part.strip()]


def _run_fetch(out_dir: Path, day: str, qidian: str, fanqie: str, ciweimao: str, limit: int) -> int:
    from .ciweimao import fetch_ciweimao_rank

    wrote: list[Path] = []
    try:
        for category in _split(qidian, ()) if qidian else []:
            snapshot = fetch_qidian_mobile(category, limit)
            wrote.append(write_snapshot(snapshot, out_dir, day))
        for category in _split(fanqie, ()) if fanqie else []:
            snapshot = fetch_fanqie_rank(category, limit)
            wrote.append(write_snapshot(snapshot, out_dir, day))
        for category in _split(ciweimao, ()) if ciweimao else []:
            snapshot = fetch_ciweimao_rank(category, limit)
            wrote.append(write_snapshot(snapshot, out_dir, day))
    except RankFetchError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if not wrote:
        print("name --qidian, --fanqie, or --ciweimao", file=sys.stderr)
        return 2
    for path in wrote:
        print(path)
    return 0


def self_test() -> int:
    checks = 0
    source = qidian_source("yuepiao")
    parsed = parse_qidian_mobile_rank_ssr(_QIDIAN_FIXTURE, category=source.category, limit=20)
    if not parsed.ok or parsed.items[0]["bName"] != "测试书甲":
        print("qidian fixture parse failed", file=sys.stderr)
        return 2
    snapshot = normalize_qidian_mobile(source, parsed)
    text = render_markdown(snapshot)
    if "测试书甲" not in text or "100万月票" not in text or "榜单值：[待补]" not in text:
        print("qidian markdown missing fields", file=sys.stderr)
        return 2
    checks += 1
    if resolve_qidian_category("hotsales") != "mobile-hotsales":
        print("qidian alias failed", file=sys.stderr)
        return 2
    checks += 1
    try:
        resolve_qidian_category("desktop-yuepiao")
    except RankFetchError:
        checks += 1
    else:
        print("desktop qidian was accepted", file=sys.stderr)
        return 2
    fanqie_source_category = resolve_fanqie_category("male-hot-xifangqihuan")
    if fanqie_source_category != "1_2_1141":
        print(f"fanqie alias failed: {fanqie_source_category}", file=sys.stderr)
        return 2
    checks += 1
    from .fanqie import fanqie_source

    fanqie = fanqie_source("1_2_1141")
    fanqie_parsed = parse_fanqie_initial_state(_FANQIE_FIXTURE, limit=10)
    if not fanqie_parsed.ok or fanqie_parsed.items[0]["bookName"] != "番茄书":
        print("fanqie fixture parse failed", file=sys.stderr)
        return 2
    fanqie_snapshot = normalize_fanqie(fanqie, fanqie_parsed)
    if polluted_fields(fanqie_snapshot):
        print("clean fanqie fixture looked polluted", file=sys.stderr)
        return 2
    if "在读：1.2万" not in render_markdown(fanqie_snapshot):
        print("fanqie markdown missing read count", file=sys.stderr)
        return 2
    checks += 1
    polluted = normalize_fanqie(fanqie, parse_fanqie_initial_state(_FANQIE_POLLUTED, limit=5))
    bad = polluted_fields(polluted)
    if not any(part.endswith(":book_name") for part in bad):
        print(f"polluted title was not named: {bad}", file=sys.stderr)
        return 2
    checks += 1
    fanqie_app = Path(__file__).resolve().parents[1] / "fanqie_app"
    if str(fanqie_app) not in sys.path:
        sys.path.insert(0, str(fanqie_app))
    try:
        from fanqie_client import FanqieClient
        from fanqie_pure import sign_headers
    except ModuleNotFoundError as exc:
        print(f"fanqie missing module: {exc.name}", file=sys.stderr)
        return 2
    if not callable(FanqieClient) or not callable(sign_headers):
        print("fanqie client missing", file=sys.stderr)
        return 2
    checks += 1
    try:
        fetch_qidian_mobile("mm", 1)
    except RankFetchError as exc:
        if "unavailable" not in str(exc):
            print(f"qidian female error changed: {exc}", file=sys.stderr)
            return 2
    else:
        print("qidian female rank was fetched", file=sys.stderr)
        return 2
    checks += 1
    empty = parse_qidian_mobile_rank_ssr("<html></html>", category="mobile-yuepiao", limit=5)
    if empty.ok or empty.failure_code != "ssr_marker_missing":
        print("missing qidian marker did not fail", file=sys.stderr)
        return 2
    checks += 1
    bridge = Path(__file__).resolve().parents[1]
    if str(bridge) not in sys.path:
        sys.path.insert(0, str(bridge))
    try:
        from ciweimao_app.api import Session
        from ciweimao_app.protocol import sign_request
    except ModuleNotFoundError as exc:
        print(f"ciweimao missing module: {exc.name}", file=sys.stderr)
        return 2
    signed = sign_request("acct", "2.9.365", "0011223344556677")
    if signed.get("rand_str") != "0011223344556677" or len(signed.get("p") or "") < 40:
        print("ciweimao client sign failed", file=sys.stderr)
        return 2
    if not callable(Session):
        print("ciweimao client session missing", file=sys.stderr)
        return 2
    from .ciweimao_egress import build_proxy_url

    if build_proxy_url("203.0.113.8:8080", "", "") != "http://203.0.113.8:8080":
        print("ciweimao proxy endpoint failed", file=sys.stderr)
        return 2
    if build_proxy_url("203.0.113.8:8080", "user", "pw") != "http://user:pw@203.0.113.8:8080":
        print("ciweimao proxy auth endpoint failed", file=sys.stderr)
        return 2
    checks += 1
    source = ciweimao_source("fans_value:week")
    parsed = parse_ciweimao_rank(
        {
            "code": "100000",
            "data": {
                "book_list": [{
                    "book_id": "1001",
                    "book_name": "猫测书",
                    "author_name": "作者丁",
                    "description": "简介丁",
                    "total_word_count": "20000",
                    "is_paid": "1",
                    "category_name": "轻小说",
                }]
            },
        },
        10,
    )
    if not parsed.ok:
        print("ciweimao fixture parse failed", file=sys.stderr)
        return 2
    ciweimao_text = render_markdown(normalize_ciweimao(source, parsed))
    if "猫测书" not in ciweimao_text or "2.0万" not in ciweimao_text or "付费书" not in ciweimao_text:
        print("ciweimao markdown missing fields", file=sys.stderr)
        return 2
    if "榜单值：[待补]" not in ciweimao_text or "rankmin-app" not in ciweimao_text:
        print("ciweimao markdown labeled the missing score", file=sys.stderr)
        return 2
    from .markdown_out import output_name

    if output_name(normalize_ciweimao(source, parsed), "20261009") != "刺猬猫粉丝值周榜_20261009.md":
        print("ciweimao filename failed", file=sys.stderr)
        return 2
    checks += 1
    try:
        resolve_ciweimao_category("desktop-click")
    except RankFetchError:
        checks += 1
    else:
        print("unknown ciweimao rank was accepted", file=sys.stderr)
        return 2
    blank = parse_ciweimao_rank(
        {"code": "100000", "data": {"book_list": [{"book_id": "1002", "book_name": ""}]}},
        5,
    )
    missing_name = normalize_ciweimao(ciweimao_source("favor"), blank)
    if missing_name.items and missing_name.items[0].book_name:
        print("blank ciweimao title was kept", file=sys.stderr)
        return 2
    checks += 1
    print(f"rankmin self-test ok ({checks})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rankmin")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", default="")
    parser.add_argument("--qidian", default="")
    parser.add_argument("--fanqie", default="")
    parser.add_argument("--ciweimao", default="")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--date", default="")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.limit < 1:
        print("limit must be at least 1", file=sys.stderr)
        return 2
    day = args.date or today_cst()
    if not _DAY.match(day):
        print("date must be YYYYMMDD", file=sys.stderr)
        return 2
    if not args.out:
        print("pass --out", file=sys.stderr)
        return 2
    if not args.qidian and not args.fanqie and not args.ciweimao:
        print("pass --qidian, --fanqie, or --ciweimao", file=sys.stderr)
        return 2
    if args.qidian == "default":
        args.qidian = ",".join(QIDIAN_DEFAULTS)
    if args.fanqie == "default":
        args.fanqie = ",".join(FANQIE_DEFAULTS)
    if args.ciweimao == "default":
        args.ciweimao = ",".join(CIWEIMAO_DEFAULTS)
    return _run_fetch(Path(args.out), day, args.qidian, args.fanqie, args.ciweimao, args.limit)


if __name__ == "__main__":
    raise SystemExit(main())
