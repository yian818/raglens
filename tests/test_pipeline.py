import unittest

from rag_lens.config import load_config
from rag_lens.dataset import load_docs, load_golden_qa
from rag_lens.embeddings import build_embedder
from rag_lens.retriever import run_experiment


class TestPipeline(unittest.TestCase):
    """端到端：用内置样例数据跑完整实验，验证无 Key 链路可通。"""

    def test_end_to_end(self):
        cfg = load_config("config.example.yaml")
        docs = load_docs(cfg)
        qa = load_golden_qa(cfg)
        embedder = build_embedder(cfg)

        results = run_experiment(cfg, embedder, docs, qa)

        self.assertEqual(len(results), 3)  # 配置了 3 种切片策略
        for _, r in results.items():
            self.assertGreater(r["n_chunks"], 0)
            self.assertEqual(len(r["queries"]), len(qa))
            self.assertIn("hit_rate@5", r["aggregate"])
            self.assertIn("mrr@5", r["aggregate"])

    def test_rerank_enabled(self):
        cfg = load_config("config.example.yaml")
        cfg["rerank"]["enabled"] = True
        docs = load_docs(cfg)
        qa = load_golden_qa(cfg)
        embedder = build_embedder(cfg)
        results = run_experiment(cfg, embedder, docs, qa)
        self.assertIn("fixed_256", results)


if __name__ == "__main__":
    unittest.main()
