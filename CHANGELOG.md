# 变更记录

本项目遵循语义化版本。正式 Release 日期在发布时填写。

## [0.2.0] - Unreleased

### Added

- Context Capsule、Gate Summary、EvidenceKey、GateLease 和隐私安全 Token Telemetry。
- marker 管理的单向知识库投影、可复用全局 Token 规则安装器和 strict zero-skip unittest runner。
- GitHub Gate 摘要的 artifact digest 与 provenance attestation 双重验证。

### Changed

- distribution manifest 升级为 format 4，安装与升级会携带全部 Token 高效 runtime、schema、模板和宿主配置。
- 状态 wire contract 写入版本 2，同时保留严格版本 1 读取兼容。
- Gate Matrix 版本 2 支持执行层、复用策略、输入模式和摘要格式；版本 1 保持安全的 HEAD-only 默认值。
- 成功 Gate 不再向 Agent 暴露 stdout/stderr，失败诊断限制为脱敏有界摘要。
- strict zero-skip unittest runner 使用独立的 discovery loader，避免继承外层测试运行器的根目录状态。

### Security

- EvidenceKey 绑定策略、schema、Harness 实现、runtime 与文件模式；symlink 输入和不确定 runtime 均失败关闭。
- 过期租约只有在完成证据无效且本机 owner PID 不存活时才允许接管。
- 相同 GitHub workflow 的摘要没有匹配 attestation 时拒绝导入。

## [0.1.0] - Unreleased

### Added

- 自治工程 CLI、状态机、质量门、Git 约束、诊断脱敏与受控执行核心。
- Python 3.11-3.14 运行边界和独立 worktree 约束。
- 通用宿主模板、最小接入示例及安装、升级、卸载、安全和 Release 文档。
- 基于路径、模式和 SHA-256 的安装 ownership manifest，以及 linked worktree、完整 host seed 和 symlink 越界回归测试。
- generated 路径的隔离重生成验证、输入/输出摘要绑定、越界写入检测和结构化失败 evidence；distribution manifest format 3 登记新增 verifier runtime，同时保留 format 1/2 的历史精确文件集合。

### Changed

- `doctor` 验证 `HARNESS_HOST.json` 引用的计划、delivery、ledger、fixture 与状态文档。
- portable CI 覆盖 Ubuntu/macOS × Python 3.11-3.14，并实际校验 minimal delivery 初态。
- macOS Python 信任根收窄到 hardened hosted toolcache 或严格权限的 uv runtime；默认 Homebrew prefix 不受支持。
- delivery evidence 仅允许在 implementation commit 后继续最小文档/审查同步，任何后续源码、配置或未列路径提交都会被 `check_docs` 拒绝。
- 升级改为已验证备份支持的套件级事务；运行时文件或 manifest 写入失败会自动恢复完整旧套件并报告脱敏恢复结果。
- distribution 生命周期绑定 checksum/mode 校验时的 descriptor identity，拒绝校验后普通文件替换竞态，并对原始 target 绝对路径逐组件 no-follow。
- 支持从 `4727ca9` 的 `0.1.0` 纯文本安装 marker 经历史哈希校验迁移；JSON manifest 按自身 versioned file-set schema 校验，允许新 format 合法增删 owned files。
- delivery 同步改为逐 descendant commit、逐 parent 的 NUL-safe 路径历史校验；repository complete 改由限定 repository/workflow 的 GitHub signed implementation-commit artifact attestation 证明，后续仅允许预声明文档同步，本地环境变量不再被信任。
- distribution 将 validated repository root identity 贯穿全部操作；install rollback 保存创建时 identity，replace/unlink 采用同父目录 quarantine rename，并保留随机 private entry，避免 POSIX identity-unbound unlink 误删并发换入的宿主文件。
- generated 路径不再无条件拒绝；只有策略绑定的固定 argv 在临时输入树中重跑并精确复现当前输出后，才允许 scope bind 和 Gate，`deny`、`approval_required` 与普通 `review_required` 语义保持不变。
- GitHub Actions 的 Python 信任链在 Linux 上直接硬化 hosted toolcache；macOS 在执行仓库代码前以 runner 的受控 `sudo` 收紧 root-owned setup-python runtime，再由 Harness 重新验证原始解释器身份。

### Known limitations

- 不提供常驻队列、Web 控制台或生产部署执行器。
- 宿主质量门、审批和外部交付同步仍由接入项目负责。
- 许可证待仓库所有者选择，`LICENSE` 尚未创建。
