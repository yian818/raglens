"""二阶段重排（rerank）。

默认只提供 local_lexical：字符 bigram 重叠度。它不是 cross-encoder，
价值在于让你在没有重排模型时，也能量化"加上一步重排，结果变好了多少"。
"""

import math
from typing import List, Tuple

from .chunker import Chunk
from .embeddings import LocalHashEmbedder

_lex = LocalHashEmbedder(dim=256)


def lexical_overlap(a: str, b: str) -> float:
    """字符集合的 Dice 相似度。"""
    ta, tb = _lex.tokens(a), _lex.tokens(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    return 2 * inter / (len(ta) + len(tb))


def rerank_candidates(
    query: str, candidates: List[Tuple[Chunk, float]], top_k: int
) -> List[Tuple[Chunk, float]]:
    """把向量分（归一化到 0~1）与词面重叠分做等权融合，重排后取 top_k。"""
    scored = []
    for chunk, vec_score in candidates:
        vec_norm = max(0.0, min(1.0, (vec_score + 1.0) / 2.0))
        lex = lexical_overlap(query, chunk.text)
        fused = 0.5 * vec_norm + 0.5 * lex
        scored.append((chunk, round(fused, 4)))
    scored.sort(key=lambda x: -x[1])
    return scored[:top_k]
