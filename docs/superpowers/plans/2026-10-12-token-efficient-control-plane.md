# Token-efficient Control Plane 0.2.0 Plan

**Status:** 已实现并完成本地交付验证；等待 GitHub 分支 CI

## Milestone m1: 外置上下文与状态契约

**Files:**
- Modify: `tools/agent-harness/agent_harness/state.py`
- Create: `tools/agent-harness/agent_harness/context_capsule.py`
- Create: `docs/agent/CONTEXT_CAPSULE_SCHEMA.json`
- Create: `docs/agent/TOKEN_REPORT_SCHEMA.json`

Acceptance: Context Capsule 只包含有界、可追溯的稳定规则、任务增量和脱敏诊断；状态 wire contract 保持 v1 读取兼容。

## Milestone m2: Gate 证据复用与并发去重

**Files:**
- Modify: `tools/agent-harness/agent_harness/gate_runner.py`
- Modify: `tools/agent-harness/agent_harness/run_service.py`
- Create: `tools/agent-harness/agent_harness/evidence_cache.py`
- Create: `tools/agent-harness/agent_harness/gate_lease.py`
- Create: `tools/agent-harness/agent_harness/gate_summary.py`

Acceptance: EvidenceKey 绑定仓库、HEAD、命令、环境、输入和策略；严格 HEAD、发布与生产 Gate 不跨提交复用；相同并发 Gate 共享安全租约。

## Milestone m3: 遥测、知识库与全局规则

**Files:**
- Modify: `tools/agent-harness/agent_harness/cli.py`
- Create: `tools/agent-harness/agent_harness/token_report.py`
- Create: `tools/agent-harness/agent_harness/memory_projection.py`
- Create: `tools/agent-harness/agent_harness/global_policy.py`

Acceptance: Token 报告只包含数值元数据；知识库投影为 marker 管理的单向同步；全局规则安装可检查、可回滚，不覆盖人工内容。

## Milestone m4: GitHub、分发与发布闭环

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `tools/agent-harness/agent_harness/distribution.py`
- Create: `tools/agent-harness/agent_harness/github_evidence.py`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/install.md`
- Modify: `docs/upgrade.md`

Acceptance: distribution format 4 可安装、升级、回滚与卸载；CI 生成、签名并上传脱敏 Gate Summary；完整单元测试、故障注入和治理检查通过。
