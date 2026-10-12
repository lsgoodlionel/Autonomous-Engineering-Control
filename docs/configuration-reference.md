# 配置参考

## 通用规则

`GATE_MATRIX.yaml` 与 `PROTECTED_PATHS.yaml` 使用 YAML 1.2 的 JSON 子集，并由 Python `json` 模块解析。必须使用双引号、显式数组和对象；不支持注释、锚点、隐式类型或重复 key。Gate Matrix 支持版本 `1` 与 `2`，保护路径当前为版本 `1`；未知字段拒绝。

所有路径均使用仓库相对 POSIX 形式，不允许绝对路径、反斜杠或 `..`。运行状态中的 `worktreePath` 是唯一需要记录绝对路径的字段，由运行时生成，不应手工写进模板。

## GATE_MATRIX.yaml

顶层字段：

- `version`：`1` 使用安全兼容默认值；`2` 要求每个 Gate 显式声明执行与复用元数据。
- `gates`：至少一个 Gate。
- `profiles`：至少一个路径 profile。

版本 1 Gate 字段：`id`、`command`、`cwd`、`timeout_seconds`。其默认执行层为 `local_integration`、复用策略为 `head`、输入为仓库根、摘要格式为 `generic`。

版本 2 还必须声明：

- `execution_tier`：`local_fast`、`local_integration`、`github_full` 或 `production_strict`。
- `reuse_policy`：`content`、`head` 或 `never`。
- `input_patterns`：至少一个仓库相对 glob，参与 EvidenceKey 输入摘要。
- `summary_format`：`unittest`、`vitest`、`maven`、`playwright` 或 `generic`。

`id` 使用小写连字符格式；命令是非空字符串数组。生产、安全、发布和迁移 Gate 应使用 `head` 或 `never`，不能用 `content` 降低验收边界。

Profile 字段：`paths` 与 `gates`。引用的 Gate ID 必须存在且不得重复。

## PROTECTED_PATHS.yaml

顶层字段：`version` 与非空 `rules`。规则字段：

- `id`：规则唯一标识。
- `patterns`：仓库相对 glob。
- `operations`：`add`、`modify`、`delete` 的非空子集。
- `action`：`deny`、`approval_required`、`review_required` 或 `generated`。
- `generator`：仅 `generated` 必需，且为非空参数数组。

生成器配置示例：

```json
{
  "id": "generated-docs",
  "patterns": ["docs/generated/capability-map.md"],
  "operations": ["add", "modify", "delete"],
  "action": "generated",
  "generator": ["python3", "tools/render_capabilities.py"]
}
```

`generator` 是唯一可执行命令来源，不接受计划、agent 输出或 CLI 临时覆盖。策略文件摘要在 `init` 时绑定；argv
变化属于策略漂移。验证器复制当前工作区全部已跟踪和未忽略未跟踪输入，但故意不复制目标输出，防止 no-op 生成器
借用现有文件通过。生成后逐字节比对当前工作区输出，并把输入摘要、输出 SHA-256、命令、超时与失败分类写入 ignored
evidence。当前 schema 使用固定 120 秒生成超时，不提供运行时放宽字段。

## HARNESS_HOST.json

顶层字段固定为：

- `version`
- `activePlan`
- `deliveryManifest`
- `deliverySyncPaths`
- `expectedRepository`
- `repositoryAttestation`
- `ledger`
- `secretPolicy`
- `fixture`
- `documentation`

`activePlan` 与 `fixture.planPath` 当前必须位于 `docs/superpowers/plans/`。`secretPolicy.patterns` 指定秘密候选路径，`allowlist` 只能做窄范围模板豁免，不能放行真实配置。`documentation.statusMarkerPaths` 列出需要与交付状态一致的宿主文档。

`deliverySyncPaths` 是实现证据建立后仍允许提交的最小精确路径清单，不支持 glob。它必须包含 active plan、delivery manifest、ledger 和全部状态文档；额外路径只能是 `docs/` 或 `reviews/` 下预先声明的 Markdown 审查报告。源码（包括 `src/` 下的 Markdown）、运行配置、依赖文件以及任何未列路径都不能加入同步阶段。`check_docs` 要求 `implementationCommit` 是当前 `HEAD` 的祖先，并逐一检查该范围内每个 descendant commit 相对其每个 parent 的 NUL 分隔路径；rename 按删除与新增检查两端。因此禁止路径即使在后续提交恢复，或只从 merge parent 引入，也会使旧 delivery evidence 失效。

