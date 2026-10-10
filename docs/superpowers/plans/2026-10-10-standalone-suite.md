# Standalone Control Plane Plan

**Status:** 已确认

## Milestone m1: Portable distribution

**Files:**
- Modify: `scripts/agent-harness`
- Modify: `tools/agent-harness/agent_harness/doctor.py`
- Modify: `tools/agent-harness/tests/test_governance.py`
- Create: `.github/workflows/ci.yml`
- Create: `docs/agent/GATE_MATRIX.yaml`
- Create: `docs/agent/PROTECTED_PATHS.yaml`
- Create: `docs/agent/STATE_SCHEMA.json`
- Create: `docs/agent/AUTONOMY.md`
- Create: `docs/agent/PROJECT_MEMORY.md`
- Create: `install.sh`
- Create: `upgrade.sh`
- Create: `uninstall.sh`

Acceptance: the standalone repository contains no host-product coupling, all non-Docker tests and deterministic drills pass, the pinned Linux integration suite passes with zero skips, and the repository can install, upgrade and uninstall a disposable host fixture without deleting host policy or run history.

