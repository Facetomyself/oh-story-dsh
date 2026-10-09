from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

from .contracts import ParseResult, RankFetchError, RankItem, RankSnapshot, SourceSpec
from .http_client import fetch_text
from .textutil import extract_json_object_after_marker, has_private_use_chars, now_cst_iso

PARSER_VERSION = "fanqie_initial_state_v2"
STATE_MARKER = "window.__INITIAL_STATE__"
BASE_URL = "https://fanqienovel.com/rank"
BASE_PAGE = "https://fanqienovel.com/"
REFERER = "https://fanqienovel.com/rank/"
_CATEGORY_PATTERN = re.compile(r"^[01]_[12]_\d+$")
CHECKED_FIELDS = ("book_name", "author_name", "description")


@dataclass(frozen=True, slots=True)
class FanqieGenre:
    slug: str
    name: str
    category_id: str
    gender: str


MALE_GENRES: tuple[FanqieGenre, ...] = (
    FanqieGenre("xifangqihuan", "西方奇幻", "1141", "male"),
    FanqieGenre("dongfangxianxia", "东方仙侠", "1140", "male"),
    FanqieGenre("kehuanmoshi", "科幻末世", "8", "male"),
    FanqieGenre("dushirichang", "都市日常", "261", "male"),
    FanqieGenre("dushixiuzhen", "都市修真", "124", "male"),
    FanqieGenre("dushigaowu", "都市高武", "1014", "male"),
    FanqieGenre("lishigudai", "历史古代", "273", "male"),
    FanqieGenre("zhanshenzhuixu", "战神赘婿", "27", "male"),
    FanqieGenre("dushizhongtian", "都市种田", "263", "male"),
    FanqieGenre("chuantongxuanhuan", "传统玄幻", "258", "male"),
    FanqieGenre("lishinaodong", "历史脑洞", "272", "male"),
    FanqieGenre("xuanyinaodong", "悬疑脑洞", "539", "male"),
    FanqieGenre("dushinaodong", "都市脑洞", "262", "male"),
    FanqieGenre("xuanhuanaodong", "玄幻脑洞", "257", "male"),
    FanqieGenre("xuanyilingyi", "悬疑灵异", "751", "male"),
    FanqieGenre("kangzhandiezhan", "抗战谍战", "504", "male"),
    FanqieGenre("youxitiyu", "游戏体育", "746", "male"),
    FanqieGenre("dongmanyansheng", "动漫衍生", "718", "male"),
    FanqieGenre("nanpinyansheng", "男频衍生", "1016", "male"),
)

FEMALE_GENRES: tuple[FanqieGenre, ...] = (
    FanqieGenre("gufengshiqing", "古风世情", "1139", "female"),
    FanqieGenre("kehuanmoshi", "科幻末世", "8", "female"),
    FanqieGenre("youxitiyu", "游戏体育", "746", "female"),
    FanqieGenre("nvpinyansheng", "女频衍生", "1015", "female"),
    FanqieGenre("xuanhuanyanqing", "玄幻言情", "248", "female"),
    FanqieGenre("zhongtian", "种田", "23", "female"),
    FanqieGenre("niandai", "年代", "79", "female"),
    FanqieGenre("xianyannaodong", "现言脑洞", "267", "female"),
    FanqieGenre("gongdouzhairdou", "宫斗宅斗", "246", "female"),
    FanqieGenre("xuanyinaodong", "悬疑脑洞", "539", "female"),
    FanqieGenre("guyannaodong", "古言脑洞", "253", "female"),
    FanqieGenre("kuaichuan", "快穿", "24", "female"),
    FanqieGenre("qingchuntianchong", "青春甜宠", "749", "female"),
    FanqieGenre("xingguangcuican", "星光璀璨", "745", "female"),
    FanqieGenre("nvpianxuanyi", "女频悬疑", "747", "female"),
    FanqieGenre("zhichanghunlian", "职场婚恋", "750", "female"),
    FanqieGenre("haomenzongcai", "豪门总裁", "748", "female"),
    FanqieGenre("minguoyanqing", "民国言情", "1017", "female"),
)

RANK_TYPES = {
    "hot": {"code": "2", "name": "阅读榜"},
    "read": {"code": "2", "name": "阅读榜"},
    "reading": {"code": "2", "name": "阅读榜"},
    "new": {"code": "1", "name": "新书榜"},
    "newbook": {"code": "1", "name": "新书榜"},
}
GENDERS = {"male": "1", "m": "1", "nan": "1", "female": "0", "f": "0", "nv": "0"}
GENDER_NAMES = {"1": "男频", "0": "女频"}
GENRES_BY_GENDER = {"1": MALE_GENRES, "0": FEMALE_GENRES}
DEFAULT_CATEGORIES = (
    "male-hot-xifangqihuan",
    "male-newbook-xifangqihuan",
    "female-hot-gufengshiqing",
    "female-newbook-gufengshiqing",
)


