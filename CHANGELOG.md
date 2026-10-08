# 更新日志

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/) 格式。

## [0.3.0] - 2026-10-08

### Added
- embedding 一键预设：`preset: bge-m3 / bge-large-zh / m3e / openai`，自动填 base_url/model，显式配置仍可覆盖
- 可插拔重排后端：`rerank.provider: local_lexical | hf_cross_encoder`，后者接 bge-reranker（可选依赖 `raglens[rerank]`）
- PDF 文档加载（可选依赖 pdfminer.six；未安装时给出明确安装提示而非崩溃）
- `raglens compare` 报告新增逐 query 变化明细：哪个问题改好了（↑）、哪个改差了（↓）
- 测试 17 → 21，覆盖预设展开、PDF 优雅降级、hf 依赖提示、对比明细

## [0.2.0] - 2026-10-08

### Added
- `markdown_heading` 切片策略：按 Markdown 标题章节切分，超长章节按句子二次切分并保留标题
- faithfulness 答案层评测：mock 词面裁判 + OpenAI 兼容 LLM 裁判（judge.py）
- 报告新增分片长度分布直方图（纯 inline SVG，无外部依赖）
- `expected_chunk_hint`：命中目标片段时在报告里 🎯 高亮
- `raglens compare --old a.yaml --new b.yaml`：两次实验并排对比报告（▲ 变好 / ▼ 变差）
- `--json` 导出机器可读报告，`--min-hit-rate5` CI 阈值模式（不达标退出码 1）

### Changed
- 汇总表新增 Faithfulness 列（黄金问答集提供 answer 时计算）
- 样例数据集升级：4 种切片策略对比，2 条带 answer、3 条带片段提示

## [0.1.0] - 2026-10-08

### Added
- 三种切片策略并排对比（fixed 256 / fixed 512 / sentence）
- 黄金问答集评测：HitRate@3、HitRate@5、MRR@5
- 单文件离线 HTML 实验报告（逐 query 命中明细可视化）
- local 哈希嵌入器：零依赖、零 API Key 跑通全流程
- OpenAI 兼容 embedding 接入（Ollama / DeepSeek / vLLM）
- local_lexical 二阶段重排演示开关
- 内置 2 篇中文样例文档 + 6 条黄金问答集
- 11 个单元测试，覆盖切片、指标与端到端流水线
