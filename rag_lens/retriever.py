"""实验流水线：对每种切片策略建索引 -> 跑黄金问答集 -> 出逐 query 结果。

这是 RagLens 的"实验台"本体：同一份语料、同一组问题，只换切片策略，
结果差异一目了然，这就是"把调参变成可复现实验"。
"""

from typing import Dict, List

from .chunker import chunk_document
from .embeddings import cosine
from .judge import judge_faithfulness
from .metrics import aggregate
from .reranker import rerank_candidates


class Index:
    """内存向量索引：对小语料（几千 chunk）足够，O(n) 暴力检索。

    为什么不上 FAISS：RagLens 的定位是"调试台"，语料规模通常很小；
    少一个原生依赖就少一个环境坑，纯 Python 检索对 demo 场景足够快。
    """

    def __init__(self, chunks, vectors: List[List[float]]):
        self.chunks = chunks
        self.vectors = vectors

    def search(self, query_vec: List[float], top_k: int):
        scored = [
            (self.chunks[i], cosine(query_vec, self.vectors[i]))
            for i in range(len(self.chunks))
        ]
        scored.sort(key=lambda x: -x[1])
        return scored[:top_k]


def run_experiment(cfg: dict, embedder, docs: dict, golden_qa: list) -> Dict[str, dict]:
    top_k = int(cfg["retrieval"].get("top_k", 5))
    use_rerank = bool(cfg.get("rerank", {}).get("enabled"))
    results: Dict[str, dict] = {}

    for strategy in cfg["chunker"]["strategies"]:
        chunks = []
        for doc_id, text in docs.items():
            chunks.extend(chunk_document(doc_id, text, strategy))

        vectors = embedder.encode([c.text for c in chunks])
        index = Index(chunks, vectors)
        q_vectors = embedder.encode([qa["query"] for qa in golden_qa])

        query_records = []
        for qa, qvec in zip(golden_qa, q_vectors):
            hits = index.search(qvec, top_k)
            if use_rerank:
                hits = rerank_candidates(qa["query"], hits, top_k, cfg=cfg)

            doc_ids = [c.doc_id for c, _ in hits]
            expected = qa["expected_doc"]
            hint = qa.get("expected_chunk_hint")

            retrieved_items = []
            for c, score in hits:
                retrieved_items.append({
                    "doc": c.doc_id,
                    "score": round(score, 4),
                    "preview": c.text[:80],
                    "hint_hit": bool(hint and hint in c.text),
                })

            answer = qa.get("answer")
            faith = None
            if answer:
                faith = judge_faithfulness(
                    answer, [c.text for c, _ in hits], qa["query"], cfg
                )

            query_records.append({
                "query": qa["query"],
                "expected_doc": expected,
                "expected_chunk_hint": hint,
                "doc_ids": doc_ids,
                "hit_at_3": 1.0 if expected in doc_ids[:3] else 0.0,
                "hit_at_5": 1.0 if expected in doc_ids[:5] else 0.0,
                "rr_at_5": (1.0 / (doc_ids[:5].index(expected) + 1)) if expected in doc_ids[:5] else 0.0,
                "faithfulness": faith,
                "retrieved": retrieved_items,
            })

        results[strategy["name"]] = {
            "strategy": strategy,
            "n_chunks": len(chunks),
            "avg_chunk_len": round(sum(c.char_len for c in chunks) / (len(chunks) or 1), 1),
            "chunk_lengths": [c.char_len for c in chunks],
            "queries": query_records,
            "aggregate": aggregate(query_records, top_k),
        }
    return results
