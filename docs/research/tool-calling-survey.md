# 工具调用方案调研（M5）

状态：**结论已按"优先采用开源实现"的人工指示落地**

日期：2026-09-04（所有来源访问日期均为当日）

## 要回答的问题

M5 最小工具调用，哪些部分有匹配的开源实现可以直接采用，哪些需要自建；许可证与依赖重量是否可接受。

## 发现

### 1. MiniMax Anthropic 兼容端点：原生支持工具（决定性前提）

来源：[platform.minimaxi.com text-anthropic-api](https://platform.minimaxi.com/docs/api-reference/text-anthropic-api)

- `tools`、`tool_choice`、`tool_use` 块、`tool_result` 块均标注"完全支持"；M3/M2.x 全系可用。
- **硬约束**：多轮工具调用必须完整回传 `response.content`（含 thinking/text/tool_use 所有块），thinking 块要原样保留，否则破坏思维链。
- `mcp_servers` 参数被静默忽略：该端点不支持服务端 MCP，未来 MCP 只能以"我们进程内跑客户端"的方式接入。
- 另见 [MiniMax-M3 issue #23](https://github.com/MiniMax-AI/MiniMax-M3/issues/23)：端点对部分内建工具（如 WebSearch）支持有缺口；M5 自定义工具不受影响。

### 2. anthropic Python SDK（已采用，MIT）

协议层实现：`tools` 参数、`tool_use`/`tool_result` 块、`stop_reason == "tool_use"` 判定都由 SDK 承担。这是"直接使用开源实现"的最大一块，M4 已引入。

### 3. MCP 官方 Python SDK（MIT，暂不采用）

来源：[modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk)

- 非常活跃（24.2k stars），v2 支持 2026-07-28 规范；装饰器工具 + 类型提示生成 schema + 自动校验，无需手写 JSON Schema。
- 但它是 client/server 形态且基于 asyncio；单进程内使用需要自定义 transport，为协议付异步与进程模型成本。
- **当前没有外部工具互通需求，其核心价值用不上**。结论：作为未来"外部工具来源"的边界保留，出现第一个真实 MCP 工具源时再引入。

### 4. pydantic-ai（MIT，不采用，留作替代）

来源：[pydantic/pydantic-ai](https://github.com/pydantic/pydantic-ai)；社区比较见 [Langfuse 框架对比](https://langfuse.com/blog/2025-03-19-ai-agent-comparison)

- Pydantic 官方团队的 Agent 框架，口碑好（"要类型安全和校验、不要重编排时的最强选择"）。
- 但采用它即意味着**让它拥有 Agent 主循环**，替换我们 ADR-0001 基线下自建的薄编排层（`agent.py`/`provider.py`）；也有社区反馈其工具调用提示质量的一般性问题。
- 结论：框架级决策，与当前已接受基线冲突；若未来薄层失控膨胀，作为整体迁移候选重新评估。

### 5. pydantic v2（MIT，本次采用）

来源：[pydantic/pydantic](https://github.com/pydantic/pydantic)

工具参数的 schema 生成（`model_json_schema()`）与校验（`model_validate()`）直接采用 pydantic——这正是 MCP SDK 与 pydantic-ai 底层使用的同一块积木，学习收益可迁移。新增依赖，纯库、无框架行为。

## 采用结论

| 层 | 选择 | 来源 |
|---|---|---|
| 协议（tools/块/stop_reason） | anthropic SDK（已有依赖） | 开源直接使用 |
| 参数 schema + 校验 | pydantic v2（新增依赖） | 开源直接使用 |
| 工具注册表 + 执行循环 | 自建（约百行） | 自建 |

循环自建的理由：它由端点约束塑造（thinking 块完整回传、`mcp_servers` 不可用），不是通用逻辑；也没有匹配该约束的现成微库。校验失败按惯例以错误字符串经 `tool_result` 回给模型自我纠正，而不是中断循环。

## 重新评估条件

- 出现第一个真实外部工具源 → 引入 MCP 官方 SDK 作为工具来源边界；
- `agent.py`/`provider.py` 膨胀失控或需要持久化状态图/暂停恢复 → 把 pydantic-ai 作为框架迁移候选评估；
- MiniMax 端点未来支持 `mcp_servers` → 重新比较服务端 MCP 与客户端 MCP。

## 许可证摘要

anthropic（MIT）、pydantic（MIT）、MCP Python SDK（MIT）、pydantic-ai（MIT）——均允许当前使用方式，无 SaaS/品牌限制。
