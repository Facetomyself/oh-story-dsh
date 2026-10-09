from __future__ import annotations

import re
from pathlib import Path

from .contracts import RankItem, RankSnapshot

_UNSAFE = re.compile(r'[\\/:*?"<>|\s]+')


def _blank(value: str) -> str:
    text = (value or "").strip()
    return text if text else "[待补]"


def _safe_label(value: str) -> str:
    cleaned = _UNSAFE.sub("", value or "")
    return cleaned or "榜"


def output_name(snapshot: RankSnapshot, day: str) -> str:
    if snapshot.site == "qidian":
        return f"起点{_safe_label(snapshot.category_name)}_{day}.md"
    label = _safe_label(snapshot.category_name.replace("/", ""))
    return f"番茄{label}_{day}.md"


def _qidian_block(item: RankItem) -> list[str]:
    sub_cat = str(item.extra.get("sub_cat") or "").strip()
    genre = item.category_text
    if sub_cat and sub_cat not in genre:
        genre = f"{genre}·{sub_cat}" if genre else sub_cat
    meta = " · ".join(part for part in (item.author_name, genre, item.status) if part)
    lines = [f"## #{item.rank_position} {item.book_name}"]
    if meta:
        lines.append(f"*{meta}*")
    lines.append(f"**字数：{_blank(item.word_count_text)}**")
    lines.append(f"**榜单值：{_blank(item.score_text)}**")
    lines.append("**总推荐：[待补]**")
    lines.append("**签约：[待补]**")
    lines.append("**收费模式：[待补]**")
    if item.book_url:
        lines.append(f"[作品页]({item.book_url})")
    if item.description:
        lines.extend(["", "**简介**", "", item.description])
    lines.extend(["", "---", ""])
    return lines


def _fanqie_block(item: RankItem) -> list[str]:
    meta = " · ".join(part for part in (item.author_name, item.category_text, item.status) if part)
    lines = [f"### #{item.rank_position} {item.book_name}"]
    if meta:
        lines.append(f"*{meta}*")
    lines.append(f"**在读：{_blank(str(item.extra.get('read_count') or ''))}**")
    lines.append(f"**字数：{_blank(item.word_count_text)}**")
    if item.tags:
        lines.append(f"**标签：** {'、'.join(item.tags)}")
    if item.latest_update_time or item.latest_chapter:
        lines.append(f"**最新更新：** {_blank(item.latest_chapter)} {item.latest_update_time}".rstrip())
    if item.book_url:
        lines.append(f"[作品页]({item.book_url})")
    if item.description:
        lines.extend(["", "**简介**", "", item.description])
    lines.extend(["", "---", ""])
    return lines


def render_markdown(snapshot: RankSnapshot) -> str:
    lines = [
        f"# {snapshot.site_name} · {snapshot.category_name}",
        "",
        f"- 来源：{snapshot.source_url}",
        "- 抓取方式：rankmin-http",
        f"- 抓取时间：{snapshot.snapshot_at}",
        f"- 条目数：{len(snapshot.items)}",
        f"- 解析：{snapshot.parser_version}",
        "",
        "---",
        "",
    ]
    renderer = _qidian_block if snapshot.site == "qidian" else _fanqie_block
    for item in snapshot.items:
        lines.extend(renderer(item))
    return "\n".join(lines).rstrip() + "\n"


def write_snapshot(snapshot: RankSnapshot, out_dir: Path, day: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / output_name(snapshot, day)
    path.write_text(render_markdown(snapshot), encoding="utf-8", newline="\n")
    return path
