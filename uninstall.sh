#!/bin/sh
set -eu

usage() { printf 'Usage: %s <git-repository>\n' "$0" >&2; exit 2; }
[ "$#" -eq 1 ] || usage
target=$(CDPATH= cd -- "$1" && pwd -P) || usage
[ -f "$target/.agent-harness-install" ] || { printf 'Harness is not installed\n' >&2; exit 3; }
rm -f "$target/scripts/agent-harness" "$target/tools/agent-harness/run_tests.py"
rm -rf "$target/tools/agent-harness/agent_harness" "$target/tools/agent-harness/drills"
rm -f "$target/.agent-harness-install"
printf 'Removed runtime files. Host policy, backups and var/agent-harness were preserved.\n'