`expectedRepository` 使用精确的 GitHub `OWNER/REPOSITORY`。`repositoryAttestation` 固定为 provider `github-artifact-attestation`，以 `.github/workflows/*.yml` 或 `.yaml` 的精确 `signerWorkflow` 限定签名工作流，并以完整 `refs/heads/*` 的 `sourceRef` 限定来源分支。`GITHUB_ACTIONS`、`GITHUB_SHA` 和 `GITHUB_REPOSITORY` 都是进程可控输入，不构成身份证明。

可信 repository gate 在每个通过测试的 main push 上使用 `actions/attest` 对该次 HEAD archive 生成 Sigstore-backed artifact attestation。第一次实现 push 可以保持 repository pending；后续只修改 `deliverySyncPaths` 的 commit 才能把 repository 标记 complete。此时 `check_docs` 在临时目录重建 manifest `implementationCommit` 的 archive，再调用 `gh attestation verify`，同时限制 repository、官方 `https://github.com/` signer workflow URL、source digest=`implementationCommit` 和 `sourceRef`。当前 docs descendant HEAD 不需要自己的 attestation。该 workflow job 仅获 `contents: read`、`id-token: write` 与 `attestations: write`；本地无对应 attestation、`gh`、GitHub API 访问、令牌或网络时失败关闭，不得降级为环境检查。测试只 mock `gh` 进程边界并核对 implementation archive digest 与完整参数，不请求真实秘密或外网。

`doctor` 将上述 active plan、delivery manifest、ledger、fixture、fixture plan 和状态文档视为完整宿主契约：路径必须安全、文件必须存在且不得经过 symlink。

## STATE_SCHEMA.json

这是运行状态 wire contract，不是手工状态文件。重要约束包括：

- `runId` 为 UUID，计划和失败指纹为 SHA-256，提交为完整 40 位 SHA。
- `planPath`、`changedPaths` 与 `evidencePath` 为仓库相对路径。
- Gate `passed` 必须同时有退出码 0、起止时间和证据路径。
- 状态结构合法不代表转换合法；转换、HEAD 和必需 Gate 一致性由运行层继续检查。

版本 2 Gate evidence 额外记录 `summaryPath`、`evidenceKey`、`source`、`reused` 与 `diagnosticBytes`。版本 1 状态可读，后续写入规范化为版本 2。

## 摘要、胶囊、遥测与投影

- `GATE_SUMMARY_SCHEMA.json`：固定成功/失败摘要，禁止原始日志字段。
- `CONTEXT_CAPSULE_SCHEMA.json`：稳定前缀、任务增量、来源摘要与总字节预算。
- `TOKEN_REPORT_SCHEMA.json`：只允许内容无关的数值聚合，并单列 reviewer 用量。
- `MEMORY_PROJECTIONS.json`：声明 Vault 相对 note、唯一 marker 与 projection ID；绝对路径只保存在 ignored 的本机配置中。

## PROJECT_MEMORY.md 与 AUTONOMY.md

项目记忆只保存稳定事实、权威入口、技术栈、质量门和维护边界。不要写当前分支、临时端口、一次性错误、运行 ID 或未验证完成度。

自治 SOP 定义准入、质量门、路径规则、失败预算、恢复、人工升级和交付边界。宿主可以收紧规则，不能通过文档放宽核心强制约束。

## HARNESS_DELIVERY.json

交付清单属于宿主集成契约，不是核心运行状态。模板初态固定为 `not_started`、空实现提交、pending evidence/external sync、空报告和 `security`、`dx_ci`、`whole_branch` reviewer 列表；宿主应由交付控制器填入计划步骤、当前实现提交、验证证据、独立复审和外部同步状态。不得复制其他项目的 commit、报告摘要或同步状态。

manifest 不能自引用包含自身的提交，因此 `implementationCommit` 不要求等于 `HEAD`。允许它落后于 `HEAD` 的唯一原因是 `deliverySyncPaths` 中预先列出的文档与审查同步；repository complete 只有在匹配 `repositoryAttestation` policy 的 GitHub 签名 implementation-commit attestation 已发布并通过在线验证后才可达。该证明不表示当前 docs HEAD 自身已签，状态也不能在 manifest、环境或命令输出中预填或伪造。
