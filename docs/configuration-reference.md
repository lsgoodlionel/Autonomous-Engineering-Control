# 配置参考

## 通用规则

`GATE_MATRIX.yaml` 与 `PROTECTED_PATHS.yaml` 使用 YAML 1.2 的 JSON 子集，并由 Python `json` 模块解析。必须使用双引号、显式数组和对象；不支持注释、锚点、隐式类型或重复 key。当前配置版本均为 `1`，未知字段拒绝。

所有路径均使用仓库相对 POSIX 形式，不允许绝对路径、反斜杠或 `..`。运行状态中的 `worktreePath` 是唯一需要记录绝对路径的字段，由运行时生成，不应手工写进模板。

## GATE_MATRIX.yaml

顶层字段：

- `version`：固定为 `1`。
- `gates`：至少一个 Gate。
- `profiles`：至少一个路径 profile。

Gate 字段：`id`、`command`、`cwd`、`timeout_seconds`。`id` 使用小写连字符格式；命令是非空字符串数组。

Profile 字段：`paths` 与 `gates`。引用的 Gate ID 必须存在且不得重复。

## PROTECTED_PATHS.yaml

顶层字段：`version` 与非空 `rules`。规则字段：

- `id`：规则唯一标识。
- `patterns`：仓库相对 glob。
- `operations`：`add`、`modify`、`delete` 的非空子集。
- `action`：`deny`、`approval_required`、`review_required` 或 `generated`。
- `generator`：仅 `generated` 必需，且为非空参数数组。

## HARNESS_HOST.json

顶层字段固定为：

- `version`
- `activePlan`
- `deliveryManifest`
- `ledger`
- `secretPolicy`
- `fixture`
- `documentation`

`activePlan` 与 `fixture.planPath` 当前必须位于 `docs/superpowers/plans/`。`secretPolicy.patterns` 指定秘密候选路径，`allowlist` 只能做窄范围模板豁免，不能放行真实配置。`documentation.statusMarkerPaths` 列出需要与交付状态一致的宿主文档。

`doctor` 将上述 active plan、delivery manifest、ledger、fixture、fixture plan 和状态文档视为完整宿主契约：路径必须安全、文件必须存在且不得经过 symlink。

## STATE_SCHEMA.json

这是运行状态 wire contract，不是手工状态文件。重要约束包括：

- `runId` 为 UUID，计划和失败指纹为 SHA-256，提交为完整 40 位 SHA。
- `planPath`、`changedPaths` 与 `evidencePath` 为仓库相对路径。
- Gate `passed` 必须同时有退出码 0、起止时间和证据路径。
- 状态结构合法不代表转换合法；转换、HEAD 和必需 Gate 一致性由运行层继续检查。

## PROJECT_MEMORY.md 与 AUTONOMY.md

项目记忆只保存稳定事实、权威入口、技术栈、质量门和维护边界。不要写当前分支、临时端口、一次性错误、运行 ID 或未验证完成度。

自治 SOP 定义准入、质量门、路径规则、失败预算、恢复、人工升级和交付边界。宿主可以收紧规则，不能通过文档放宽核心强制约束。

## HARNESS_DELIVERY.json

交付清单属于宿主集成契约，不是核心运行状态。模板初态固定为 `not_started`、空实现提交、pending evidence/external sync、空报告和 `security`、`dx_ci`、`whole_branch` reviewer 列表；宿主应由交付控制器填入计划步骤、当前实现提交、验证证据、独立复审和外部同步状态。不得复制其他项目的 commit、报告摘要或同步状态。
