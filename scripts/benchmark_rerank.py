#!/usr/bin/env python3
"""bge-reranker 真重排基准：同一份语料和黄金问答集，对比"向量检索" vs "向量+重排"。

前置条件：
    pip install raglens[rerank]   # sentence-transformers + torch
    配置里 embedding 用真实模型（如 preset: bge-m3），别用 local 演示件

用法：
    python scripts/benchmark_rerank.py config.yaml

产出：终端一张对比表（HitRate@k / MRR 提升了多少）。
这个脚本不生成 HTML——它回答的就是一个问题："上重排到底值不值？"
"""

import copy
import sys
import pathlib

# 允许从仓库根目录直接 `python scripts/benchmark_rerank.py ...` 运行
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from rag_lens.config import load_config
from rag_lens.dataset import load_docs, load_golden_qa
from rag_lens.embeddings import build_embedder
from rag_lens.retriever import run_experiment


def main() -> int:
    if len(sys.argv) != 2:
        print("用法: python scripts/benchmark_rerank.py config.yaml")
        return 1
    cfg = load_config(sys.argv[1])
    if cfg["embedding"].get("provider", "local") == "local":
        print("⚠️  警告：当前是 local 哈希嵌入器，基准数字没有业务意义。")
        print("    正式基准请在 config 里配真实 embedding（preset: bge-m3）。")

    docs = load_docs(cfg)
    qa = load_golden_qa(cfg)
    embedder = build_embedder(cfg)

    # 实验 A：不重排
    cfg_off = copy.deepcopy(cfg)
    cfg_off["rerank"]["enabled"] = False
    res_off = run_experiment(cfg_off, embedder, docs, qa)

    # 实验 B：开重排（默认 local_lexical；配置里改成 hf_cross_encoder 即真模型）
    cfg_on = copy.deepcopy(cfg)
    cfg_on["rerank"]["enabled"] = True
    res_on = run_experiment(cfg_on, embedder, docs, qa)

    rerank_name = cfg["rerank"].get("provider", "local_lexical")
    print(f"\n=== 重排基准：rerank={rerank_name} ===")
    print(f"{'策略':<16}{'模式':<10}{'Hit@5':>10}{'MRR@5':>10}")
    for name in res_off:
        a = res_off[name]["aggregate"]
        b = res_on[name]["aggregate"]
        print(f"{name:<16}{'无重排':<10}{a['hit_rate@5']:>10.2f}{a['mrr@5']:>10.2f}")
        print(f"{'':<16}{'加重排':<10}{b['hit_rate@5']:>10.2f}{b['mrr@5']:>10.2f}")
        d_hit = b["hit_rate@5"] - a["hit_rate@5"]
        d_mrr = b["mrr@5"] - a["mrr@5"]
        verdict = "✅ 值得" if d_hit + d_mrr > 0 else "➖ 无收益"
        print(f"{'':<16}{'变化':<10}{d_hit:>+10.2f}{d_mrr:>+10.2f}   {verdict}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
