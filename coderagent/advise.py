"""把已核对的原句交给模型，生成带来源的建议。"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Sequence

from coderagent.models import GOAL_LABEL, Advice, Evidence, Line, Request, Stop

Complete = Callable[[list[dict[str, str]]], str]

INVALID_JSON = "模型返回的不是可用的建议 JSON。"
NEED_FIELDS = "每一条都要有 text 和 evidence_id。"
NO_REASONS = f"模型没有给出可引用的原因。{NEED_FIELDS}"
NO_LATER = f"模型没有给出可引用的暂时不做。{NEED_FIELDS}"
NO_NEXT = f"模型没有给出可引用的下一步。{NEED_FIELDS}"


def advise_with_model(
    request: Request,
    evidence: Sequence[Evidence],
    complete: Complete,
    *,
    model: str,
) -> tuple[Advice | Stop, tuple[str, ...]]:
    raw = complete(build_messages(request, evidence))
    return parse_advice(raw, request, evidence, model)


def build_messages(request: Request, evidence: Sequence[Evidence]) -> list[dict[str, str]]:
    payload = {
        "question": request.question,
        "options": list(request.options),
        "profile": {
            "background": list(request.profile.background),
            "prior_ai_project": request.profile.prior_ai_project,
            "goal": request.profile.goal,
            "goal_label": GOAL_LABEL[request.profile.goal],
            "hours_per_week": request.profile.hours_per_week,
        },
        "evidence": [
            {
                "id": item.id,
                "option": item.option,
                "dimension": item.dimension,
                "quote": item.quote,
            }
            for item in evidence
        ],
    }
    system = (
        "你负责技术选型建议。只能依据给定 evidence 里的原句，结合 profile 做判断。"
        "不要使用证据之外的技术事实，不要编造证据 id。"
        "只输出一个 JSON 对象，不要输出其他文字。格式："
        '{"recommend":"选项之一","recommend_evidence_id":"证据 id",'
        '"reasons":[{"text":"一句原因","evidence_id":"证据 id"}],'
        '"not_yet":[{"text":"一句暂时不做的理由","evidence_id":"证据 id"}],'
        '"next_step":{"text":"一个具体下一步","evidence_id":"证据 id"}}'
        "reasons 和 not_yet 各 1 到 3 条，next_step 恰好一条。"
        "recommend 的证据必须对应该选项。text 用中文写给这个用户。"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


def parse_advice(
    raw: str,
    request: Request,
    evidence: Sequence[Evidence],
    model: str,
) -> tuple[Advice | Stop, tuple[str, ...]]:
    data = _load_json(raw)
    if data is None:
        return Stop(INVALID_JSON), ()

    by_id = {item.id: item for item in evidence}
    rejected: list[str] = []
    recommend = _match_option(data.get("recommend"), request.options)
    recommend_id = str(data.get("recommend_evidence_id", "")).strip()
    if recommend is None:
        return Stop("模型给出的选项不在问题里。"), tuple(rejected)
    cited = by_id.get(recommend_id)
    if cited is None or cited.option != recommend:
        return Stop("模型没有为建议先做的选项引用对应证据。"), tuple(rejected)

    reasons = _collect(data.get("reasons"), by_id, rejected, "原因", limit=3)
    later = _collect(data.get("not_yet"), by_id, rejected, "暂时不做", limit=3)
    nxt = _one(data.get("next_step"), by_id, rejected, "下一步")
    if not reasons:
        return Stop(NO_REASONS), tuple(rejected)
    if not later:
        return Stop(NO_LATER), tuple(rejected)
    if nxt is None:
        return Stop(NO_NEXT), tuple(rejected)
    if by_id[nxt[0]].option != recommend:
        return Stop("下一步引用的证据不属于建议先做的选项。"), tuple(rejected)

    return Advice(
        recommend=Line(text=recommend, ref=_ref(model, recommend_id)),
        reasons=tuple(Line(text=text, ref=_ref(model, evidence_id)) for evidence_id, text in reasons),
        not_yet=tuple(Line(text=text, ref=_ref(model, evidence_id)) for evidence_id, text in later),
        next_step=Line(text=nxt[1], ref=_ref(model, nxt[0])),
    ), tuple(rejected)


def _collect(value: object, by_id: dict[str, Evidence], rejected: list[str], label: str, limit: int):
    if not isinstance(value, list):
        rejected.append(f"{label}：不是列表")
        return []
    if len(value) > limit:
        rejected.append(f"{label}：超过 {limit} 条，只保留前 {limit} 条")
    kept = []
    for item in value[:limit]:
        cited = _cite(item, by_id, rejected, label)
        if cited is not None:
            kept.append(cited)
    return kept


def _one(value: object, by_id: dict[str, Evidence], rejected: list[str], label: str):
    if isinstance(value, list):
        if len(value) != 1:
            rejected.append(f"{label}：必须恰好一条")
            return None
        value = value[0]
    return _cite(value, by_id, rejected, label)


def _cite(item: object, by_id: dict[str, Evidence], rejected: list[str], label: str):
    if not isinstance(item, dict):
        rejected.append(f"{label}：不是对象。{NEED_FIELDS}")
        return None
    evidence_id = item.get("evidence_id")
    text = item.get("text")
    if not isinstance(evidence_id, str) or not evidence_id.strip():
        rejected.append(f"{label}：缺少 evidence_id。{NEED_FIELDS}")
        return None
    evidence_id = evidence_id.strip()
    if not isinstance(text, str) or not text.strip():
        rejected.append(f"{label}：缺少 text。{NEED_FIELDS}")
        return None
    if evidence_id not in by_id:
        rejected.append(f"{label}：evidence_id 不存在：{evidence_id}。{NEED_FIELDS}")
        return None
    return evidence_id, text.strip()


def _match_option(value: object, options: Sequence[str]) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    for option in options:
        if option == text or option.casefold() == text.casefold():
            return option
    return None


def _load_json(raw: str) -> dict | None:
    text = raw.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.S)
    if fenced:
        text = fenced.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def _ref(model: str, evidence_id: str) -> str:
    return f"model:{model}:{evidence_id}"
