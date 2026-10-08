"""RAG 检索评测指标。

只做文档级判定：召回的 top-k 里是否包含"正确文档"。
这是评测台里最基础、最可复现的一层——先把这层做扎实，再谈 answer 层指标。
"""

from typing import Dict, List


def hit_rate_at_k(doc_ids: List[str], expected_doc: str, k: int) -> float:
    """top-k 中是否出现了正确文档（0/1）。"""
    return 1.0 if expected_doc in doc_ids[:k] else 0.0


def reciprocal_rank(doc_ids: List[str], expected_doc: str, k: int) -> float:
    """第一个正确文档排名的倒数（排在第 1 名得 1 分，第 2 名得 0.5 分，依次类推）。"""
    for rank, doc in enumerate(doc_ids[:k], start=1):
        if doc == expected_doc:
            return 1.0 / rank
    return 0.0


def aggregate(per_query: List[Dict], top_k: int) -> Dict[str, float]:
    """对一批 query 求平均，输出报表用的汇总指标。"""
    n = len(per_query) or 1
    return {
        "hit_rate@3": round(sum(q["hit_at_3"] for q in per_query) / n, 4),
        "hit_rate@5": round(sum(q["hit_at_5"] for q in per_query) / n, 4),
        "mrr@%d" % min(5, top_k): round(sum(q["rr_at_5"] for q in per_query) / n, 4),
    }
