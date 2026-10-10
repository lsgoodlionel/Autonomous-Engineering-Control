# 安装指南

仓库提供本地、可审查的 `install.sh`；不要把安装命令包装为无审查的远程管道。

## 前置条件

- Git 可用，目标项目已初始化且有至少一个提交；unborn repository 会被拒绝。
- Python 版本为 3.11、3.12、3.13 或 3.14。
- 自治执行使用独立 Git worktree，而不是主检出目录。
- 已确定宿主的测试命令、保护路径、批准计划和人工升级联系人。

## 接入步骤

1. 在目标项目建立专用分支；目标可以是主检出目录或 linked worktree。
2. 从经过校验的 Release 制品运行 `./install.sh <目标仓库>`。
3. 安装器逐级拒绝 `scripts/`、`tools/`、manifest 和宿主 seed 路径中的 symlink；任何已有核心目标文件都会使安装失败。
4. 安装器生成 `.agent-harness-install.json`，记录每个套件拥有文件的路径、模式和 SHA-256；缺失的宿主模板、active plan、delivery、ledger 与 smoke fixture 会完整 seed，已有普通宿主文件保持不变。
5. 按 [宿主接入](host-integration.md) 替换占位内容，并创建已批准计划。
6. 将 `/var/agent-harness/` 加入宿主 `.gitignore`。
7. 先提交并审查核心与宿主策略，再运行 `doctor`。核心会校验已跟踪 wrapper，并检查 `HARNESS_HOST.json` 引用的全部文件。

## 验证

```sh
scripts/agent-harness --python --version
scripts/agent-harness doctor --json
scripts/agent-harness --python \
  -m unittest discover -s tools/agent-harness/tests -p 'test_*.py' -v
```

版本输出必须落在 3.11-3.14。`doctor` 的 error 必须全部处理；warning 需判断是否与当前 Milestone 有关。未安装的可选工具不应被伪造为可用。

macOS 使用 CI `setup-python` 的 hardened hosted toolcache 或用户私有且逐级不可 group/other-write 的 uv runtime。默认 Homebrew prefix 的 `bin` 通常可被 group 写入，因此不作为 Harness Python 信任根；不要通过放宽权限检查来启用它。

## 独立 worktree

使用仓库约定创建功能分支和 worktree，例如：

```sh
git worktree add -b feat/example ../project-example-worktree main
```

worktree 路径由操作者选择，不应写入通用模板或永久记忆。完成后只能在确认无未提交改动、无运行任务且证据已按策略保存后清理。

## 失败处理

- wrapper 找不到受支持 Python：安装受支持版本并重新运行，不修改版本检查。
- `doctor` 报非独立 worktree：迁移任务到独立 worktree，不绕过检查。
- 配置无效：按严格 JSON 语法修复，禁止引入隐式 YAML 行为。
- 核心文件与 HEAD 不一致：先审查并提交预期变更，再重新验证。
