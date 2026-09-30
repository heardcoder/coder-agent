"""ReAct 研究循环。模型决定查资料还是提交建议，程序执行工具并核对结果。"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from typing import Optional
from pathlib import Path

from coderagent.advise import parse_advice
from coderagent.compare import compare
from coderagent.lookup import Search, lookup
from coderagent.models import GOAL_LABEL, Advice, Evidence, Request, Result, Stop

MAX_ROUNDS = 6
NO_MATERIAL = "没有读到来源。本地笔记和联网搜索都没有可用资料。"
EXHAUSTED = "研究轮次已用尽，没有交出合格建议。"
Turn = Callable[[list, Optional[list]], dict]
StepListener = Callable[[str, str, str], None]

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lookup",
            "description": "按选项查资料。程序先读本地笔记，没有再联网搜索，并把新页面写回笔记。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "要查的问题"},
                    "option": {"type": "string", "description": "这个问题在比较的选项之一"},
                },
                "required": ["query", "option"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_advice",
            "description": "资料足够时提交最终建议。evidence_id 必须来自本次 lookup 返回的原句。",
            "parameters": {
                "type": "object",
                "properties": {
                    "recommend": {"type": "string"},
                    "recommend_evidence_id": {"type": "string"},
                    "reasons": {"type": "array", "items": {"type": "object"}},
                    "not_yet": {"type": "array", "items": {"type": "object"}},
                    "next_step": {"type": "object"},
                },
                "required": ["recommend", "recommend_evidence_id", "reasons", "not_yet", "next_step"],
            },
        },
    },
]

SYSTEM = (
    "你在做技术选型。每次只调用一个工具。"
    "先用 lookup 读取资料。query 只写技术名称，不要写「应该」「先学」这类词。"
    "资料足够后再调用 submit_advice。"
    "建议中的 evidence_id 必须来自 lookup 返回的 evidence，不要编造。"
    "理由、暂时不做和下一步都用中文写给这个用户。"
)


def research(
    request: Request,
    corpus_dir: Path,
    turn: Turn,
    model: str,
    search: Search,
    on_step: StepListener | None = None,
) -> Result:
    evidence: dict[str, Evidence] = {}
    rejected: list[str] = []
    notes = []
    cache: dict[tuple[str, str], str] = {}
    log: list[str] = []
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": _task(request)},
    ]

    def emit(state: str) -> None:
        if on_step is not None:
            on_step("research", state, "\n".join(log))

    for index in range(1, MAX_ROUNDS + 1):
        message = turn(messages, TOOLS)
        calls = message.get("tool_calls") or []
        assistant = {"role": "assistant", "content": message.get("content") or ""}
        if calls:
            assistant["tool_calls"] = calls
        messages.append(assistant)
        if not calls:
            log.append(f"第 {index} 轮：没有调用工具")
            emit("running")
            messages.append({"role": "user", "content": "请调用 lookup 或 submit_advice。"})
            continue
        for call in calls:
            name, arguments, call_id = _call_parts(call, index)
            if name == "lookup":
                content = _run_lookup(
                    arguments, request, corpus_dir, search, evidence, rejected, notes, log, index, cache
                )
            elif name == "submit_advice":
                outcome, content = _run_submit(arguments, request, evidence, rejected, model)
                if isinstance(outcome, Advice):
                    log.append(f"第 {index} 轮：建议先做 {outcome.recommend.text}")
                    emit("done")
                    return _result(request, tuple(notes), evidence, outcome, rejected, model)
                log.append(f"第 {index} 轮：建议不合格，{json.loads(content)['reason']}")
                emit("running")
            else:
                content = f"不认识的工具 {name}"
                log.append(f"第 {index} 轮：{content}")
                emit("running")
            messages.append({"role": "tool", "tool_call_id": call_id, "content": content})
            if name == "lookup":
                emit("running")
    reason = NO_MATERIAL if not evidence else EXHAUSTED
    log.append(reason)
    emit("stopped")
    return _result(request, tuple(notes), evidence, Stop(reason), rejected, model)


def _run_lookup(arguments, request, corpus_dir, search, evidence, rejected, notes, log, index, cache) -> str:
    data = _object(arguments)
    if data is None:
        text = "lookup 的参数不是 JSON 对象。"
        log.append(f"第 {index} 轮：{text}")
        return text
    option = _canonical(data.get("option"), request.options)
    query = data.get("query")
    if option is None:
        text = "lookup 的 option 不在这次要比较的选项里。"
        log.append(f"第 {index} 轮：{text}")
        return text
    if not isinstance(query, str):
        text = "lookup 缺少 query。"
        log.append(f"第 {index} 轮：{text}")
        return text
    key = (option, query.strip())
    if key in cache:
        log.append(f"第 {index} 轮：lookup {option}，重复查询，沿用上一次的结果")
        return cache[key]
    found = lookup(corpus_dir, query, option, search)
    rejected.extend(found.rejected)
    for note in found.notes:
        if note.id not in {item.id for item in notes}:
            notes.append(note)
    for item in found.evidence:
        evidence[item.id] = item
    if found.found and found.origin == "local":
        where = "、".join(note.title for note in found.notes)
        text = f"读到本地笔记：{where}"
    elif found.found:
        text = f"本地没有，已联网并写入笔记：{found.notes[0].title}"
    else:
        text = found.reason
    log.append(f"第 {index} 轮：lookup {option}，{text}")
    payload = json.dumps(found.as_dict(), ensure_ascii=False)
    cache[key] = payload
    return payload


def _run_submit(arguments, request, evidence, rejected, model):
    raw = arguments if isinstance(arguments, str) else json.dumps(arguments, ensure_ascii=False)
    outcome, extra = parse_advice(raw, request, tuple(evidence.values()), model)
    rejected.extend(extra)
    if isinstance(outcome, Advice):
        return outcome, f"建议先做 {outcome.recommend.text}"
    payload = {
        "ok": False,
        "reason": outcome.reason,
        "evidence_ids": list(evidence),
    }
    return None, json.dumps(payload, ensure_ascii=False)


def _task(request: Request) -> str:
    profile = request.profile
    payload = {
        "question": request.question,
        "options": list(request.options),
        "profile": {
            "background": list(profile.background),
            "prior_ai_project": profile.prior_ai_project,
            "goal": profile.goal,
            "goal_label": GOAL_LABEL[profile.goal],
            "hours_per_week": profile.hours_per_week,
        },
    }
    return json.dumps(payload, ensure_ascii=False)


def _call_parts(call: dict, index: int) -> tuple[str, object, str]:
    function = call.get("function") if isinstance(call, dict) else None
    if not isinstance(function, dict):
        return "", "", f"call-{index}"
    name = str(function.get("name") or "")
    arguments = function.get("arguments")
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            if name == "lookup":
                arguments = None
    call_id = str(call.get("id") or f"call-{index}")
    return name, arguments, call_id


def _object(value: object) -> dict | None:
    if isinstance(value, dict):
        return value
    return None


def _canonical(value: object, options: Sequence[str]) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    for option in options:
        if option == text or option.casefold() == text.casefold():
            return option
    return None


def _result(request: Request, notes, evidence, outcome, rejected, model: str) -> Result:
    return Result(
        sources=notes,
        comparison=compare(request.options, tuple(evidence.values())),
        outcome=outcome,
        rejected=tuple(rejected),
        model=model,
    )
