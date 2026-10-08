# 🔬 RagLens

**把 RAG 调参从玄学变成可复现实验**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-green.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-17%20passing-brightgreen.svg)](tests)
[![Local-first](https://img.shields.io/badge/运行-本地可跑-orange.svg)](config.example.yaml)

> English summary: RagLens is a lightweight, Chinese-friendly RAG debugging & evaluation console. It lets you run chunking-strategy experiments side by side, visualize retrieval hits per query, and score a golden QA set with HitRate@k / MRR — `pip install` and see results in 5 minutes, no API key required.

---

## 为什么做这个项目

做过 RAG 的人都懂那种感觉：换了 embedding 模型、把分片从 512 改成 256、加了个 overlap，到底是变好了还是变坏了？

**答案是说不清的。** 大多数团队的做法是：肉眼随机问几个问题，看一眼回答，然后"感觉好像还行"。于是切片策略靠拍脑袋、调参记录靠聊天框、半年后没人知道为什么当初选了这个配置。

RagLens 要做的事很简单：**固定其他条件，只换一个变量，把 HitRate / MRR 的差异摆在同一张表上**。一次实验产出一份单文件 HTML 报告，断网也能看，三个月后打开也不会烂尾。

## 它和 ragas / Langfuse 有什么区别

| | ragas | Langfuse | **RagLens** |
|---|---|---|---|
| 形态 | Python 评测库 | 自托管观测平台 | **单文件 HTML 报告的调试台** |
| 上手成本 | 要写代码 | 要部署服务 | **5 分钟出结果，零部署** |
| 切片对比 | 不直接支持 | 不直接支持 | **核心功能，多策略并排对比** |
| 中文样例 | 英文为主 | 英文为主 | **内置中文语料与黄金问答集** |
| 离线可用 | 部分 | 否 | **默认 local 嵌入器，无 Key 跑通** |

不是要替代它们：做生产级观测请选 Langfuse，写评测代码请用 ragas。**如果你只是想搞清楚"我的 RAG 到底哪里不行、改了有没有用"，先用 RagLens。**

## 一分钟快速开始

```bash
git clone https://github.com/<your-name>/raglens.git
cd raglens
pip install -r requirements.txt
raglens run --config config.example.yaml
# 或不安装：python3 -m rag_lens.cli run --config config.example.yaml
```

打开生成的 `report.html` 即可看到：

- **策略对比表**：不同切片策略的 HitRate@3 / HitRate@5 / MRR@5 / Faithfulness 并排对比
- **分片长度分布图**：每种策略切出来的分片到底多长，一眼看出有没有切歪
- **逐 query 明细**：每个问题召回了哪些分片、哪个命中了正确文档（绿色行）、是否命中目标片段（🎯），一眼看穿

**CI 集成**（评测不达标直接阻断发布）：

```bash
raglens run --config config.yaml --json report.json --min-hit-rate5 0.8
# 任一策略 HitRate@5 < 0.8 → 退出码 1，CI 变红
```

**两次实验对比**（改完配置后，直接看变好还是变坏）：

```bash
raglens compare --old before.yaml --new after.yaml --out compare.html
# ▲ 绿色=变好，▼ 红色=变差
```

> 默认使用内置的 local 哈希嵌入器——**不需要任何 API Key**，先让整条链路跑通。正式评测时在 `config.yaml` 里切到 `openai_compatible`（Ollama / DeepSeek / vLLM 均可），接真实 embedding 模型。

![报告示例（GIF 占位）](docs/screenshot-report.gif)
<!-- 首发前请替换为真实报告的动图：截取策略对比表 + 逐 query 命中高亮滚动过程，5~8 秒 -->

## 配置说明

复制 `config.example.yaml` 为 `config.yaml`，关键三段：

```yaml
data:
  docs_dir: "你的文档目录"          # .md / .txt
  golden_qa: "golden_qa.jsonl"     # query + expected_doc；可加 answer / expected_chunk_hint

chunker:
  strategies:                       # 想对比几种就写几种
    - { name: "fixed_256", type: "fixed", chunk_size: 256, overlap: 32 }
    - { name: "sentence",  type: "sentence", max_len: 300 }
    - { name: "md",        type: "markdown_heading", max_len: 300 }   # 按标题章节切

embedding:
  provider: "local"                 # 正式评测改 openai_compatible
  # base_url: "http://localhost:11434/v1"
  # model: "bge-m3"
  # api_key_env: "OPENAI_API_KEY"
```

golden_qa.jsonl 每行示例：

```json
{"query": "什么是 HitRate@k？", "expected_doc": "doc2.md",
 "answer": "HitRate@k 是正确文档出现在前 k 名的问题占比。",   // 可选：有 answer 才算 faithfulness
 "expected_chunk_hint": "正确文档出现在前 k 名"}               // 可选：报告里高亮具体片段
```

## 指标说明

- **HitRate@k**：正确文档出现在前 k 名的 query 占比。回答"找不找得到"。
- **MRR@5**：正确文档排名倒数的平均（第 1 名得 1 分，第 2 名得 0.5 分）。回答"排得够不够靠前"。

## 目录结构

```
raglens/
├── rag_lens/           # 核心库
│   ├── chunker.py      # 切片策略（fixed / sentence / markdown_heading）
│   ├── embeddings.py    # 嵌入器：local 降级 / OpenAI 兼容
│   ├── retriever.py     # 实验流水线
│   ├── metrics.py       # HitRate / MRR
│   ├── reranker.py      # 二阶段重排（local 词面重叠）
│   ├── judge.py         # faithfulness 裁判（mock / OpenAI 兼容）
│   └── report.py        # 单文件 HTML 报告（含 compare 对比报告）
├── data/sample_docs/   # 内置中文样例语料
├── data/golden_qa.jsonl
└── config.example.yaml
```

## 🎯 Good First Issue

欢迎第一次来贡献的朋友从这些入手（都是 1~3 小时量级）：

1. 给 `embeddings.py` 增加 `http` provider：直接 POST 到自托管 embedding 服务
2. 补一个 `raglens init` 命令：一键在当前目录生成 config.yaml + 样例数据
3. compare 报告里加"逐 query 变化明细"（哪个问题改好了/改差了）
4. 支持 PDF 文档加载（pdfminer.six，可选依赖）
5. 报告页加暗色模式（ prefers-color-scheme）

贡献前请先看 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 路线图

见 [ROADMAP.md](ROADMAP.md)。v0.2 已完成：markdown 标题切片、分片长度分布图、`--json` 导出与 CI 阈值阻断、`raglens compare` 双实验对比、expected_chunk_hint 片段高亮、faithfulness mock 裁判。下一步接真实 cross-encoder rerank。

## 开源协议

[MIT](LICENSE)。依赖仅 pyyaml（MIT），远程可选依赖 openai（Apache-2.0），无 copyleft 传染风险。

## 一句话推荐

> 如果你正在做 RAG，并且"效果到底好不好"还只能靠猜——先跑一次 RagLens。

⭐ 如果这个项目帮到了你，点个 star 让更多人看到。
