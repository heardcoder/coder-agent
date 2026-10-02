"""把笔记正文切成可检索的段落。

分三步，都不在一句话中间断开：

1. 按句号、问号、叹号，以及空行，切成不可再分的单位。
2. 把相邻单位装进一段，每段大约 size 个字。超长的一句单独成段。
3. 短于 minimum 字的句子并进相邻段，不单独成段。
4. 下一段从上一尾部往回 overlap 个字的那一句开始，边界上的句子会重复出现。
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_SIZE = 320
DEFAULT_OVERLAP = 64
MIN_CHUNK = 40
_SENTENCE_END = "。！？.!?"


@dataclass(frozen=True)
class Chunk:
    text: str
    start: int
    end: int


def chunk_text(
    text: str,
    *,
    size: int = DEFAULT_SIZE,
    overlap: int = DEFAULT_OVERLAP,
    minimum: int = MIN_CHUNK,
) -> list[Chunk]:
    units = split_units(text)
    chunks: list[Chunk] = []
    index = 0
    while index < len(units):
        end_index = _fill_short(units, text, index, _pack(units, index, size), minimum)
        start = units[index][0]
        end = units[end_index][1]
        piece = text[start:end]
        short = len(piece.strip()) < minimum
        if short and chunks and chunks[-1].end >= end:
            if end_index >= len(units) - 1:
                break
            index = end_index + 1
            continue
        if short and chunks:
            previous = chunks[-1]
            chunks[-1] = Chunk(text[previous.start : end], previous.start, end)
        else:
            chunks.append(Chunk(piece, start, end))
        if end_index >= len(units) - 1:
            break
        index = _next_start(units, end, overlap, index)
    return chunks


def split_units(text: str) -> list[tuple[int, int]]:
    """返回每个单位在原文中的 [start, end)。"""
    units: list[tuple[int, int]] = []
    start = 0
    index = 0
    length = len(text)
    while index < length:
        if text[index] in _SENTENCE_END:
            _keep(units, text, start, index + 1)
            start = index + 1
            index += 1
            continue
        if text[index] == "\n" and index + 1 < length and text[index + 1] == "\n":
            _keep(units, text, start, index)
            index += 2
            while index < length and text[index] in "\n\t ":
                index += 1
            start = index
            continue
        index += 1
    _keep(units, text, start, length)
    return units


def _fill_short(
    units: list[tuple[int, int]],
    text: str,
    index: int,
    end_index: int,
    minimum: int,
) -> int:
    """这一段太短、后面还有句子时，把后面的句子并进来。"""
    start = units[index][0]
    while end_index + 1 < len(units) and len(text[start : units[end_index][1]].strip()) < minimum:
        end_index += 1
    return end_index


def _pack(units: list[tuple[int, int]], index: int, size: int) -> int:
    """从 index 起尽量装满 size 字。至少保留当前这一句。"""
    end_index = index
    start = units[index][0]
    while end_index + 1 < len(units):
        if units[end_index + 1][1] - start > size:
            break
        end_index += 1
    return end_index


def _next_start(
    units: list[tuple[int, int]],
    chunk_end: int,
    overlap: int,
    current: int,
) -> int:
    """下一段对齐到「往回 overlap 字」所在的那一句，并且必须前进。"""
    target = max(0, chunk_end - overlap)
    for position in range(current + 1, len(units)):
        if units[position][1] > target:
            return position
    return len(units)


def _keep(units: list[tuple[int, int]], text: str, start: int, end: int) -> None:
    if text[start:end].strip():
        units.append((start, end))
