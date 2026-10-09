from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

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


def _run_fetch(out_dir: Path, day: str, qidian: str, fanqie: str, limit: int) -> int:
    wrote: list[Path] = []
    try:
        for category in _split(qidian, ()) if qidian else []:
            snapshot = fetch_qidian_mobile(category, limit)
            wrote.append(write_snapshot(snapshot, out_dir, day))
        for category in _split(fanqie, ()) if fanqie else []:
            snapshot = fetch_fanqie_rank(category, limit)
            wrote.append(write_snapshot(snapshot, out_dir, day))
    except RankFetchError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if not wrote:
        print("name --qidian or --fanqie", file=sys.stderr)
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
    empty = parse_qidian_mobile_rank_ssr("<html></html>", category="mobile-yuepiao", limit=5)
    if empty.ok or empty.failure_code != "ssr_marker_missing":
        print("missing qidian marker did not fail", file=sys.stderr)
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
    if not args.qidian and not args.fanqie:
        print("pass --qidian or --fanqie", file=sys.stderr)
        return 2
    if args.qidian == "default":
        args.qidian = ",".join(QIDIAN_DEFAULTS)
    if args.fanqie == "default":
        args.fanqie = ",".join(FANQIE_DEFAULTS)
    return _run_fetch(Path(args.out), day, args.qidian, args.fanqie, args.limit)


if __name__ == "__main__":
    raise SystemExit(main())
