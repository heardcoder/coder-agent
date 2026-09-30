"""把结果印成可读的决定。背景行只回显输入。"""

from __future__ import annotations

from coderagent.models import GOAL_LABEL, Advice, Line, Profile, Request, Result, Stop


def render(request: Request, result: Result) -> str:
    parts = [
        f"问题：{request.question}",
        f"选项：{'、'.join(request.options)}",
        "",
        *_profile_block(request.profile),
        "",
    ]
    if result.sources:
        parts.append("读过的来源：")
        for source in result.sources:
            parts.append(f"- [{source.id}] {source.title}（{source.path}）")
        parts.append("")
    if result.sources and result.comparison:
        parts.append("比较：")
        for row in result.comparison:
            parts.append(f"- {row.dimension}")
            for option, lines in row.cells:
                if not lines:
                    parts.append(f"  - {option}：（这一维没有原句）")
                    continue
                for line in lines:
                    parts.append(f"  - {option}：{line.text} [{_short(line.ref)}]")
        parts.append("")

    if result.model:
        parts.append(f"模型：{result.model}")
        parts.append("")

    outcome = result.outcome
    if isinstance(outcome, Stop):
        parts.append("不能给出建议。")
        parts.append(outcome.reason)
    else:
        parts.append(f"建议先做：{outcome.recommend.text} [{_short(outcome.recommend.ref)}]")
        parts.append("原因：")
        for line in outcome.reasons:
            parts.append(f"- {line.text} [{_short(line.ref)}]")
        parts.append("暂时不做：")
        for line in outcome.not_yet:
            parts.append(f"- {line.text} [{_short(line.ref)}]")
        parts.append("下一步：")
        parts.append(f"- {outcome.next_step.text} [{_short(outcome.next_step.ref)}]")
    parts.append("")
    parts.extend(_audit(request.profile, result))
    return "\n".join(parts).rstrip() + "\n"


def _profile_block(profile: Profile) -> list[str]:
    lines = _profile_lines(profile)
    labels = {
        "profile.background": "当前基础",
        "profile.prior_ai_project": "已有 AI 项目",
        "profile.hours_per_week": "每周投入",
        "profile.goal": "目标",
    }
    return [f"{labels[line.ref]}：{line.text} [{line.ref}]" for line in lines]


def _profile_lines(profile: Profile) -> tuple[Line, ...]:
    prior = "已经做过可以演示的 AI 项目" if profile.prior_ai_project else "还没有做过检索或 Agent 项目"
    return (
        Line("、".join(profile.background), "profile.background"),
        Line(prior, "profile.prior_ai_project"),
        Line(f"{profile.hours_per_week} 小时", "profile.hours_per_week"),
        Line(GOAL_LABEL[profile.goal], "profile.goal"),
    )


def _audit(profile: Profile, result: Result) -> list[str]:
    technical = () if isinstance(result.outcome, Stop) else result.outcome.technical_lines()
    compared = [
        line
        for row in result.comparison
        for _, lines in row.cells
        for line in lines
    ]
    return [
        "检查：",
        _ref_line("背景复述", _profile_lines(profile), "profile."),
        _ref_line("技术结论", technical, "model:"),
        _ref_line("比较原句", compared, "evidence:"),
        f"- 模型撰写 {sum(1 for line in technical if line.ref.startswith('model:'))} 条",
        f"- 无来源结论 {len(_untraced(technical)) + len(_untraced(compared))} 条",
        f"- 丢弃的证据 {len(result.rejected)} 条",
        *[f"  - {item}" for item in result.rejected],
    ]


def _ref_line(name: str, lines: tuple[Line, ...] | list[Line], prefix: str) -> str:
    if not lines:
        return f"- {name} 0 条"
    bad = _untraced(lines, prefix)
    if bad:
        return f"- {name} {len(lines)} 条，其中 {len(bad)} 条引用不符合 {prefix}*"
    return f"- {name} {len(lines)} 条，引用都是 {prefix}*"


def _untraced(lines: tuple[Line, ...] | list[Line], prefix: str | None = None) -> list[Line]:
    if prefix is None:
        return [line for line in lines if not line.ref.startswith(("profile.", "evidence:", "model:"))]
    return [line for line in lines if not line.ref.startswith(prefix)]


def _short(ref: str) -> str:
    if ref.startswith("model:"):
        return ref.removeprefix("model:")
    return ref.removeprefix("evidence:")
