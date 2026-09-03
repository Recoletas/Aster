# Aster 当前计划

## 当前阶段

M1–M4 均已完成（2026-09-04）。人工验收经用户授权跳过；后续方向等待人工选择。

## 已完成里程碑

### M1 核心消息边界（M1-A 设计 + M1-B 实现）

- 契约：`ConversationRef` + `IncomingMessage`/`Reply`（text-only），见 `docs/architecture/m1-message-contract.md`。
- 实现：Console JSON line 边界校验 → 规范消息 → 确定性 Core → Console 输出；Core 不依赖渠道。
- 状态：已完成；Git 基线提交 `b5b64e5`。

### M2 最小 Agent 对话链路

- 目标：会话级内存状态 + 依赖轮次的回复，会话之间隔离。
- 状态：已完成；提交 `d40f8da`。

### M3 会话持久化

- 目标：会话状态落盘并在重启后恢复；重复投递最小幂等。
- 实现：`aster/storage.py`（单 JSON 文件、原子替换）、重复 id 返回既有轮次、`--store PATH`。
- 状态：已完成；提交 `91c3f6d`。

### M4 最小 LLM 对话边界

- 目标：真实模型回复接入现有链路，会话历史作为上下文；provider 细节隔离在单一模块。
- 实现：`aster/provider.py`（MiniMax，Anthropic 兼容端点，`MINIMAX_API_KEY` 环境变量注入）；`agent.py` 历史改为 (role, text) 交替对、策略经构造参数注入（默认离线 echo）；`console.py --llm`（懒导入，离线用法无需 SDK）；`requirements.txt`（anthropic>=1.3.0，首个第三方依赖）。
- 已知代价：持久化格式从 `user_texts` 变更为交替 history，旧存储文件大声失败需重建；引入首个依赖。
- 关键发现：Python anthropic SDK 的 base_url 不得带 `/v1`（SDK 自行拼接 `/v1/messages`），与 openmaic 的 JS AI SDK 配置写法不同。
- 状态：已完成；15 个离线测试通过；真实三进程接力演示通过（跨进程记忆 + 会话隔离）。

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

M4 已完成并停止。后续候选需人工定优先级：流式输出、工具调用/MCP、RAG、首个真实消息渠道、会话历史数据库化。未获明确授权前不得自行开始。
