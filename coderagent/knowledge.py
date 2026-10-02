"""知识库：段落和向量存在 SQLite 里，正文仍以笔记为准。

查询就三步：把问题变成向量，取出最近的几段，把距离换算成相似度。
删掉这个库之后，可以从 corpus/ 重新生成。
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from coderagent.chunk import chunk_text
from coderagent.load import load_corpus
from coderagent.models import Source

try:
    import apsw
    import sqlite_vec
except ImportError as exc:
    raise ImportError("知识库需要安装 apsw 和 sqlite-vec。") from exc

Embed = Callable[[list[str]], list[list[float]]]


@dataclass(frozen=True)
class Hit:
    note_id: str
    path: str
    url: str
    text: str
    start: int
    end: int
    score: float


class KnowledgeBase:
    def __init__(self, path: Path, embed: Embed):
        self.path = path
        self.embed = embed

    def index_corpus(self, corpus_dir: Path) -> None:
        """把还没进库的笔记补进索引。已经有的路径跳过。"""
        for source in load_corpus(corpus_dir):
            self.add_source(source)

    def add_source(self, source: Source) -> None:
        db = self._connect()
        try:
            chunks = chunk_text(source.body)
            if not chunks:
                _log("切分", f"{source.path} 切不出段落")
                return
            stored = [
                row[0]
                for row in db.execute(
                    "SELECT text FROM chunks WHERE path = ? ORDER BY start, id",
                    (source.path,),
                )
            ] if self._has_path(db, source.path) else []
            if stored == [chunk.text for chunk in chunks]:
                _log("存储", f"已在库中，跳过：{source.path}")
                return
            if stored:
                _log("存储", f"段落有变化，重新写入：{source.path}")
            _log(
                "切分",
                f"笔记：{source.path}",
                f"正文 {len(source.body)} 字，切成 {len(chunks)} 段",
                *[
                    f"- 第 {index} 段 [{chunk.start}:{chunk.end}] {len(chunk.text)} 字：{_preview(chunk.text)}"
                    for index, chunk in enumerate(chunks, start=1)
                ],
            )
            _log("向量化", f"笔记：{source.path}，{len(chunks)} 段")
            vectors = [_unit(row) for row in self.embed([chunk.text for chunk in chunks])]
            print(
                f"得到 {len(vectors)} 个向量，维度 {len(vectors[0])}，第 1 段前 4 维：{_head(vectors[0])}",
                file=sys.stderr,
            )
            self._ensure(db, len(vectors[0]))
            url = _url(source)
            tags = ",".join(source.tags)
            _log("存储", f"库：{self.path}", f"笔记：{source.path}")
            db.execute("BEGIN")
            try:
                if stored:
                    _delete_path(db, source.path)
                for index, (chunk, vector) in enumerate(zip(chunks, vectors), start=1):
                    db.execute(
                        """
                        INSERT INTO chunks(note_id, path, url, tags, start, end, text)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (source.id, source.path, url, tags, chunk.start, chunk.end, chunk.text),
                    ).fetchall()
                    db.execute(
                        "INSERT INTO chunk_vec(rowid, embedding) VALUES (?, ?)",
                        (db.last_insert_rowid(), sqlite_vec.serialize_float32(vector)),
                    ).fetchall()
                    print(
                        f"- 第 {index} 段 [{chunk.start}:{chunk.end}] 维度 {len(vector)}",
                        file=sys.stderr,
                    )
                db.execute("COMMIT")
            except Exception:
                db.execute("ROLLBACK")
                raise
            print(f"写入 {len(chunks)} 段", file=sys.stderr)
        finally:
            db.close()

    def search(self, query: str, *, limit: int = 4) -> list[Hit]:
        """返回最接近 query 的段落，score 越大越近。"""
        query = query.strip()
        if not query or limit < 1:
            return []
        _log("查询", f"问题：{query}", f"库：{self.path}")
        db = self._connect()
        try:
            if not self._has_vectors(db):
                print("库里还没有向量", file=sys.stderr)
                return []
            vector = _unit(self.embed([query])[0])
            print(f"查询向量维度 {len(vector)}，前 4 维：{_head(vector)}", file=sys.stderr)
            rows = list(
                db.execute(
                    """
                    SELECT c.note_id, c.path, c.url, c.text, c.start, c.end, v.distance
                    FROM chunk_vec AS v
                    JOIN chunks AS c ON c.id = v.rowid
                    WHERE v.embedding MATCH ?
                      AND k = ?
                    ORDER BY v.distance
                    """,
                    (sqlite_vec.serialize_float32(vector), limit),
                )
            )
        finally:
            db.close()
        hits = [
            Hit(
                note_id=note_id,
                path=path,
                url=url,
                text=text,
                start=start,
                end=end,
                score=_cosine(distance),
            )
            for note_id, path, url, text, start, end, distance in rows
        ]
        if not hits:
            print("没有召回段落", file=sys.stderr)
            return []
        print("最近的段落：", file=sys.stderr)
        for index, hit in enumerate(hits, start=1):
            print(
                f"- 第 {index} 名 相似度 {hit.score:.3f} {hit.path} [{hit.start}:{hit.end}] {_preview(hit.text)}",
                file=sys.stderr,
            )
        return hits

    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = apsw.Connection(str(self.path))
        db.enableloadextension(True)
        db.loadextension(sqlite_vec.loadable_path())
        return db

    def _ensure(self, db, dimension: int) -> None:
        self._ensure_tables(db)
        saved = _meta(db, "dimension")
        if saved is None:
            db.execute(f"CREATE VIRTUAL TABLE chunk_vec USING vec0(embedding float[{int(dimension)}])")
            db.execute("INSERT INTO meta(key, value) VALUES ('dimension', ?)", (str(dimension),))
            return
        if int(saved) != dimension:
            raise RuntimeError(f"知识库向量维度是 {saved}，这次的向量是 {dimension}。")

    def _has_path(self, db, path: str) -> bool:
        self._ensure_tables(db)
        return bool(list(db.execute("SELECT 1 FROM chunks WHERE path = ? LIMIT 1", (path,))))

    def _has_vectors(self, db) -> bool:
        self._ensure_tables(db)
        if _meta(db, "dimension") is None:
            return False
        return bool(list(db.execute("SELECT 1 FROM chunks LIMIT 1")))

    def _ensure_tables(self, db) -> None:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY,
                note_id TEXT NOT NULL,
                path TEXT NOT NULL,
                url TEXT NOT NULL,
                tags TEXT NOT NULL,
                start INTEGER NOT NULL,
                end INTEGER NOT NULL,
                text TEXT NOT NULL
            )
            """
        )
        db.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")


def _meta(db, key: str) -> Optional[str]:
    rows = list(db.execute("SELECT value FROM meta WHERE key = ?", (key,)))
    if not rows:
        return None
    return rows[0][0]


def _unit(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        raise ValueError("向量长度为 0。")
    return [value / norm for value in vector]


def _delete_path(db, path: str) -> None:
    row_ids = [row[0] for row in db.execute("SELECT id FROM chunks WHERE path = ?", (path,))]
    for row_id in row_ids:
        db.execute("DELETE FROM chunk_vec WHERE rowid = ?", (row_id,)).fetchall()
    db.execute("DELETE FROM chunks WHERE path = ?", (path,)).fetchall()


def _log(title: str, *lines: str) -> None:
    print(f"--- {title} ---", file=sys.stderr)
    if lines:
        print("\n".join(lines), file=sys.stderr)


def _preview(text: str, limit: int = 42) -> str:
    flat = " ".join(text.split())
    if len(flat) <= limit:
        return flat
    return flat[:limit] + "…"


def _head(vector: list[float]) -> str:
    return "[" + ", ".join(f"{value:.4f}" for value in vector[:4]) + "]"


def _cosine(distance: float) -> float:
    """单位向量的欧氏距离换回余弦相似度。"""
    return 1 - (distance * distance) / 2


def _url(source: Source) -> str:
    for line in source.raw.splitlines():
        if line.startswith("url:"):
            return line.split(":", 1)[1].strip()
    return ""