def _norm(value: str) -> str:
    return value.strip().lower().replace("_", "-")


def resolve_fanqie_category(value: str) -> str:
    token_value = (value or "").strip()
    if not token_value:
        raise RankFetchError("fanqie category missing")
    if _CATEGORY_PATTERN.match(token_value):
        return token_value
    parts = [part for part in _norm(token_value).split("-") if part]
    gender_code = "1"
    rank_key = "hot"
    genre_slug = ""
    for part in parts:
        if part in GENDERS:
            gender_code = GENDERS[part]
        elif part in RANK_TYPES:
            rank_key = "newbook" if part in {"new", "newbook"} else "hot"
        else:
            genre_slug = part
    if not genre_slug:
        raise RankFetchError(f"fanqie category unsupported: {value}")
    for genre in GENRES_BY_GENDER[gender_code]:
        if genre.slug == genre_slug or genre.category_id == genre_slug or _norm(genre.name) == genre_slug:
            return f"{gender_code}_{RANK_TYPES[rank_key]['code']}_{genre.category_id}"
    raise RankFetchError(f"fanqie category unsupported: {value}")


def fanqie_source(category: str) -> SourceSpec:
    resolved = resolve_fanqie_category(category)
    gender_code, rank_code, genre_id = resolved.split("_", 2)
    rank_key = "newbook" if rank_code == "1" else "hot"
    genre = next((item for item in GENRES_BY_GENDER.get(gender_code, ()) if item.category_id == genre_id), None)
    rank = RANK_TYPES[rank_key]
    genre_name = genre.name if genre else genre_id
    return SourceSpec(
        site_id="fanqie",
        site_name="番茄小说",
        source_id=f"fanqie_{resolved}",
        semantic_key=f"{'male' if gender_code == '1' else 'female'}-{rank_key}",
        category=resolved,
        category_name=f"{GENDER_NAMES[gender_code]}{rank['name']} / {genre_name}",
        url=f"{BASE_URL}/{resolved}",
        required_adapters=["fanqie_initial_state_parser"],
        known_risks=["private-use titles fail closed; this provider does not open book pages"],
    )


def _is_identifier_char(ch: str) -> bool:
    return ch == "_" or ch.isalnum()


def _replace_js_undefined(text: str) -> tuple[str, int]:
    out: list[str] = []
    in_string = False
    escape = False
    replacements = 0
    index = 0
    while index < len(text):
        ch = text[index]
        if in_string:
            out.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            index += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            index += 1
            continue
        if text.startswith("undefined", index):
            before = text[index - 1] if index else ""
            after_index = index + len("undefined")
            after = text[after_index] if after_index < len(text) else ""
            if not _is_identifier_char(before) and not _is_identifier_char(after):
                out.append("null")
                replacements += 1
                index = after_index
                continue
        out.append(ch)
        index += 1
    return "".join(out), replacements


def parse_fanqie_initial_state(html: str, limit: int = 20) -> ParseResult:
    if STATE_MARKER not in html:
        return ParseResult(
            ok=False,
            failure_code="state_marker_missing",
            failure_detail="window.__INITIAL_STATE__ not found",
            parser_version=PARSER_VERSION,
        )
    try:
        state_json = extract_json_object_after_marker(html, STATE_MARKER)
    except ValueError as exc:
        return ParseResult(
            ok=False,
            failure_code=str(exc),
            failure_detail="failed to extract state JSON object",
            parser_version=PARSER_VERSION,
        )
    state_json, undefined_replacements = _replace_js_undefined(state_json)
    notes = [f"fanqie_js_undefined_to_null:{undefined_replacements}"] if undefined_replacements else []
    try:
        state = json.loads(state_json)
    except json.JSONDecodeError as exc:
        return ParseResult(
            ok=False,
            failure_code="state_json_decode_failed",
            failure_detail=str(exc),
            parser_version=PARSER_VERSION,
            source_notes=notes,
        )
    rank_node = state.get("rank")
    if not isinstance(rank_node, dict):
        return ParseResult(ok=False, failure_code="rank_node_missing", failure_detail="state.rank missing", parser_version=PARSER_VERSION)
    book_list = rank_node.get("book_list")
    if not isinstance(book_list, list) or not book_list:
        code = "book_list_empty" if isinstance(book_list, list) else "book_list_missing"
        return ParseResult(ok=False, failure_code=code, failure_detail="rank.book_list unusable", parser_version=PARSER_VERSION)
    items: list[dict[str, Any]] = []
    for index, raw_item in enumerate(book_list[:limit], start=1):
        if not isinstance(raw_item, dict):
            continue
        item = dict(raw_item)
        item["_rank_position"] = index
        items.append(item)
    if not items:
        return ParseResult(ok=False, failure_code="item_parse_failed", failure_detail="no dict item", parser_version=PARSER_VERSION)
    return ParseResult(
        ok=True,
        items=items,
        category_name=str(rank_node.get("rankTypeText") or "").strip(),
        parser_version=PARSER_VERSION,
        source_notes=notes,
    )


