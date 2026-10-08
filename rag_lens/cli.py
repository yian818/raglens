"""RagLens 命令行入口。

用法：
    raglens run --config config.example.yaml [--json out.json] [--min-hit-rate5 0.8]
    raglens compare --old before.yaml --new after.yaml --out compare.html
"""

import argparse
import json
import sys
from pathlib import Path

from .config import load_config, resolve_path
from .dataset import load_docs, load_golden_qa
from .embeddings import build_embedder
from .report import render_compare_html, render_html
from .retriever import run_experiment


def _note(cfg: dict) -> str:
    provider = cfg["embedding"].get("provider", "local")
    if provider == "local":
        return "local（演示用哈希向量，非真实语义）"
    return f"openai_compatible:{cfg['embedding'].get('model', '')}"


def _print_summary(results: dict):
    print("\n=== 策略对比汇总 ===")
    print(f"{'策略':<16}{'分片数':>8}{'Hit@3':>10}{'Hit@5':>10}{'MRR@5':>10}")
    for name, r in results.items():
        agg = r["aggregate"]
        print(f"{name:<16}{r['n_chunks']:>8}{agg['hit_rate@3']:>10.2f}{agg['hit_rate@5']:>10.2f}{agg['mrr@5']:>10.2f}")


def cmd_run(args) -> int:
    cfg = load_config(args.config)
    docs = load_docs(cfg)
    golden_qa = load_golden_qa(cfg)
    embedder = build_embedder(cfg)

    print(f"[RagLens] 载入文档 {len(docs)} 篇，黄金问答 {len(golden_qa)} 条")
    results = run_experiment(cfg, embedder, docs, golden_qa)
    _print_summary(results)

    out = args.out or cfg["experiment"].get("output", "report.html")
    html_text = render_html(cfg["experiment"]["name"], cfg, results, _note(cfg))
    Path(out).write_text(html_text, encoding="utf-8")
    print(f"\n[RagLens] 报告已生成: {resolve_path(cfg, out)}")

    if args.json:
        payload = {"experiment": cfg["experiment"]["name"], "results": results}
        Path(args.json).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[RagLens] JSON 已导出: {args.json}")

    # CI 阈值模式：任一策略不达标即非零退出
    if args.min_hit_rate5 is not None:
        failed = [n for n, r in results.items() if r["aggregate"]["hit_rate@5"] < args.min_hit_rate5]
        if failed:
            print(f"\n[RagLens] ❌ 未达标（HitRate@5 < {args.min_hit_rate5}）: {', '.join(failed)}")
            return 1
        print(f"\n[RagLens] ✅ HitRate@5 全部 ≥ {args.min_hit_rate5}")
    return 0


def cmd_compare(args) -> int:
    cfg_old = load_config(args.old)
    cfg_new = load_config(args.new)
    docs_old = load_docs(cfg_old)
    docs_new = load_docs(cfg_new)
    qa_old = load_golden_qa(cfg_old)
    qa_new = load_golden_qa(cfg_new)

    old_results = run_experiment(cfg_old, build_embedder(cfg_old), docs_old, qa_old)
    new_results = run_experiment(cfg_new, build_embedder(cfg_new), docs_new, qa_new)

    html_text = render_compare_html(
        cfg_old["experiment"]["name"], old_results,
        cfg_new["experiment"]["name"], new_results,
    )
    Path(args.out).write_text(html_text, encoding="utf-8")
    print(f"[RagLens] 对比报告已生成: {args.out}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="raglens", description="把 RAG 调参从玄学变成可复现实验")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="跑一次评测实验并生成 HTML 报告")
    p_run.add_argument("--config", required=True, help="YAML 配置文件路径")
    p_run.add_argument("--out", default=None, help="报告输出路径（默认取配置里的 output）")
    p_run.add_argument("--json", default=None, help="同时导出机器可读 JSON 报告（用于 CI）")
    p_run.add_argument("--min-hit-rate5", type=float, default=None,
                       help="CI 阈值：任一策略 HitRate@5 低于此值则退出码为 1")
    p_run.set_defaults(func=cmd_run)

    p_cmp = sub.add_parser("compare", help="对比两次配置的实验结果")
    p_cmp.add_argument("--old", required=True, help="改前配置 yaml")
    p_cmp.add_argument("--new", required=True, help="改后配置 yaml")
    p_cmp.add_argument("--out", default="compare.html", help="对比报告输出路径")
    p_cmp.set_defaults(func=cmd_compare)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
