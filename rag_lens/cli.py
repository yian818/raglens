"""RagLens 命令行入口。

用法：
    raglens run --config config.example.yaml
    python -m rag_lens.cli run --config config.example.yaml
"""

import argparse
import sys
from pathlib import Path

from .config import load_config, resolve_path
from .dataset import load_docs, load_golden_qa
from .embeddings import build_embedder
from .report import render_html
from .retriever import run_experiment


def cmd_run(args) -> int:
    cfg = load_config(args.config)
    docs = load_docs(cfg)
    golden_qa = load_golden_qa(cfg)
    embedder = build_embedder(cfg)

    provider = cfg["embedding"].get("provider", "local")
    embedder_note = "local（演示用哈希向量，非真实语义）" if provider == "local" else f"openai_compatible:{cfg['embedding'].get('model', '')}"

    print(f"[RagLens] 载入文档 {len(docs)} 篇，黄金问答 {len(golden_qa)} 条")
    results = run_experiment(cfg, embedder, docs, golden_qa)

    # 终端打印汇总
    print("\n=== 策略对比汇总 ===")
    print(f"{'策略':<16}{'分片数':>8}{'Hit@3':>10}{'Hit@5':>10}{'MRR@5':>10}")
    for name, r in results.items():
        agg = r["aggregate"]
        print(f"{name:<16}{r['n_chunks']:>8}{agg['hit_rate@3']:>10.2f}{agg['hit_rate@5']:>10.2f}{agg['mrr@5']:>10.2f}")

    out = args.out or cfg["experiment"].get("output", "report.html")
    html_text = render_html(cfg["experiment"]["name"], cfg, results, embedder_note)
    Path(out).write_text(html_text, encoding="utf-8")
    print(f"\n[RagLens] 报告已生成: {resolve_path(cfg, out)}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="raglens", description="把 RAG 调参从玄学变成可复现实验")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="跑一次评测实验并生成 HTML 报告")
    p_run.add_argument("--config", required=True, help="YAML 配置文件路径")
    p_run.add_argument("--out", default=None, help="报告输出路径（默认取配置里的 output）")
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
