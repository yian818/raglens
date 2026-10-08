"""RagLens 命令行入口。

用法：
    raglens init                          # 在当前目录脚手架化你的项目
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


_INIT_CONFIG = """# RagLens 项目配置（由 raglens init 生成）
experiment:
  name: "我的第一次评测"
  output: "report.html"

data:
  docs_dir: "docs"                   # 把你的 .md/.txt/.pdf 文档放这里
  golden_qa: "golden_qa.jsonl"      # 黄金问答集：先照着样例写 5~10 条

chunker:
  strategies:
    - { name: "fixed_256", type: "fixed", chunk_size: 256, overlap: 32 }
    - { name: "sentence", type: "sentence", max_len: 300 }

embedding:
  provider: "local"                  # 先 local 跑通；有 Ollama 后改成 preset: "bge-m3"

retrieval:
  top_k: 5

rerank:
  enabled: false
  provider: "local_lexical"
"""

_INIT_DOC = """# 我的知识文档 1

把你的业务文档（产品手册、工单历史、FAQ……）复制到 docs/ 目录。
RagLens 会对它们切片、建索引，然后用黄金问答集去考它。
"""

_INIT_QA = """{"query": "示例问题：你的产品怎么退款？", "expected_doc": "doc1.md"}
"""


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


def cmd_init(args) -> int:
    """在当前目录生成 config.yaml + docs/ + golden_qa.jsonl，已有文件不覆盖。"""
    cwd = Path.cwd()
    made = []

    cfg_path = cwd / "config.yaml"
    if cfg_path.exists():
        print("· config.yaml 已存在，跳过（不覆盖）")
    else:
        cfg_path.write_text(_INIT_CONFIG, encoding="utf-8")
        made.append("config.yaml")

    docs_dir = cwd / "docs"
    docs_dir.mkdir(exist_ok=True)
    doc1 = docs_dir / "doc1.md"
    if doc1.exists():
        print("· docs/doc1.md 已存在，跳过")
    else:
        doc1.write_text(_INIT_DOC, encoding="utf-8")
        made.append("docs/doc1.md")

    qa_path = cwd / "golden_qa.jsonl"
    if qa_path.exists():
        print("· golden_qa.jsonl 已存在，跳过（不覆盖）")
    else:
        qa_path.write_text(_INIT_QA, encoding="utf-8")
        made.append("golden_qa.jsonl")

    print("[RagLens] 已生成: " + ", ".join(made) if made else "[RagLens] 无需生成（文件都在）")
    print("\n下一步：")
    print("  1. 把你的文档放进 docs/")
    print("  2. 照着样例编辑 golden_qa.jsonl（写 5~10 条真实问题）")
    print("  3. raglens run --config config.yaml")
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

    p_init = sub.add_parser("init", help="在当前目录脚手架化：生成 config.yaml + docs/ + golden_qa.jsonl")
    p_init.set_defaults(func=cmd_init)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
