# Aster 当前计划

## 当前阶段

M2–M3：最小对话应用与会话持久化。M1 已完成；人工验收经用户授权跳过（2026-09-04）。

## 已完成里程碑

### M1 核心消息边界（M1-A 设计 + M1-B 实现）

- 契约：`ConversationRef` + `IncomingMessage`/`Reply`（text-only），见 `docs/architecture/m1-message-contract.md`。
- 实现：Console JSON line 边界校验 → 规范消息 → 确定性 Core → Console 输出；Core 不依赖渠道。
- 状态：已完成；Git 基线提交 `b5b64e5`。

### M2 最小 Agent 对话链路

- 目标：会话级内存状态 + 依赖轮次的回复，会话之间隔离。
- 实现：`aster/agent.py`（`ConversationSession`/`SessionStore`）、`aster/core.py`（turn 参数）、`aster/console.py`（多行输入共享 store）。
- 已知代价：策略演示输出由 `echo: text` 演进为 `echo #n: text`；消息契约字段不变。
- 状态：已完成；8 个标准库测试通过。

## 当前里程碑

### M3 会话持久化

状态：进行中。

#### 目标

- 会话状态保存到 JSON 文件并在进程重启后恢复；
- 同一外部消息重复投递不重复计数、输出稳定（最小幂等）。

#### 范围

- `aster/storage.py`：`SessionStore` 与 JSON 文件互转，原子写入（临时文件 + `os.replace`）；
- `aster/agent.py`：会话记录外部消息 id 到轮次的映射，重复 id 返回既有轮次；
- `aster/console.py`：`--store PATH` 选项，启动时加载、逐行保存；
- 标准库测试：roundtrip、重复投递、跨进程重启续号。

#### 非目标

- 数据库、ORM、SQLite、并发/锁、加密；
- LLM/RAG/MCP、真实渠道、Web、async、MQ、Docker；
- 完整消息审计历史的持久化（当前只持久化会话状态）。

#### 验收标准

- [ ] save → load 后会话历史与轮次完全一致；
- [ ] 同一 external_message_id 重复投递：历史不变，回复文本与首次相同；
- [ ] 进程重启后继续既有轮次编号；
- [ ] 不带 `--store` 时行为与 M2 相同；
- [ ] 标准库测试全部通过；CLI 重启演示通过。

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

M3 完成后停止。接入真实 LLM provider 需要 API key 和 provider 决定，属人工事项，不得自行引入。
