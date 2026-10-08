# 更新日志

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/) 格式。

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
