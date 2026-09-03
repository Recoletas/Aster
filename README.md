# Aster

Aster 是一个由两人共同演进的智能体客服学习项目。项目希望逐步验证智能对话、知识检索、工具调用、消息渠道和人工客服之间的边界，而不是一次搭建完整平台。

## 当前状态

**M1–M3 已完成**：核心消息边界、最小对话应用层和会话持久化。

当前已有：

- 可运行的最小纵向链路：Console JSON line → 规范消息 → 会话状态 → 确定性回复 → Console 输出；
- 每会话内存状态与轮次回复，会话之间隔离（M2）；
- 单 JSON 文件持久化、重启恢复、重复投递幂等（M3，`--store`）；
- 11 个标准库测试；无第三方依赖。

当前没有：

- LLM、RAG、MCP、Web API；
- 真实消息渠道、自动化或工单实现；
- 数据库（持久化是可逆的 JSON 文件实验）与部署方案。

## 运行

需要 Python 3.11+，仅使用标准库：

```bash
printf '%s\n' '{"room":"room-7","event":"msg-42","user":"alice","body":"hello"}' | python3 -m aster.console
# {"room":"room-7","reply_to":"msg-42","body":"echo #1: hello"}

# 同一会话连续消息：echo #1、echo #2
printf '%s\n%s\n' '{"room":"r","event":"m1","user":"a","body":"hi"}' '{"room":"r","event":"m2","user":"a","body":"again"}' | python3 -m aster.console

# 会话跨进程持久化：第二次运行从 data/sessions.json 恢复，输出 echo #2
printf '%s\n' '{"room":"r","event":"m1","user":"a","body":"hi"}' | python3 -m aster.console --store data/sessions.json
printf '%s\n' '{"room":"r","event":"m2","user":"a","body":"back"}' | python3 -m aster.console --store data/sessions.json

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
