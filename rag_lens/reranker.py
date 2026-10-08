"""二阶段重排（rerank）。

默认只提供 local_lexical：字符 bigram 重叠度。它不是 cross-encoder，
价值在于让你在没有重排模型时，也能量化"加上一步重排，结果变好了多少"。

正式评测可通过配置切换到 hf_cross_encoder（bge-reranker 等），
依赖 sentence-transformers + torch，按需安装：pip install raglens[rerank]。
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


class HFCrossEncoder:
    """HuggingFace cross-encoder 重排器（懒加载，未装依赖时给出明确提示）。"""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as e:
            raise RuntimeError(
                "cross-encoder 重排需要额外依赖：\n"
                "  pip install raglens[rerank]\n"
                "（即 sentence-transformers + torch；local_lexical 不需要它）"
            ) from e
        self.model = CrossEncoder(model_name)
        self.model_name = model_name

    def score(self, query: str, text: str) -> float:
        return float(self.model.predict([(query, text)])[0])


def rerank_candidates(
    query: str,
    candidates: List[Tuple[Chunk, float]],
    top_k: int,
    cfg: dict = None,
) -> List[Tuple[Chunk, float]]:
    """按配置选择重排后端，重排后取 top_k。

    cfg["rerank"]["provider"]:
      - local_lexical（默认）：向量分与词面重叠分等权融合，零依赖
      - hf_cross_encoder：真 cross-encoder 打分，配置 model 指定模型名
    """
    rcfg = (cfg or {}).get("rerank", {})
    provider = rcfg.get("provider", "local_lexical")

    if provider == "hf_cross_encoder":
        model = HFCrossEncoder(rcfg.get("model", "cross-encoder/ms-marco-MiniLM-L-6-v2"))
        scored = [(chunk, model.score(query, chunk.text)) for chunk, _ in candidates]
        scored.sort(key=lambda x: -x[1])
        return scored[:top_k]

    # local_lexical：把向量分（归一化到 0~1）与词面重叠分做等权融合
    scored = []
    for chunk, vec_score in candidates:
        vec_norm = max(0.0, min(1.0, (vec_score + 1.0) / 2.0))
        lex = lexical_overlap(query, chunk.text)
        fused = 0.5 * vec_norm + 0.5 * lex
        scored.append((chunk, round(fused, 4)))
    scored.sort(key=lambda x: -x[1])
    return scored[:top_k]
