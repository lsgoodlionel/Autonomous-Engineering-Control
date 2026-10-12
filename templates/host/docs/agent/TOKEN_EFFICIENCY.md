# Token 高效工程操作手册

本项目使用 Context Capsule、Gate Summary、EvidenceKey、GateLease、内容无关 Token Telemetry 与单向知识库投影减少重复模型上下文，同时保持所有质量门和人工审批标准。

## 规则

1. 新 Agent 默认只读取 Context Capsule 与任务增量，缺少事实时按来源定点读取。
2. 成功 Gate 不进入模型日志；失败只暴露脱敏、去重且不超过 4 KiB 的诊断。
3. 证据复用必须绑定仓库、HEAD、命令、环境、输入、策略和 runtime；不确定时真实重跑。
4. 严格 HEAD、发布、生产和安全验收不得跨提交复用或降级。
5. Token 遥测只保留数值聚合，不保存 Prompt、消息、源码、秘密或原始日志。

## 命令

```sh
scripts/agent-harness token-report --since <RFC3339> --until <RFC3339> --format json
scripts/agent-harness configure-memory --vault <absolute-local-path>
scripts/agent-harness memory-status --json
scripts/agent-harness sync-memory --run-id <uuid> --json
scripts/agent-harness install-global-policy --codex-home "$HOME/.codex" --dry-run
```

知识库只接收 marker 管理的单向投影；冲突时失败关闭，仓库与 Harness 始终是事实源。
