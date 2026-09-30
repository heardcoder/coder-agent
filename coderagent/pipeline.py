"""研究流程：拆解在外面完成，建议由 ReAct 循环产生。"""

from __future__ import annotations

from pathlib import Path

from coderagent.llm import LLMError
from coderagent.lookup import Search, search_web
from coderagent.models import Request, Result
from coderagent.react import NO_MATERIAL, StepListener, Turn, research

MISSING_KEY = "调用模型需要 API 密钥，请在命令里传入 --api-key。"


def run(
    request: Request,
    corpus_dir: Path,
    *,
    turn: Turn | None,
    model: str,
    on_step: StepListener | None = None,
    search: Search = search_web,
) -> Result:
    if turn is None:
        raise LLMError(MISSING_KEY)
    return research(request, corpus_dir, turn, model, search, on_step)


__all__ = ["MISSING_KEY", "NO_MATERIAL", "run"]
