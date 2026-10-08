# 贡献指南

先感谢你愿意给 RagLens 提 issue 或 PR。这个项目的目标是"轻、快、可复现"，请在贡献时守住这三条：

## 三条底线

1. **不增加重型依赖**。新功能优先纯 Python 实现；确需第三方库时，先在 issue 里讨论为什么不能用标准库解决。
2. **无 Key 必须能跑通**。任何新功能都要有 local 降级路径或 mock，不能默认依赖外部 API。
3. **每个公开函数有 docstring**，关键决策在注释里写"为什么"，而不是"做了什么"。

## 提 PR 流程

1. 先开 issue 说明你要做什么（good first issue 列表见 README）；
2. Fork 后新建分支：`feat/xxx` 或 `fix/xxx`；
3. 保持 PR 小而聚焦——一次只做一件事；
4. 本地跑通 `python3 -m unittest discover -s tests` 且全部通过；
5. 更新 README 对应章节（如涉及用户可见行为）。

## 代码风格

- Python 3.9+ 语法，不引入类型检查器强依赖；
- 中文注释、中文面向用户文案；
- 报告 HTML 保持单文件、无外部 CDN 依赖。
