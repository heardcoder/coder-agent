"""固定的研究流程：检索、核对、比较，再由模型写建议。"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from coderagent.advise import Complete, advise_with_model
from coderagent.compare import compare
from coderagent.extract import extract
from coderagent.llm import LLMError
from coderagent.models import Request, Result, Row, Source, Stop
from coderagent.retrieve import retrieve

StepListener = Callable[[str, str, str], None]

NO_SOURCE = "没有读到来源。选项在本地语料里没有对应笔记，这一步不会让模型补全。"
NO_EVIDENCE = "来源里没有可用的原句，不会让模型编建议。"
MISSING_KEY = "调用模型需要 API 密钥，请在命令里传入 --api-key。"


def run(
    request: Request,
    sources: Sequence[Source],
    *,
    complete: Complete | None,
    model: str,
    on_step: StepListener | None = None,
) -> Result:
    def emit(step: str, state: str, text: str = "") -> None:
        if on_step is not None:
            on_step(step, state, text)

    emit("retrieve", "running", "按选项在本地笔记里查找")
    found = retrieve(request.options, sources)
    if not found:
        emit("retrieve", "stopped", NO_SOURCE)
        _skip(emit, "extract", "compare", "advise")
        return _result(found, compare(request.options, ()), Stop(NO_SOURCE), ())

    emit("retrieve", "done", "、".join(source.title for source in found))
    emit("extract", "running", "核对引用句是否在正文里")
    evidence, rejected = extract(found)
    if not evidence:
        emit("extract", "stopped", NO_EVIDENCE)
        _skip(emit, "compare", "advise")
        return _result(found, compare(request.options, evidence), Stop(NO_EVIDENCE), rejected)

    dropped = f"，丢掉 {len(rejected)} 条" if rejected else ""
    emit("extract", "done", f"留下 {len(evidence)} 条原句{dropped}")
    if complete is None:
        raise LLMError(MISSING_KEY)

    emit("compare", "running", "按固定维度排列原句")
    comparison = compare(request.options, evidence)
    emit("compare", "done", _compare_text(comparison))
    emit("advise", "running", "模型根据这些原句写建议")
    outcome, extra = advise_with_model(request, evidence, complete, model=model)
    if isinstance(outcome, Stop):
        emit("advise", "stopped", outcome.reason)
    else:
        emit("advise", "done", f"建议先做 {outcome.recommend.text}")
    return _result(found, comparison, outcome, tuple(rejected) + extra, model)


def _skip(emit, *steps: str) -> None:
    for step in steps:
        emit(step, "skipped", "")


def _compare_text(comparison: Sequence[Row]) -> str:
    count = sum(len(lines) for row in comparison for _, lines in row.cells)
    dimensions = "、".join(row.dimension for row in comparison)
    return f"{dimensions}，共 {count} 条原句"


def _result(found, comparison, outcome, rejected, model: str = "") -> Result:
    return Result(
        sources=tuple(found),
        comparison=tuple(comparison),
        outcome=outcome,
        rejected=tuple(rejected),
        model=model,
    )
