# 参与 Aster

Aster 当前以学习和可维护性优先。一次贡献应足够小，让另一位成员能独立理解、运行和验收。
协作在 GitHub 上进行：**任务从 issue 开始，代码从分支开始，改动经 PR 验收合并**——不直接 push 到 `main`。

## 开始前

按顺序阅读 `README.md`、`docs/requirements.md`、`PLAN.md`、相关架构文档/ADR，以及 `DEVLOG.md` 最近记录。Coding Agent 还需阅读 `AGENTS.md`。

## 1. Issue：一切任务的起点

- **里程碑任务**：用「里程碑任务」模板开 issue，写清所属里程碑、目标与范围、明确不做什么、验收标准。一个 issue 必须能独立验收，PR 必须逐条回应验收标准。
- **Bug**：用「Bug 报告」模板，给出复现步骤与环境（commit SHA）。
- 跨模块或高成本的技术选型**不开实现任务**：先在 issue 里写候选与权衡（见下文"架构问题"），确认后走 ADR。
- 认领任务：在 issue 里说一声，把 assignee 设为自己；开始时从 `PLAN.md` 同步状态。

## 2. 分支：从最新 `main` 切出

命名 `<类型>/<issue 号>-<短描述>`：

```
feat/24-ticket-persist     # 新功能
fix/31-stream-partial      # 缺陷修复
docs/12-contributing       # 仅文档
chore/40-dependabot        # 工程/依赖
```

## 3. Commit：Conventional Commits

格式 `<类型>(<可选范围>): <祈使句描述>`，一行的改动主题不要淹没在格式化 diff 里：

```
feat(tools): add claim reconciliation for ticket ids
fix(storage): fail loudly on retired JSON store
docs: rewrite CONTRIBUTING with the PR flow
chore(deps): bump anthropic to 1.4.0
```

类型：`feat` `fix` `docs` `refactor` `test` `chore`。破坏性变更在描述末尾加 `!` 并在正文说明迁移方式。
不 force push 共享分支；不要让格式化或重构淹没功能改动（分开提交）。

## 4. PR：逐条回应验收标准

1. PR 模板会要求：对应 issue、改动内容、**验收标准逐条回应**、实际执行过的验证、未验证项、架构影响；
2. 一个 PR 只解决一个 issue；`Fixes #NN` 让合并自动关闭 issue；
3. CI（lint + format + mypy + 测试）必须绿——CI 失败的 PR 不进入评审；
4. `make check` 在本地先跑过再请求评审。

## 5. 评审与合并

- `CODEOWNERS` 会自动请求 owner 评审；**至少一人验收通过才合并**（两人团队不设复杂审批层级）；
- 评审意见用 issue 评论或 PR review 解决；`PLAN.md` / `DEVLOG.md` 未随代码更新的 PR 不合并；
- 合并方式：`main` 使用 squash merge（保持 Conventional Commits 标题），合并后删除分支。

## Label 约定

`bug` `task` `triage` `dependencies` `area:*`（影响面，与 issue 模板对应）`milestone:*`（里程碑归属）。

## 提交前检查

- 完整质量门：`make check`（ruff 检查与格式、mypy、全部离线测试；CI 执行同一组命令）；
- 完整 `git status` 和 diff，移除无关修改；确认没有密钥、Token、真实用户数据；
- 更新 `PLAN.md` 任务状态和 `DEVLOG.md` 高信号记录；
- 只报告实际执行过的验证，无法执行时说明原因与影响。

## 架构问题

可逆的小选择先采用简单默认值，并记录假设。涉及技术栈、持久化边界、进程拆分、公共协议、许可证或长期迁移成本的选择：开 issue 写候选与权衡，经确认后创建 ADR（`docs/adr/`，含背景、选项、结果、理由、代价、重评条件）。没有接受结果时不写"已决定"的 ADR。
