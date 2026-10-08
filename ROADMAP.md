# 路线图

## v0.1.0（已发布）— 最小可用
- [x] 三种切片策略对比：fixed 定长 / sentence 句子贪心
- [x] 黄金问答集评测：HitRate@3 / HitRate@5 / MRR@5
- [x] 逐 query 召回可视化（单文件 HTML 报告）
- [x] local 嵌入器降级：无 API Key 跑通全流程
- [x] OpenAI 兼容 embedding 接入（Ollama / DeepSeek / vLLM）
- [x] 内置中文样例语料 + 6 条黄金问答
- [x] 可选 local_lexical 二阶段重排演示

## v0.2.0（已发布）— 答案层与可对比性
- [x] markdown_heading 切片策略（按 Markdown 标题章节切分）
- [x] faithfulness 答案层评测（mock 词面裁判 + OpenAI 兼容 LLM 裁判）
- [x] 报告增加分片长度分布直方图（纯 inline SVG）
- [x] `raglens compare`：两次实验并排对比，▲ 变好 / ▼ 变差
- [x] golden_qa 支持 expected_chunk_hint，命中片段 🎯 高亮
- [x] `--json` 导出机器可读报告，`--min-hit-rate5` CI 阈值阻断（不达标退出码 1）

## v0.3 — 生态接入
- [ ] 接入真实 cross-encoder rerank 模型（bge-reranker）
- [ ] 常用 embedding 提供商一键切换 preset（bge-m3 / m3e / bge-large-zh）
- [ ] compare 报告加逐 query 变化明细
- [ ] PDF 文档加载（pdfminer.six，可选依赖）
- [ ] awesome-rag / awesome-llmops 收录

## v1.0
- [ ] Web 交互调试台（本地起服务，浏览器里改切片参数即时重跑）
- [ ] 评测数据集版本管理
- [ ] 1000+ chunk 语料性能优化（上 FAISS，可选依赖）
