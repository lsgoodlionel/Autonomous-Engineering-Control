# 最小宿主示例

这是通用接入结构示例，不代表任何真实项目的交付状态。使用时把本目录复制到临时 Git 仓库，再把套件核心的 `scripts/` 与 `tools/agent-harness/` 放入同一仓库。

示例只包含一个标准库单元测试、一个文本 fixture、通用路径策略和批准计划。先提交全部文件，再从该仓库创建独立 worktree并执行：

```sh
scripts/agent-harness doctor --json
scripts/agent-harness init \
  --plan docs/superpowers/plans/approved-plan.md \
  --milestone milestone-1
```

`doctor` 还会根据当前核心版本检查必要配置与受控 Python。运行时需要 Python 3.11-3.14。
宿主若增加 generated 路径，应使用配置参考中的参数数组形态；Harness 会在临时树重跑并绑定输入与输出摘要。
