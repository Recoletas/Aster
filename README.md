# Aster

Aster 是一个由两人共同演进的智能体客服学习项目。项目希望逐步验证智能对话、知识检索、工具调用、消息渠道和人工客服之间的边界，而不是一次搭建完整平台。

## 当前状态

**M1–M4 已完成**：核心消息边界、最小对话应用层、会话持久化和真实 LLM 对话（MiniMax）。

当前已有：

- 可运行的最小纵向链路：Console JSON line → 规范消息 → 会话状态 → 回复策略 → Console 输出；
- 每会话交替历史，会话之间隔离；
- 单 JSON 文件持久化、重启恢复、重复投递幂等（`--store`）；
- 真实 LLM 回复：MiniMax（Anthropic 兼容端点）；离线确定性 echo 是默认策略，`--llm` 切换；
- 15 个标准库测试（全部离线）。

当前没有：

- 流式输出、工具调用、RAG、MCP、Web API；
- 真实消息渠道、自动化或工单实现；
- 数据库（持久化是可逆的 JSON 文件实验）与部署方案。

## 运行

需要 Python 3.11+。离线模式仅用标准库；`--llm` 需要 `requirements.txt` 中的 `anthropic` SDK 和 `MINIMAX_API_KEY` 环境变量（密钥绝不入库）。第三方依赖一律装入项目本地 `.venv`，不要装进全局或 conda 环境：

```bash
printf '%s\n' '{"room":"room-7","event":"msg-42","user":"alice","body":"hello"}' | python3 -m aster.console
# {"room":"room-7","reply_to":"msg-42","body":"echo #1: hello"}

python3 -m unittest discover -s tests
# 离线全绿；未安装 SDK 时 provider 测试自动跳过

# 真实 LLM 模式
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
export MINIMAX_API_KEY=sk-...
printf '%s\n' '{"room":"r","event":"m1","user":"a","body":"你好"}' | .venv/bin/python -m aster.console --llm --store data/sessions.json
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
