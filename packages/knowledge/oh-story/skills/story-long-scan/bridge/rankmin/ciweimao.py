"""Ciweimao app rank list only.

Reads /bookcity/get_rank_book_list. Session values come from the environment.
This module does not register a guest, solve a captcha, or download chapters.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from typing import Any, Mapping
from urllib.parse import quote

from .contracts import ParseResult, RankFetchError, RankItem, RankSnapshot, SourceSpec
from .http_client import post_form
from .textutil import now_cst_iso

PARSER_VERSION = "ciweimao_app_rank_v1"
APP_VERSION = "2.9.365"
BASE_URL = "https://app1.happybooker.cn"
RANK_PATH = "/bookcity/get_rank_book_list"
USER_AGENT = f"Android com.kuangxiangciweimao.novel {APP_VERSION}"
# App 2.9.328+ request signature and 2.9.352+ response key. Not a user credential.
_SIGN_KEY = "a90f3731745f1c30ee77cb13fc00005a"
_SIGN_SUFFIX = "CkMxWNB666"
_RESPONSE_KEY = "sD6doAOcW7hm7iaeK6UlcdtAIWlZGlBr"
_ENV_ACCOUNT = "CIWEIMAO_ACCOUNT"
_ENV_LOGIN = "CIWEIMAO_LOGIN_TOKEN"
_ENV_DEVICE = "CIWEIMAO_DEVICE_TOKEN"
_TIMES = ("week", "month", "total")
_ORDERS = (
    "fans_value",
    "no_vip_click",
    "yp",
    "word_count",
    "track_read",
    "complet",
    "blade",
    "yp_new",
    "recommend",
    "tsukkomi",
    "favor",
)
_DEFAULT_TIME = {
    "fans_value": "week",
    "no_vip_click": "week",
    "yp": "month",
    "word_count": "week",
    "track_read": "week",
    "complet": "month",
    "blade": "month",
    "yp_new": "month",
    "recommend": "total",
    "tsukkomi": "week",
    "favor": "week",
}
_LABELS = {
    "fans_value:week": "粉丝值周榜",
    "fans_value:month": "粉丝值月榜",
    "fans_value:total": "粉丝值总榜",
    "no_vip_click:week": "非VIP点击周榜",
    "yp:month": "月票月榜",
    "word_count:week": "字数周榜",
    "track_read:week": "追读周榜",
    "complet:month": "完结月榜",
    "blade:month": "刀片月榜",
    "yp_new:month": "新书月票月榜",
    "recommend:total": "推荐总榜",
    "tsukkomi:week": "吐槽周榜",
    "favor:week": "收藏周榜",
}
DEFAULT_CATEGORIES = (
    "fans_value:week",
    "favor:week",
    "tsukkomi:week",
    "yp_new:month",
)
_SCORE_KEYS = (
    "fans_value",
    "total_click",
    "click_total",
    "total_favor",
    "favor",
    "recommend_num",
    "month_ticket",
    "yp",
    "score",
    "rank_value",
    "hot_value",
)


def _gf_mul(left: int, right: int) -> int:
    product = 0
    for _ in range(8):
        if right & 1:
            product ^= left
        left <<= 1
        if left & 0x100:
            left ^= 0x11B
        right >>= 1
    return product & 0xFF


def _rotl8(value: int, shift: int) -> int:
    return ((value << shift) | (value >> (8 - shift))) & 0xFF


def _sbox_table() -> tuple[bytes, bytes]:
    forward = [0] * 256
    for value in range(256):
        inverse = 0
        if value:
            for candidate in range(1, 256):
                if _gf_mul(value, candidate) == 1:
                    inverse = candidate
                    break
        substituted = inverse
        substituted ^= _rotl8(inverse, 1) ^ _rotl8(inverse, 2)
        substituted ^= _rotl8(inverse, 3) ^ _rotl8(inverse, 4) ^ 0x63
        forward[value] = substituted & 0xFF
    inverse_box = [0] * 256
    for index, substituted in enumerate(forward):
        inverse_box[substituted] = index
    return bytes(forward), bytes(inverse_box)


_SBOX, _INV_SBOX = _sbox_table()
_RCON = (0x00, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36)


def _xor_words(left: bytes, right: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(left, right))


def _sub_word(word: bytes, box: bytes) -> bytes:
    return bytes(box[part] for part in word)


def _expand_key(key: bytes) -> list[bytes]:
    if len(key) != 32:
        raise ValueError("AES-256 key must be 32 bytes")
    words = [key[index:index + 4] for index in range(0, 32, 4)]
    for index in range(8, 60):
        temp = words[index - 1]
        if index % 8 == 0:
            rotated = temp[1:] + temp[:1]
            temp = _xor_words(_sub_word(rotated, _SBOX), bytes((_RCON[index // 8], 0, 0, 0)))
        elif index % 8 == 4:
            temp = _sub_word(temp, _SBOX)
        words.append(_xor_words(words[index - 8], temp))
    return words


def _mix_column(column: bytes, matrix: tuple[tuple[int, int, int, int], ...]) -> bytes:
    mixed = []
    for row in matrix:
        mixed.append(
            _gf_mul(column[0], row[0])
            ^ _gf_mul(column[1], row[1])
            ^ _gf_mul(column[2], row[2])
            ^ _gf_mul(column[3], row[3])
        )
    return bytes(mixed)


_ENC_MATRIX = ((2, 3, 1, 1), (1, 2, 3, 1), (1, 1, 2, 3), (3, 1, 1, 2))
_DEC_MATRIX = ((14, 11, 13, 9), (9, 14, 11, 13), (13, 9, 14, 11), (11, 13, 9, 14))


def _shift_rows(state: bytearray, inverse: bool) -> None:
    for row in range(1, 4):
        shift = (4 - row) if inverse else row
        cells = [state[row + 4 * column] for column in range(4)]
        for column in range(4):
            state[row + 4 * column] = cells[(column + shift) % 4]


def _mix_columns(state: bytearray, matrix: tuple[tuple[int, int, int, int], ...]) -> None:
    for column in range(4):
        mixed = _mix_column(bytes(state[4 * column:4 * column + 4]), matrix)
        state[4 * column:4 * column + 4] = mixed


def _add_round_key(state: bytearray, words: list[bytes], round_index: int) -> None:
    block = b"".join(words[4 * round_index:4 * round_index + 4])
    for index, value in enumerate(block):
        state[index] ^= value


def _crypt_block(block: bytes, words: list[bytes], decrypt: bool) -> bytes:
    state = bytearray(block)
    if not decrypt:
        _add_round_key(state, words, 0)
        for round_index in range(1, 14):
            for index, value in enumerate(state):
                state[index] = _SBOX[value]
            _shift_rows(state, False)
            _mix_columns(state, _ENC_MATRIX)
            _add_round_key(state, words, round_index)
        for index, value in enumerate(state):
            state[index] = _SBOX[value]
        _shift_rows(state, False)
        _add_round_key(state, words, 14)
        return bytes(state)
    _add_round_key(state, words, 14)
    for round_index in range(13, 0, -1):
        _shift_rows(state, True)
        for index, value in enumerate(state):
            state[index] = _INV_SBOX[value]
        _add_round_key(state, words, round_index)
        _mix_columns(state, _DEC_MATRIX)
    _shift_rows(state, True)
    for index, value in enumerate(state):
        state[index] = _INV_SBOX[value]
    _add_round_key(state, words, 0)
    return bytes(state)


def aes_cbc_decrypt(ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
    if len(ciphertext) == 0 or len(ciphertext) % 16 != 0:
        raise ValueError("ciphertext length")
    words = _expand_key(key)
    previous = iv
    plain = bytearray()
    for offset in range(0, len(ciphertext), 16):
        block = ciphertext[offset:offset + 16]
        plain.extend(byte ^ previous[index] for index, byte in enumerate(_crypt_block(block, words, True)))
        previous = block
    pad = plain[-1]
    if pad < 1 or pad > 16 or plain[-pad:] != bytes([pad]) * pad:
        raise ValueError("pkcs7")
    return bytes(plain[:-pad])


def decrypt_response(response_b64: str, key_str: str = _RESPONSE_KEY) -> bytes:
    raw = "".join(response_b64.split())
    ciphertext = base64.b64decode(raw, validate=False)
    key = hashlib.sha256(key_str.encode("utf-8")).digest()
    return aes_cbc_decrypt(ciphertext, key, bytes(16))


def sign_request(account: str, app_version: str, rand_str: str) -> dict[str, str]:
    encoded = quote(str(account), safe="")
    source = (
        f"account={encoded}&app_version={app_version}"
        f"&rand_str={rand_str}&signatures={_SIGN_KEY}{_SIGN_SUFFIX}"
    )
    digest = hmac.new(_SIGN_KEY.encode("utf-8"), source.encode("utf-8"), hashlib.sha256).digest()
    return {"rand_str": rand_str, "p": base64.b64encode(digest).decode("ascii")}


def resolve_ciweimao_category(category: str) -> str:
    text = (category or "").strip()
    if text in _LABELS:
        return text
    if ":" in text:
        order, time_type = text.split(":", 1)
    else:
        order, time_type = text, _DEFAULT_TIME.get(text, "")
    if order not in _ORDERS or time_type not in _TIMES:
        known = ", ".join(DEFAULT_CATEGORIES)
        raise RankFetchError(f"ciweimao unknown rank: {category or '(empty)'}; examples: {known}")
    key = f"{order}:{time_type}"
    if key not in _LABELS:
        raise RankFetchError(f"ciweimao unknown rank: {key}")
    return key


def ciweimao_source(category: str) -> SourceSpec:
    key = resolve_ciweimao_category(category)
    order, time_type = key.split(":", 1)
    return SourceSpec(
        site_id="ciweimao",
        site_name="刺猬猫",
        source_id=f"ciweimao-{key}",
        semantic_key=key,
        category=key,
        category_name=_LABELS[key],
        url=f"{BASE_URL}{RANK_PATH}?order={order}&time_type={time_type}",
        required_adapters=["ciweimao_app_rank"],
        known_risks=["session_env", "no_chapter_fallback"],
    )


def _text(value: Any) -> str:
    return str(value or "").strip()


def _book(raw: dict[str, Any]) -> dict[str, Any]:
    nested = raw.get("book_info")
    if isinstance(nested, dict) and _text(nested.get("book_id") or nested.get("book_name")):
        return nested
    return raw


def _words(value: Any) -> str:
    text = _text(value)
    if not text or text == "0":
        return ""
    try:
        number = int(text)
    except ValueError:
        return text
    if number >= 10000:
        scaled = number / 10000
        return f"{scaled:.1f}万"
    return str(number)


def _pay_text(raw: dict[str, Any]) -> str:
    flag = _text(raw.get("is_paid"))
    if flag == "0":
        return "免费"
    if flag == "1":
        return "付费书"
    return ""


def _score(raw: dict[str, Any], order: str) -> str:
    for key in (order, *_SCORE_KEYS):
        text = _text(raw.get(key))
        if text and text != "0":
            return text
    return ""


def parse_ciweimao_rank(payload: dict[str, Any] | str, limit: int) -> ParseResult:
    if isinstance(payload, str):
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return ParseResult(False, failure_code="json_invalid", failure_detail="body", parser_version=PARSER_VERSION)
    else:
        data = payload
    code = _text(data.get("code"))
    if code and code != "100000":
        return ParseResult(False, failure_code="api_code", failure_detail=code, parser_version=PARSER_VERSION)
    body = data.get("data") if isinstance(data.get("data"), dict) else data
    books = body.get("book_list") if isinstance(body, dict) else None
    if not isinstance(books, list) or not books:
        return ParseResult(False, failure_code="empty_book_list", parser_version=PARSER_VERSION)
    items = []
    for raw in books[:limit]:
        if isinstance(raw, dict):
            items.append(_book(raw))
    if not items:
        return ParseResult(False, failure_code="empty_book_list", parser_version=PARSER_VERSION)
    return ParseResult(True, items=items, parser_version=PARSER_VERSION)


def normalize_ciweimao(source: SourceSpec, parsed: ParseResult) -> RankSnapshot:
    order = source.semantic_key.split(":", 1)[0]
    items: list[RankItem] = []
    for index, raw in enumerate(parsed.items, start=1):
        book_id = _text(raw.get("book_id")) or f"ciweimao-{index}"
        book_name = _text(raw.get("book_name"))
        category_text = _text(raw.get("category_name") or raw.get("category"))
        description = _text(raw.get("description") or raw.get("book_description"))
        items.append(RankItem(
            rank_position=index,
            book_id=book_id,
            book_name=book_name,
            author_name=_text(raw.get("author_name")),
            book_url=f"https://www.ciweimao.com/book/{book_id}" if book_id else "",
            cover_url=_text(raw.get("cover") or raw.get("cover_url")),
            description=description,
            category_text=category_text,
            score_text=_score(raw, order),
            word_count_text=_words(raw.get("total_word_count")),
            extra={"pay_text": _pay_text(raw)},
            field_confidence={
                "book_name": "verified" if book_name else "missing",
            },
        ))
    return RankSnapshot(
        site=source.site_id,
        site_name=source.site_name,
        category=source.category,
        category_name=source.category_name,
        semantic_key=source.semantic_key,
        source_url=source.url,
        snapshot_at=now_cst_iso(),
        items=items,
        raw_ref="",
        parse_status="ok" if parsed.ok else parsed.failure_code,
        parser_version=parsed.parser_version or PARSER_VERSION,
    )


def load_credentials(env: Mapping[str, str] | None = None) -> tuple[str, str, str]:
    source = os.environ if env is None else env
    values = {
        _ENV_ACCOUNT: _text(source.get(_ENV_ACCOUNT)),
        _ENV_LOGIN: _text(source.get(_ENV_LOGIN)),
        _ENV_DEVICE: _text(source.get(_ENV_DEVICE)),
    }
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise RankFetchError("ciweimao missing field: " + ",".join(missing))
    return values[_ENV_ACCOUNT], values[_ENV_LOGIN], values[_ENV_DEVICE]


def _decode_body(text: str) -> dict[str, Any]:
    raw = text.strip()
    if not raw:
        raise RankFetchError("ciweimao response empty")
    try:
        if raw.startswith("{"):
            data = json.loads(raw)
        else:
            data = json.loads(decrypt_response(raw).decode("utf-8"))
    except RankFetchError:
        raise
    except Exception as exc:
        raise RankFetchError("ciweimao response decrypt failed") from exc
    if not isinstance(data, dict):
        raise RankFetchError("ciweimao response parse failed")
    return data


def fetch_ciweimao_rank(
    category: str,
    limit: int = 20,
    env: Mapping[str, str] | None = None,
) -> RankSnapshot:
    if limit < 1:
        raise RankFetchError("ciweimao limit must be at least 1")
    source = ciweimao_source(category)
    account, login_token, device_token = load_credentials(env)
    order, time_type = source.semantic_key.split(":", 1)
    fields = {
        "login_token": login_token,
        "account": account,
        "device_token": device_token,
        "app_version": APP_VERSION,
        "order": order,
        "time_type": time_type,
        "page": "0",
        "count": str(max(1, min(int(limit), 100))),
        "category_index": "0",
    }
    fields.update(sign_request(account, APP_VERSION, secrets.token_hex(8)))
    response = post_form(
        f"{BASE_URL}{RANK_PATH}",
        fields,
        headers={"User-Agent": USER_AGENT},
    )
    if response.error or response.status != 200 or not response.text:
        raise RankFetchError(
            f"ciweimao request failed: category={source.category} status={response.status}"
        )
    data = _decode_body(response.text)
    code = _text(data.get("code"))
    if code == "200100":
        raise RankFetchError("ciweimao missing field: CIWEIMAO_LOGIN_TOKEN expired")
    parsed = parse_ciweimao_rank(data, limit)
    if not parsed.ok:
        detail = parsed.failure_detail or parsed.failure_code
        raise RankFetchError(f"ciweimao parse failed: category={source.category} code={detail}")
    snapshot = normalize_ciweimao(source, parsed)
    missing = [item.book_id for item in snapshot.items if not item.book_name]
    if not snapshot.items or missing:
        named = missing[0] if missing else source.category
        raise RankFetchError(f"ciweimao missing field: {named}:book_name")
    return snapshot
