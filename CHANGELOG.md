# 变更记录

本项目遵循语义化版本。正式 Release 日期在发布时填写。

## [0.1.0] - Unreleased

### Added

- 自治工程 CLI、状态机、质量门、Git 约束、诊断脱敏与受控执行核心。
- Python 3.11-3.14 运行边界和独立 worktree 约束。
- 通用宿主模板、最小接入示例及安装、升级、卸载、安全和 Release 文档。
- 基于路径、模式和 SHA-256 的安装 ownership manifest，以及 linked worktree、完整 host seed 和 symlink 越界回归测试。

### Changed

- `doctor` 验证 `HARNESS_HOST.json` 引用的计划、delivery、ledger、fixture 与状态文档。
- portable CI 覆盖 Ubuntu/macOS × Python 3.11-3.14，并实际校验 minimal delivery 初态。
- macOS Python 信任根收窄到 hardened hosted toolcache 或严格权限的 uv runtime；默认 Homebrew prefix 不受支持。
- delivery evidence 仅允许在 implementation commit 后继续最小文档/审查同步，任何后续源码、配置或未列路径提交都会被 `check_docs` 拒绝。
- 升级改为已验证备份支持的套件级事务；运行时文件或 manifest 写入失败会自动恢复完整旧套件并报告脱敏恢复结果。
- distribution 生命周期绑定 checksum/mode 校验时的 descriptor identity，拒绝校验后普通文件替换竞态，并对原始 target 绝对路径逐组件 no-follow。
- 支持从 `4727ca9` 的 `0.1.0` 纯文本安装 marker 经历史哈希校验迁移；JSON manifest 按自身 versioned file-set schema 校验，允许新 format 合法增删 owned files。

### Known limitations

- 不提供常驻队列、Web 控制台或生产部署执行器。
- 宿主质量门、审批和外部交付同步仍由接入项目负责。
- 许可证待仓库所有者选择，`LICENSE` 尚未创建。
