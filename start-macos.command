#!/bin/sh
set -eu
exec sh "$(dirname "$0")/docs/bridge/start-macos.command" "$@"
