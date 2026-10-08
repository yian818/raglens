import json
import os
import tempfile
import unittest
from pathlib import Path

from rag_lens.cli import main as cli_main
from rag_lens.config import load_config
from rag_lens.dataset import load_docs, load_golden_qa
from rag_lens.embeddings import apply_presets, build_embedder
from rag_lens.report import render_compare_html
from rag_lens.retriever import run_experiment
from rag_lens.reranker import rerank_candidates


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

    def test_embedding_preset(self):
        cfg = apply_presets({"preset": "bge-m3"})
        self.assertEqual(cfg["provider"], "openai_compatible")
        self.assertEqual(cfg["model"], "bge-m3")
        # 显式字段覆盖预设
        cfg2 = apply_presets({"preset": "bge-m3", "model": "my-own-model"})
        self.assertEqual(cfg2["model"], "my-own-model")
        # 未知 preset 明确报错
        with self.assertRaises(ValueError):
            apply_presets({"preset": "nope-not-a-model"})

    def test_pdf_graceful_error(self):
        # 强制模拟"未安装 pdfminer.six"环境，验证友好报错文案
        import sys
        saved = sys.modules.get("pdfminer")
        sys.modules["pdfminer"] = None
        try:
            with tempfile.TemporaryDirectory() as td:
                (Path(td) / "blank.pdf").write_bytes(b"%PDF-1.4 fake")
                cfg = load_config("config.example.yaml")
                cfg["data"]["docs_dir"] = td
                with self.assertRaises(RuntimeError) as ctx:
                    load_docs(cfg)
                self.assertIn("pdfminer", str(ctx.exception))
        finally:
            sys.modules["pdfminer"] = saved

    def test_hf_rerank_missing_dep_message(self):
        from rag_lens.chunker import Chunk
        fake = [(Chunk("d", "x", 0, "任意文本"), 0.5)]
        cfg = {"rerank": {"enabled": True, "provider": "hf_cross_encoder"}}
        with self.assertRaises(RuntimeError) as ctx:
            rerank_candidates("任意问题", fake, 5, cfg=cfg)
        self.assertIn("sentence-transformers", str(ctx.exception))

    def test_compare_per_query_detail(self):
        agg = {"hit_rate@3": 1.0, "hit_rate@5": 1.0, "mrr@5": 1.0}
        left = {"s1": {"aggregate": agg, "queries": [
            {"query": "Q1", "hit_at_5": 1.0, "rr_at_5": 1.0},
            {"query": "Q2", "hit_at_5": 0.0, "rr_at_5": 0.0},
        ]}}
        right = {"s1": {"aggregate": agg, "queries": [
            {"query": "Q1", "hit_at_5": 1.0, "rr_at_5": 1.0},
            {"query": "Q2", "hit_at_5": 1.0, "rr_at_5": 0.5},
        ]}}
        html = render_compare_html("old", left, "new", right)
        self.assertIn("改好了", html)
        self.assertIn("Q2", html)

    def test_init_scaffold(self):
        import os as _os
        cwd = _os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as td:
                _os.chdir(td)
                self.assertEqual(cli_main(["init"]), 0)
                self.assertTrue((Path(td) / "config.yaml").exists())
                self.assertTrue((Path(td) / "docs" / "doc1.md").exists())
                self.assertTrue((Path(td) / "golden_qa.jsonl").exists())
                # 二次运行不覆盖已有文件
                old_cfg = (Path(td) / "config.yaml").read_text(encoding="utf-8")
                self.assertEqual(cli_main(["init"]), 0)
                self.assertEqual(
                    (Path(td) / "config.yaml").read_text(encoding="utf-8"), old_cfg
                )
        finally:
            _os.chdir(cwd)

    def test_report_dark_mode(self):
        from rag_lens.report import render_html
        cfg = load_config("config.example.yaml")
        docs = load_docs(cfg)
        qa = load_golden_qa(cfg)
        results = run_experiment(cfg, build_embedder(cfg), docs, qa)
        html_text = render_html("t", cfg, results, "n")
        self.assertIn("prefers-color-scheme: dark", html_text)


if __name__ == "__main__":
    unittest.main()
