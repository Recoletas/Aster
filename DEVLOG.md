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
