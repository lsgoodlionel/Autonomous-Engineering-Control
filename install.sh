#!/bin/sh
set -eu

usage() { printf 'Usage: %s <git-repository>\n' "$0" >&2; exit 2; }
[ "$#" -eq 1 ] || usage
source_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
target=$(CDPATH= cd -- "$1" && pwd -P) || usage
[ -d "$target/.git" ] || { printf 'Target must be a Git repository\n' >&2; exit 2; }
[ ! -e "$target/.agent-harness-install" ] || { printf 'Harness is already installed; use upgrade.sh\n' >&2; exit 3; }
[ ! -e "$target/scripts/agent-harness" ] || { printf 'Target already owns scripts/agent-harness\n' >&2; exit 3; }

install -d "$target/scripts" "$target/tools/agent-harness"
cp "$source_root/scripts/agent-harness" "$target/scripts/agent-harness"
cp -R "$source_root/tools/agent-harness/agent_harness" "$target/tools/agent-harness/agent_harness"
cp "$source_root/tools/agent-harness/run_tests.py" "$target/tools/agent-harness/run_tests.py"
cp -R "$source_root/tools/agent-harness/drills" "$target/tools/agent-harness/drills"
chmod 0755 "$target/scripts/agent-harness"
printf '%s\n' "$(cat "$source_root/VERSION")" > "$target/.agent-harness-install"
printf 'Installed control plane %s. Copy and review templates/host before first run.\n' "$(cat "$source_root/VERSION")"

