# Aster 当前计划

## 当前阶段

M1–M3 均已完成（2026-09-04）。人工验收经用户授权跳过；下一步方向等待人工决定。

## 已完成里程碑

### M1 核心消息边界（M1-A 设计 + M1-B 实现）

- 契约：`ConversationRef` + `IncomingMessage`/`Reply`（text-only），见 `docs/architecture/m1-message-contract.md`。
- 实现：Console JSON line 边界校验 → 规范消息 → 确定性 Core → Console 输出；Core 不依赖渠道。
- 状态：已完成；Git 基线提交 `b5b64e5`。

### M2 最小 Agent 对话链路

- 目标：会话级内存状态 + 依赖轮次的回复，会话之间隔离。
- 实现：`aster/agent.py`（`ConversationSession`/`SessionStore`）、`aster/core.py`（turn 参数）、`aster/console.py`（多行输入共享 store）。
- 已知代价：策略演示输出由 `echo: text` 演进为 `echo #n: text`；消息契约字段不变。
- 状态：已完成；8 个标准库测试通过。提交 `d40f8da`。

### M3 会话持久化

- 目标：会话状态落盘并在重启后恢复；重复投递最小幂等。
- 实现：`aster/storage.py`（单 JSON 文件、临时文件 + `os.replace` 原子替换）、`aster/agent.py`（外部消息 id → 轮次映射，重复 id 返回既有轮次）、`aster/console.py`（`--store PATH`）。
- 已知代价：只持久化会话状态（非审计历史）；无并发/锁；损坏文件大声失败。
- 状态：已完成；11 个标准库测试通过，真实子进程重启演示通过。

## 已接受决策

- Python 模块化单体作为当前可逆实验基线（ADR-0001）。
- M1 使用进程内 Fake/Console Adapter；Core 不依赖具体平台 SDK。
- 当前不建设动态插件发现、独立插件进程、HTTP/WS 插件协议、插件市场或第三方插件 SDK。
- 多租户 SaaS 保持开放，但当前不引入租户系统、权限平台或复杂基础设施。
- M3 以单个 JSON 文件作为首个持久化实验；这是可逆默认值，数据库选型仍开放。

## 开放问题

- Aster 是否最终面向多租户 SaaS 或再分发产品？当前不要求回答。
- LLM provider 选择与 API key 提供，是真实模型对话的前置条件。

## 下一道人工确认门

M1–M3 已完成并停止。下一方向需要人工决定，例如：接入真实 LLM provider（需 API key 与 provider 选择）、会话历史的数据库化、或首个真实消息渠道。未获明确授权前不得自行引入。
