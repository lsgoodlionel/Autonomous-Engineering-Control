# Token-efficient Control Plane 0.2.0 Verification

日期：2026-10-12

分支：`feat/token-efficient-control-plane`

基线：`5915164`

## 结论

0.2.0 的 Context Capsule、Gate Summary、EvidenceKey/GateLease、Token Telemetry、知识库投影、全局规则安装、GitHub evidence 和 distribution format 4 已完成本地实现与验证。验证不替代 GitHub `main` push 的 provenance attestation，也不表示已创建正式 Release。

## 证据

| 检查 | 结果 |
| --- | --- |
| 非 Docker 完整套件 | PASS，508 tests，zero skip，364.743 秒 |
| 固定 digest Linux Docker fixture | PASS，9 tests，zero skip，7.800 秒 |
| Token Telemetry 最终聚焦回归 | PASS，6 tests，0.011 秒 |
| 故障注入 | PASS，50 tests；包含超时、状态中断、历史漂移、秘密脱敏和便携副本 smoke |
| distribution lifecycle | PASS；install、format 1-3 upgrade、format 4、rollback 和 uninstall 均在完整套件中通过 |
| diff hygiene | PASS，`git diff --check` 无输出 |
| 产品耦合/秘密扫描 | PASS，通用 runtime 与模板未发现 Survey/LimeSurvey 名称或凭据形态 |

## 独立审查

限定安全审查首轮发现一个 Important：只按 `cwd` 前缀归属 Token session 时，宿主仓库内嵌套的独立 Git 仓库可能被误计。实现已收紧为“session `cwd` 最近 Git 根必须等于报告项目根”，并要求报告根本身是 Git 根；新增窗口事件与嵌套仓库回归测试。复审确认该问题关闭，未发现新的 Critical/Important。

## 外部边界

- GitHub CI 的 Gate Summary 只在 `main` push 且 unit/Linux jobs 成功后生成，再由 GitHub artifact attestation 签名并上传。
- 正式 Release、tag、Release asset、SBOM 和许可证选择不属于本次分支推送；不得把功能分支推送写成正式发布。
- Token 报告只处理数值 token metadata；不会把 prompt、message、source payload 或原始日志写入报告。

## 真实宿主验证：离线计时器

验证使用 GitHub 分支 `feat/token-efficient-control-plane` 的提交
`909cb0b93c41dea5f946576c201442b9d7e6456d`，宿主基线为离线计时器提交
`33422312173ce90b03e16d7940bd7b61b89809c5`。全部安装、升级和卸载操作均在一次性 linked worktree
完成，没有修改、合并或推送原计时器仓库。

| 检查 | 结果 |
| --- | --- |
| GitHub 分支身份 | PASS；远端 checkout HEAD 与预期提交一致 |
| 安装 | PASS；安装 `0.2.0`、manifest format 4，宿主文件未覆盖，`git diff --check` 通过 |
| `doctor` | PASS；宿主配置完成后 22 项 ok、4 项 optional warning、0 error |
| 真实产品 Gate | PASS；`node --test` 为 42/42，0 fail |
| Context Capsule | PASS；2,215 bytes，5 个有行号和 digest 的来源片段，低于 24,576-byte 上限 |
| EvidenceKey 复用 | PASS；相同 HEAD、命令、环境、输入和 policy 下第二轮两个 Gate 均 `source=reused` |
| Gate Summary 数据最小化 | PASS；缓存 record + summary 共 706 bytes，不包含 stdout/stderr 原文 |
| 同版本升级 | PARTIAL；内容和测试保持正确，但不是 no-op，会创建备份、quarantine 和 private entries |
| 卸载 | PASS；owned runtime 和 manifest 移除，宿主策略、用户计划、产品代码、备份及历史保留；卸载后 42/42 通过 |
| 产品质量保持 | PASS；安装前、升级后和卸载后均为 42/42，0 fail |

