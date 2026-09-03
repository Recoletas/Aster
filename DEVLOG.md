# Aster 开发日志

## 2026-09-03 — Phase 0 启动

### 本次目标

核查新仓库与开发环境，完成针对性架构调研，建立工程文档并形成待确认建议；不编写业务代码。

### 实际完成

- 检查了工作目录、占位目录、远端引用和本地工具链；
- 调研了 Chatwoot、Dify、Dify Plugin Daemon、RAGFlow、n8n 和 Codex Skills 的官方资料；
- 梳理了需求、非目标、架构候选、许可证影响、验证方案和后续三个候选里程碑；
- 创建 README、Agent 规则、贡献指南、计划及架构/调研文档。

### 关键发现

- 本次 Agent 工作区不是有效 Git 工作树；执行环境把 `.git` 暴露为空的只读挂载点。用户提供的远端可访问，但 `HEAD/main/master` 均无引用，符合空远端仓库特征。
- Codex 官方支持仓库级 `.agents/skills`；本次执行环境中的 `.agents` 同样是只读挂载点，`chmod u+w .agents` 失败，因此暂以 `docs/agent-workflow.md` 提供非自动加载的回退流程。这不是 Aster 的长期目录策略。
- 大型客服/AI/自动化平台适合用作边界参考或后续外部服务实验，不适合成为 Aster Phase 1 的 Fork 基线。
- 当前建议是 Python 模块化单体、进程内最小渠道契约、薄 Agent 编排层、内存起步；这些均未被团队接受。

### 已执行验证命令

- `uname -a`
- `git --version`
- `python3 --version`
- `node --version`
- `npm --version`
- `docker --version`
- `docker compose version`
- `rg --version`
- `git status --short --branch`（失败：当前不是 Git 仓库）
- `git ls-remote git@github.com:Recoletas/Aster.git HEAD refs/heads/main refs/heads/master`
- `find . -maxdepth 3 -type f ...`
- Node 本地 Markdown 链接目标检查（9 个文件，全部存在）
- `rg -n '[[:blank:]]+$' --glob '*.md'`
- `find . -maxdepth 4 -type f ...`（确认只有本里程碑的 9 个 Markdown 文件）
- `chmod u+w .agents`（失败：只读文件系统）
- `git diff --check` / `git diff --stat`（未执行到 diff：当前不是 Git 仓库）
- `git diff --no-index -- /dev/null <file>`（逐文件审阅 9 个新增文档，作为无 Git 基线时的回退）

### 未解决问题

- 本次执行环境无有效 Git 元数据，无法使用 Git diff/status 验证改动；需要在正常可写的 clone 中建立基线。
- 项目级 Skill 尚未落在官方发现路径。
- 三项高成本架构/产品问题仍等待人工决定，见 `PLAN.md`。

### 下一步建议

先人工评审架构建议并恢复有效 Git 工作树和可写 `.agents` 路径；确认后只执行 M1。

## 2026-09-03 — M1-A 消息契约设计

### 本次目标

只设计 Aster Core 与 Fake/Console Channel 的最小消息契约，调整后续路线；不写业务实现。

### 实际完成

- 将 Python 模块化单体、M1 进程内 Adapter 和多租户处理原则记录为 ADR-0001；
- 比较了成对消息、统一双向消息和 Envelope + Content Parts 三种契约；
- 推荐显式 `ConversationRef` 加 `IncomingMessage`/`Reply`，首版不加入 metadata 或多媒体抽象；
- 将路线调整为 M1 消息边界 → M2 最小 Agent 对话 → M3 会话持久化；
- 从固定 Roadmap 移除进程外 Channel Adapter，只保留重评触发条件。

### 关键发现

- 仓库根目录位于可写 ext4；`.git`、`.agents`、`.codex` 是本次 Agent 环境分别注入的只读 `tmpfs`，设备号与仓库根目录不同。因此只读状态不是 Aster 仓库属性。
- 当前目录仍不是有效 Git 工作树，无法取得正式 status/diff；这同样是本次执行环境呈现，不应写成长期项目事实。

### 执行过的检查

