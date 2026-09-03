# Aster 当前计划

## 当前阶段

M1：核心消息边界实验。

## 当前里程碑

M1-B：实现已接受的核心消息契约与进程内 Fake/Console 纵向链路。状态：已完成，等待人工验收。

### 目标

- 把 Console/Fake 原始输入转换为经过校验的规范 `IncomingMessage`。
- 用确定性 Core 生成 `Reply`，再转换为 Console/Fake 输出到 stdout。
- 用最少标准库测试证明关键契约和完整链路。

### 范围

- `ConversationRef`、`IncomingMessage` 和 `Reply` 三个不可变值对象；
- Console/Fake JSON line 的直接校验、入站和出站转换；
- 确定性 echo Core；
- 3～6 个标准库 `unittest` 测试。

### 非目标

- LLM、RAG、MCP、数据库、Web API、async、MQ、Docker；
- 真实渠道、动态插件、进程外协议、用户/工单/自动化。
- ABC、Protocol、Manager/Registry/Factory、依赖注入、配置系统和第三方依赖。

### 验收标准

- [x] 示例 JSON 完成 Console → Core → Console 的实际演示；
- [x] 边界拒绝缺失、类型错误和空白必要字段，并指出字段；
- [x] 测试证明合法转换、非法输入不进入 Core、确定性 Reply、出站转换和完整链路；
- [x] Core 不导入 Console 或任何渠道专有类型；
- [x] 标准库测试、语法/导入检查和可用的 diff 替代审阅完成；
- [x] 更新 M1-B 的最终 DEVLOG 记录并停止。

## 已接受决策

- Python 模块化单体作为当前可逆实验基线。
- M1 使用进程内 Fake/Console Adapter；Core 不依赖具体平台 SDK。
- 当前不建设动态插件发现、独立插件进程、HTTP/WS 插件协议、插件市场或第三方插件 SDK。
- 多租户 SaaS 保持开放，但当前不引入租户系统、权限平台或复杂基础设施。

详见 `docs/adr/0001-experimental-baseline.md`。

## M1-B 实现范围

- 目标：按已确认契约实现 Fake/Console → 规范消息 → 确定性 Core → Reply → Console 输出。
- 实现文件：`aster/messages.py`、`aster/core.py`、`aster/console.py`、`tests/test_message_flow.py`；不为目录填充空占位文件。
- 非目标：与 M1 总非目标相同。
- 验收：运行 `python -m aster.console` 完成一条 JSON line 演示；运行标准库 `unittest` 验证关键契约；Core 不导入 Console Adapter。

## 调整后的后续路线（未授权）

1. M1：核心消息边界。
2. M2：最小 Agent 对话链路。
3. M3：会话持久化。

进程外 Channel Adapter 不在固定 Roadmap；只有 SDK/语言冲突、崩溃隔离、独立升级/扩缩容或非可信第三方代码出现时才重新研究。

## 开放问题

- Aster 是否最终面向多租户 SaaS 或再分发产品？当前不要求回答。

## 下一道人工确认门

完成 M1-B 验收后停止，由人工决定是否进入 M2；不得自行设计或实现 M2。