def _creation_status(value: object) -> str:
    if value in ("0", 0):
        return "已完结"
    if value in ("1", 1):
        return "连载中"
    return str(value) if value is not None else ""


def _timestamp(value: object) -> str:
    if not value:
        return ""
    try:
        return datetime.fromtimestamp(int(value)).strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError, OSError):
        return str(value)


def normalize_fanqie(source: SourceSpec, parse_result: ParseResult) -> RankSnapshot:
    items: list[RankItem] = []
    for index, raw in enumerate(parse_result.items, start=1):
        rank_position = int(raw.get("_rank_position") or raw.get("currentPos") or index)
        book_id = str(raw.get("bookId") or f"fanqie-{rank_position}")
        book_name = str(raw.get("bookName") or "").strip()
        author_name = str(raw.get("author") or "").strip()
        description = str(raw.get("abstract") or "").strip()
        category = str(raw.get("category") or "").strip()
        category_v2 = str(raw.get("categoryV2") or "").strip()
        read_count = str(raw.get("read_count") or raw.get("readCount") or "").strip()
        word_number = str(raw.get("wordNumber") or "").strip()
        items.append(RankItem(
            rank_position=rank_position,
            book_id=book_id,
            book_name=book_name,
            author_name=author_name,
            book_url=urljoin(BASE_PAGE, f"page/{book_id}"),
            cover_url=str(raw.get("thumbUri") or ""),
            description=description,
            category_text=" / ".join(part for part in (category, category_v2) if part),
            score_text=f"在读：{read_count}" if read_count else "",
            word_count_text=word_number,
            status=_creation_status(raw.get("creationStatus")),
            tags=[part for part in (category, category_v2) if part],
            latest_chapter=str(raw.get("lastChapterTitle") or "").strip(),
            latest_update_time=_timestamp(raw.get("lastChapterUpdateTime")),
            extra={"read_count": read_count},
            field_confidence={
                "book_name": "polluted" if has_private_use_chars(book_name) else ("verified" if book_name else "missing"),
                "author_name": "polluted" if has_private_use_chars(author_name) else ("verified" if author_name else "missing"),
                "description": "polluted" if has_private_use_chars(description) else ("verified" if description else "missing"),
            },
        ))
    return RankSnapshot(
        site=source.site_id,
        site_name=source.site_name,
        category=source.category,
        category_name=parse_result.category_name or source.category_name,
        semantic_key=source.semantic_key,
        source_url=source.url,
        snapshot_at=now_cst_iso(),
        items=items,
        raw_ref="",
        parse_status="ok" if parse_result.ok else parse_result.failure_code,
        source_notes=list(parse_result.source_notes),
        parser_version=parse_result.parser_version,
    )


def polluted_fields(snapshot: RankSnapshot) -> list[str]:
    found: list[str] = []
    for item in snapshot.items:
        for field_name in CHECKED_FIELDS:
            value = getattr(item, field_name)
            if value and has_private_use_chars(value):
                found.append(f"{item.book_id}:{field_name}")
            elif field_name == "book_name" and not value:
                found.append(f"{item.book_id}:book_name")
    return found


def fetch_fanqie_rank(category: str, limit: int = 20) -> RankSnapshot:
    if limit < 1:
        raise RankFetchError("fanqie limit must be at least 1")
    source = fanqie_source(category)
    response = fetch_text(source.url, headers={"Referer": REFERER, "Accept-Encoding": "gzip"})
    if response.error or response.status != 200 or not response.text:
        raise RankFetchError(
            f"fanqie request failed: category={source.category} status={response.status} error={response.error or 'empty'}"
        )
    parsed = parse_fanqie_initial_state(response.text, limit=limit)
    if not parsed.ok:
        raise RankFetchError(
            f"fanqie parse failed: category={source.category} code={parsed.failure_code} detail={parsed.failure_detail}"
        )
    snapshot = normalize_fanqie(source, parsed)
    bad = polluted_fields(snapshot)
    if bad:
        raise RankFetchError("fanqie missing or private-use field: " + ",".join(bad))
    return snapshot