- 完整读取 `AGENTS.md`、`PLAN.md`、需求、调研、架构建议和 DEVLOG；
- `git status --short --branch`
- `git rev-parse --show-toplevel`
- `git remote -v`
- `stat -c ... . .git .agents .codex`
- `findmnt -T .`、`findmnt -T .git`、`findmnt -T .agents`
- `namei -l .git .agents`
- Node 本地 Markdown 链接检查（11 个文件，全部存在）
- Markdown 尾随空白、未完成标记和占位语句扫描（无匹配）
- `find . -maxdepth 5 -type f ! -name '*.md' -print`（无业务实现文件）
- 完整读取 M1 设计、ADR、PLAN 和 DEVLOG，检查旧 Roadmap 与环境措辞残留
- `git diff --no-index --check /dev/null <new-document>`（无空白错误；返回 1 表示存在新增内容）
- `git diff --check` / `git diff --stat`（失败：本次环境不是有效 Git 工作树）

### 未解决问题

- M1 推荐契约尚未被人工接受，不能开始 M1-B。
- 多租户 SaaS 方向继续保持开放。

### 下一步建议

评审 `docs/architecture/m1-message-contract.md`；确认后只实现 M1-B，不进入 M2。

## 2026-09-03 — M1-B 核心消息边界实现

### 本次目标

实现 Console/Fake → 规范消息 → 确定性 Core → Reply → Console/Fake stdout 的最小可运行链路。

### 实际完成

- 使用 `ConversationRef`、`IncomingMessage` 和 `Reply` 表达已接受契约；
- 在 Console 边界直接校验 JSON object 的 `room`、`event`、`user`、`body`；
- 实现不依赖渠道的确定性 echo Core，以及单行 JSON 输入输出入口；
- 增加 5 个标准库 `unittest`，未引入第三方依赖。

### 关键决策或发现

- 采用三实现文件方案：`messages.py` 独立后，Core/Adapter 的共享边界比把契约放入 `core.py` 更直观，且没有增加新的分层或抽象类型。
- `in_reply_to_external_message_id` 只表示触发关联；具体 Adapter 可选择是否使用平台原生引用回复。
- 简单字段校验足以覆盖 M1；无需 Validation Framework、Protocol、ABC、配置或 capability 系统。

### 执行过的验证

- 示例 JSON 经 `python -B -m aster.console` 输出预期单行 JSON；
- 空白 `body` 经同一 CLI 在边界报出 `body: must not be blank` 并以状态 2 退出；
- `python -B -m unittest discover -s tests -v`：5 个测试全部通过；
- `python3 -B -c 'import aster.messages, aster.core, aster.console; ...'`：导入成功；
- 使用标准库 `ast.parse` 解析 4 个 Python 文件：全部成功；
- 导入、禁用能力关键词、文件范围和全部新增代码人工审阅：未发现第三方依赖或越界抽象；
- `git diff --no-index --check /dev/null <file>`：新增代码无空白错误；
- 本地 Markdown 链接检查：11 个目标全部存在；代码及本次文档无尾随空白；
- 正式 `git status/diff`：因本次 Agent 环境将 `.git` 挂载为只读空 `tmpfs` 而不可用，未尝试修复。

### 测试覆盖

- 合法 Console payload 到规范 `IncomingMessage`；
- 缺失、类型错误和空白字段均在边界失败，且 Core 未被调用；
- Core 产生确定性 `Reply`；
- Reply 转为 Console 输出；
- 完整 JSON line 纵向链路。

### 未解决问题

- 当前只有 text-only 契约；真实多媒体需求出现后再决定内容模型。
- 当前只有 Fake/Console Adapter；进程隔离仍仅由既定触发条件启动研究。

### 下一步建议

人工验收 M1。未获明确授权前不设计或实现 M2。

## 2026-09-03 — M1-B 状态恢复与独立复核

### 本次目标

上下文压缩后恢复现场：确认被截断的语义约束已完整落盘，独立核对 M1-B 实际改动与报告一致；不实现新内容。

### 实际完成

- 完整读取 AGENTS、PLAN、DEVLOG、契约文档和 4 个 Python 文件，确认无契约外改动、无多余文件；
- 亲自重跑全部验证（见下），结果与 M1-B 报告一致；
- 确认 `in_reply_to_external_message_id` 只表示触发关联这一约束完整记录于契约文档候选 A、`Reply` docstring、Console `reply_to` 映射和 DEVLOG，未因上下文截断丢失。

### 关键发现

- 执行环境变化：`.git`、`.agents`、`.codex` 只读 tmpfs 挂载本次完全不存在；仓库根为普通可写 ext4，但当前不是 Git 仓库。恢复有效 Git 工作树仍是人工步骤。

