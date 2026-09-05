#!/usr/bin/env bash
# 一次性脚本：在 GitHub 仓库创建 CONTRIBUTING 约定的标签种子。
# 前置：gh CLI 已安装并登录（gh auth login），且在仓库目录内运行。
set -euo pipefail

create() {
  gh label create "$1" --color "$2" --description "$3" 2>/dev/null \
    || echo "已存在，跳过: $1"
}

create "task"          "1D76DB" "里程碑内可独立验收的小任务"
create "triage"        "D93F0B" "待确认影响面与优先级"
create "dependencies"  "0366D6" "依赖更新（dependabot 自动打）"

# area:*（与 issue 模板的"影响范围"下拉对应）
create "area:console"     "C2E0C6" "Console 渠道"
create "area:web"         "C2E0C6" "Web 渠道"
create "area:provider"    "BFD4F2" "LLM provider（MiniMax）"
create "area:tools"       "BFD4F2" "工具调用/对账"
create "area:knowledge"   "BFD4F2" "知识库检索"
create "area:storage"     "BFD4F2" "持久化（SQLite）"
create "area:engineering" "EDEDED" "构建/CI/依赖"
create "area:docs"        "EDEDED" "文档"

# milestone:*（新里程碑开工时补充）
create "milestone:m5"  "5319E7" "工具调用"
create "milestone:m6"  "5319E7" "对账"
create "milestone:m7"  "5319E7" "RAG 基线"
create "milestone:m8"  "5319E7" "Web 渠道"
create "milestone:m9"  "5319E7" "SQLite"
create "milestone:m10" "5319E7" "流式"

echo "标签种子完成。"
