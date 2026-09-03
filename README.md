# Aster

Aster 是一个由两人共同演进的智能体客服学习项目。项目希望逐步验证智能对话、知识检索、工具调用、消息渠道和人工客服之间的边界，而不是一次搭建完整平台。

## 当前状态

项目已完成 Phase 0，当前处于 **M1-A：核心消息边界设计**。M1-A 只产出设计，不包含业务实现。

当前已有：

- 已确认需求、非目标和关键不确定项；
- 基于官方资料的架构与许可证调研；
- 一份分级标注已接受与待确认内容的架构建议；
- 当前实验基线的首个已接受 ADR；
- 小步开发、记录和验收规则。

当前没有：

- 可运行的业务代码或启动命令；
- 已选定的后端框架、数据库或部署方案；
- 真实消息渠道、LLM、RAG、MCP、自动化或工单实现；
- 已接受的 ADR。

## 文档入口

建议按以下顺序阅读：

1. [需求与约束](docs/requirements.md)
2. [架构调研](docs/research/architecture-survey.md)
3. [架构建议（待确认）](docs/architecture/architecture-proposal.md)
4. [M1 消息契约设计（待确认）](docs/architecture/m1-message-contract.md)
5. [已接受 ADR](docs/adr/0001-experimental-baseline.md)
6. [当前计划](PLAN.md)
7. [贡献指南](CONTRIBUTING.md)
8. [开发日志](DEVLOG.md)

Coding Agent 还必须先阅读 [AGENTS.md](AGENTS.md)。

## 参与方式

从 `PLAN.md` 中当前里程碑选择一项小任务；开始前写清目标、范围、非目标和验收标准，提交前执行适合该里程碑的最少验证并自审改动。详细流程见 `CONTRIBUTING.md`。

## 许可证

Aster 自身的许可证尚未决定。在许可证确认前，不要假设仓库内容可以被复制、分发或用于商业产品，也不要复制调研项目的代码。
