# Autonomy Boundary

- Only an approved plan in `docs/superpowers/plans/` may start a run.
- Every milestone must declare exact files and deterministic acceptance gates.
- Secrets, dependency additions, release actions, protected paths and production changes require a human boundary.
- Three repeated failures, five total failure cycles or two no-progress cycles pause execution.
- Raw evidence remains ignored under `var/agent-harness/`; only sanitized summaries may be tracked.
- Generated paths require exact regeneration from bound repository inputs in a disposable workspace before scope binding or gates.
- Harness never merges, pushes, releases or deploys on behalf of a project.
