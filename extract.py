"""只收下引用句能在正文里原样找到的证据。"""

from __future__ import annotations

from collections.abc import Sequence

from coderagent.load import EVIDENCE_BLOCK
from coderagent.models import DIMENSIONS, STANCES, Evidence, Source

ALLOWED_WHEN = {"prior_ai_project", "goal", "max_hours", "min_hours"}


def extract(sources: Sequence[Source]) -> tuple[tuple[Evidence, ...], tuple[str, ...]]:
    kept: list[Evidence] = []
    rejected: list[str] = []
    seen: set[str] = set()
    for source in sources:
        for block in EVIDENCE_BLOCK.findall(source.raw):
            parsed = _parse_block(block, source)
            if isinstance(parsed, str):
                rejected.append(parsed)
                continue
            if parsed.id in seen:
                rejected.append(f"{parsed.id}: id 重复")
                continue
            seen.add(parsed.id)
            if parsed.quote not in source.body:
                rejected.append(f"{parsed.id}: 引用句不在原文中")
                continue
            kept.append(parsed)
    return tuple(kept), tuple(rejected)


def _parse_block(block: str, source: Source) -> Evidence | str:
    data: dict[str, str] = {}
    when: dict[str, object] = {}
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if ":" not in line:
            return f"{source.id}: 证据格式无法解析"
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key.startswith("when."):
            field = key.removeprefix("when.")
            if field not in ALLOWED_WHEN:
                return f"{source.id}: 不认识的条件 {field}"
            when[field] = _parse_scalar(value)
            continue
        data[key] = value

    evidence_id = data.get("id", "")
    if not evidence_id:
        return f"{source.id}: 有证据缺少 id"
    missing = [key for key in ("option", "dimension", "stance", "quote") if not data.get(key)]
    if missing:
        return f"{evidence_id}: 缺少 {', '.join(missing)}"
    if data["stance"] not in STANCES:
        return f"{evidence_id}: 不认识的 stance {data['stance']}"
    if data["option"] not in source.tags:
        return f"{evidence_id}: 选项 {data['option']} 不在来源标签里"
    if data["stance"] == "info" and data["dimension"] not in DIMENSIONS:
        return f"{evidence_id}: 比较维度不在固定列表里"
    return Evidence(
        id=evidence_id,
        source_id=source.id,
        option=data["option"],
        dimension=data["dimension"],
        stance=data["stance"],
        quote=data["quote"],
        when=tuple(sorted(when.items())),
    )


def _parse_scalar(value: str) -> object:
    if value == "true":
        return True
    if value == "false":
        return False
    if value.isdigit():
        return int(value)
    return value
