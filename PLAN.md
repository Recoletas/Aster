# Aster 当前计划

## 当前阶段

M1–M5 均已完成（2026-09-04）。人工验收经用户授权跳过；后续方向等待人工选择。

## 已完成里程碑

### M1 核心消息边界（M1-A 设计 + M1-B 实现）

- 契约：`ConversationRef` + `IncomingMessage`/`Reply`（text-only），见 `docs/architecture/m1-message-contract.md`。
- 状态：已完成；Git 基线提交 `b5b64e5`。

### M2 最小 Agent 对话链路

- 目标：会话级内存状态 + 依赖轮次的回复，会话之间隔离。
- 状态：已完成；提交 `d40f8da`。

### M3 会话持久化

- 目标：会话状态落盘并在重启后恢复；重复投递最小幂等。
- 状态：已完成；提交 `91c3f6d`。

### M4 最小 LLM 对话边界

- 实现：`aster/provider.py`（MiniMax，Anthropic 兼容端点，环境变量密钥）；策略注入接缝。
- 状态：已完成；提交 `d67d83f`。

### M5 最小工具调用

- 目标：模型能决定调用工具、参数经校验、结果回填生成最终回复，全程可审计。
- 实现：`aster/tools.py`（pydantic schema/校验 + 注册表 + 审计日志 + 内存工单假实现）；`provider.make_chat_reply` 工具循环（完整回传含 thinking 的 content）；console `--llm` 接注册表并把审计输出到 stderr；新增依赖 pydantic（方案依据见 `docs/research/tool-calling-survey.md`）。
- 关键发现：MiniMax 端点完整支持 tools，但 auto 模式下模型"是否调用工具"是非确定性的——三次演示中出现两次动作幻觉（声称建了工单但审计无记录），提示词强化只能降低不能消除；审计日志可当场检出此类不一致。
- 状态：已完成；25 个离线测试通过；真实三轮演示通过（含上述发现）。

## 已接受决策

- Python 模块化单体作为当前可逆实验基线（ADR-0001）。
- M1 使用进程内 Fake/Console Adapter；Core 不依赖具体平台 SDK。
- 当前不建设动态插件发现、独立插件进程、HTTP/WS 插件协议、插件市场或第三方插件 SDK。
- 多租户 SaaS 保持开放，但当前不引入租户系统、权限平台或复杂基础设施。
- M3 以单个 JSON 文件作为首个持久化实验；这是可逆默认值，数据库选型仍开放。

## 开放问题

- Aster 是否最终面向多租户 SaaS 或再分发产品？当前不要求回答。
- RAG 与工具调用是自建、用库还是对接外部平台（LLM provider 已定为 MiniMax 并接入）。

## 下一道人工确认门

M5 已完成并停止。后续候选需人工定优先级：工具调用可靠性策略（按意图强制 tool_choice / 结果对账）、RAG、流式输出、首个真实消息渠道、会话历史数据库化、MCP 客户端接入。未获明确授权前不得自行开始。
