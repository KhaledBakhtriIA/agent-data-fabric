#!/usr/bin/env sh
# QA Reliability Intelligence - console launcher (macOS / Linux).
# Run ./console.sh to open the interactive console. No VS Code needed.
cd "$(dirname "$0")" || exit 1
exec python3 -m reliability
