#!/bin/sh
set -eu

usage() { printf 'Usage: %s <git-repository>\n' "$0" >&2; exit 2; }
[ "$#" -eq 1 ] || usage
source_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
target=$(CDPATH= cd -- "$1" && pwd -P) || usage
[ -f "$target/.agent-harness-install" ] || { printf 'Harness is not installed\n' >&2; exit 3; }
backup="$target/.agent-harness-backups/$(date -u +%Y%m%dT%H%M%SZ)"
install -d "$backup/scripts" "$backup/tools/agent-harness"
cp "$target/scripts/agent-harness" "$backup/scripts/agent-harness"
cp -R "$target/tools/agent-harness/agent_harness" "$backup/tools/agent-harness/agent_harness"
cp "$target/tools/agent-harness/run_tests.py" "$backup/tools/agent-harness/run_tests.py"
cp -R "$target/tools/agent-harness/drills" "$backup/tools/agent-harness/drills"
cp "$source_root/scripts/agent-harness" "$target/scripts/agent-harness"
cp -R "$source_root/tools/agent-harness/agent_harness/." "$target/tools/agent-harness/agent_harness/"
cp "$source_root/tools/agent-harness/run_tests.py" "$target/tools/agent-harness/run_tests.py"
cp -R "$source_root/tools/agent-harness/drills/." "$target/tools/agent-harness/drills/"
chmod 0755 "$target/scripts/agent-harness"
printf '%s\n' "$(cat "$source_root/VERSION")" > "$target/.agent-harness-install"
printf 'Upgraded control plane to %s; backup: %s\n' "$(cat "$source_root/VERSION")" "$backup"

