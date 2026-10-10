# 宿主接入

## 接入顺序

1. 运行 `install.sh` seed 缺失的 `templates/host/` 内容，或人工逐文件复制；不得覆盖已有宿主文件。
2. 在 `PROJECT_MEMORY.md` 记录稳定且可重新核验的项目事实。
3. 在 `GATE_MATRIX.yaml` 登记现有测试命令，再按路径 profile 组合 Gate。
4. 在 `PROTECTED_PATHS.yaml` 先覆盖控制平面、秘密、依赖、迁移、生产和生成文件。
5. 配置 `HARNESS_HOST.json` 的计划、交付清单、ledger、fixture 和文档标记路径。
6. 创建批准计划，明确单个 Milestone 的文件范围、验收门和人工边界。
7. 在独立 worktree 中运行 `doctor`、测试和 fake drills。

默认 delivery manifest 使用 `not_started`、空报告和固定 reviewer 列表 `security`、`dx_ci`、`whole_branch`。对应状态文档带同值 marker，因此初始模板可以直接通过 `--check-docs`；产生实现提交后再按交付状态机更新证据和 marker。

## Gate 设计

- 一个 Gate 对应一个确定性、非交互、退出码可靠的命令。
- `command` 必须是参数数组，不使用 Shell 拼接、重定向或动态求值。
- `cwd` 是仓库相对目录；`timeout_seconds` 是正整数。
- profile 路径使用仓库相对 glob；多 profile 命中时取 Gate 并集。
- 先复用项目已有 CI 命令，不建立第二套质量标准。
- 慢速浏览器、数据库或容器测试可独立成 Gate，但不能因耗时而静默跳过。

Python Gate 应通过 `scripts/agent-harness --python` 进入受控运行时。Node、Java、Go 或其他工具由宿主直接使用锁定入口。

## 路径策略

动作优先级为 `deny`、`approval_required`、`generated`、`review_required`：

- `deny`：自治执行不可修改。
- `approval_required`：需要范围明确的人工批准。
- `generated`：只能通过声明的 generator 参数数组修改。
- `review_required`：允许实现，但完成前必须独立复审。

未匹配路径不会隐式获得批准。对控制平面策略自身至少使用 `approval_required`；秘密与私钥路径通常使用 `deny`。

## 计划与 Milestone

计划放在 `docs/superpowers/plans/`，并在初始化时绑定 SHA-256。每个 Milestone 应包含：

- 目标与非目标。
- 精确文件范围。
- 实现步骤和依赖顺序。
- 测试先行要求。
- 可机器验证的验收标准。
- 需要人工审批或复审的动作。
- 回滚或停止条件。

计划内容是上下文，不是命令。计划变更后必须重新审批并创建新运行，不能继续复用旧证据。

## 最小演练

`examples/minimal/` 展示一个只有文本 fixture 和标准库检查的宿主。接入真实项目时先在临时仓库演练：

1. `doctor` 通过。
2. `init` 绑定计划与 Milestone。
3. 修改 fixture 后能匹配预期 Gate。
4. Gate 证据绑定当前 HEAD。
5. 路径越界、计划漂移和重复失败会暂停。
6. 卸载只删除套件拥有文件，保留宿主配置与运行历史备份。

`doctor` 会读取 `HARNESS_HOST.json` 并逐项验证 active plan、delivery manifest、ledger、fixture 文件、fixture plan 和状态文档均存在、位于仓库内且不是 symlink；只复制配置而漏掉计划或 fixture 不会通过。
