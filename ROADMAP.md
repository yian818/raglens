# 路线图

## v0.1.0（已发布）— 最小可用
- [x] 三种切片策略对比：fixed 定长 / sentence 句子贪心
- [x] 黄金问答集评测：HitRate@3 / HitRate@5 / MRR@5
- [x] 逐 query 召回可视化（单文件 HTML 报告）
- [x] local 嵌入器降级：无 API Key 跑通全流程
- [x] OpenAI 兼容 embedding 接入（Ollama / DeepSeek / vLLM）
- [x] 内置中文样例语料 + 6 条黄金问答
- [x] 可选 local_lexical 二阶段重排演示

## v0.2（下一步）— 答案层与可对比性
- [ ] markdown_heading 切片策略
- [ ] faithfulness 答案层评测（LLM-as-judge，OpenAI 兼容）
- [ ] 报告增加分片长度分布直方图
- [ ] `raglens compare a.yaml b.yaml`：两次实验结果并排对比，直接看出"改配置后变好还是变坏"
- [ ] golden_qa 支持 expected_chunk_hint，命中片段高亮

## v0.3 — 生态接入
- [ ] 导出 JSON 报告，对接 CI（阈值不达标即失败）
- [ ] 接入真实 cross-encoder rerank 模型（bge-reranker）
- [ ] 常用 embedding 提供商一键切换 preset（bge-m3 / m3e / bge-large-zh）
- [ ] awesome-rag / awesome-llmops 收录

## v1.0
- [ ] Web 交互调试台（本地起服务，浏览器里改切片参数即时重跑）
- [ ] 评测数据集版本管理
- [ ] 1000+ chunk 语料性能优化（上 FAISS，可选依赖）
