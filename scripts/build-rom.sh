#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 /path/to/legally-obtained-baserom.z64 [--skip-model]" >&2
    exit 2
fi

baserom=$1
shift
exec python3 -m oot_trump build-rom --baserom "$baserom" "$@"
