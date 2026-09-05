# Aster

Aster 是一个由两人共同演进的智能体客服学习项目。项目希望逐步验证智能对话、知识检索、工具调用、消息渠道和人工客服之间的边界，而不是一次搭建完整平台。

## 当前状态

**M1–M12 已完成**：消息边界、对话应用层、持久化、真实 LLM、工具调用与对账、RAG（关键词 + MiniMax embedding）、Web 渠道、SQLite 存储、SSE 流式、MCP 工具源接入（面向 utopia）。

当前已有：

- 双渠道最小纵向链路：Console JSON line 与本地 Web 页面 → 规范消息 → 会话状态 → 回复策略 → 渠道输出；
- 每会话交替历史，会话之间隔离；
- SQLite 单文件持久化、重启恢复、重复投递幂等（`--store`）；
- 真实 LLM 回复：MiniMax（Anthropic 兼容端点）；离线确定性 echo 是默认策略，`--llm` 切换；
- 工具调用：pydantic 校验 + 注册表白名单 + 审计日志 + 声明-审计对账（虚构动作可检出并纠正），内置内存工单工具；
- RAG：`--knowledge` 本地 FAQ 注入上下文，`--kb-mode keyword|embedding` 两种检索（embedding 走 MiniMax embo-01，需密钥）；
- SSE 流式回复：Web `--stream` 模式（仅纯聊天路径，工具回复非流式）；
- 51 个标准库风格测试（全部离线）。

当前没有：

- 工具调用时机保证（模型自发决定 + 对账兜底）、工具回复的流式、MCP 客户端、鉴权；
- 真实消息渠道（QQ/企微/钉钉/飞书）、人工坐席、工单后端；
- 部署方案与 Web 框架（本地 stdlib HTTP）。

## 运行

需要 Python 3.11+。离线模式仅用标准库；`--llm` 需要 `pyproject.toml` 声明的 `anthropic` SDK 和 `MINIMAX_API_KEY` 环境变量（密钥绝不入库）。第三方依赖一律装入项目本地 `.venv`，不要装进全局或 conda 环境：

```bash
# 离线 Console 渠道
printf '%s\n' '{"room":"r","event":"m1","user":"a","body":"hello"}' | python3 -m aster.console
# {"room":"r","reply_to":"m1","body":"echo #1: hello"}

# LLM + 工具 + 知识库 + 持久化（Console）
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
export MINIMAX_API_KEY=sk-...
printf '%s\n' '{"room":"r","event":"m1","user":"a","body":"帮我建个工单：打印机坏了，优先级高"}' | .venv/bin/python -m aster.console --llm --knowledge examples/kb.json --kb-mode embedding --store data/sessions.db

# 经 MCP 挂载远程工具源（utopia 预演：本地知识库作为 MCP 服务器）
printf '%s\n' '{"room":"r","event":"m1","user":"a","body":"Aster 用什么数据库？"}' | .venv/bin/python -m aster.console --llm --mcp-command "python3 examples/kb_mcp_server.py"

# 本地 Web 渠道（浏览器打开 http://127.0.0.1:8000）
.venv/bin/python -m aster.web_channel --llm --stream --knowledge examples/kb.json --store data/sessions.db

make check   # = ruff lint + format 检查 + mypy + 全部测试（CI 同款）
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

协作走完整流程：**issue（用模板）→ 分支 → Conventional Commits → PR（逐条回应验收标准）→ owner 验收 → squash 合并**。不直接 push 到 `main`。分支命名、commit 类型、label 约定见 [CONTRIBUTING.md](CONTRIBUTING.md)；工程化入口：`make check`（提交前质量门）。详细流程见 `CONTRIBUTING.md`。

## 许可证

Aster 自身的许可证尚未决定。在许可证确认前，不要假设仓库内容可以被复制、分发或用于商业产品，也不要复制调研项目的代码。
