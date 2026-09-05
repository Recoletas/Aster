# Aster 当前计划

## 当前阶段

M1–M11 均已完成（2026-09-04）。人工验收经用户授权跳过；MCP 客户端按论证暂缓（见开放问题）。

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

### M6 工具调用对账

- 声明（claim_pattern）与审计（result_id_pattern）比对，虚构动作确定性检出并触发一轮纠正，对账事件入审计。提交 `54755e8`。

### M7 RAG 关键词基线

- CJK 二元组 + ASCII 词检索，命中条目注入 system；`examples/kb.json` 为真实 FAQ。提交 `1395548`。

### M11 embedding RAG（MiniMax embo-01）

- 人工指定 provider 为 MiniMax。`aster/embeddings.py`：非对称 db/query 协议（字段 `texts`，非 OpenAI 兼容），1536 维，stdlib urllib 零新依赖；`EmbeddingKnowledgeBase` 与关键词基线同接口，provider/策略零改动；CLI `--kb-mode keyword|embedding`。
- 关键发现：文档向量不持久化（小库启动时一次调用）；知识库内容随 M9 迁移过期（JSON→SQLite），检索质量再好也救不了过期内容——知识库需要随代码演进维护。

### M8 Web 渠道

- stdlib `ThreadingHTTPServer`（Web 框架决策继续推迟）+ 聊天页 + `/api/message`，与 Console 同一边界校验和会话语义；第二个 Adapter 未发现规范消息契约缺口。提交 `08c0b81`。

### M9 会话存储 SQLite 化

- stdlib `sqlite3` 单文件库接管原子性与写入锁；M3/M4 JSON 格式退役并大声失败。提交 `0bde7ad`。

### M10 流式输出

- SDK `messages.stream` + SSE（`/api/stream`）+ 流式页面；仅纯聊天路径（工具轮次与非文本块交错，工具回复保持非流式）；`stream_handle` 完成后落库、重复投递幂等。提交 `d226d58`。

## 已接受决策

- Python 模块化单体作为当前可逆实验基线（ADR-0001）。
- M1 使用进程内 Fake/Console Adapter；Core 不依赖具体平台 SDK。
- 当前不建设动态插件发现、独立插件进程、HTTP/WS 插件协议、插件市场或第三方插件 SDK。
- 多租户 SaaS 保持开放，但当前不引入租户系统、权限平台或复杂基础设施。
- M3 以单个 JSON 文件作为首个持久化实验；这是可逆默认值，数据库选型仍开放。

## 开放问题

- Aster 是否最终面向多租户 SaaS 或再分发产品？当前不要求回答。
- **MCP 客户端暂缓论证**：MCP 的价值在外部工具互通，当前 Aster 没有可对接的外部 MCP Server；官方 SDK 基于 asyncio，引入意味着进程模型转向。触发条件：出现第一个真实 MCP 工具源，或需要复用生态内现成工具时，再评估 client 接入（届时比较 asyncio 化与子进程桥接）。候选现实工具源：团队正在研究的 deeplethe/utopia（Apache-2.0 知识图谱平台，内置只读 MCP 工具）——若接入，Aster 定位为轻量渠道/Agent 前端，utopia 承担知识底座，两者互补而非重复。
- 工具调用时机仍依赖模型自发性（M6 对账可检出、可纠正）；意图级 tool_choice 强制需要意图分类层，等真实误判率数据再设计。

## 下一道人工确认门

M1–M11 已完成并停止。剩余方向全部需要人工输入或决策：真实消息渠道（需要平台账号/凭据）、意图分类层的引入时机、部署形态（含 Web 框架选型）、MCP 客户端（触发条件见开放问题）。未获明确授权前不得自行开始。
