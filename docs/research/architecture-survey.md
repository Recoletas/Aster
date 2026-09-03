# Phase 0 架构调研

状态：调研结论，非已接受决策。访问日期：**2026-09-03**。

## 调研问题与结论

### 1. 两人团队需要什么总体形态？

| 候选 | 优点 | 主要成本/风险 | Phase 1 判断 |
| --- | --- | --- | --- |
| 简单单体 | 最少概念和部署步骤 | 边界容易退化为大路由/大 Service | 可用于极短 spike，不宜作为长期描述 |
| 模块化单体 | 单进程开发，同时以代码依赖表达边界 | 需要持续约束模块方向，容易过度分层 | **优先候选** |
| 核心服务 + 外部适配器 | 平台 SDK、崩溃和升级隔离较好 | 本地联调、协议、日志和部署成本上升 | 渠道出现真实隔离证据后采用 |
| 多服务 | 独立扩缩容和故障域 | 两人团队承担协议、部署、可观测性和一致性成本 | 当前不建议 |

Chatwoot 把渠道汇入 inbox/conversation/message 语义，并允许 API Channel 与 webhook 对接自定义应用；这说明“统一领域模型 + 外部 HTTP 边界”可行，但其正式部署还需要 web、worker、PostgreSQL、Redis、邮件和对象存储，不适合照搬到 Aster 初期。来源：[Channel/Inbox 说明](https://www.chatwoot.com/hc/user-guide/articles/1677492191-adding-inboxes)、[AgentBot webhook 边界](https://www.chatwoot.com/hc/user-guide/articles/1677497472-how-to-use-agent-bots)、[生产架构](https://developers.chatwoot.com/self-hosted/deployment/architecture)。

### 2. 后端技术栈如何取舍？

| 候选 | 与当前团队/目标的匹配 | 风险 | 建议 |
| --- | --- | --- | --- |
| Python + 轻量 ASGI 框架 | 复用已有 Python/AI 经验；异步 webhook 与 AI 库生态直接 | 动态运行时、异步边界和类型纪律需主动管理 | **待确认首选**；框架在需要 HTTP 前再定 |
| Python + Django | ORM、管理后台和成熟业务生态强 | 在尚无后台/复杂数据模型时引入面较大 | 客服后台和关系模型成为近期核心时重评 |
| TypeScript/Node.js | webhook、实时通信、渠道 SDK 生态强，端到端类型体验好 | 团队切换语言；Python AI 组件需跨语言边界 | 平台 SDK 明显偏 Node 且隔离收益成立时用于外部适配器 |
| Go | 静态二进制、并发和资源占用可控 | 当前学习成本高，AI/RAG 生态连接更绕 | 不作为早期 Core 首选 |

结论依据主要是团队现有能力和目标，不以框架“先进性”评分。Phase 1 可先用纯 Python 验证消息边界，避免在尚不需要 HTTP 时提前锁定 FastAPI/Django。

### 3. 渠道插件边界如何演进？

| 形式 | 隔离 | 开发/调试成本 | 适用条件 |
| --- | --- | --- | --- |
| 主进程内 Adapter | 低 | 最低 | Fake/Console 和可信、轻依赖适配器 |
| 独立 Python/Node package，仍进主进程 | 低 | 低 | 只需发布/依赖边界，不需故障隔离 |
| 独立子进程 | 中 | 中 | SDK 依赖冲突或崩溃隔离，仍为同机部署 |
| 独立 HTTP/WebSocket 服务 | 高 | 高 | 独立升级、异语言、第三方插件或独立扩缩容 |

第一版建议只定义实际用到的规范消息字段和一个进程内 Fake/Console 适配器。不要做动态发现、热加载或插件市场。若出现 SDK 冲突、独立发布、非可信代码或崩溃影响，再用一次 HTTP spike 验证进程外协议；只有长连接/流式事件需要时才选 WebSocket。

Dify 的官方 Plugin Daemon 是有价值的成熟期参考：API server 通过 HTTP 调用 daemon，daemon 根据 runtime 使用子进程 STDIN/STDOUT、调试 TCP 或 serverless HTTP；但它同时引入 daemon、数据库/运行时管理和部署限制，成本远超 Aster 首版需求。来源：[Dify Plugin Daemon](https://github.com/langgenius/dify-plugin-daemon)。

### 4. Agent、RAG 与工具采用什么边界？

| 方案 | 收益 | 风险 | 当前用途判断 |
| --- | --- | --- | --- |
| 自建最小编排层 | 领域边界透明、学习价值高、供应商可替换 | 容易逐步重造框架 | **只实现当前链路所需薄层** |
| 引入 Agent 框架 | 图状态、检查点、工具生态可快速获得 | 框架对象侵入领域、升级耦合 | 出现多分支/恢复/观测需求后做 spike |
| Dify/RAGFlow 外部服务 | 快速试验完整 Agent/RAG 能力，API 隔离 | 多服务运维、数据边界、许可证/版本耦合 | 可作后续实验，不作为 Core |
| Fork 大型平台 | 初始功能丰富 | 代码体量、陌生栈、升级合并与品牌/许可证成本 | 当前不建议 |

Dify 官方定位同时覆盖 workflow、RAG、Agent、模型管理和 LLMOps，并提供 API；RAGFlow 同时覆盖复杂文档解析、检索、Agent 和多渠道。这些能力适合作为外部能力基准，但把 Aster 建在其内部模型上会模糊客服领域边界。来源：[Dify 仓库](https://github.com/langgenius/dify)、[RAGFlow 仓库](https://github.com/infiniflow/ragflow)。

工具边界未来至少应区分参数校验、权限/白名单、高风险确认和审计；RAG 应返回可追踪证据；对话编排只协调这些能力。Phase 0 不据此创建接口。

### 5. 数据与异步基础设施何时引入？

- M1 只需内存状态来验证消息边界。
- 当验收要求包含重启恢复、重复 webhook、人工接管历史或审计时，会话与消息必须持久化；SQLite 是单机学习实验候选，PostgreSQL 在并发/部署需求出现后重评。
- Docker 适合隔离明确的外部服务；本地 Python 核心可直接运行于 WSL，没必要仅为“环境完整”容器化。
- 消息队列只在需要跨进程可靠投递、削峰、独立 worker 或可度量重试语义时引入。n8n 官方 queue mode 需要主实例、worker、Redis 和共享数据库，展示了可扩展性的实际复杂度。来源：[n8n queue mode](https://docs.n8n.io/hosting/scaling/queue-mode/)。

## 开源项目用途与许可证

以下判断只针对访问日的仓库状态，不替代法律意见；真正引入依赖或复制代码前必须再次核查具体版本和文件许可证。

| 项目 | 维护/技术与成本观察 | 许可证（官方文件） | 对 Aster 的建议 |
| --- | --- | --- | --- |
| Chatwoot | 官方说明约每月发布；Ruby on Rails/Vue，生产依赖 PostgreSQL、Redis、worker 等 | 主体为 MIT Expat，`enterprise/` 另有许可：[LICENSE](https://github.com/chatwoot/chatwoot/blob/develop/LICENSE) | 客服领域、渠道/inbox、人工接管的设计参考；未来也可作为独立客服台集成。不 Fork |
| Dify | Python/TypeScript 大型平台，最低自托管指引使用 Docker Compose；插件另有 Go daemon | 修改版 Apache 2.0；多租户和前端品牌有附加条件：[LICENSE](https://github.com/langgenius/dify/blob/main/LICENSE) | 仅作设计参考或 API 实验；商业/多租户用途先做许可证审查，不 Fork |
| Dify Plugin Daemon | Go 服务管理本地、调试和 serverless runtime；展示多种隔离方式，也带来运行时/存储成本 | Apache-2.0：[LICENSE](https://github.com/langgenius/dify-plugin-daemon/blob/main/LICENSE) | 插件隔离演进参考，不作为早期依赖 |
| RAGFlow | 官方仓库在 2026 年仍列出更新；能力和自托管组件较重 | Apache-2.0：[LICENSE](https://github.com/infiniflow/ragflow/blob/main/LICENSE) | 复杂文档/RAG 的外部服务实验候选；不 Fork |
| n8n | 成熟工作流平台；queue mode 明确引入 Redis、worker 和共享 DB | Sustainable Use License，限制为内部业务或非商业/个人用途，企业文件另授权：[LICENSE](https://github.com/n8n-io/n8n/blob/master/LICENSE.md) | 自动化语义和可靠执行的设计参考；任何嵌入、分发或商业托管先审许可 |

没有继续机械调研 FastGPT、MaxKB、Flowise、Zammad：上述样本已经分别覆盖客服台、AI/RAG 平台、插件隔离和自动化队列，足以回答本阶段问题。新增项目只有在某个待验证假设无法由现有证据回答时再研究。

## Codex 项目 Skill

OpenAI 官方文档确认 Codex 从仓库根目录及上级路径的 `.agents/skills` 发现 Skill；每个 Skill 是含 `name`、`description` 的 `SKILL.md` 目录，脚本和资源可选。来源：[OpenAI Build skills](https://developers.openai.com/codex/skills)。

本次 Agent 执行环境把 `.agents` 单独挂载为只读 `tmpfs`，实际写入失败；这不是 Aster 仓库的设计或长期状态。因此没有伪造不可发现目录，临时流程记录在 `docs/agent-workflow.md`。在正常 clone 中应创建 `.agents/skills/aster-workflow/SKILL.md` 并用官方/内置 validator 验证。
