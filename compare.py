"""比较表只陈列原文，不按用户背景删句子。"""

from __future__ import annotations

from collections.abc import Sequence

from coderagent.models import DIMENSIONS, Evidence, Line, Row


def compare(options: Sequence[str], evidence: Sequence[Evidence]) -> tuple[Row, ...]:
    info = [item for item in evidence if item.stance == "info"]
    rows = []
    for dimension in DIMENSIONS:
        cells = []
        for option in options:
            lines = tuple(
                Line(text=item.quote, ref=f"evidence:{item.id}")
                for item in info
                if item.option == option and item.dimension == dimension
            )
            cells.append((option, lines))
        rows.append(Row(dimension=dimension, cells=tuple(cells)))
    return tuple(rows)