安装器为 no-clobber 和 inode 身份保护保留了 45 个 private entries。同版本升级又创建 56 个备份文件及
quarantine/private entries，卸载再保留 28 个 quarantine entries。宿主需要显式忽略
`var/agent-harness/`、`.agent-harness-backups/`、`**/.*.agent-harness-temporary-*` 和
`**/.*.agent-harness-quarantine-*`，否则生命周期操作会使工作区显示未跟踪文件。

真实 Node Gate 依靠退出码正确判定通过，但 Gate Summary 的保守计数器没有识别 Node 24 `node --test`
输出，记录为 `total=0`、`passed=0`，而独立命令的实际结果是 42/42。`doctor` 的受控 PATH 也没有发现
NVM Node，因此即使 Gate 使用已审核绝对路径成功执行，环境报告仍保留 `node` optional warning。这两项不改变
本次质量结论，但需要在后续版本改善遥测精度和 Node runtime discovery。

## Token 观察分类

| 分类 | 观测 | 可作出的结论 |
| --- | --- | --- |
| `account-level` | Codex 账户 7 日窗口 `usedPercent=41%` | 只描述账户背景；不能归因到计时器或 AEC，不能用于计算节省率 |
| `source-payload` | 一次 `read_thread(turnLimit=10, includeOutputs=true)` 报告源响应约 762,495 tokens 并截断 | 证明全量历史与工具输出读取存在高成本反例；不是账单 token |
| `observed` | 目标线程 session 文件 9,459,550 bytes、2,986 lines；完整计划 18,570 bytes；AEC Capsule 2,215 bytes；复用 Gate record + summary 706 bytes | AEC 路径显著缩小可见源载荷；只能声明 byte-level source reduction，不能换算为实际 token 节省 |
| `unavailable` | 当前任务精确 input、cached input、output、reasoning 和逐线程总量 | 缺失不是 0；不得编造 A/B Token 比例 |

有界 A/B 使用同一已批准的 Task 5 验收目标。传统组的可观测代理为 9.46 MB session 历史加 18.57 KB
完整计划；AEC 组为 2.22 KB Capsule 加 706 bytes 复用证据。两组质量基线都以同一 `node --test`
42/42 为准。这个实验支持“源上下文载荷减少且质量未下降”，不支持“实际 Token 已按某百分比下降”。

## 长线程反例与缺口

当前 AEC 会约束生成给 Codex 的 Capsule、失败诊断和 Gate 摘要，但没有包装或校验 Codex 桌面端的
`read_thread` 调用。因此它不能阻止调用方使用 `includeOutputs=true`、过大的 `turnLimit` 或无游标重复读取。
762,495-token 级源响应发生在控制平面之外，现有 0.2.0 只能减少后续转发，不能从源头防止。

最小后续控制策略：

1. 默认 `includeOutputs=false`，初次 `turnLimit<=4`，仅在缺失指定证据时按单项打开输出。
2. 后续读取必须使用 `afterCursor`；相同 thread/cursor/options fingerprint 直接去重。
3. 为单项输出、单次响应和累计 source payload 建立独立字节预算，超限只保留数值元数据与有界摘要。
4. Token report 在没有可归属 session 时必须返回显式 availability，不能用全 0 表示 unavailable。
5. A/B 报告分开保存 billed token、tool source payload、Capsule bytes、compaction count 与质量 Gate，禁止跨口径计算节省率。

## 分项判定

| 结论 | 判定 | 依据 |
| --- | --- | --- |
| 控制平面已运行 | PASS | 真实 GitHub checkout、安装、doctor、Capsule、Gate、reuse、升级、卸载均已执行 |
| Token 遥测可观测 | PARTIAL | 数值报告无 payload 泄露，但零 session 与 unavailable 不可区分，且 Gate 指标尚未聚合进 report |
| Token 明确下降 | FAIL（未证明） | 精确逐线程 token 不可用；只有 source bytes 与截断响应代理 |
| 开发质量未下降 | PASS | 生命周期三个检查点均为计时器 42/42，0 fail |

整体结论为 **PARTIAL**。AEC 0.2.0 已能作为真实宿主控制平面运行，并有效约束它自己产生的上下文与证据；
在增加线程读取预算/游标策略和 telemetry availability 之前，不能宣称它已经从源头解决长线程 Token 浪费。
