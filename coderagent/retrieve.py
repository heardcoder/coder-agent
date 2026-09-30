"""按选项标签取出笔记。不做相似度，也不读问题原句。"""

from __future__ import annotations

from collections.abc import Sequence

from coderagent.models import Source


def retrieve(options: Sequence[str], sources: Sequence[Source]) -> tuple[Source, ...]:
    wanted = {option.casefold() for option in options}
    found = [
        source
        for source in sources
        if wanted & {tag.casefold() for tag in source.tags}
    ]
    return tuple(sorted(found, key=lambda source: source.id))
