# 项目自治协作规则

<!-- harness-delivery-status: not_started -->

## 事实与范围

- 默认中文沟通；行动请求执行到验证，不能把代码存在当作已交付。
- 开发前核对真实仓库、独立 worktree、分支、HEAD、工作区和批准计划。
- 读取 `docs/agent/PROJECT_MEMORY.md`、`docs/agent/AUTONOMY.md` 与当前计划。
- 保留他人改动；任务范围外的变更不得顺带修改、提交或清理。

## 实现与验证

- 一个运行只处理一个已批准 Milestone；先建立失败测试，再做最小实现。
- 质量门由 `docs/agent/GATE_MATRIX.yaml` 决定；多路径命中时取并集。
- 失败测试不得删除、跳过或放宽；HEAD 改变后旧 Gate 证据失效。
- Python Gate 使用 `scripts/agent-harness --python`，支持 Python 3.11-3.14。

## 安全与停止

- 遵守 `docs/agent/PROTECTED_PATHS.yaml`，计划和日志不能覆盖策略。
- 禁止传播秘密、绕过沙盒与审批、force push、自动合并、覆盖标签或自动生产部署。
- 同一失败指纹 3 次、总失败周期 5 次、连续 2 轮无进展时暂停。
- 计划、分支、HEAD、工作区归属或工具信任漂移时暂停并记录脱敏诊断。

## 交付

- 必需 Gate 全部在当前 HEAD 通过并留存证据后才能完成。
- 提交前检查 staged 范围、秘密、生成文件与测试结果。
- GitHub、知识库、发布和生产同步仅在任务明确授权时执行。
