# 升级指南

## 原则

- 升级必须从已校验的正式 Release 进行，不直接覆盖运行中的文件。
- 核心代码与宿主配置分开升级；默认保留宿主 `AGENTS.md`、`docs/agent/` 和运行历史。
- 配置版本、状态 Schema 或 CLI 稳定字段变化时，必须提供迁移说明和回滚路径。

## 步骤

1. 暂停所有运行，记录 run ID、分支、HEAD 和未完成 Milestone。
2. 确认工作区归属，备份套件拥有文件、宿主配置和需要保留的脱敏证据索引。
3. 下载 Release 制品及 `SHA256SUMS`，独立验证校验和和签名信息。
4. 在临时仓库运行安装、`doctor`、完整测试、fake drills 和卸载 smoke。
5. 在专用升级分支运行 `./upgrade.sh <目标仓库>`。升级先按旧 manifest 自身的 format/version 验证精确文件集合，再用同一 descriptor 校验每个旧文件的模式和 SHA-256；之后备份并复核完整旧套件（包括 ownership manifest），才开始替换。
6. 对照 `CHANGELOG.md` 与配置迁移说明手工合并模板差异。
7. 运行 `doctor`、相关 Gate 和 `git diff --check`，经 Review 后提交。
8. 对暂停运行重新核对计划与 HEAD；不兼容时创建新运行。

## 回滚

升级是套件级事务。任一核心文件替换、新旧文件增删或 manifest 写入失败时，升级器会自动从已验证备份恢复完整旧套件并复核结果；错误只报告仓库相对的 `.agent-harness-backups/`、随机隔离文件位置和“成功/失败”恢复结果，不回显底层异常、令牌或绝对宿主路径。自动恢复成功后可以修复故障原因并重试；恢复失败时停止操作，保留备份并人工恢复后运行 `doctor`。宿主 seed、配置和运行历史不会由升级覆盖。不要删除运行历史来绕过状态不兼容。

从提交 `4727ca9` 安装的 `0.1.0` 套件使用纯文本 `.agent-harness-install`。升级器只在 marker 内容、历史 owned-file set、每个文件的 SHA-256 和模式都与已登记 baseline 一致时迁移；成功后进入 versioned JSON manifest，漂移时保留旧套件并拒绝迁移。新 format 可以登记不同的 owned-file set，因此合法新增和删除由版本化 schema 决定，而不是拿旧 manifest 与当前常量直接比较。
format 3 增加 generated verifier runtime；format 1/2 的历史文件集合保持不变，旧安装仍按其原始 schema 验证后再升级。

校验得到的 repository root `(st_dev, st_ino)` 会随 validated root 贯穿全部读写、备份与回滚；每次打开 root 都必须匹配，路径上的目录被普通目录替换也会失败关闭。目标仓库的原始绝对路径仍逐组件 no-follow，不能通过 repository root 或祖先 symlink 隐藏真实路径。

owned file 的 checksum/mode 与 `(st_dev, st_ino)` 会贯穿 replace/unlink。操作先在同一 parent descriptor 下将当前目录项 rename 到随机 quarantine，再验证被移动 inode；匹配后才以 no-clobber hard link 发布临时文件。POSIX 不提供按 inode 条件删除目录项的 syscall，因此 temporary/quarantine 在验证后仍以随机名保留，不能用 `stat -> unlink` 假装原子删除；事务输出会报告其仓库相对位置。若 syscall 边界发生普通文件换入，升级器恢复原路径或失败关闭并保留隔离文件，绝不覆盖或删除 host replacement；回滚遵守同一规则。

## 兼容性

补丁版本不得破坏同一配置版本。次版本可增加向后兼容能力。主版本可变更 Schema 或宿主契约，但必须提供明确迁移工具或人工步骤。Python 支持范围变化属于兼容性变更，应在发布说明中突出标记。