### 执行过的验证

- `python3 -B -m unittest discover -s tests -v`：5 个测试全部通过；
- 合法 JSON line 经 `python3 -B -m aster.console`：输出预期单行 JSON，状态 0；
- 空白 `body`：输出 `error: body: must not be blank`，状态 2；
- `import aster.messages, aster.core, aster.console`：成功；
- `aster/core.py` 导入检查：仅依赖 `aster.messages`；
- `stat`/`findmnt`：确认 `.git` 不存在、根目录为可写 ext4。

### 未解决问题

- 无有效 Git 工作树，仍无法产生正式 status/diff 基线。
- M1 整体等待人工验收。

### 下一步建议

人工验收 M1-B 并决定是否进入 M2；恢复 Git 工作树后建议以当前 15 个文件建立首次提交基线。

## 2026-09-04 — Git 基线建立

### 本次目标

在环境变为可写后建立有效 Git 工作树，使后续里程碑有真实 diff 可审。

### 实际完成

- `git init -b main`；`.git` 不再是只读挂载，仓库根为可写 ext4；
- 新增 `.gitignore`（`__pycache__/`、`*.pyc`、`data/`）；
- 以 M1-B 原状提交基线 `b5b64e5`（16 个文件），提交使用用户全局 Git 身份，仅本地未推送。

### 关键发现

- `.git`、`.agents`、`.codex` 的只读 tmpfs 挂载本次已完全消失，此前"环境限制"不再存在。

### 执行过的验证

- `git log --oneline`、`git status --short`：基线提交后工作树干净。

## 2026-09-04 — M2 最小 Agent 对话链路

### 本次目标

把一次性 echo 升级为带会话状态的最小对话应用层；不做持久化与幂等。

### 实际完成

- 新增 `aster/agent.py`：`ConversationSession`（已收文本）与 `SessionStore`（内存会话表）；
- `aster/core.py`：`handle_message` 增加 turn 参数，回复为 `echo #n: text`；
- `aster/console.py`：多行 JSON line 输入，整个输入流共享一个 `SessionStore`，空行跳过；
- 测试：更新 M1 回归测试（新签名与 `#1` 输出），新增 3 个会话测试，共 8 个。

### 关键决策或发现

- 轮次由应用层计数，策略只读取 turn：状态与策略分离，且策略仍是纯函数。
- M1 契约文档中的 `echo: hello` 输出属 M1-B 验收记录，不回写；契约字段未变。

### 执行过的验证

- `python3 -B -m unittest discover -s tests -v`：8 个测试全部通过；
- 三行 CLI 演示：room-7 得 `#1`/`#2`，room-8 独立得 `#1`，退出码 0；
- 空白 `body`：边界拒绝，退出码 2；
- 导入方向检查：core→messages，agent→core+messages，均无渠道导入。

### 未解决问题

- 会话状态仅在内存，进程结束即丢失（M3 处理）。
- 重复投递尚未幂等（M3 处理）。

### 下一步建议

按计划继续 M3 会话持久化。

## 2026-09-04 — M3 会话持久化

### 本次目标

会话状态落盘并在重启后恢复；同一外部消息重复投递幂等；不引入数据库。

### 实际完成

- 新增 `aster/storage.py`：`save_store`/`load_store`，单 JSON 文件，写临时文件后 `os.replace` 原子替换，自动创建父目录；
- `aster/agent.py`：会话增加 `turn_by_message_id`，重复外部消息 id 返回既有轮次且不再改动会话；
- `aster/console.py`：新增 `--store PATH`，启动时加载、逐行保存；不带 `--store` 行为与 M2 相同；
- 新增 3 个持久化测试，共 11 个。

### 关键决策或发现

- 幂等语义：外部消息 id 到轮次的映射随会话持久化，重复投递得到与首次相同的确定性输出——这是"最小幂等"，不处理跨渠道全局去重。
- 持久化的是会话状态而非完整审计历史；损坏文件由 JSON/KeyError 大声失败，不静默降级。
- 开发中发现一处测试自身 bug：对含两行输出的子进程 stdout 直接 `json.loads`，已改为逐行解析；CLI 行为本身正确。

### 执行过的验证

