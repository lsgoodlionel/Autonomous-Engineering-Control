# 运行与恢复

## 标准流程

```sh
scripts/agent-harness doctor --json
scripts/agent-harness init --plan <plan-path> --milestone <milestone-id>
scripts/agent-harness status --run-id <run-id> --json
scripts/agent-harness next --run-id <run-id> --json
scripts/agent-harness gate --run-id <run-id>
scripts/agent-harness finalize --run-id <run-id>
```

`next` 只给出状态机允许的下一类动作。执行前仍需遵守宿主的人工批准和任务范围。

## 自动执行

```sh
scripts/agent-harness run-codex --run-id <run-id> --max-cycles 1
```

自动执行只适用于已批准、边界明确、有可靠测试的 Milestone。建议每次先使用一个 cycle，观察状态、diff 和 Gate 选择，再决定是否继续。禁止通过无限循环或扩大权限掩盖失败。

## 暂停与恢复

```sh
scripts/agent-harness pause --run-id <run-id> --reason <sanitized-reason>
scripts/agent-harness resume --run-id <run-id>
```

恢复前重新运行 `doctor`，核对仓库、worktree、分支、HEAD、计划摘要、工作区归属和工具状态。若计划、历史、分支或未知改动发生变化，应创建新的经批准运行，不静默改写旧状态。

## 失败预算

- 同一失败指纹第 3 次后暂停。
- 单 Milestone 第 5 个失败周期后暂停。
- 连续 2 轮 diff、失败指纹和 Gate 结果均无实质变化时暂停。

认证、配额、权限、架构冲突、生产审批和真实秘密问题不进入盲目重试。

## 证据管理

Gate 证据只对记录的 HEAD 有效。提交新修复后，旧证据必须失效并重跑。原始日志放在 `var/agent-harness/`；可提交摘要应包含计划、Milestone、HEAD、Gate、结果、失败分类和恢复命令，且不得复制秘密或完整原始输出。

## 故障演练

默认 drills 使用临时目录和 fake 命令：

```sh
scripts/agent-harness --python tools/agent-harness/drills/run_drills.py
```

真实执行器 smoke 必须由人工显式批准，仅操作当前 HEAD 创建的 disposable worktree，并限制为一个 cycle。CI 不运行真实执行器 smoke。
