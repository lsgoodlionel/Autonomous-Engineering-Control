# Autonomous Engineering Control

面向长程自治开发的工程控制平面。它将批准计划、Git 身份、路径策略、质量门、失败预算、脱敏诊断和受控执行组合为可恢复的单 Milestone 状态机。

本仓库提供控制能力，不替代需求评审、代码审查、分支保护、生产审批或发布平台。核心只负责确定性执行与证据；宿主仓库负责业务规则、测试命令、保护路径和交付流程。

## 能力边界

- 核心层：`scripts/agent-harness` 与 `tools/agent-harness/`，提供 CLI、状态机、Gate、Git 约束、故障演练、诊断脱敏和 Token 高效执行。
- 宿主层：由接入项目维护 `AGENTS.md` 和 `docs/agent/`，声明计划、质量门、保护路径、稳定记忆与秘密策略。
- 运行层：`var/agent-harness/` 保存状态、事件、证据和原始日志，必须被 Git 忽略，不进入发布包。

套件不会猜测宿主使用 Node、Java、Docker 或其他工具，也不会自动批准依赖、迁移、认证、生产、推送、合并和发布操作。

## Token 高效执行

- Context Capsule 将稳定规则、任务增量和失败诊断分层，并执行 12 KiB/8 KiB/4 KiB 字节预算。
- Gate Summary 成功时不携带 stdout/stderr；失败只暴露脱敏、去重且有界的诊断。
- EvidenceKey 绑定仓库、HEAD、命令、环境、输入、策略、schema 与 runtime；GateLease 合并相同并发执行。
- Token Telemetry 只汇总数值元数据，implementation 与 reviewer 分开统计，不读取或输出消息正文。
- GitHub 摘要导入同时验证 artifact digest 与 provenance attestation；知识库同步是 marker 管理的单向投影。

操作口径与命令见 [Token 高效工程手册](docs/agent/TOKEN_EFFICIENCY.md)。

## 环境要求

- Git；安装接受已有提交的主检出目录或 linked worktree，自治任务只在独立 linked worktree 中运行。
- Python 3.11、3.12、3.13 或 3.14；Ubuntu 与 macOS 的版本矩阵由 CI 验证，核心仅依赖 Python 标准库。
- 宿主 Gate 所需的其他工具由宿主自行安装、锁定和验证。
- 自动执行器为可选能力；未安装、未认证或权限不足时应安全暂停。

## 快速接入

1. 阅读 [架构与边界](docs/architecture.md) 和 [安装指南](docs/install.md)。
2. 运行 `./install.sh <目标仓库>`；安装器只补充缺失宿主模板，不覆盖已有宿主文件，并按 [宿主接入](docs/host-integration.md) 完成替换。
3. 为运行目录加入忽略规则：`/var/agent-harness/`。
4. 在独立 worktree 中执行环境检查：

```sh
scripts/agent-harness doctor --json
```

5. 以已批准计划初始化单个 Milestone：

```sh
scripts/agent-harness init \
  --plan docs/superpowers/plans/approved-plan.md \
  --milestone milestone-1
```

6. 按 `next` 输出推进，并在当前 HEAD 上运行必需 Gate：

```sh
scripts/agent-harness next --run-id <run-id> --json
scripts/agent-harness gate --run-id <run-id>
scripts/agent-harness finalize --run-id <run-id>
```

完整最小结构见 [examples/minimal](examples/minimal/README.md)。恢复、暂停与证据处理见 [运行手册](docs/operations.md)。

## 安全原则

- 配置失败关闭；未知字段、路径逃逸、符号链接逃逸和歧义命令均拒绝。
- 安装、升级和卸载对原始目标绝对路径逐组件 no-follow，并在每次 root open 复核 repository inode；versioned JSON manifest 绑定套件文件的路径、模式、SHA-256 与已登记文件集合。replace/unlink 通过同父目录 quarantine rename 验证 descriptor identity；因 POSIX 没有 inode-bound unlink，已验证的随机私有项保留并报告，绝不冒险删除并发换入的宿主文件。
- Gate 使用参数数组，不把计划、日志或模型输出拼接为 Shell 命令。
- `generated` 路径只接受策略中登记的固定 argv；Harness 在临时隔离树中从当前工作区的绑定输入重跑生成器，输出字节一致且没有越界仓库写入后才允许进入 Gate。
- 同一失败指纹最多自动修复 3 次；单 Milestone 最多 5 个失败周期；连续 2 轮无进展即暂停。
- HEAD 改变后旧 Gate 证据失效；只有当前 HEAD 的必需 Gate 全部通过才可完成。
- delivery 同步逐 commit/parent 检查 `implementationCommit..HEAD` 路径历史；repository complete 只验证 GitHub Actions 为 manifest 指定的真实实现提交生成的签名 artifact attestation，后续 HEAD 只能包含 allowlist 内的文档同步，本地环境变量不能充当身份。
- 原始日志留在忽略目录；提交材料只包含经过脱敏的最小证据。

安全边界与威胁模型见 [安全模型](docs/security-model.md)，漏洞报告方式见 [SECURITY.md](SECURITY.md)。

## 文档

- [架构与边界](docs/architecture.md)
- [安装指南](docs/install.md)
- [宿主接入](docs/host-integration.md)
- [配置参考](docs/configuration-reference.md)
- [Token 高效工程手册](docs/agent/TOKEN_EFFICIENCY.md)
- [运行与恢复](docs/operations.md)
- [安全模型](docs/security-model.md)
- [升级](docs/upgrade.md)
- [卸载](docs/uninstall.md)
- [Release](docs/release.md)

## 版本与许可证

当前版本见 [VERSION](VERSION)，变更记录见 [CHANGELOG.md](CHANGELOG.md)。许可证尚待仓库所有者选择，因此当前仓库不创建 `LICENSE`，也不默认授予复制、分发或再许可权；正式公开发布前必须完成许可证决策。