- `python3 -B -m unittest discover -s tests -v`：11 个测试全部通过（含真实子进程重启续号）；
- 重复投递 CLI 演示：同一行两次均输出 `echo #1`，存储文件 `user_texts` 只有一条；
- 两个进程接力演示：第二进程从存储恢复后输出 `echo #2`；
- 不带 `--store`：行为与 M2 一致；
- `data/sessions.json` 内容人工核对正确；
- 导入方向检查：storage→agent+messages，console 为组合根，core/agent 无渠道依赖；
- `git diff --check`：无空白错误。

### 未解决问题

- 无并发/锁；多进程同时写同一存储文件会相互覆盖（出现真实需求前不处理）。
- 存储文件无版本号/迁移机制；文件损坏的恢复策略未定义。
- 完整消息审计历史不持久化，涉隐私与审计的取舍未决定。

### 下一步建议

停止并等待人工决定下一方向：真实 LLM provider（需 API key）、会话历史数据库化，或首个真实消息渠道。

## 2026-09-04 — aster-workflow 项目级 Skill 迁移

### 本次目标

把临时回退流程迁移为可被 Coding Agent 自动加载的项目级 Skill；不复制 `AGENTS.md`。

### 实际完成

- 经 ZCode 官方配置指南确认项目级 Skill 的官方位置：仓库内 `.zcode/skills/` 或 `.agents/skills/`（目录 + SKILL.md），且跨工具共享建议使用 `.agents/skills/`——与 Phase 0 调研的 Codex 官方仓库级路径一致；
- 创建 `.agents/skills/aster-workflow/SKILL.md`：检查 → 计划 → 实现 → 验证 → 记录 → 停止，指向 `AGENTS.md`/`PLAN.md`/`DEVLOG` 而非复制内容；
- `docs/agent-workflow.md` 状态更新为"已迁移，本文件保留为工具无关参考"。

### 执行过的验证

- Skill 路径符合官方发现顺序（工作区 `.agents/skills` 在扫描列表内）；
- Markdown 链接与空白检查纳入本次全量验证。

### 未解决问题

- Skill 的自动加载需在下一个新会话中确认其出现在可用列表（本会话启动时列表已固定），属待验证而非已验证。

## 2026-09-04 — LLM provider 调研输入与首次推送

### 本次目标

按人工指示：只读调研 `~/openmaic` 中已配置的 MiniMax 模型接入，作为 M4 的 provider 输入；将本地提交推送到远端。

### 关键发现（来源：openmaic `.env.local` 实际配置与 `lib/ai/providers.ts` 注释）

- LLM 走 **Anthropic 兼容端点**：`https://api.minimaxi.com/anthropic/v1`（国际站备用 `https://api.minimax.io/anthropic/v1`），官方推荐该接入方式（参考 platform.minimaxi.com 的 text-anthropic-api 文档，见 providers.ts 头部来源注释）；
- 已配置模型 `MiniMax-M3`：1M 上下文、32K 输出、支持流式/工具/视觉；同端点还有 M2.7 系列；
- openmaic 用 `@ai-sdk/anthropic` 以自定义 baseURL 调用，即标准 Anthropic Messages 协议；
- 另有 TTS/联网搜索的 MiniMax key，与本里程碑无关。

### 密钥处理

- 密钥只存在于 openmaic 本地 `.env.local`；本仓库不复制、不落盘，本次输出已掩码。Aster 侧应经环境变量注入并加入 `.gitignore` 约束。

### 实际完成

- `PLAN.md` 开放问题与确认门更新为"provider 已定 MiniMax，M4 待批准"；
- 添加远端 `origin = git@github.com:Recoletas/Aster.git` 并推送全部本地提交。

### 未解决问题

- M4 依赖选择：`anthropic` Python SDK（协议实现更稳，但引入首个第三方依赖）或标准库 `urllib` 直发 Messages 请求（零依赖，先非流式）——待 M4 计划中定。
- MiniMax 官方文档的端点/鉴权细节尚未经本仓库直接验证，M4 设计时应核对官方文档。

## 2026-09-04 — M4 最小 LLM 对话边界

### 本次目标

人工批准方案 A：用 anthropic Python SDK（覆写 baseURL）接入 MiniMax，把现有链路的回复策略换成真实模型；provider 细节不泄漏进 core/agent。

### 实际完成

