"""比较表只陈列原文，不按用户背景删句子。"""

from __future__ import annotations

from collections.abc import Sequence

from coderagent.models import DIMENSIONS, Evidence, Line, Row


def compare(options: Sequence[str], evidence: Sequence[Evidence]) -> tuple[Row, ...]:
    info = [item for item in evidence if item.stance == "info"]
    dimensions: list[str] = []
    for dimension in list(DIMENSIONS) + [item.dimension for item in info]:
        if dimension not in dimensions:
            dimensions.append(dimension)
    rows = []
    for dimension in dimensions:
        cells = []
        for option in options:
            lines = tuple(
                Line(text=item.quote, ref=f"evidence:{item.id}")
                for item in info
                if item.option == option and item.dimension == dimension
            )
            cells.append((option, lines))
        if any(lines for _, lines in cells):
            rows.append(Row(dimension=dimension, cells=tuple(cells)))
    return tuple(rows)
