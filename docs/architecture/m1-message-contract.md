# M1 消息契约设计

状态：**已接受；M1-B 已按本契约实现**

目标链路：Fake/Console 输入 → Adapter 转换 → Aster 规范消息 → 确定性 Core → Aster Reply → Adapter 输出。

## 设计尺度

M1 只处理一条文本入站消息和一条直接回复。契约必须明确外部消息、会话和回复关系；不为尚未出现的多媒体、持久化、主动消息或插件协议预建通用模型。

## 候选 A：显式会话引用 + 成对消息

概念形状：

```text
ConversationRef(channel_id, external_conversation_id)
IncomingMessage(conversation, external_message_id, external_sender_id, text)
Reply(conversation, in_reply_to_external_message_id, text)
```

- 简洁程度：高。三个不可变值对象，没有基类、泛型或可选字段矩阵。
- 平台耦合：低。`channel_id` 标识 Aster 配置中的渠道实例；其余 ID 都是不透明字符串，不出现平台字段。
- 多媒体未来扩展：中。首版明确 text-only；出现第二种内容后可把 `text` 演进为类型化 `content`，会有一次显式契约变更。
- 请求/响应关系：强。`Reply.in_reply_to_external_message_id` 明确记录触发这条输出的外部消息；它不要求 Adapter 使用平台原生“引用回复”能力。
- 外部 message ID：强。字段命名说明它不是 Aster 内部 ID。
- conversation/thread：强。`(channel_id, external_conversation_id)` 共同确定会话，支持同一平台的多个渠道实例。M1 把渠道中可回复的 room/thread 映射为 `external_conversation_id`，不额外猜测一层 thread 模型。
- metadata 风险：低。首版没有通用 metadata；新跨渠道概念必须证明价值后成为一等字段。

## 候选 B：统一双向 Message

概念形状：

```text
Message(conversation, external_message_id?, sender_id?, direction,
        text, reply_to_external_message_id?)
```

- 简洁程度：表面只有一个类型，但可选字段和方向组合产生无效状态。
- 平台耦合：低。
- 多媒体未来扩展：中，与候选 A 相同。
- 请求/响应关系：中，依赖可选 `reply_to` 和方向规则。
- 外部 message ID：中，出站发送前通常没有平台 ID，字段被迫可选。
- conversation/thread：强，可复用同一会话引用。
- metadata 风险：低到中；虽然可以不加 metadata，但统一类型容易继续堆入站/出站专有字段。

## 候选 C：Envelope + 类型化 Content Parts

概念形状：

```text
MessageEnvelope(source, conversation, message_id, sender,
                parts=[TextPart | ImagePart | ...], reply_to?, metadata?)
```

- 简洁程度：低。首个 echo 链路就需要 envelope、part 联合类型和更多校验。
- 平台耦合：低；适配复杂平台能力较自然。
- 多媒体未来扩展：强，新内容可增加 part 类型。
- 请求/响应关系：中到强，取决于是否统一入站/出站及 `reply_to` 约束。
- 外部 message ID：强，但仍要处理出站发送前无平台 ID。
- conversation/thread：强，可表达更复杂 thread 层次。
- metadata 风险：高。缺少真实平台样本时，metadata 很容易成为无法治理的原始载荷垃圾桶。

## 推荐

推荐 **候选 A**，置信度中高。

它用一个共享 `ConversationRef` 解决路由和会话身份，用不同的 `IncomingMessage`/`Reply` 避免统一消息的无效状态，并明确保存当前链路真正需要的外部 ID。text-only 是有意限制：多媒体需求出现时进行一次小而可见的契约演进，比现在猜测 Content Parts 更容易理解和测试。

首版不加入：

- Aster 内部 message/conversation ID：M1 没有持久化或跨进程身份需求；
- timestamp：确定性 echo 不消费时间，Console 载荷也无需伪造；
- direction/type enum：成对类型已经表达方向；
- 通用 metadata 或完整 raw payload：渠道专有数据留在 Adapter；
- attachments/content parts：等首个真实多媒体用例；
- tenant/account/user profile：不为未知 SaaS 方向预建；
- protocol version/capabilities：当前不是进程外公共协议。

非法渠道输入不静默补默认值：缺少、类型错误或空白的必要字段由 Adapter 抛出带字段信息的 `ValueError`。Core 只接收已经合法的 `IncomingMessage`。

## M1-B 最少文件

M1-B 实际只新增：

- `aster/messages.py`：三个契约值对象，独立呈现 Core 与 Adapter 共享的稳定边界。
- `aster/core.py`：确定性 `handle_message`；不得导入 Console Adapter。
- `aster/console.py`：Fake/Console JSON line 的入站/出站转换与可运行入口。
- `tests/test_message_flow.py`：使用标准库 `unittest` 验证关键契约。

不创建空 `__init__.py`、PluginManager、Adapter 基类、工厂、配置系统或 `pyproject.toml`。Python 3.11 可将 `aster/` 作为 namespace package，通过 `python -m aster.console` 运行。

## 可执行验收例子

M1-B 预期演示命令：

```bash
printf '%s\n' '{"room":"room-7","event":"msg-42","user":"alice","body":"hello"}' | python -m aster.console
```

预期单行 JSON 输出（键顺序不作为契约）：

```json
{"room":"room-7","reply_to":"msg-42","body":"echo: hello"}
```

转换结果必须保留：

- `channel_id = "console"`
- `external_conversation_id = "room-7"`
- `external_message_id = "msg-42"`
- `external_sender_id = "alice"`
- Reply 的 `in_reply_to_external_message_id = "msg-42"`

必要测试：

1. 合法 Console 载荷可转为 `IncomingMessage`。
2. 会话、消息和发送者外部标识不丢失。
3. 缺少、空白或类型错误的必要字段产生明确 `ValueError`，不调用 Core。
4. `Reply` 正确转换为 Console 输出并保留 room/reply relationship。
5. `aster/core.py` 不导入 `aster.console`，Core 测试只使用规范契约字段。

`Reply` 继续只表达当前的直接回复；M1 不为未来主动通知增加 `OutboundMessage` 或 capability 系统。