- 新增 `aster/provider.py`：唯一认识 SDK 与端点的模块（`to_api_messages`/`extract_text`/`chat_reply`/`build_client`）；`MINIMAX_API_KEY` 缺失时抛 RuntimeError，CLI 捕获后干净退出 2；
- `aster/agent.py`：会话历史改为 (role, text) 交替对；回复策略经构造参数注入（默认 `core.echo_reply`）；策略调用基于历史候选、成功后才落状态，失败不产生半写；重复投递直接复用已记录的 assistant 文本，不重调策略；
- `aster/core.py`：收敛为确定性策略 `echo_reply(history)`；
- `aster/console.py`：`--llm` 开关，provider 懒导入——不装 SDK 的离线用法完全不受影响；`--store` 与 `--llm` 可组合且加载时保留策略；
- `aster/storage.py`：持久化格式变为 history 交替对，`load_store` 接受并保留策略；
- `requirements.txt`（anthropic>=1.3.0，项目首个第三方依赖）、`.env.example`、`.gitignore` 增加 `.env`；
- 测试：更新边界/会话/持久化测试（非法输入用注入的记录函数证明策略未被调用），新增 provider 边界测试（假 client，不触网），共 15 个。

### 关键决策或发现

- **BASE_URL 陷阱**：Python anthropic SDK 会自动追加 `/v1/messages`，base_url 写 openmaic 式的 `.../anthropic/v1` 会请求 `.../v1/v1/messages` → 404。正确值是 `https://api.minimaxi.com/anthropic`，已用最小探针验证并加注释。
- 策略注入是项目第一个真正的参数化接缝：此前规则是"没有第二实现不做抽象"，现在 LLM 与 echo 两个实现都真实存在。
- 重复投递语义升级：复用历史中的 assistant 回复而非重新生成，对 LLM 计费安全。
- MiniMax 返回内容按 block type 过滤，仅拼接 `text` 块，兼容潜在的 thinking 块。

### 执行过的验证

- `python3 -B -m unittest discover -s tests`：15 个测试全部通过（离线，无网络调用）；
- 缺 `MINIMAX_API_KEY` 时 `--llm` 输出 `error: MINIMAX_API_KEY: environment variable not set`，退出码 2；
- 无 `--llm` 时 CLI 行为与 M3 一致（含 `--store`）；
- 导入方向：agent→core+messages；storage→agent+core+messages；provider 不导入任何 aster 模块；console 仅在 `--llm` 分支懒导入 provider；
- **真实演示（三个独立进程，`--store` 接力）**：P1 告知"我叫小明，后端工程师"→ MiniMax 确认；P2（新进程从 JSON 恢复）问"我叫什么"→ 正确答出；P3 另一会话问同样问题 → 正确回答不知道（会话隔离有效）；
- 密钥处理：仅经管道注入进程环境变量，未写入仓库任何文件，输出未回显。

### 未解决问题

- 非流式调用，长回复需整体等待；thinking 块的流式行为未验证。
- anthropic SDK 安装在用户全局 miniconda 环境，无虚拟环境隔离。
- 会话历史无限增长，无窗口或摘要策略。

### 下一步建议

停止。后续候选需人工定优先级：流式输出、工具调用/MCP、RAG、首个真实消息渠道、会话历史数据库化。

## 2026-09-04 — 依赖环境整改：全局 miniconda 回滚，项目改用 .venv

### 本次目标

修复人工指出的问题：M4 把 anthropic SDK 装进了用户全局 miniconda 环境。要求全局环境恢复原状，依赖改入项目本地 `.venv`。

### 实际完成

- 卸载全局环境中的 anthropic 及仅由其带入的依赖（`docstring_parser`、`httpcore2`、`httpx2`；卸载前核对 Required-by，确认无其他依赖方）；
- `idna` 由 anthropic 安装时被动升级的 3.19 回退到原版本 3.7，原有 httpx/requests/anyio 导入验证正常；
- 创建 `~/Aster/.venv` 并安装 `requirements.txt`；`.gitignore` 增加 `.venv/`；
- `tests/test_provider.py` 在无 SDK 环境模块级 `unittest.SkipTest`，离线套件保持全绿；
- `--llm` 缺 SDK 时输出可操作错误（提示 `pip install -r requirements.txt`）而非堆栈，退出码 2；
- `AGENTS.md` 新增规则：第三方依赖一律装项目本地 `.venv`，禁止进用户全局/conda 环境；README 更新运行方式。

### 关键教训

引入项目首个第三方依赖时，必须同步建立隔离环境，并把这条边界写进 Agent 规则；本次先装后补属于流程失误，已用规则防复发。

