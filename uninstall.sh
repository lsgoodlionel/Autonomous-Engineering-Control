#!/bin/sh
set -eu

usage() { printf 'Usage: %s <git-repository>\n' "$0" >&2; exit 2; }
[ "$#" -eq 1 ] || usage
source_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
case "$1" in
    /*) target=$1 ;;
    *) target=$(pwd -P)/$1 ;;
esac
cd "$source_root"
exec scripts/agent-harness --python -m agent_harness.distribution uninstall "$target"
