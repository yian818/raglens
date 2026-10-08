import json
import os
import unittest

from rag_lens.cli import main as cli_main
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

        self.assertEqual(len(results), 4)  # 配置了 4 种切片策略
        for _, r in results.items():
            self.assertGreater(r["n_chunks"], 0)
            self.assertEqual(len(r["queries"]), len(qa))
            self.assertIn("hit_rate@5", r["aggregate"])
            self.assertIn("mrr@5", r["aggregate"])
            self.assertIn("chunk_lengths", r)

        # 带 answer 的 query 应算出 faithfulness（mock 裁判）
        faiths = [q["faithfulness"] for q in results["fixed_256"]["queries"] if q["faithfulness"] is not None]
        self.assertGreater(len(faiths), 0)

        # expected_chunk_hint 应在召回项里产生 hint_hit
        any_hint = any(
            item.get("hint_hit")
            for q in results["fixed_256"]["queries"]
            for item in q["retrieved"]
        )
        self.assertTrue(any_hint)

    def test_rerank_enabled(self):
        cfg = load_config("config.example.yaml")
        cfg["rerank"]["enabled"] = True
        docs = load_docs(cfg)
        qa = load_golden_qa(cfg)
        embedder = build_embedder(cfg)
        results = run_experiment(cfg, embedder, docs, qa)
        self.assertIn("fixed_256", results)

    def test_cli_json_and_threshold(self):
        rc = cli_main([
            "run", "--config", "config.example.yaml",
            "--out", "/tmp/raglens_test_report.html",
            "--json", "/tmp/raglens_test_report.json",
        ])
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists("/tmp/raglens_test_report.json"))
        with open("/tmp/raglens_test_report.json", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("results", data)

    def test_cli_threshold_fails(self):
        # 要求 HitRate@5 达到 1.01，必然不满足 → 退出码 1（CI 阻断）
        rc = cli_main([
            "run", "--config", "config.example.yaml",
            "--out", "/tmp/raglens_test_report2.html",
            "--min-hit-rate5", "1.01",
        ])
        self.assertEqual(rc, 1)

    def test_cli_compare(self):
        rc = cli_main([
            "compare", "--old", "config.example.yaml",
            "--new", "config.example.yaml",
            "--out", "/tmp/raglens_compare.html",
        ])
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists("/tmp/raglens_compare.html"))


if __name__ == "__main__":
    unittest.main()
