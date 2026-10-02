"""本地向量模型。第一次编码时才加载，测试可以换成自己的函数。"""

from __future__ import annotations

import sys


class BgeM3:
    def __init__(self, model_name: str = "BAAI/bge-m3"):
        self.model_name = model_name
        self._model = None

    def __call__(self, texts: list[str]) -> list[list[float]]:
        model = self._load()
        print(f"编码 {len(texts)} 条文本", file=sys.stderr)
        rows = []
        for text in texts:
            vector = model.encode([text], normalize_embeddings=True)[0]
            rows.append([float(value) for value in vector])
        if rows:
            print(f"维度 {len(rows[0])}，第 1 条前 4 维：{_head(rows[0])}", file=sys.stderr)
        return rows

    def _load(self):
        if self._model is None:
            print(f"加载向量模型：{self.model_name}", file=sys.stderr)
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError("使用 bge-m3 需要先安装 sentence-transformers。") from exc
            self._model = SentenceTransformer(self.model_name)
            print(f"向量模型已加载：{self.model_name}", file=sys.stderr)
        return self._model


def _head(vector: list[float]) -> str:
    return "[" + ", ".join(f"{value:.4f}" for value in vector[:4]) + "]"