### 执行过的验证

- 全局 `python3 -c "import anthropic"` → ModuleNotFoundError；`pip show idna` → 3.7；httpx/requests/anyio 导入正常；
- 系统 python 套件：13 个测试 OK（1 skipped = provider，无失败）；无 SDK 时 `--llm` 退出码 2 且提示清晰；
- `.venv` python 套件：15 个全部通过；
- 真实调用经 `.venv/bin/python -m aster.console --llm` 成功（MiniMax-M3 回复"收到"）。

### 未解决问题

- 无。

### 下一步建议

维持此前停止点：流式输出、工具调用/MCP、RAG、首个真实消息渠道、会话历史数据库化，等人工定优先级。

## 2026-09-04 — M5 最小工具调用

### 本次目标

按人工指示"充分调研市场，有开源实现直接使用"后实现：模型能决定调用工具、参数经校验、结果回填生成最终回复，全程可审计。

### 调研结论（详见 `docs/research/tool-calling-survey.md`）

- MiniMax Anthropic 兼容端点对 `tools`/`tool_use`/`tool_result` 完全支持；硬约束：必须完整回传含 thinking 的 `response.content`；`mcp_servers` 被忽略（服务端 MCP 不可用）；
- 采用：anthropic SDK（协议层，已有）+ pydantic v2（schema 与校验，新增，MIT）；
- 不采用：MCP 官方 SDK（client/server + asyncio，当前无外部工具互通需求，留作未来工具来源边界）、pydantic-ai（采用即替换自建薄编排层，与 ADR-0001 基线冲突，留作薄层失控时的迁移候选）；注册表与循环自建（被端点约束塑造，无匹配微库）。

### 实际完成

- 新增 `aster/tools.py`：`Tool`（pydantic 参数模型 → JSON Schema，校验失败以错误字符串经 `tool_result` 回给模型自纠）+ `ToolRegistry`（注册即白名单 + 审计日志）+ 内存工单假实现（create_ticket/list_tickets）；
- `aster/provider.py`：`make_chat_reply(registry)` 工具循环（stop_reason=tool_use → 执行 → tool_result → 续跑，上限 4 轮），`echo_content` 按端点要求完整回传含 thinking 的内容；系统提示词明确"动作必须走工具、查询必须确认"；
- `aster/console.py`：`--llm` 接注册表，审计输出到 stderr（不污染 stdout JSON 协议）；
- 依赖：pydantic 入 `requirements.txt` 并只装 `.venv`；测试在无 SDK/pydantic 环境自动跳过；
- 测试：新增工具边界与脚本化假 client 工具循环测试，共 25 个（`.venv`）。

### 关键发现

- **模型调用工具是非确定性的**：同一三句话场景跑了三轮，`tool_choice: auto` 下动作类消息（建工单）两次未被调用、模型虚构"工单号 2"；查询类一次凭上下文跳过工具（碰巧答对）。提示词强化能降低不能消除。
- **审计日志当场检出幻觉**：声称"工单 2 已建"与审计（无第二次 create 记录）不一致立即可见；`list_tickets` 的真实返回也直接戳穿虚构。审计是本阶段唯一可靠的工具调用对账手段。
- 自身流程事故一次：console 编辑时把逐行 `save_store` 挤进了审计打印循环，持久化静默失效——被 M3 的跨进程重启回归测试当场抓住。回归测试的价值实证。

### 执行过的验证

- `.venv`：25 个测试全部通过；系统 python（无 SDK/pydantic）：20 个通过、1 个模块级跳过；
- 真实三轮演示 ×3（建工单×2 + 查询）：工具调用、参数校验（priority 归一化为 high/normal）、结果回填、最终回复引用真实工单号均验证成功；同时记录上述非确定性发现；
- 审计日志：成功调用与校验失败均有记录；
- 导入方向：tools 不被 core/agent 依赖，console 为组合根，provider 不导入 aster 模块。

### 未解决问题

- 工具调用时机依赖模型自发性：缓解靠审计对账；根治需按意图强制 `tool_choice` 或动作结果对账机制（候选里程碑）。
- 工单数据不持久化（进程内假实现）；审计仅 stderr 输出；会话历史无限增长。

### 下一步建议

停止。候选：工具调用可靠性策略、RAG、流式输出、真实渠道、数据库化、MCP 客户端，等人工定优先级。
