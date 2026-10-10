# 卸载指南

仓库提供基于 ownership manifest 的 `uninstall.sh`。卸载严格区分套件拥有文件、宿主策略和运行证据。

## 卸载前

1. 暂停所有运行并确认没有执行器、Gate 或子进程仍在工作。
2. 记录套件版本、当前分支、HEAD、未完成 Milestone 和恢复责任人。
3. 按组织策略备份 `var/agent-harness/`，其中可能含敏感日志，不应提交。
4. 使用与安装版本兼容的套件运行 `./uninstall.sh <目标仓库>`；禁止手工按目录名称猜测并批量删除。

## 文件归属

manifest 可以删除的套件核心：

- `scripts/agent-harness`
- `tools/agent-harness/agent_harness/`、`tools/agent-harness/drills/` 与 `tools/agent-harness/run_tests.py`

卸载在发生任何删除前验证全部 owned entry 的安全相对路径、普通文件类型、模式和 SHA-256。任一文件缺失、被修改或任一路径组件为 symlink 时整体拒绝；成功后只删除逐项验证过的文件和 manifest，并只清理空目录。

模式与摘要从同一打开的 descriptor 读取。后续 unlink 先在同一 parent descriptor 下把目录项 rename 到随机 quarantine，确认被移动文件仍匹配 `(st_dev, st_ino)` 后才删除；校验后在 rename syscall 边界换入的普通文件会被恢复到原路径，无法恢复时保留在 quarantine 并失败关闭。repository root identity 也会在每次打开时复核。历史 JSON manifest 按自身 format 的精确 file-set schema 校验，不能由当前版本文件集合决定其合法性。

默认保留：

- 宿主 `AGENTS.md`
- `docs/agent/` 中的项目规则、记忆和交付记录
- 已批准计划、审查报告和按保留策略保存的运行历史
- 宿主新增的测试、业务代码与 `.gitignore` 其他规则
- 安装器 seed 的宿主计划、delivery、ledger、fixture 和状态文档

## 验证

- 搜索并移除指向已删除核心入口的 CI、文档和脚本引用。
- 确认没有破坏宿主原有测试命令和分支保护。
- 审查 Git diff，确保只删除安装清单拥有的文件。
- 若未来可能恢复，记录最后版本、配置版本和备份位置，不记录秘密值。

卸载不撤销曾暴露的凭据，也不自动删除外部 CI secret、仓库权限或云端制品；这些资源需由各自所有者单独处理。
