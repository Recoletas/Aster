# Aster

Aster 是一个由两人共同演进的智能体客服学习项目。项目希望逐步验证智能对话、知识检索、工具调用、消息渠道和人工客服之间的边界，而不是一次搭建完整平台。

## 当前状态

当前处于 **M2–M3：最小对话应用与会话持久化**。M1（核心消息边界）已完成。

当前已有：

- 可运行的最小纵向链路：Console JSON line → 规范消息 → 会话状态 → 确定性回复 → Console 输出；
- 每会话内存状态与轮次回复（M2）；
- 8 个标准库测试；无第三方依赖。

当前没有：

- 持久化（M3 进行中）、LLM、RAG、MCP、Web API；
- 真实消息渠道、自动化或工单实现；
- 已选定的数据库或部署方案。

## 运行

需要 Python 3.11+，仅使用标准库：

```bash
printf '%s\n' '{"room":"room-7","event":"msg-42","user":"alice","body":"hello"}' | python3 -m aster.console
# {"room":"room-7","reply_to":"msg-42","body":"echo #1: hello"}

printf '%s\n%s\n' '{"room":"r","event":"m1","user":"a","body":"hi"}' '{"room":"r","event":"m2","user":"a","body":"again"}' | python3 -m aster.console
# 同一会话连续两条消息：echo #1、echo #2

python3 -m unittest discover -s tests
```

## 文档入口

建议按以下顺序阅读：

1. [需求与约束](docs/requirements.md)
2. [架构调研](docs/research/architecture-survey.md)
3. [架构建议（部分已接受）](docs/architecture/architecture-proposal.md)
4. [M1 消息契约（已接受）](docs/architecture/m1-message-contract.md)
5. [已接受 ADR](docs/adr/0001-experimental-baseline.md)
6. [当前计划](PLAN.md)
7. [贡献指南](CONTRIBUTING.md)
8. [开发日志](DEVLOG.md)

Coding Agent 还必须先阅读 [AGENTS.md](AGENTS.md)。

## 参与方式

从 `PLAN.md` 中当前里程碑选择一项小任务；开始前写清目标、范围、非目标和验收标准，提交前执行适合该里程碑的最少验证并自审改动。详细流程见 `CONTRIBUTING.md`。

## 许可证

Aster 自身的许可证尚未决定。在许可证确认前，不要假设仓库内容可以被复制、分发或用于商业产品，也不要复制调研项目的代码。
